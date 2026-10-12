"""关键词管理：列表 / 新增 / 批量导入 / 启用开关 / 删除 / 开始采集。"""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..models import Comment, Keyword, SearchTask, Video

bp = Blueprint("keywords", __name__)


@bp.route("/")
def index():
    kws = list(Keyword.select().order_by(Keyword.id.desc()))
    rows = []
    for kw in kws:
        rows.append(
            {
                "kw": kw,
                "video_count": Video.select().where(Video.source_keyword == kw.text).count(),
                "comment_count": Comment.select().where(Comment.source_keyword == kw.text).count(),
            }
        )
    return render_template("keywords.html", nav="keywords", rows=rows)


@bp.route("/add", methods=["POST"])
def add():
    text = (request.form.get("text") or "").strip()
    if not text:
        flash("关键词不能为空", "error")
    else:
        _, created = Keyword.get_or_create(text=text)
        flash(f"已添加关键词：{text}" if created else f"关键词已存在：{text}")
    return redirect(url_for("keywords.index"))


@bp.route("/import", methods=["POST"])
def batch_import():
    raw = request.form.get("texts") or ""
    added, existed = 0, 0
    for line in raw.splitlines():
        t = line.strip()
        if not t:
            continue
        _, created = Keyword.get_or_create(text=t)
        if created:
            added += 1
        else:
            existed += 1
    flash(f"批量导入完成：新增 {added} 个，已存在 {existed} 个")
    return redirect(url_for("keywords.index"))


@bp.route("/toggle/<int:kw_id>", methods=["POST"])
def toggle(kw_id):
    kw = Keyword.get_or_none(Keyword.id == kw_id)
    if kw:
        kw.enabled = not kw.enabled
        kw.save()
        flash(f"关键词「{kw.text}」已{'启用' if kw.enabled else '禁用'}")
    return redirect(url_for("keywords.index"))


@bp.route("/delete/<int:kw_id>", methods=["POST"])
def delete(kw_id):
    kw = Keyword.get_or_none(Keyword.id == kw_id)
    if kw:
        text = kw.text
        kw.delete_instance()
        flash(f"已删除关键词：{text}")
    return redirect(url_for("keywords.index"))


@bp.route("/collect/<int:kw_id>", methods=["POST"])
def collect(kw_id):
    kw = Keyword.get_or_none(Keyword.id == kw_id)
    if not kw:
        flash("关键词不存在", "error")
    else:
        SearchTask.create(task_type="keyword", keyword=kw, status="pending")
        flash("任务已创建，等待采集引擎执行")
    return redirect(url_for("keywords.index"))
