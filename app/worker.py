"""后台采集任务执行器：轮询 SearchTask，执行搜索→视频→评论→入库。

运行：python -m app.worker（systemd 常驻）
任务状态机：pending → running → done/failed；支持 paused/cancelled（轮询时检查）。
"""
from __future__ import annotations

import asyncio
import datetime
import json
import sys
import time
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml
from playwright.async_api import Page

from app.collector import browser as browser_mod
from app.collector import comments as comments_mod
from app.collector import profile as profile_mod
from app.collector import search as search_mod
from app.models import (
    Comment,
    ErrorLog,
    Favorite,
    Keyword,
    SearchTask,
    Topic,
    User,
    Video,
    db,
)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class Worker:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.crawl = cfg.get("crawl", {})
        self.delay = (
            self.crawl.get("request_delay_min_s", 1.5),
            self.crawl.get("request_delay_max_s", 3.5),
        )

    # ---------- 入库（upsert 去重） ----------
    def save_user(self, u: dict) -> User | None:
        if not u.get("sec_uid"):
            return None
        user, _ = User.get_or_create(
            sec_uid=u["sec_uid"],
            defaults={
                "nickname": u.get("nickname") or "未知",
                "homepage_url": u.get("homepage_url") or "",
            },
        )
        # 更新可变字段
        user.nickname = u.get("nickname") or user.nickname
        user.unique_id = u.get("unique_id") or user.unique_id
        user.bio = u.get("bio") or user.bio
        user.follower_count = u.get("follower_count") or 0
        user.avatar_url = u.get("avatar_url") or user.avatar_url
        user.uid = u.get("uid") or user.uid
        user.last_seen = utcnow()
        user.save()
        return user

    def save_video(self, v: dict, task: SearchTask) -> Video:
        video, created = Video.get_or_create(
            aweme_id=v["aweme_id"],
            defaults={
                "title": v.get("title") or "",
                "video_url": v.get("video_url") or "",
                "author_sec_uid": v.get("author_sec_uid") or "",
                "author_nickname": v.get("author_nickname") or "",
                "digg_count": v.get("digg_count") or 0,
                "comment_count": v.get("comment_count") or 0,
                "source_keyword": v.get("source_keyword") or "",
                "source_topic": v.get("source_topic") or "",
                "task": task,
            },
        )
        if not created:
            video.digg_count = v.get("digg_count") or video.digg_count
            video.comment_count = v.get("comment_count") or video.comment_count
            video.save()
        return video

    def save_comment(self, c: dict, video: Video, task: SearchTask,
                     parent_cid: str | None = None) -> None:
        user = self.save_user(c.get("user") or {})
        ct = c.get("create_time")
        create_time = (
            datetime.datetime.fromtimestamp(ct, tz=datetime.timezone.utc)
            if isinstance(ct, (int, float)) and ct > 0 else None
        )
        Comment.insert(
            cid=c["cid"],
            video=video,
            user=user,
            parent_cid=parent_cid,
            text=c.get("text") or "",
            digg_count=c.get("digg_count") or 0,
            reply_total=c.get("reply_total") or 0,
            create_time=create_time,
            ip_label=c.get("ip_label") or "",
            image_url=c.get("image_url") or "",
            source_keyword=task.keyword.text if task.keyword else "",
            source_topic=task.topic.name if task.topic else "",
        ).on_conflict(
            conflict_target=[Comment.cid],
            update={
                Comment.last_seen: utcnow(),
                Comment.digg_count: c.get("digg_count") or 0,
            },
        ).execute()

    def log_error(self, task: SearchTask | None, stage: str, msg: str, detail: str = ""):
        ErrorLog.create(task=task, stage=stage, message=msg[:2000], detail=detail[:4000])
        print(f"[ERROR][{stage}] {msg}")

    # ---------- 任务执行 ----------
    async def run_task(self, task: SearchTask, page: Page):
        task.status = "running"
        task.updated_at = utcnow()
        task.save()
        try:
            if task.task_type == "keyword" and task.keyword:
                await self.run_keyword(task, page, task.keyword.text)
            elif task.task_type == "topic" and task.topic:
                await self.run_topic(task, page, task.topic)
            elif task.task_type == "video" and task.video_url:
                await self.run_video_url(task, page, task.video_url)
            else:
                raise RuntimeError("任务类型或关联数据缺失")
            if task.status == "running":  # 未被外部暂停/取消
                task.status = "done"
        except Exception as e:
            task.status = "failed"
            task.error = str(e)[:2000]
            self.log_error(task, "task", str(e), traceback.format_exc()[-3000:])
        finally:
            task.updated_at = utcnow()
            task.save()

    def check_control(self, task: SearchTask) -> bool:
        """检查暂停/取消。返回 False 表示应停止。"""
        fresh = SearchTask.get_by_id(task.id)
        if fresh.status in ("paused", "cancelled"):
            task.status = fresh.status
            task.save()
            return False
        return True

    async def run_keyword(self, task: SearchTask, page: Page, keyword: str):
        max_videos = self.crawl.get("max_videos_per_keyword", 50)
        videos = await search_mod.search_all_keyword(page, keyword, max_videos=max_videos)
        task.total_videos = len(videos)
        task.save()
        for v in videos:
            if not self.check_control(task):
                return
            video = self.save_video(v, task)
            await self.collect_video_comments(task, page, video)
            task.done_videos += 1
            task.save()

    async def run_topic(self, task: SearchTask, page: Page, topic: Topic):
        # 一期：话题按关键词搜索平替（话题页直抓二期实测后接入）
        self.log_error(task, "topic", f"话题直抓待二期验证，暂用话题名做关键词搜索：{topic.name}")
        await self.run_keyword(task, page, topic.name)

    async def run_video_url(self, task: SearchTask, page: Page, url: str):
        # 从 URL 提取 aweme_id（/video/<id> 或 /note/<id>）
        import re
        m = re.search(r"/(?:video|note)/(\d+)", url)
        if not m:
            raise RuntimeError(f"无法从 URL 解析视频 ID：{url}")
        aweme_id = m.group(1)
        v = {
            "aweme_id": aweme_id, "title": "", "video_url": url,
            "author_sec_uid": "", "author_nickname": "",
            "digg_count": 0, "comment_count": 0,
            "source_keyword": "", "source_topic": "",
        }
        video = self.save_video(v, task)
        task.total_videos = 1
        task.save()
        await self.collect_video_comments(task, page, video)
        task.done_videos = 1
        task.save()

    async def collect_video_comments(self, task: SearchTask, page: Page, video: Video):
        max_comments = self.crawl.get("comments_per_video", 200)
        max_replies = self.crawl.get("replies_per_comment", 50)
        # 断点：从上次 cursor 继续
        cursor = video.comments_cursor or "0"
        done_here = 0
        while done_here < max_comments:
            if not self.check_control(task):
                return
            try:
                batch = await comments_mod.fetch_comments(
                    page, video.aweme_id, cursor=cursor, delay=self.delay)
            except Exception as e:
                self.log_error(task, "comments", f"视频 {video.aweme_id} 评论页失败：{e}")
                break
            if not batch["comments"]:
                break
            for c in batch["comments"]:
                self.save_comment(c, video, task)
                # 二级回复
                if c["reply_total"] > 0:
                    await self.collect_replies(task, page, video, c, max_replies)
                done_here += 1
                task.total_comments += 1
                if done_here >= max_comments:
                    break
            # 存断点
            video.comments_cursor = batch["cursor"]
            video.comments_seen = (video.comments_seen or 0) + len(batch["comments"])
            video.last_collect_at = utcnow()
            video.save()
            task.save()
            if not batch["has_more"]:
                break
            cursor = batch["cursor"]

    async def collect_replies(self, task: SearchTask, page: Page,
                              video: Video, comment: dict, max_replies: int):
        rcursor = "0"
        got = 0
        while got < min(comment["reply_total"], max_replies):
            if not self.check_control(task):
                return
            try:
                rb = await comments_mod.fetch_replies(
                    page, video.aweme_id, comment["cid"], cursor=rcursor, delay=self.delay)
            except Exception as e:
                self.log_error(task, "replies", f"评论 {comment['cid']} 回复失败：{e}")
                break
            if not rb["comments"]:
                break
            for r in rb["comments"]:
                self.save_comment(r, video, task, parent_cid=comment["cid"])
                task.total_comments += 1
                got += 1
            if not rb["has_more"]:
                break
            rcursor = rb["cursor"]

    # ---------- 主循环 ----------
    async def serve_forever(self):
        from app.collector.browser import get_context, is_logged_in
        cfg_b = self.cfg.get("browser", {})
        pw, ctx = await get_context(
            cfg_b.get("user_data_dir", "data/browser_profile"),
            headless=cfg_b.get("headless", False),
        )
        try:
            # 等登录：每 10 秒检查一次，直到登录成功
            while not await is_logged_in(ctx):
                print("等待扫码登录…（请在网页 设置→扫码登录 完成）")
                await asyncio.sleep(10)
            print("已登录。")
            page = await ctx.new_page()
            print("Worker 启动，轮询任务中…")
            while True:
                task = (SearchTask
                        .select()
                        .where(SearchTask.status == "pending")
                        .order_by(SearchTask.created_at)
                        .first())
                if task:
                    print(f"执行任务 #{task.id}（{task.task_type}）")
                    await self.run_task(task, page)
                else:
                    await asyncio.sleep(5)
        finally:
            await ctx.close()
            await pw.stop()


def main():
    with open("config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    db_path = cfg["database"]["path"]
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    from app.models import db as _db, TABLES
    _db.init(db_path)
    _db.connect()
    _db.create_tables(TABLES)
    worker = Worker(cfg)
    asyncio.run(worker.serve_forever())


if __name__ == "__main__":
    main()
