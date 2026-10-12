"""网页扫码登录：Playwright 打开抖音登录页，截取二维码图片供手机扫码。

供 /settings/login 页面调用。无 SSH 时的登录方案。
"""
from __future__ import annotations

import asyncio
import base64
import threading
import time

_qr_cache: dict = {"img": None, "ts": 0, "done": False}
_lock = threading.Lock()


def _capture_qr(user_data_dir: str, headless: bool):
    """后台线程：打开浏览器抓二维码。"""
    from playwright.async_api import async_playwright

    async def _run():
        async with async_playwright() as pw:
            ctx = await pw.chromium.launch_persistent_context(
                user_data_dir,
                headless=headless,
                viewport={"width": 1366, "height": 900},
            )
            # 先检查是否已登录
            from .browser import is_logged_in
            if await is_logged_in(ctx):
                with _lock:
                    _qr_cache["done"] = True
                await ctx.close()
                return
            page = await ctx.new_page()
            await page.goto("https://www.douyin.com/", wait_until="domcontentloaded")
            await page.wait_for_timeout(4000)
            # 找二维码图片（抖音登录弹窗的 QR）
            img_b64 = None
            for sel in ["canvas", "img[src*='qr']", "[class*='qrcode'] img"]:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        shot = await el.screenshot()
                        img_b64 = base64.b64encode(shot).decode()
                        break
                except Exception:
                    continue
            if not img_b64:
                # 兜底：全屏截图
                shot = await page.screenshot()
                img_b64 = base64.b64encode(shot).decode()
            with _lock:
                _qr_cache["img"] = img_b64
                _qr_cache["ts"] = time.time()
            # 等待扫码（最多 5 分钟），轮询登录态
            for _ in range(60):
                await asyncio.sleep(5)
                if await is_logged_in(ctx):
                    with _lock:
                        _qr_cache["done"] = True
                    break
            await ctx.close()

    asyncio.run(_run())


def start_qr_capture(user_data_dir: str, headless: bool = True) -> None:
    with _lock:
        _qr_cache.update({"img": None, "ts": 0, "done": False})
    t = threading.Thread(target=_capture_qr, args=(user_data_dir, headless), daemon=True)
    t.start()


def get_qr_status() -> dict:
    with _lock:
        return dict(_qr_cache)
