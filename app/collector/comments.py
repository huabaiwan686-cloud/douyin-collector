"""评论采集：一级评论 + 楼中楼二级回复。

接口（Yht20927/douyin-cli，MIT；hskyer/douyin-comments，MIT）：
- 一级：GET /aweme/v1/web/comment/list/      ?aweme_id&cursor&count&item_type=0
- 二级：GET /aweme/v1/web/comment/list/reply/ ?item_id&comment_id&cursor&count&item_type=0
"""
from __future__ import annotations

from playwright.async_api import Page

from ._api import api_get, ensure_douyin_page


def _norm_user(u: dict | None) -> dict:
    u = u or {}
    sec_uid = u.get("sec_uid") or ""
    # 主页链接：优先 sec_uid（稳定），回退短链
    homepage = f"https://www.douyin.com/user/{sec_uid}" if sec_uid else ""
    return {
        "sec_uid": sec_uid,
        "uid": str(u.get("uid") or u.get("short_id") or ""),
        "nickname": u.get("nickname") or "未知",
        "unique_id": u.get("unique_id") or "",
        "homepage_url": homepage,
        "avatar_url": (u.get("avatar_thumb") or {}).get("url_list", [""])[0]
        if isinstance(u.get("avatar_thumb"), dict) else "",
        "bio": u.get("signature") or "",
        "follower_count": u.get("follower_count") or 0,
    }


def _norm_comment(c: dict) -> dict:
    return {
        "cid": str(c.get("cid")),
        "text": c.get("text") or "",
        "digg_count": c.get("digg_count") or 0,
        "reply_total": c.get("reply_comment_total") or 0,
        "create_time": c.get("create_time"),  # Unix 时间戳
        "ip_label": c.get("ip_label") or "",
        "image_url": (c.get("image_list") or [{}])[0].get("url_list", [""])[0]
        if c.get("image_list") else "",
        "user": _norm_user(c.get("user")),
    }


async def fetch_comments(page: Page, aweme_id: str, cursor: str = "0",
                         count: int = 20, delay=(1.5, 3.5)) -> dict:
    """取一页一级评论。返回 {comments:[...], cursor, has_more}。"""
    await ensure_douyin_page(page)
    data = await api_get(page, "/aweme/v1/web/comment/list/", {
        "aweme_id": aweme_id, "cursor": cursor, "count": count, "item_type": "0",
    }, delay=delay)
    return {
        "comments": [_norm_comment(c) for c in (data.get("comments") or [])],
        "cursor": str(data.get("cursor", "0")),
        "has_more": bool(data.get("has_more")),
        "total": data.get("total") or 0,
    }


async def fetch_replies(page: Page, aweme_id: str, comment_id: str,
                        cursor: str = "0", count: int = 20, delay=(1.5, 3.5)) -> dict:
    """取一页楼中楼回复。"""
    await ensure_douyin_page(page)
    data = await api_get(page, "/aweme/v1/web/comment/list/reply/", {
        "item_id": aweme_id, "comment_id": comment_id,
        "cursor": cursor, "count": count, "item_type": "0",
    }, delay=delay)
    return {
        "comments": [_norm_comment(c) for c in (data.get("comments") or [])],
        "cursor": str(data.get("cursor", "0")),
        "has_more": bool(data.get("has_more")),
    }


async def fetch_all_comments(page: Page, aweme_id: str, max_comments: int = 200,
                             max_replies_each: int = 50,
                             on_progress=None) -> list[dict]:
    """采完一个视频的评论树（一级 + 每条的二级）。带断点恢复由调用方用 cursor 实现。"""
    tree: list[dict] = []
    cursor = "0"
    while len(tree) < max_comments:
        batch = await fetch_comments(page, aweme_id, cursor=cursor)
        if not batch["comments"]:
            break
        for c in batch["comments"]:
            # 二级回复
            replies: list[dict] = []
            if c["reply_total"] > 0:
                rcursor = "0"
                while len(replies) < min(c["reply_total"], max_replies_each):
                    rb = await fetch_replies(page, aweme_id, c["cid"], cursor=rcursor)
                    if not rb["comments"]:
                        break
                    replies.extend(rb["comments"])
                    if not rb["has_more"]:
                        break
                    rcursor = rb["cursor"]
            c["replies"] = replies
            tree.append(c)
            if on_progress:
                on_progress(len(tree))
            if len(tree) >= max_comments:
                break
        if not batch["has_more"]:
            break
        cursor = batch["cursor"]
    return tree
