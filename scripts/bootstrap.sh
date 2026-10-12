#!/bin/bash
# 抖音采集工具一键部署（Ubuntu 24.04）
# 在服务器上执行：curl -sSL https://raw.githubusercontent.com/huabaiwan686-cloud/douyin-collector/master/scripts/bootstrap.sh | bash
set -e

echo "=== 1/6 安装系统依赖 ==="
apt update -qq && apt install -y -qq python3.12 python3.12-venv xvfb curl > /dev/null 2>&1
echo OK

echo "=== 2/6 安装 cloudflared（内网穿透） ==="
if ! command -v cloudflared &> /dev/null; then
  curl -sSL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared
  chmod +x /usr/local/bin/cloudflared
fi
echo OK

echo "=== 3/6 拉取项目代码 ==="
if [ -d /opt/douyin-collector/.git ]; then
  cd /opt/douyin-collector && git pull -q
else
  rm -rf /opt/douyin-collector
  git clone -q https://github.com/huabaiwan686-cloud/douyin-collector.git /opt/douyin-collector
  cd /opt/douyin-collector
fi
echo OK

echo "=== 4/6 安装 Python 依赖（约 3-5 分钟） ==="
python3.12 -m venv venv 2>/dev/null || true
venv/bin/pip install -q -r requirements.txt
venv/bin/playwright install chromium 2>&1 | tail -1
venv/bin/playwright install-deps chromium > /dev/null 2>&1 || true
echo OK

echo "=== 5/6 初始化配置与数据库 ==="
[ -f config.yaml ] || cp config.example.yaml config.yaml
venv/bin/python scripts/init_db.py

echo "=== 6/6 启动服务 ==="
pkill -f "run.py" 2>/dev/null || true
pkill -f "app.worker" 2>/dev/null || true
pkill -f "cloudflared tunnel" 2>/dev/null || true
# Xvfb（给无头服务器提供虚拟显示）
Xvfb :99 -screen 0 1366x900x24 > /dev/null 2>&1 &
export DISPLAY=:99
# Web UI
nohup venv/bin/python run.py > data/web.log 2>&1 &
# 采集 worker
nohup venv/bin/python -m app.worker > data/worker.log 2>&1 &
sleep 3
# 内网穿透
nohup cloudflared tunnel --url http://localhost:5000 > data/tunnel.log 2>&1 &
sleep 8
URL=$(grep -oE "https://[a-zA-Z0-9.-]+\.trycloudflare\.com" data/tunnel.log | head -1)

echo ""
echo "=========================================="
echo " 部署完成！"
echo " 网页地址：$URL"
echo " 先打开上面的地址 → 设置 → 扫码登录"
echo " 日志：data/web.log data/worker.log data/tunnel.log"
echo "=========================================="
