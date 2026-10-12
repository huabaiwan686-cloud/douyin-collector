"""创作者主页 + 公开作品获取。

接口参数与字段映射参考 Evil0ctal/Douyin_TikTok_Download_API（Apache-2.0）：
- 主页：GET /aweme/v1/web/user/profile/other/ ?sec_user_id
- 作品：GET /aweme/v1/web/aweme/post/ ?sec_user_id&cursor&count
稳定主键用 sec_uid（数字 uid 会轮换，不可靠）。
"""
from __future__ import annotations

from playwright.async_api import Page

from ._api import api_get, ensure_douyin_page


def norm_profile(u: dict) -> dict:
    sec_uid = u.get("sec_uid") or ""
    return {
        "sec_uid": sec_uid,
        "uid": str(u.get("uid") or ""),
        "nickname": u.get("nickname") or "未知",
        "unique_id": u.get("unique_id") or u.get("short_id") or "",
        "homepage_url": f"https://www.douyin.com/user/{sec_uid}" if sec_uid else "",
        "bio": u.get("signature") or "",
        "follower_count": u.get("follower_count") or 0,
        "following_count": u.get("following_count") or 0,
        "aweme_count": u.get("aweme_count") or 0,
        "avatar_url": (u.get("avatar_larger") or {}).get("url_list", [""])[0]
        if isinstance(u.get("avatar_larger"), dict) else "",
    }


async def fetch_profile(page: Page, sec_uid: str) -> dict:
    """取用户主页公开资料。"""
    await ensure_douyin_page(page)
    data = await api_get(page, "/aweme/v1/web/user/profile/other/", {
        "sec_user_id": sec_uid,
    })
    user = data.get("user") or {}
    if not user:
        raise RuntimeError(f"主页无数据（sec_uid={sec_uid[:12]}…，可能私密/注销）")
    return norm_profile(user)


async def fetch_posts(page: Page, sec_uid: str, cursor: str = "0",
                      count: int = 18) -> dict:
    """取用户公开作品一页。"""
    await ensure_douyin_page(page)
    data = await api_get(page, "/aweme/v1/web/aweme/post/", {
        "sec_user_id": sec_uid,
        "cursor": cursor,
        "count": count,
    })
    videos = []
    for v in (data.get("aweme_list") or []):
        aweme_id = str(v.get("aweme_id") or "")
        cover = (v.get("video") or {}).get("cover") or {}
        videos.append({
            "aweme_id": aweme_id,
            "title": v.get("desc") or "",
            "video_url": f"https://www.douyin.com/video/{aweme_id}",
            "cover_url": (cover.get("url_list") or [""])[0],
            "digg_count": (v.get("statistics") or {}).get("digg_count") or 0,
        })
    return {
        "videos": videos,
        "cursor": str(data.get("cursor", "0")),
        "has_more": bool(data.get("has_more")),
    }
