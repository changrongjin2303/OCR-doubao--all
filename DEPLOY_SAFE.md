# 安全部署指南 - 避免影响现有系统

## 重要说明

你的阿里云服务器上已经部署了其他系统，为了确保不影响现有服务，我们做了以下隔离措施：

### 1. 独立部署路径
- **部署路径**: `/opt/ocr-doubao`
- 不会影响其他系统的文件

### 2. 端口检查
- **默认端口**: `5050`
- 部署脚本会自动检查端口占用
- 如果端口被占用，可以修改 `deploy.sh` 中的 `SERVICE_PORT` 变量

### 3. 独立服务
- **服务名称**: `ocr-doubao`
- 使用 systemd 独立管理，不影响其他服务

### 4. Python 虚拟环境
- 使用独立的虚拟环境 `venv/`
- 不会影响系统 Python 或其他项目的依赖

## 部署前检查清单

在部署前，建议手动检查：

```bash
# 1. 检查端口占用
ssh root@8.136.59.48 "netstat -tuln | grep 5050"

# 2. 检查现有服务
ssh root@8.136.59.48 "systemctl list-units --type=service | grep -E 'running|active'"

# 3. 检查磁盘空间
ssh root@8.136.59.48 "df -h"
```

## 如果端口被占用

如果 5050 端口被占用，可以：

1. **修改端口**（推荐）：
   - 编辑 `deploy.sh`，修改 `SERVICE_PORT="5051"`（或其他可用端口）
   - 访问时使用新端口：`http://8.136.59.48:5051`

2. **查看占用端口的服务**：
   ```bash
   ssh root@8.136.59.48 "netstat -tulnp | grep 5050"
   ```

## 部署后验证

```bash
# 1. 检查服务状态
ssh root@8.136.59.48 "sudo systemctl status ocr-doubao"

# 2. 检查端口监听
ssh root@8.136.59.48 "netstat -tuln | grep 5050"

# 3. 测试访问
curl http://8.136.59.48:5050
```

## 回滚方案

如果部署后出现问题，可以快速回滚：

```bash
# 停止服务
ssh root@8.136.59.48 "sudo systemctl stop ocr-doubao"

# 禁用服务
ssh root@8.136.59.48 "sudo systemctl disable ocr-doubao"

# 删除服务文件（可选）
ssh root@8.136.59.48 "sudo rm /etc/systemd/system/ocr-doubao.service"

# 删除部署目录（可选）
ssh root@8.136.59.48 "rm -rf /opt/ocr-doubao"
```

## 安全建议

1. **防火墙配置**：如果服务器有防火墙，需要开放 5050 端口
2. **API 密钥安全**：`.env` 文件包含敏感信息，确保权限正确：
   ```bash
   chmod 600 /opt/ocr-doubao/.env
   ```
3. **定期备份**：建议定期备份 `.env` 文件

