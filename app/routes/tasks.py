"""采集任务管理（/tasks）：暂停/继续/取消/重试 + 错误日志。"""
from __future__ import annotations

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..models import ErrorLog, SearchTask, utcnow

bp = Blueprint("tasks", __name__)

STATUS_LABELS = {
    "pending": "待开始",
    "running": "运行中",
    "paused": "已暂停",
    "done": "已完成",
    "failed": "失败",
    "cancelled": "已取消",
}
TYPE_LABELS = {"keyword": "关键词", "topic": "话题", "video": "视频"}
PAGE_SIZE = 30


def _task_or_404(tid: int) -> SearchTask | None:
    return SearchTask.get_or_none(SearchTask.id == tid)


@bp.route("/")
def index():
    page = max(int(request.args.get("page", 1) or 1), 1)
    q = SearchTask.select().order_by(SearchTask.updated_at.desc())
    total = q.count()
    items = list(q.paginate(page, PAGE_SIZE))
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    return render_template(
        "tasks.html",
        nav="tasks",
        items=items,
        total=total,
        page=page,
        pages=pages,
        status_labels=STATUS_LABELS,
        type_labels=TYPE_LABELS,
    )


def _set_status(tid: int, to_status: str, ok_msg: str):
    t = _task_or_404(tid)
    if t is None:
        flash("任务不存在", "error")
        return redirect(url_for("tasks.index"))
    t.status = to_status
    t.updated_at = utcnow()
    t.save()
    flash(ok_msg)
    return redirect(url_for("tasks.index"))


@bp.route("/<int:tid>/pause", methods=["POST"])
def pause(tid: int):
    return _set_status(tid, "paused", f"任务 #{tid} 已暂停")


@bp.route("/<int:tid>/resume", methods=["POST"])
def resume(tid: int):
    return _set_status(tid, "pending", f"任务 #{tid} 已恢复，等待继续执行")


@bp.route("/<int:tid>/cancel", methods=["POST"])
def cancel(tid: int):
    return _set_status(tid, "cancelled", f"任务 #{tid} 已取消")


@bp.route("/<int:tid>/retry", methods=["POST"])
def retry(tid: int):
    t = _task_or_404(tid)
    if t is None:
        flash("任务不存在", "error")
        return redirect(url_for("tasks.index"))
    if t.status != "failed":
        flash("只有失败的任务可以重试", "error")
        return redirect(url_for("tasks.index"))
    t.status = "pending"
    t.retry_count = (t.retry_count or 0) + 1
    t.error = None
    t.updated_at = utcnow()
    t.save()
    flash(f"任务 #{tid} 已重新入队（第 {t.retry_count} 次重试）")
    return redirect(url_for("tasks.index"))


@bp.route("/<int:tid>/errors")
def errors(tid: int):
    t = _task_or_404(tid)
    if t is None:
        flash("任务不存在", "error")
        return redirect(url_for("tasks.index"))
    logs = list(
        ErrorLog.select()
        .where(ErrorLog.task == t)
        .order_by(ErrorLog.created_at.desc())
        .limit(200)
    )
    return render_template(
        "tasks.html",
        nav="tasks",
        items=None,
        total=0,
        page=1,
        pages=1,
        status_labels=STATUS_LABELS,
        type_labels=TYPE_LABELS,
        error_task=t,
        error_logs=logs,
    )
