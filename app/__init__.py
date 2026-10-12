"""Flask 应用工厂。"""
from __future__ import annotations

import os
from pathlib import Path

import yaml
from flask import Flask

from .models import db


def load_config(path: str = "config.yaml") -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def create_app(config_path: str = "config.yaml") -> Flask:
    cfg = load_config(config_path)
    app = Flask(__name__)
    app.config["COLLECTOR_CFG"] = cfg
    app.secret_key = os.environ.get("FLASK_SECRET", "dy-collector-dev-key")

    # 数据库
    db_path = Path(cfg["database"]["path"])
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db.init(str(db_path))

    @app.before_request
    def _db_connect():
        if db.is_closed():
            db.connect()

    @app.teardown_request
    def _db_close(exc):
        if not db.is_closed():
            db.close()

    # 蓝图（10 个页面）
    from .routes import dashboard, keywords, topics, videos, tree, profile, favorites, export, tasks, settings
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(keywords.bp, url_prefix="/keywords")
    app.register_blueprint(topics.bp, url_prefix="/topics")
    app.register_blueprint(videos.bp, url_prefix="/videos")
    app.register_blueprint(tree.bp, url_prefix="/tree")
    app.register_blueprint(profile.bp, url_prefix="/profile")
    app.register_blueprint(favorites.bp, url_prefix="/favorites")
    app.register_blueprint(export.bp, url_prefix="/export")
    app.register_blueprint(tasks.bp, url_prefix="/tasks")
    app.register_blueprint(settings.bp, url_prefix="/settings")

    return app
