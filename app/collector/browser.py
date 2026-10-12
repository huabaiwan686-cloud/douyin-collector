"""浏览器管理：Playwright 持久化上下文 + 扫码登录。

登录流程参考 Annoyingwinter/douyin-comment-screen 的 login_check.py（MIT）：
首次运行弹可见浏览器，用户用小号扫码一次，登录态存 user_data_dir，
之后重启自动恢复，无需重复扫码。
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from playwright.async_api import BrowserContext, async_playwright


async def ensure_login(user_data_dir: str, headless: bool = False) -> bool:
    """返回 True 表示已登录。未登录时弹浏览器等扫码（阻塞直到登录或 Ctrl+C）。"""
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(
            user_data_dir,
            headless=headless,
            viewport={"width": 1366, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
            ),
        )
        page = await ctx.new_page()
        await page.goto("https://www.douyin.com/", wait_until="domcontentloaded")
        await page.wait_for_timeout(3000)
        if await is_logged_in(ctx):
            print("已登录，无需扫码。")
            await ctx.close()
            return True
        print("=" * 50)
        print("请用抖音小号扫码登录浏览器弹窗（60 秒轮询，最多等 10 分钟）。")
        print("=" * 50)
        for _ in range(120):
            await page.wait_for_timeout(5000)
            if await is_logged_in(ctx):
                print("登录成功，登录态已保存。")
                await ctx.close()
                return True
        print("等待超时，未检测到登录。")
        await ctx.close()
        return False


async def is_logged_in(ctx: BrowserContext) -> bool:
    """登录态检测：右上角不再是登录按钮 / 能读到用户 cookie。"""
    cookies = await ctx.cookies("https://www.douyin.com/")
    names = {c["name"] for c in cookies}
    # sessionid / sid_tt 为登录后 Cookie；仅 ttwid/__ac_nonce 为访客
    return bool(names & {"sessionid", "sid_tt", "sessionid_ss"})


async def get_context(user_data_dir: str, headless: bool = False) -> tuple:
    """供采集引擎使用：返回 (playwright, context)。调用方负责 close。"""
    pw = await async_playwright().start()
    ctx = await pw.chromium.launch_persistent_context(
        user_data_dir,
        headless=headless,
        viewport={"width": 1366, "height": 900},
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
        ),
    )
    return pw, ctx


if __name__ == "__main__":
    # python -m app.collector.browser --login
    data_dir = sys.argv[sys.argv.index("--dir") + 1] if "--dir" in sys.argv else "data/browser_profile"
    headless = "--headless" in sys.argv
    ok = asyncio.run(ensure_login(data_dir, headless=headless))
    sys.exit(0 if ok else 1)
