import os
import shutil
import threading
import uuid
import time
from pathlib import Path
from typing import List, Dict, Any

from flask import Flask, request, redirect, url_for, send_file, render_template, abort
from werkzeug.utils import secure_filename

import fitz
from process_pdfs import process_pdf, process_images, ensure_dir


BASE_DIR = Path(__file__).parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
WORD_DIR = OUTPUT_DIR / "word"
EXCEL_DIR = OUTPUT_DIR / "excel"

ensure_dir(UPLOAD_DIR)
ensure_dir(OUTPUT_DIR)
ensure_dir(WORD_DIR)
ensure_dir(EXCEL_DIR)

app = Flask(__name__)


# 简单的内存任务状态存储
TASKS: Dict[str, Dict[str, Any]] = {}


def has_ark_config() -> bool:
    return bool(os.getenv("ARK_API_KEY")) and bool(os.getenv("ARK_BASE_URL"))


@app.route("/")
def index():
    ark_ok = has_ark_config()
    source = os.getenv("ARK_SOURCE", "both")
    return render_template("index.html", ark_ok=ark_ok, source=source)


@app.route("/upload", methods=["POST"])
def upload():
    if not has_ark_config():
        return (
            "缺少 API 配置，请先在终端设置 ARK_API_KEY 与 ARK_BASE_URL（通过火山引擎 Ark 平台访问豆包 API）",
            400,
        )
    files = request.files.getlist("files")
    if not files:
        return ("请至少选择一个 PDF 或图片", 400)

    # 获取识别模式：text（文字识别->Word）或 table（表格提取->Excel）
    extract_mode = request.form.get("mode", "text")

    # 保存到 uploads 并分类
    pdf_paths: List[Path] = []
    image_paths: List[Path] = []
    for f in files:
        if not f.filename:
            continue
        filename = secure_filename(f.filename)
        save_path = UPLOAD_DIR / filename
        f.save(save_path)
        lower = filename.lower()
        if lower.endswith(".pdf"):
            pdf_paths.append(save_path)
        elif any(lower.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".bmp", ".webp"]):
            image_paths.append(save_path)

    created_task_ids: List[str] = []

    # 为每个 PDF 创建任务
    for pdf_path in pdf_paths:
        task_id = uuid.uuid4().hex
        pdf_name = pdf_path.stem

        # 预估计数
        embedded, pages = 0, 0
        source_mode = os.getenv("ARK_SOURCE", "embedded")
        try:
            doc = fitz.open(str(pdf_path))
            for i in range(len(doc)):
                page = doc.load_page(i)
                embedded += len(page.get_images(full=True))
            pages = len(doc)
        except Exception:
            pass

        # 根据模式计算总数
        if source_mode == "both":
            total = embedded + pages
        elif source_mode == "page":
            total = pages
        else:  # embedded
            total = embedded

        TASKS[task_id] = {
            "pdf_name": pdf_name,
            "status": "pending",
            "total": total,
            "done": 0,
            "embedded": embedded,
            "pages": pages,
            "errors": [],
            "control": {"paused": False, "stop": False},
            "mode": extract_mode,  # 记录识别模式
            "start_time": time.time(),  # 记录开始时间
        }

        def _cb_pdf(event: str, data: Dict[str, Any], tid=task_id):
            t = TASKS.get(tid)
            if not t:
                return
            if event == "start":
                t["status"] = "in_progress"
                t["total"] = data.get("total", t["total"]) or 0
                t["embedded"] = data.get("embedded", t["embedded"]) or 0
                t["pages"] = data.get("pages", t["pages"]) or 0
            elif event == "step":
                t["status"] = "in_progress"
                t["done"] = data.get("done", t["done"]) or 0
                err = data.get("error")
                if err:
                    t["errors"].append({"image": data.get("image"), "error": err})
            elif event == "finish":
                t["status"] = "completed"
                t["done"] = data.get("done", t["done"]) or t["total"]

        def _worker_pdf(pdfp=pdf_path, cb=_cb_pdf, mode=extract_mode):
            try:
                def _control():
                    t = TASKS.get(task_id, {})
                    return t.get("control", {})
                process_pdf(
                    pdf_path=pdfp,
                    output_root=OUTPUT_DIR,
                    api_key=os.getenv("ARK_API_KEY"),
                    base_url=os.getenv("ARK_BASE_URL").rstrip("/"),
                    model=os.getenv("ARK_MODEL", "doubao-seed-1-6-vision-250815"),
                    dpi=int(os.getenv("ARK_DPI", "200")),
                    progress_cb=cb,
                    max_workers=int(os.getenv("ARK_WORKERS", "4")),
                    source_mode=os.getenv("ARK_SOURCE", "embedded"),
                    control_getter=_control,
                    extract_mode=mode,  # 传递识别模式
                )
            except Exception as e:
                t = TASKS.get(task_id)
                if t:
                    t["status"] = "failed"
                    t["errors"].append({"error": str(e)})

        threading.Thread(target=_worker_pdf, daemon=True).start()
        created_task_ids.append(task_id)

    # 为图片批次创建一个任务
    if image_paths:
        # 使用原始文件名作为显示名称
        if len(image_paths) == 1:
            # 单个文件：使用文件名（去掉扩展名）
            display_name = image_paths[0].stem
        else:
            # 多个文件：使用第一个文件名 + "等X个文件"
            first_name = image_paths[0].stem
            display_name = f"{first_name}等{len(image_paths)}个文件"
        
        # 内部使用批次ID（用于文件保存，避免文件名冲突和特殊字符问题）
        batch_id = f"images-batch-{uuid.uuid4().hex[:8]}"
        task_id = uuid.uuid4().hex
        TASKS[task_id] = {
            "pdf_name": display_name,  # 显示名称（用户看到的）
            "batch_id": batch_id,      # 内部批次ID（用于保存文件）
            "status": "pending",
            "total": len(image_paths),
            "done": 0,
            "embedded": len(image_paths),
            "pages": 0,
            "errors": [],
            "control": {"paused": False, "stop": False},
            "mode": extract_mode,  # 记录识别模式
            "start_time": time.time(),  # 记录开始时间
        }

        def _cb_imgs(event: str, data: Dict[str, Any], tid=task_id):
            t = TASKS.get(tid)
            if not t:
                return
            if event == "start":
                t["status"] = "in_progress"
                t["total"] = data.get("total", t["total"]) or 0
                t["embedded"] = data.get("embedded", t["embedded"]) or 0
                t["pages"] = data.get("pages", t["pages"]) or 0
            elif event == "step":
                t["status"] = "in_progress"
                t["done"] = data.get("done", t["done"]) or 0
                err = data.get("error")
                if err:
                    t["errors"].append({"image": data.get("image"), "error": err})
            elif event == "finish":
                t["status"] = "completed"
                t["done"] = data.get("done", t["done"]) or t["total"]

        def _worker_images(imgs=image_paths, bname=batch_id, cb=_cb_imgs, mode=extract_mode):
            try:
                def _control():
                    t = TASKS.get(task_id, {})
                    return t.get("control", {})
                process_images(
                    image_paths=imgs,
                    batch_name=bname,  # 使用批次ID保存文件（避免文件名冲突）
                    output_root=OUTPUT_DIR,
                    api_key=os.getenv("ARK_API_KEY"),
                    base_url=os.getenv("ARK_BASE_URL").rstrip("/"),
                    model=os.getenv("ARK_MODEL", "doubao-seed-1-6-vision-250815"),
                    progress_cb=cb,
                    max_workers=int(os.getenv("ARK_WORKERS", "4")),
                    control_getter=_control,
                    extract_mode=mode,  # 传递识别模式
                )
            except Exception as e:
                t = TASKS.get(task_id)
                if t:
                    t["status"] = "failed"
                    t["errors"].append({"error": str(e)})

        threading.Thread(target=_worker_images, daemon=True).start()
        created_task_ids.append(task_id)

    if not created_task_ids:
        return ("未处理任何文件（可能文件名为空或类型不支持）", 400)

    return redirect(url_for("progress", task_id=created_task_ids[0]))


