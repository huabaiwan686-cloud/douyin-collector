"""启动入口：python run.py"""
from app import create_app

app = create_app()

if __name__ == "__main__":
    cfg = app.config["COLLECTOR_CFG"]["server"]
    app.run(host=cfg["host"], port=cfg["port"], debug=False, threaded=True)
