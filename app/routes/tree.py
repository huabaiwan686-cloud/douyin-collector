"""评论树：作品信息 + 一级→二级缩进展示（<details> 展开/折叠）。"""
from __future__ import annotations

from flask import Blueprint, abort, render_template, request

from ..models import Comment, Video

bp = Blueprint("tree", __name__)


@bp.route("/<aweme_id>")
def show(aweme_id):
    video = Video.get_or_none(Video.aweme_id == aweme_id)
    if not video:
        abort(404)

    q_text = (request.args.get("q") or "").strip()
    sort = request.args.get("sort", "digg")

    l1 = Comment.select().where(
        (Comment.video == video) & Comment.parent_cid.is_null(True)
    )
    if q_text:
        l1 = l1.where(Comment.text.contains(q_text))
    if sort == "time":
        l1 = l1.order_by(Comment.create_time.desc())
    else:
        sort = "digg"
        l1 = l1.order_by(Comment.digg_count.desc())

    tree = []
    for c in l1:
        replies = list(
            Comment.select()
            .where(Comment.parent_cid == c.cid)
            .order_by(Comment.digg_count.desc())
        )
        tree.append((c, replies))

    return render_template(
        "tree.html", nav="videos", video=video, tree=tree,
        q=q_text, sort=sort,
    )
