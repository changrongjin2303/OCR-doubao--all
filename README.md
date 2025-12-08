# PDF/图片文字识别到 Word

智能识别 PDF 和图片中的所有文字内容，自动按层级结构组织标题和正文，输出清晰的 Word 文档。

## 功能特点

- 🔍 **智能识别全部文字**：准确提取图片中的所有文字内容
- 📝 **自动分级标题结构**：根据字体大小、位置自动判断标题层级（h1/h2/h3）
- 📋 **忽略水印盖章干扰**：自动过滤水印、印章、背景装饰等干扰元素
- 📄 **输出 Word 文档**：生成格式清晰、结构完整的 .docx 文件
- 📊 **表格识别**：保留文档中的表格结构

## 快速配置

在项目根目录创建 `.env` 文件，`./start.sh` 会自动加载：

```
# 必填
ARK_API_KEY=你的密钥
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3

# 可选
ARK_MODEL=doubao-seed-1-6-vision-250815
ARK_SOURCE=page   # embedded | page | both（推荐使用 page 或 both）
ARK_DPI=200
ARK_WORKERS=4
```

之后直接运行：

```
./start.sh
```

## 环境准备

1) 安装依赖：

```
pip install -r requirements.txt
```

2) 配置豆包 Ark API：

- `ARK_API_KEY`：你的 API Key（例如火山引擎 Ark 平台的密钥）
- `ARK_BASE_URL`：基础地址，例如 `https://ark.cn-beijing.volces.com/api/v3`

在 macOS/Linux 终端中可临时设置：

```
export ARK_API_KEY="你的key"
export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
```

## 使用方法

### 网页界面（推荐）

启动 Web 服务：

```
./start.sh
```

访问 `http://localhost:5050/`，上传 PDF 或图片文件即可。

### 命令行

处理单个 PDF：

```
python process_pdfs.py --input "/path/to/your.pdf"
```

批量处理目录中的所有 PDF：

```
python process_pdfs.py --input "/path/to/pdf_folder"
```

输出文件位置：`output/word/<文件名>.docx`

## 输出格式

系统会将识别到的内容按以下层级组织：

- **h1**：页面最大的主标题
- **h2**：章节标题或次级大标题
- **h3**：小节标题
- **paragraph**：普通正文段落
- **list**：带序号或项目符号的列表
- **table**：表格数据

## 配置说明

### 图片来源模式（ARK_SOURCE）

- `page`：渲染整页为图片（**推荐**，适合大多数场景）
- `embedded`：仅处理 PDF 内嵌图片
- `both`：同时处理内嵌图片与整页渲染

对于需要识别完整页面文字的场景，建议使用 `page` 或 `both` 模式。

### 并行处理

环境变量 `ARK_WORKERS` 控制并行处理线程数（默认 4）：

```
export ARK_WORKERS=6
./start.sh
```

### 超时与重试

- `ARK_TIMEOUT`：读取超时（秒），默认 `180`
- `ARK_RETRIES`：重试次数，默认 `3`

```
echo "ARK_TIMEOUT=240" >> .env
echo "ARK_RETRIES=4" >> .env
./start.sh
```

### 进度轮询频率

- `ARK_POLL_MS`：进度页轮询间隔（毫秒），默认 `10000`

## 常见问题

### 1. 未识别到文字内容

- 检查 `ARK_SOURCE` 设置，建议使用 `page` 或 `both`
- 检查图片质量，可尝试提高 DPI：`ARK_DPI=300`

### 2. 标题层级不准确

- 模型会根据字体大小和位置自动判断层级
- 如果原图层级不明显，可能需要人工调整

### 3. 水印/盖章被识别

- 系统会尽量过滤水印和盖章，但极个别情况可能仍会识别
- 可在生成的 Word 文档中手动删除

## 依赖

- PyMuPDF：PDF 处理
- requests：API 调用
- python-docx：Word 文档生成
- Flask：Web 界面
- Pillow：图片处理

## 说明

- 本工具使用豆包 Vision 模型进行文字识别
- 模型名默认使用 `doubao-seed-1-6-vision-250815`，可通过 `--model` 参数指定其他模型