@app.route("/result/<pdf_name>")
def result(pdf_name: str):
    word_file = WORD_DIR / f"{pdf_name}.docx"
    files = [word_file.name] if word_file.exists() else []
    if not files:
        abort(404)
    return render_template(
        "result.html",
        pdf_name=pdf_name,
        files=files,
    )


@app.route("/progress/<task_id>")
def progress(task_id: str):
    t = TASKS.get(task_id)
    if not t:
        abort(404)
    poll_ms = int(os.getenv("ARK_POLL_MS", "10000"))
    mode = t.get("mode", "text")
    return render_template("progress.html", task_id=task_id, t=t, poll_ms=poll_ms, mode=mode)


@app.route("/status/<task_id>")
def status(task_id: str):
    t = TASKS.get(task_id)
    if not t:
        return {"error": "not_found"}, 404
    
    # 计算已用时间（排除暂停时间）
    start_time = t.get("start_time", time.time())
    total_pause_time = t.get("total_pause_time", 0)
    # 如果当前处于暂停状态，也要加上当前暂停的时间
    if t.get("status") == "paused" and "pause_start" in t:
        total_pause_time += time.time() - t["pause_start"]
    elapsed_time = (time.time() - start_time) - total_pause_time
    
    return {
        "task_id": task_id,
        "pdf_name": t.get("pdf_name"),
        "status": t.get("status"),
        "total": t.get("total", 0),
        "done": t.get("done", 0),
        "embedded": t.get("embedded", 0),
        "pages": t.get("pages", 0),
        "errors": t.get("errors", []),
        "control": t.get("control", {}),
        "mode": t.get("mode", "text"),  # 返回识别模式
        "elapsed_time": elapsed_time,  # 返回已用时间（秒）
    }


