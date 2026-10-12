"""批量导出（/export）：CSV / Excel / JSON + 一键复制链接。"""
from __future__ import annotations

from datetime import datetime
from io import BytesIO

import pandas as pd
from flask import Blueprint, current_app, render_template, request, send_file

from ..models import Favorite, User
from .favorites import REVIEW_LABELS, build_favorite_query

bp = Blueprint("export", __name__)

COLUMNS = [
    "昵称", "抖音号", "主页链接", "简介", "粉丝数",
    "来源关键词", "来源话题", "来源作品", "触发评论",
    "备注", "标签", "审核状态", "收藏时间",
]


def _rows(favs) -> list[dict]:
    rows = []
    for f in favs:
        u = f.user
        rows.append({
            "昵称": f.nickname_snapshot,
            "抖音号": u.unique_id or "—",
            "主页链接": f.homepage_url,
            "简介": u.bio or "—",
            "粉丝数": u.follower_count or 0,
            "来源关键词": f.source_keyword or "—",
            "来源话题": f.source_topic or "—",
            "来源作品": f.source_video_url or "—",
            "触发评论": f.trigger_comment or "—",
            "备注": f.note or "—",
            "标签": f.tags or "—",
            "审核状态": REVIEW_LABELS.get(f.review_status, f.review_status),
            "收藏时间": f.created_at.strftime("%Y-%m-%d %H:%M:%S") if f.created_at else "—",
        })
    return rows


def _filtered():
    return list(build_favorite_query(request.args))


def _send(df: pd.DataFrame, filename: str, mime: str, writer):
    buf = BytesIO()
    writer(df, buf)
    buf.seek(0)
    return send_file(buf, mimetype=mime, as_attachment=True, download_name=filename)


@bp.route("/")
def index():
    favs = _filtered()
    total = len(favs)
    distinct = len({f.homepage_url for f in favs})
    dup = total - distinct
    cfg = current_app.config["COLLECTOR_CFG"]
    threshold = int(cfg.get("export", {}).get("favorite_threshold", 100))
    over = total >= threshold
    urls = "\n".join(f.homepage_url for f in favs)
    return render_template(
        "export.html",
        nav="export",
        total=total,
        distinct=distinct,
        dup=dup,
        threshold=threshold,
        over=over,
        urls=urls,
        args_str=request.query_string.decode(),
    )


@bp.route("/csv")
def csv():
    df = pd.DataFrame(_rows(_filtered()), columns=COLUMNS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _send(
        df, f"favorites_{stamp}.csv", "text/csv",
        lambda d, b: b.write(d.to_csv(index=False).encode("utf-8-sig")),
    )


@bp.route("/excel")
def excel():
    df = pd.DataFrame(_rows(_filtered()), columns=COLUMNS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _send(
        df, f"favorites_{stamp}.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        lambda d, b: d.to_excel(b, index=False),
    )


@bp.route("/json")
def json():
    df = pd.DataFrame(_rows(_filtered()), columns=COLUMNS)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return _send(
        df, f"favorites_{stamp}.json", "application/json",
        lambda d, b: b.write(
            d.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")),
    )
