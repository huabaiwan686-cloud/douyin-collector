"""话题管理：列表 / 新增 / 批量导入 / 启用开关 / 删除 / 开始采集。"""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..models import Comment, SearchTask, Topic, Video

bp = Blueprint("topics", __name__)


@bp.route("/")
def index():
    topics = list(Topic.select().order_by(Topic.id.desc()))
    rows = []
    for tp in topics:
        rows.append(
            {
                "topic": tp,
                "video_count": Video.select().where(Video.source_topic == tp.name).count(),
                "comment_count": Comment.select().where(Comment.source_topic == tp.name).count(),
            }
        )
    return render_template("topics.html", nav="topics", rows=rows)


@bp.route("/add", methods=["POST"])
def add():
    name = (request.form.get("name") or "").strip()
    hashtag_id = (request.form.get("hashtag_id") or "").strip() or None
    if not name:
        flash("话题名称不能为空", "error")
    else:
        tp, created = Topic.get_or_create(name=name, defaults={"hashtag_id": hashtag_id})
        if not created and hashtag_id and not tp.hashtag_id:
            tp.hashtag_id = hashtag_id
            tp.save()
        flash(f"已添加话题：{name}" if created else f"话题已存在：{name}")
    return redirect(url_for("topics.index"))


@bp.route("/import", methods=["POST"])
def batch_import():
    raw = request.form.get("texts") or ""
    added, existed = 0, 0
    for line in raw.splitlines():
        t = line.strip().lstrip("#")
        if not t:
            continue
        _, created = Topic.get_or_create(name=t)
        if created:
            added += 1
        else:
            existed += 1
    flash(f"批量导入完成：新增 {added} 个，已存在 {existed} 个")
    return redirect(url_for("topics.index"))


@bp.route("/toggle/<int:topic_id>", methods=["POST"])
def toggle(topic_id):
    tp = Topic.get_or_none(Topic.id == topic_id)
    if tp:
        tp.enabled = not tp.enabled
        tp.save()
        flash(f"话题「{tp.name}」已{'启用' if tp.enabled else '禁用'}")
    return redirect(url_for("topics.index"))


@bp.route("/delete/<int:topic_id>", methods=["POST"])
def delete(topic_id):
    tp = Topic.get_or_none(Topic.id == topic_id)
    if tp:
        name = tp.name
        tp.delete_instance()
        flash(f"已删除话题：{name}")
    return redirect(url_for("topics.index"))


@bp.route("/collect/<int:topic_id>", methods=["POST"])
def collect(topic_id):
    tp = Topic.get_or_none(Topic.id == topic_id)
    if not tp:
        flash("话题不存在", "error")
    else:
        SearchTask.create(task_type="topic", topic=tp, status="pending")
        flash("任务已创建，等待采集引擎执行")
    return redirect(url_for("topics.index"))
