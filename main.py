"""Windows EXE 入口：双击启动 Web UI + 采集 worker，自动打开浏览器。

打包：PyInstaller douyin-collector.spec（GitHub Actions 自动构建）
"""
import os
import sys
import threading
import time
import webbrowser


def setup_paths():
    # PyInstaller onedir 模式：exe 同目录为工作目录
    if getattr(sys, "frozen", False):
        base = os.path.dirname(sys.executable)
        os.chdir(base)
        # Playwright 浏览器路径指向打包目录
        bw = os.path.join(base, "ms-playwright")
        if os.path.isdir(bw):
            os.environ["PLAYWRIGHT_BROWSERS_PATH"] = bw


def ensure_config():
    import shutil
    if not os.path.exists("config.yaml"):
        shutil.copy("config.example.yaml", "config.yaml")
    os.makedirs("data", exist_ok=True)


def run_web():
    from app import create_app
    app = create_app("config.yaml")
    cfg = app.config["COLLECTOR_CFG"]["server"]
    app.run(host="127.0.0.1", port=cfg.get("port", 5000),
            debug=False, threaded=True, use_reloader=False)


def run_worker():
    import yaml
    from app.models import TABLES, db
    from app.worker import Worker
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    db.init(cfg["database"]["path"])
    db.connect()
    db.create_tables(TABLES)
    db.close()
    # worker 自带 browser 登录检查，未登录时只打印提示不崩溃
    import asyncio
    worker = Worker(cfg)
    try:
        asyncio.run(worker.serve_forever())
    except Exception as e:
        print(f"Worker 退出：{e}")


def main():
    setup_paths()
    ensure_config()
    # 初始化数据库
    sys.path.insert(0, os.getcwd())
    import yaml
    from app.models import init_database
    with open("config.yaml", encoding="utf-8") as f:
        _cfg = yaml.safe_load(f)
    init_database(_cfg["database"]["path"])

    threading.Thread(target=run_web, daemon=True).start()
    threading.Thread(target=run_worker, daemon=True).start()
    time.sleep(2)
    webbrowser.open("http://127.0.0.1:5000/settings/login")
    print("=" * 50)
    print("抖音采集工具已启动，浏览器已打开 http://127.0.0.1:5000")
    print("请先扫码登录，再使用采集功能。关闭此窗口即退出程序。")
    print("=" * 50)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
