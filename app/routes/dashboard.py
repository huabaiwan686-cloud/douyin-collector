"""工作台：统计卡片 + 最近任务 + 收藏阈值进度。"""
from __future__ import annotations

from flask import Blueprint, current_app, render_template

from ..models import Comment, Favorite, Keyword, SearchTask, Topic, Video

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def index():
    stats = {
        "keywords": Keyword.select().count(),
        "topics": Topic.select().count(),
        "videos": Video.select().count(),
        "comments_l1": Comment.select().where(Comment.parent_cid.is_null(True)).count(),
        "comments_l2": Comment.select().where(Comment.parent_cid.is_null(False)).count(),
        "favorites": Favorite.select().count(),
    }
    stats["comments_total"] = stats["comments_l1"] + stats["comments_l2"]

    tasks = list(SearchTask.select().order_by(SearchTask.id.desc()).limit(10))

    threshold = current_app.config["COLLECTOR_CFG"]["export"]["favorite_threshold"]
    fav_count = stats["favorites"]
    reached = bool(threshold) and fav_count >= threshold
    pct = min(100, int(fav_count / threshold * 100)) if threshold else 100

    return render_template(
        "dashboard.html",
        nav="dashboard",
        stats=stats,
        tasks=tasks,
        threshold=threshold,
        fav_count=fav_count,
        pct=pct,
        reached=reached,
    )
