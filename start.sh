#!/usr/bin/env bash
set -e

# 启动本地可视化应用（Flask）
# 使用前请在终端设置：
#   export ARK_API_KEY="你的key"
#   export ARK_BASE_URL="https://ark.cn-beijing.volces.com/api/v3"
# 可选：
#   export ARK_MODEL="doubao-seed-1-6-vision-250815"
#   export ARK_DPI=200

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# 自动加载本地 .env 配置（如果存在），避免每次手动 export
ENV_FILE="$SCRIPT_DIR/.env"
if [[ -f "$ENV_FILE" ]]; then
  # 导出 .env 中的变量到环境
  set -a
  source "$ENV_FILE"
  set +a
fi

if [[ -z "${ARK_API_KEY}" || -z "${ARK_BASE_URL}" ]]; then
  echo "[ERROR] 缺少 Ark API 配置，请设置 ARK_API_KEY 与 ARK_BASE_URL 环境变量"
  exit 1
fi

echo "[INFO] 启动应用于 http://localhost:5050/"
echo "[INFO] 使用模型: ${ARK_MODEL:-doubao-seed-1-6-vision-250815} | 来源模式: ${ARK_SOURCE:-embedded} | DPI: ${ARK_DPI:-200}"
python3 app.py
