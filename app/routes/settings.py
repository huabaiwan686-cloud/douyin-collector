"""设置（/settings）：配置展示、登录态检测、数据库备份、日志查看。"""
from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path

from flask import Blueprint, current_app, flash, redirect, render_template, url_for

from ..models import ErrorLog

bp = Blueprint("settings", __name__)


def _cfg() -> dict:
    return current_app.config["COLLECTOR_CFG"]


def _db_path() -> Path:
    return Path(_cfg()["database"]["path"])


def _backup_dir() -> Path:
    d = Path("data/backup")
    d.mkdir(parents=True, exist_ok=True)
    return d


@bp.route("/")
def index():
    cfg = _cfg()
    db_path = _db_path()
    profile_dir = Path(cfg.get("browser", {}).get("user_data_dir", "data/browser_profile"))
    login_ok = profile_dir.exists() and any(profile_dir.iterdir())
    backups = sorted(
        (p for p in _backup_dir().glob("collector_*.db")),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    backup_rows = [
        {
            "name": p.name,
            "kb": p.stat().st_size // 1024,
            "time": datetime.fromtimestamp(p.stat().st_mtime).strftime(
                "%Y-%m-%d %H:%M:%S"
            ),
        }
        for p in backups
    ]
    logs = list(ErrorLog.select().order_by(ErrorLog.created_at.desc()).limit(100))
    sections = {
        "server": cfg.get("server", {}),
        "database": cfg.get("database", {}),
        "browser": cfg.get("browser", {}),
        "crawl": cfg.get("crawl", {}),
        "export": cfg.get("export", {}),
    }
    return render_template(
        "settings.html",
        nav="settings",
        sections=sections,
        login_ok=login_ok,
        profile_dir=str(profile_dir),
        db_exists=db_path.exists(),
        db_path=str(db_path),
        backups=backup_rows,
        logs=logs,
    )


@bp.route("/backup", methods=["POST"])
def backup():
    src = _db_path()
    if not src.exists():
        flash("数据库文件不存在，无法备份", "error")
        return redirect(url_for("settings.index"))
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    dst = _backup_dir() / f"collector_{stamp}.db"
    shutil.copy2(src, dst)
    flash(f"已备份到 {dst.name}")
    return redirect(url_for("settings.index"))


@bp.route("/login")
def login_page():
    """扫码登录页：显示二维码，轮询登录状态。"""
    from ..collector.qr_login import get_qr_status
    cfg = current_app.config["COLLECTOR_CFG"]
    profile_dir = Path(cfg["browser"]["user_data_dir"])
    st = get_qr_status()
    return render_template(
        "login.html", nav="settings",
        qr_img=st.get("img"), qr_ts=st.get("ts"),
        logged_in=st.get("done"),
        has_profile=profile_dir.exists(),
    )


@bp.route("/login/start", methods=["POST"])
def login_start():
    """开始抓取登录二维码（后台线程）。"""
    from ..collector.qr_login import start_qr_capture
    cfg = current_app.config["COLLECTOR_CFG"]
    b = cfg.get("browser", {})
    start_qr_capture(
        b.get("user_data_dir", "data/browser_profile"),
        headless=b.get("headless", True),
    )
    flash("正在打开抖音登录页抓取二维码，请稍等 10 秒后刷新")
    return redirect(url_for("settings.login_page"))


@bp.route("/login/status")
def login_status():
    """JSON：二维码与登录状态（供页面轮询）。"""
    from flask import jsonify
    from ..collector.qr_login import get_qr_status
    st = get_qr_status()
    return jsonify({"has_qr": bool(st.get("img")), "logged_in": bool(st.get("done"))})
