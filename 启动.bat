@echo off
cd /d "%~dp0"

echo ============================================
echo  Douyin Collector - Starting
echo ============================================

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Install Python 3.12 first:
    echo https://www.python.org/downloads/
    echo Check "Add python.exe to PATH" during install.
    pause
    exit /b 1
)

:: First run: venv + deps
if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creating venv...
    python -m venv venv
    echo [2/3] Installing deps (3-5 min, first run only)...
    venv\Scripts\pip install -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt
    echo [3/3] Downloading browser (first run only)...
    venv\Scripts\playwright install chromium
    echo Done!
)

if not exist "config.yaml" copy "config.example.yaml" "config.yaml" >nul

echo Starting... browser will open soon.
timeout /t 5 /nobreak >nul
start "" http://127.0.0.1:5000/settings/login
venv\Scripts\python main.py
pause
