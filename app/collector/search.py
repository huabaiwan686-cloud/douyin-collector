"""关键词/话题搜索 → 视频列表。

思路（wendell0218/tiktok_crawler 的"拦截搜索 API"模式，借鉴思路未复制代码）：
在已登录页面上下文中直接调抖音搜索接口，无需 DOM 解析。
- 关键词：GET /aweme/v1/web/general/search/single/ ?keyword&offset&count
- 话题页：直接打开 https://www.douyin.com/hashtag/<id> 读页面数据（TODO 二期实测）
"""
from __future__ import annotations

from playwright.async_api import Page

from ._api import api_get, ensure_douyin_page


def _norm_video(v: dict, source_keyword: str = "", source_topic: str = "") -> dict:
    aweme_id = str(v.get("aweme_id") or "")
    author = v.get("author") or {}
    sec_uid = author.get("sec_uid") or ""
    stats = v.get("statistics") or {}
    return {
        "aweme_id": aweme_id,
        "title": v.get("desc") or "",
        "video_url": f"https://www.douyin.com/video/{aweme_id}",
        "author_sec_uid": sec_uid,
        "author_nickname": author.get("nickname") or "",
        "digg_count": stats.get("digg_count") or 0,
        "comment_count": stats.get("comment_count") or 0,
        "source_keyword": source_keyword,
        "source_topic": source_topic,
    }


async def search_keyword(page: Page, keyword: str, offset: int = 0,
                         count: int = 10) -> dict:
    """关键词搜视频一页。返回 {videos:[...], has_more, cursor}。"""
    await ensure_douyin_page(page)
    data = await api_get(page, "/aweme/v1/web/general/search/single/", {
        "keyword": keyword,
        "offset": offset,
        "count": count,
        "is_filter_search": "0",
        "from_group_id": "0",
    })
    # 接口返回结构：data.data[].aweme_info（多版本兼容）
    raw = data.get("data") or []
    videos = []
    for item in raw:
        info = item.get("aweme_info") or item
        if info.get("aweme_id"):
            videos.append(_norm_video(info, source_keyword=keyword))
    cursor = data.get("cursor") or data.get("offset")
    return {
        "videos": videos,
        "has_more": bool(data.get("has_more", len(videos) >= count)),
        "cursor": cursor,
    }


async def search_all_keyword(page: Page, keyword: str, max_videos: int = 50,
                             on_progress=None) -> list[dict]:
    """关键词搜视频（翻页到上限）。"""
    out: list[dict] = []
    offset = 0
    while len(out) < max_videos:
        batch = await search_keyword(page, keyword, offset=offset)
        if not batch["videos"]:
            break
        out.extend(batch["videos"])
        if on_progress:
            on_progress(len(out))
        if not batch["has_more"]:
            break
        # offset 翻页（cursor 语义多变，用 offset 兜底）
        offset += len(batch["videos"])
        if offset > 500:  # 搜索接口实际可翻深度有限，保护性截断
            break
    return out[:max_videos]
