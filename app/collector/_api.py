"""页面上下文 API 调用：在已登录的 douyin.com 页面里用 fetch 调接口。

原理（hskyer/douyin-comments + Yht20927/douyin-cli，均为 MIT）：
浏览器页面自带登录 Cookie + Referer，直接 fetch 抖音 web 接口，无需破解签名。
"""
from __future__ import annotations

import json
import random
import time
from urllib.parse import urlencode

from playwright.async_api import Page

BASE_Q = {
    "device_platform": "webapp",
    "aid": "6383",
    "channel": "channel_pc_web",
    "version_code": "170400",
    "version_name": "17.4.0",
    "cookie_enabled": "true",
    "browser_language": "zh-CN",
    "browser_platform": "Win32",
    "browser_name": "Chrome",
    "browser_online": "true",
    "os_name": "Windows",
    "os_version": "10",
    "platform": "PC",
}


async def api_get(page: Page, path: str, params: dict, delay: tuple[float, float] = (1.5, 3.5)) -> dict:
    """在页面上下文中 GET JSON 接口，带随机延迟与重试。"""
    # 保守的请求间隔（防风控）
    time.sleep(random.uniform(*delay))
    qs = urlencode({**BASE_Q, **{k: str(v) for k, v in params.items()}})
    url = f"{path}?{qs}"
    js = f"""fetch({json.dumps(url)}, {{credentials: 'include'}})
        .then(r => r.text().then(t => ({{status: r.status, body: t}})))"""
    for attempt in range(3):
        try:
            res = await page.evaluate(js)
            if res["status"] != 200 or not res["body"].strip():
                time.sleep(2 ** attempt * 2)
                continue
            data = json.loads(res["body"])
            if isinstance(data, dict) and data.get("status_msg") == "blocked":
                raise RuntimeError("接口被风控拦截（blocked），请降低频率或稍后重试")
            return data
        except RuntimeError:
            raise
        except Exception:
            time.sleep(2 ** attempt * 2)
    raise RuntimeError(f"接口请求失败（3 次重试）：{path}")


async def ensure_douyin_page(page: Page) -> None:
    """确保当前在 douyin.com 页面上下文（fetch 相对路径才带对 Cookie/Referer）。"""
    if "douyin.com" not in (page.url or ""):
        await page.goto("https://www.douyin.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(2000)