@app.route("/download/<pdf_name>.zip")
def download_zip(pdf_name: str):
    # 兼容旧路由：如果只有一个 Word，则直接返回该文件
    word_file = WORD_DIR / f"{pdf_name}.docx"
    if word_file.exists():
        return send_file(word_file, as_attachment=True, download_name=f"{word_file.name}")
    abort(404)

@app.route("/download_word/<pdf_name>")
def download_word(pdf_name: str):
    word_file = WORD_DIR / f"{pdf_name}.docx"
    if not word_file.exists():
        abort(404)
    return send_file(word_file, as_attachment=True, download_name=f"{word_file.name}")


@app.route("/download_excel/<pdf_name>")
def download_excel(pdf_name: str):
    excel_file = EXCEL_DIR / f"{pdf_name}.xlsx"
    if not excel_file.exists():
        abort(404)
    return send_file(excel_file, as_attachment=True, download_name=f"{excel_file.name}")


@app.route("/files/<pdf_name>/<path:fname>")
def serve_file(pdf_name: str, fname: str):
    # 仅开放 output 目录的文件访问
    fpath = OUTPUT_DIR / pdf_name / fname
    if not fpath.exists():
        abort(404)
    return send_file(fpath, as_attachment=True)


# 任务控制接口
@app.route("/task/<task_id>/pause", methods=["POST"])
def pause_task(task_id: str):
    t = TASKS.get(task_id)
    if not t:
        return {"error": "not_found"}, 404
    t["control"]["paused"] = True
    t["status"] = "paused"
    # 记录暂停时间，用于计算实际处理时间
    if "pause_start" not in t:
        t["pause_start"] = time.time()
    return {"ok": True}

@app.route("/task/<task_id>/resume", methods=["POST"])
def resume_task(task_id: str):
    t = TASKS.get(task_id)
    if not t:
        return {"error": "not_found"}, 404
    t["control"]["paused"] = False
    # 累计暂停时间
    if "pause_start" in t:
        pause_duration = time.time() - t["pause_start"]
        t["total_pause_time"] = t.get("total_pause_time", 0) + pause_duration
        del t["pause_start"]
    if t.get("done", 0) < t.get("total", 0):
        t["status"] = "in_progress"
    return {"ok": True}

@app.route("/task/<task_id>/stop", methods=["POST"])
def stop_task(task_id: str):
    t = TASKS.get(task_id)
    if not t:
        return {"error": "not_found"}, 404
    t["control"]["stop"] = True
    # 状态由工作线程在收到 stop 后设置为 completed（写出部分结果并 finish）
    return {"ok": True}


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5050"))
    app.run(host="0.0.0.0", port=port, debug=False)
