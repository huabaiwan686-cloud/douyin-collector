"""作品与评论结果：视频列表（分页/筛选/排序）+ 视频详情（一级评论分页）。"""
from __future__ import annotations

from flask import Blueprint, abort, render_template, request

from ..models import Comment, Video

bp = Blueprint("videos", __name__)
PAGE_SIZE = 20


@bp.route("/")
def index():
    page = max(1, request.args.get("page", 1, type=int))
    kw = (request.args.get("keyword") or "").strip()
    topic = (request.args.get("topic") or "").strip()
    sort = request.args.get("sort", "latest")

    q = Video.select()
    if kw:
        q = q.where(Video.source_keyword == kw)
    if topic:
        q = q.where(Video.source_topic == topic)
    if sort == "digg":
        q = q.order_by(Video.digg_count.desc())
    elif sort == "comments":
        q = q.order_by(Video.comment_count.desc())
    else:
        sort = "latest"
        q = q.order_by(Video.created_at.desc())

    total = q.count()
    videos = list(q.paginate(page, PAGE_SIZE))
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return render_template(
        "videos.html", nav="videos", videos=videos, page=page,
        pages=pages, total=total, kw=kw, topic=topic, sort=sort,
    )


@bp.route("/<aweme_id>")
def detail(aweme_id):
    video = Video.get_or_none(Video.aweme_id == aweme_id)
    if not video:
        abort(404)
    page = max(1, request.args.get("page", 1, type=int))
    q = (
        Comment.select()
        .where((Comment.video == video) & Comment.parent_cid.is_null(True))
        .order_by(Comment.digg_count.desc())
    )
    total = q.count()
    comments = list(q.paginate(page, PAGE_SIZE))
    pages = max(1, (total + PAGE_SIZE - 1) // PAGE_SIZE)
    return render_template(
        "video_detail.html", nav="videos", video=video,
        comments=comments, page=page, pages=pages, total=total,
    )
