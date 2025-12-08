#!/bin/bash
# 部署脚本 - 部署到阿里云服务器

set -e

# 配置信息（请根据实际情况修改）
SERVER_IP=""           # 阿里云服务器IP
SERVER_USER="root"     # SSH用户名（通常是 root 或 ubuntu）
SSH_KEY=""            # SSH密钥路径（如果使用密钥，留空则使用密码）
DEPLOY_PATH="/opt/ocr-doubao"  # 服务器上的部署路径
SERVICE_NAME="ocr-doubao"      # systemd服务名称

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}开始部署到阿里云服务器...${NC}"

# 检查配置
if [ -z "$SERVER_IP" ]; then
    echo -e "${RED}错误: 请先设置 SERVER_IP${NC}"
    exit 1
fi

# 构建SSH命令
if [ -n "$SSH_KEY" ]; then
    SSH_CMD="ssh -i $SSH_KEY $SERVER_USER@$SERVER_IP"
    SCP_CMD="scp -i $SSH_KEY"
else
    SSH_CMD="ssh $SERVER_USER@$SERVER_IP"
    SCP_CMD="scp"
fi

echo -e "${YELLOW}1. 测试服务器连接...${NC}"
$SSH_CMD "echo '连接成功'" || {
    echo -e "${RED}无法连接到服务器，请检查IP、用户名和SSH配置${NC}"
    exit 1
}

echo -e "${YELLOW}2. 在服务器上创建目录...${NC}"
$SSH_CMD "mkdir -p $DEPLOY_PATH"

echo -e "${YELLOW}3. 检查服务器上的Git...${NC}"
$SSH_CMD "which git > /dev/null || (apt-get update && apt-get install -y git)" || {
    echo -e "${RED}无法安装Git，请手动安装${NC}"
    exit 1
}

echo -e "${YELLOW}4. 克隆或更新代码...${NC}"
$SSH_CMD "if [ -d $DEPLOY_PATH/.git ]; then
    cd $DEPLOY_PATH && git pull
else
    git clone git@github.com:changrongjin2303/OCR-doubao--all.git $DEPLOY_PATH || git clone https://github.com/changrongjin2303/OCR-doubao--all.git $DEPLOY_PATH
fi"

echo -e "${YELLOW}5. 检查Python环境...${NC}"
$SSH_CMD "cd $DEPLOY_PATH && python3 --version || (echo 'Python3未安装，正在安装...' && apt-get update && apt-get install -y python3 python3-pip python3-venv)"

echo -e "${YELLOW}6. 创建虚拟环境并安装依赖...${NC}"
$SSH_CMD "cd $DEPLOY_PATH && 
    if [ ! -d venv ]; then
        python3 -m venv venv
    fi &&
    source venv/bin/activate &&
    pip install --upgrade pip &&
    pip install -r requirements.txt"

echo -e "${YELLOW}7. 检查.env文件...${NC}"
$SSH_CMD "cd $DEPLOY_PATH && 
    if [ ! -f .env ]; then
        echo -e '${RED}警告: .env文件不存在，请手动创建${NC}'
        echo '需要设置以下环境变量:'
        echo '  ARK_API_KEY=你的API密钥'
        echo '  ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3'
        echo '  ARK_MODEL=doubao-seed-1-6-vision-250815'
        echo '  ARK_SOURCE=page'
        echo '  ARK_DPI=200'
        echo '  ARK_WORKERS=4'
    fi"

echo -e "${YELLOW}8. 创建systemd服务文件...${NC}"
$SSH_CMD "cat > /tmp/$SERVICE_NAME.service << 'EOF'
[Unit]
Description=OCR Doubao Service
After=network.target

[Service]
Type=simple
User=$SERVER_USER
WorkingDirectory=$DEPLOY_PATH
Environment=\"PATH=$DEPLOY_PATH/venv/bin:/usr/local/bin:/usr/bin:/bin\"
ExecStart=$DEPLOY_PATH/venv/bin/python3 $DEPLOY_PATH/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
sudo mv /tmp/$SERVICE_NAME.service /etc/systemd/system/ &&
sudo systemctl daemon-reload &&
sudo systemctl enable $SERVICE_NAME &&
sudo systemctl restart $SERVICE_NAME"

echo -e "${YELLOW}9. 检查服务状态...${NC}"
$SSH_CMD "sudo systemctl status $SERVICE_NAME --no-pager -l" || true

echo -e "${GREEN}部署完成！${NC}"
echo -e "${GREEN}服务地址: http://$SERVER_IP:5050${NC}"
echo -e "${YELLOW}常用命令:${NC}"
echo "  查看服务状态: ssh $SERVER_USER@$SERVER_IP 'sudo systemctl status $SERVICE_NAME'"
echo "  查看日志: ssh $SERVER_USER@$SERVER_IP 'sudo journalctl -u $SERVICE_NAME -f'"
echo "  重启服务: ssh $SERVER_USER@$SERVER_IP 'sudo systemctl restart $SERVICE_NAME'"
echo "  停止服务: ssh $SERVER_USER@$SERVER_IP 'sudo systemctl stop $SERVICE_NAME'"

