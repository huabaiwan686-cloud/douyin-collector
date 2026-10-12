"""已收藏主页管理（/favorites）。"""
from __future__ import annotations

from flask import Blueprint, flash, redirect, request, render_template, url_for

from ..models import Favorite, User

bp = Blueprint("favorites", __name__)

REVIEW_LABELS = {"pending": "待审核", "approved": "符合条件", "rejected": "不符合条件"}
PAGE_SIZE = 50


def build_favorite_query(args) -> "Favorite":
    """按筛选参数构造收藏查询（export 蓝图复用）。"""
    q = Favorite.select().join(User)
    keyword = (args.get("keyword") or "").strip()
    topic = (args.get("topic") or "").strip()
    status = (args.get("status") or "").strip()
    tag = (args.get("tag") or "").strip()
    kw = (args.get("q") or "").strip()
    ids = (args.get("ids") or "").strip()
    if keyword:
        q = q.where(Favorite.source_keyword == keyword)
    if topic:
        q = q.where(Favorite.source_topic == topic)
    if status in REVIEW_LABELS:
        q = q.where(Favorite.review_status == status)
    if tag:
        q = q.where(Favorite.tags.contains(tag))
    if kw:
        q = q.where(User.nickname.contains(kw))
    if ids:
        id_list = [int(i) for i in ids.split(",") if i.strip().isdigit()]
        if id_list:
            q = q.where(Favorite.id.in_(id_list))
    return q.order_by(Favorite.created_at.desc())


@bp.route("/")
def index():
    page = max(int(request.args.get("page", 1) or 1), 1)
    q = build_favorite_query(request.args)
    total = q.count()
    items = list(q.paginate(page, PAGE_SIZE))
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    qstr = "&".join(
        f"{k}={v}" for k, v in request.args.items() if k != "page" and v
    )
    return render_template(
        "favorites.html",
        nav="favorites",
        items=items,
        total=total,
        page=page,
        pages=pages,
        args=request.args,
        qstr=qstr,
        labels=REVIEW_LABELS,
    )


@bp.route("/add", methods=["POST"])
def add():
    sec_uid = (request.form.get("sec_uid") or "").strip()
    trigger_comment = (request.form.get("trigger_comment") or "").strip() or None
    if not sec_uid:
        flash("缺少 sec_uid，无法收藏", "error")
        return redirect(request.referrer or url_for("favorites.index"))
    user = User.get_or_none(User.sec_uid == sec_uid)
    if user is None:
        flash("用户不存在（可能尚未采集），无法收藏", "error")
        return redirect(request.referrer or url_for("favorites.index"))
    fav = Favorite.get_or_none(Favorite.user == user)
    if fav is not None:
        flash(f"已收藏过「{user.nickname}」，自动去重", "error")
        return redirect(request.referrer or url_for("favorites.index"))
    Favorite.create(
        user=user,
        homepage_url=user.homepage_url,
        nickname_snapshot=user.nickname,
        source_keyword=(request.form.get("source_keyword") or "").strip() or None,
        source_topic=(request.form.get("source_topic") or "").strip() or None,
        source_video_url=(request.form.get("source_video_url") or "").strip() or None,
        trigger_comment=trigger_comment,
    )
    flash(f"已收藏「{user.nickname}」")
    return redirect(request.referrer or url_for("favorites.index"))


@bp.route("/<int:fid>/update", methods=["POST"])
def update(fid: int):
    fav = Favorite.get_or_none(Favorite.id == fid)
    if fav is None:
        flash("收藏记录不存在", "error")
        return redirect(url_for("favorites.index"))
    status = (request.form.get("review_status") or "").strip()
    if status in REVIEW_LABELS:
        fav.review_status = status
    fav.note = (request.form.get("note") or "").strip() or None
    fav.tags = (request.form.get("tags") or "").strip() or None
    fav.save()
    flash("已更新")
    return redirect(request.referrer or url_for("favorites.index"))


@bp.route("/<int:fid>/delete", methods=["POST"])
def delete(fid: int):
    fav = Favorite.get_or_none(Favorite.id == fid)
    if fav is None:
        flash("收藏记录不存在", "error")
    else:
        name = fav.nickname_snapshot
        fav.delete_instance()
        flash(f"已取消收藏「{name}」")
    return redirect(request.referrer or url_for("favorites.index"))


@bp.route("/batch", methods=["POST"])
def batch():
    raw: list[str] = []
    for v in request.form.getlist("ids"):
        raw.extend(str(v).split(","))
    ids = [int(i) for i in raw if i.strip().isdigit()]
    action = request.form.get("action", "")
    if not ids:
        flash("请先勾选要操作的收藏", "error")
        return redirect(url_for("favorites.index"))
    if action == "delete":
        n = Favorite.delete().where(Favorite.id.in_(ids)).execute()
        flash(f"已批量取消收藏 {n} 条")
    elif action.startswith("status:"):
        status = action.split(":", 1)[1]
        if status not in REVIEW_LABELS:
            flash("无效的审核状态", "error")
            return redirect(url_for("favorites.index"))
        n = (
            Favorite.update(review_status=status)
            .where(Favorite.id.in_(ids))
            .execute()
        )
        flash(f"已批量标记 {n} 条为「{REVIEW_LABELS[status]}」")
    else:
        flash("未知批量操作", "error")
    return redirect(url_for("favorites.index"))
