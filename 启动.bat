@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo  抖音采集工具 - 启动
echo ============================================

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 没找到 Python，请先安装 Python 3.12：
    echo https://www.python.org/downloads/
    echo 安装时勾选 "Add python.exe to PATH"
    pause
    exit /b 1
)

:: 首次运行：创建虚拟环境并安装依赖
if not exist "venv\Scripts\python.exe" (
    echo [1/3] 创建虚拟环境...
    python -m venv venv
    echo [2/3] 安装依赖（约3-5分钟，仅首次）...
    venv\Scripts\pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
    echo [3/3] 下载浏览器（仅首次）...
    venv\Scripts\playwright install chromium
    echo 安装完成！
)

:: 复制配置文件
if not exist "config.yaml" copy "config.example.yaml" "config.yaml" >nul

:: 启动
echo 正在启动，浏览器会自动打开...
start "" http://127.0.0.1:5000/settings/login
venv\Scripts\python main.py
pause
