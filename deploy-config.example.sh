#!/bin/bash
# 部署配置文件示例
# 复制此文件为 deploy-config.sh 并填入你的实际信息

# 阿里云服务器信息
export SERVER_IP="your-server-ip"           # 例如: 47.xxx.xxx.xxx
export SERVER_USER="root"                   # 通常是 root 或 ubuntu
export SSH_KEY=""                           # SSH密钥路径，例如: ~/.ssh/id_rsa（如果使用密码登录则留空）

# 部署路径
export DEPLOY_PATH="/opt/ocr-doubao"

# 服务名称
export SERVICE_NAME="ocr-doubao"

