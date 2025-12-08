# 部署指南

## 部署到阿里云 ECS

### 前置要求

1. **Git 仓库信息**
   - Git 仓库地址（GitHub/GitLab/Gitee）
   - 访问权限（SSH key 或 HTTPS token）

2. **阿里云服务器信息**
   - 服务器 IP 地址
   - SSH 用户名（通常是 `root` 或 `ubuntu`）
   - SSH 密钥路径或密码
   - 服务器操作系统（Ubuntu/CentOS 等）

3. **服务器环境**
   - Python 版本（建议 3.8+）
   - 是否需要安装 Python 依赖

### 部署步骤

#### 1. 在服务器上克隆代码

```bash
# 进入工作目录
cd /opt  # 或其他目录

# 克隆仓库
git clone <你的仓库地址> ocr-doubao
cd ocr-doubao
```

#### 2. 安装依赖

```bash
# 安装 Python 依赖
pip3 install -r requirements.txt

# 或使用虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### 3. 配置环境变量

```bash
# 创建 .env 文件
cat > .env << EOF
ARK_API_KEY=你的API密钥
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=doubao-seed-1-6-vision-250815
ARK_SOURCE=page
ARK_DPI=200
ARK_WORKERS=4
ARK_TIMEOUT=180
ARK_RETRIES=3
ARK_POLL_MS=10000
EOF
```

#### 4. 使用 systemd 管理服务（推荐）

创建服务文件：

```bash
sudo nano /etc/systemd/system/ocr-doubao.service
```

内容：

```ini
[Unit]
Description=OCR Doubao Service
After=network.target

[Service]
Type=simple
User=你的用户名
WorkingDirectory=/opt/ocr-doubao
Environment="PATH=/opt/ocr-doubao/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/opt/ocr-doubao/venv/bin/python3 app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable ocr-doubao
sudo systemctl start ocr-doubao
sudo systemctl status ocr-doubao
```

#### 5. 配置 Nginx 反向代理（可选）

如果需要通过域名访问：

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5050;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### 更新部署

```bash
cd /opt/ocr-doubao
git pull
# 如果有新的依赖
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart ocr-doubao
```

