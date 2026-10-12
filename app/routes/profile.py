"""创作者主页查看（/profile）。"""
from __future__ import annotations

from flask import Blueprint, render_template

from ..models import User, Video

bp = Blueprint("profile", __name__)


@bp.route("/<sec_uid>")
def detail(sec_uid: str):
    user = User.get_or_none(User.sec_uid == sec_uid)
    works = []
    if user is not None:
        works = list(
            Video.select()
            .where(Video.author_sec_uid == sec_uid)
            .order_by(Video.digg_count.desc())
            .limit(24)
        )
    return render_template(
        "profile.html", nav="profile", user=user, works=works, sec_uid=sec_uid
    )
