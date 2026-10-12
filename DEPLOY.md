# 服务器部署步骤（Ubuntu 24.04）

## 1. 环境准备
```bash
apt update && apt install -y python3.12 python3.12-venv xvfb
```

## 2. 部署代码
```bash
mkdir -p /opt/douyin-collector
# 上传项目文件到 /opt/douyin-collector
cd /opt/douyin-collector
python3.12 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/playwright install chromium
venv/bin/playwright install-deps chromium
```

## 3. 配置
```bash
cp config.example.yaml config.yaml
# 按需修改端口、采集间隔、阈值
venv/bin/python scripts/init_db.py
```

## 4. 扫码登录（首次）
```bash
# 服务器无桌面，用 xvfb 跑 headed 浏览器
Xvfb :99 -screen 0 1366x900x24 &
DISPLAY=:99 venv/bin/python -m app.collector.browser --login --dir data/browser_profile
# 用抖音小号扫码，看到"登录成功"即可 Ctrl+C
```

## 5. 启动服务
```bash
cp scripts/dy-web.service scripts/dy-worker.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now dy-web dy-worker
# Web UI: http://服务器IP:5000
```

## 6. 数据备份
- 数据库：data/collector.db（定时 cp 到 data/backup/）
- 登录态：data/browser_profile/（备份即保留登录）

## 7. 验证清单
- [ ] Web UI 可打开
- [ ] 扫码登录成功
- [ ] 关键词搜到真实视频
- [ ] 评论树显示一级+二级
- [ ] 收藏去重生效
- [ ] CSV/Excel/JSON 导出可打开
