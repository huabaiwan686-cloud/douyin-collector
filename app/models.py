"""数据模型（peewee + SQLite）。

设计参考（MIT/Apache-2.0）：
- 去重/增量/断点：Yht20927/douyin-cli 的 upsert + first_seen/last_seen + 进度表模式
- 用户主键：Evil0ctal 的 sec_uid 稳定主键结论（数字 uid 会轮换）
"""
from __future__ import annotations

import datetime

from peewee import (
    AutoField,
    BigIntegerField,
    BooleanField,
    CharField,
    DateTimeField,
    ForeignKeyField,
    IntegerField,
    SqliteDatabase,
    TextField,
)

db = SqliteDatabase(None)  # 由 init_db / app factory 绑定路径


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


class BaseModel(__import__("peewee").Model):
    class Meta:
        database = db


class Keyword(BaseModel):
    """关键词（功能1）"""
    id = AutoField()
    text = CharField(unique=True, max_length=200)
    enabled = BooleanField(default=True)
    created_at = DateTimeField(default=utcnow)

    class Meta:
        table_name = "keywords"


class Topic(BaseModel):
    """话题（功能2）：名称或 hashtag 标识"""
    id = AutoField()
    name = CharField(unique=True, max_length=200)
    hashtag_id = CharField(null=True, max_length=200)
    enabled = BooleanField(default=True)
    created_at = DateTimeField(default=utcnow)

    class Meta:
        table_name = "topics"


class SearchTask(BaseModel):
    """搜索/采集任务：暂停/继续/重试/断点续采"""
    TASK_TYPES = ("keyword", "topic", "video")
    STATUS = ("pending", "running", "paused", "done", "failed", "cancelled")

    id = AutoField()
    task_type = CharField(max_length=20)          # keyword/topic/video
    keyword = ForeignKeyField(Keyword, null=True, backref="tasks", on_delete="CASCADE")
    topic = ForeignKeyField(Topic, null=True, backref="tasks", on_delete="CASCADE")
    video_url = CharField(null=True, max_length=500)  # 直接投喂视频链接
    status = CharField(max_length=20, default="pending")
    # 进度（断点续采）
    total_videos = IntegerField(default=0)
    done_videos = IntegerField(default=0)
    total_comments = IntegerField(default=0)
    cursor_state = TextField(null=True)           # JSON：各视频/接口的 cursor 快照
    error = TextField(null=True)
    retry_count = IntegerField(default=0)
    created_at = DateTimeField(default=utcnow)
    updated_at = DateTimeField(default=utcnow)

    class Meta:
        table_name = "search_tasks"
        indexes = ((("status",), False),)


class Video(BaseModel):
    """作品"""
    aweme_id = CharField(primary_key=True, max_length=64)
    title = TextField(null=True)
    video_url = CharField(max_length=500)
    author_sec_uid = CharField(null=True, max_length=128)
    author_nickname = CharField(null=True, max_length=100)
    digg_count = IntegerField(default=0)
    comment_count = IntegerField(default=0)
    # 来源
    source_keyword = CharField(null=True, max_length=200)
    source_topic = CharField(null=True, max_length=200)
    task = ForeignKeyField(SearchTask, null=True, backref="videos", on_delete="SET NULL")
    # 采集进度
    comments_seen = IntegerField(default=0)       # 已采一级评论数（断点）
    comments_cursor = CharField(null=True, max_length=64)
    last_collect_at = DateTimeField(null=True)
    created_at = DateTimeField(default=utcnow)

    class Meta:
        table_name = "videos"
        indexes = (
            (("source_keyword",), False),
            (("source_topic",), False),
        )


class User(BaseModel):
    """评论者/创作者：sec_uid 做稳定主键（数字 uid 会轮换，不可靠）"""
    sec_uid = CharField(primary_key=True, max_length=128)
    uid = CharField(null=True, max_length=64)     # 数字 uid，仅参考
    nickname = CharField(max_length=100)
    unique_id = CharField(null=True, max_length=100)  # 抖音号（可为空/可改）
    homepage_url = CharField(max_length=500)
    bio = TextField(null=True)
    follower_count = IntegerField(default=0)
    avatar_url = CharField(null=True, max_length=500)
    verified = BooleanField(default=False)         # 身份是否确认（昵称相同≠同一人）
    first_seen = DateTimeField(default=utcnow)
    last_seen = DateTimeField(default=utcnow)

    class Meta:
        table_name = "users"
        indexes = ((("nickname",), False),)


class Comment(BaseModel):
    """一级评论 + 楼中楼回复（parent_cid 为空=一级）"""
    cid = CharField(primary_key=True, max_length=64)
    video = ForeignKeyField(Video, backref="comments", on_delete="CASCADE")
    user = ForeignKeyField(User, null=True, backref="comments", on_delete="SET NULL")
    parent_cid = CharField(null=True, max_length=64)  # 空=一级评论
    reply_to_cid = CharField(null=True, max_length=64)
    text = TextField()
    digg_count = IntegerField(default=0)
    reply_total = IntegerField(default=0)          # 楼中楼回复数（平台返回）
    create_time = DateTimeField(null=True)        # 评论发布时间（平台返回则填）
    ip_label = CharField(null=True, max_length=64)
    image_url = CharField(null=True, max_length=500)
    # 来源
    source_keyword = CharField(null=True, max_length=200)
    source_topic = CharField(null=True, max_length=200)
    # 增量
    first_seen = DateTimeField(default=utcnow)
    last_seen = DateTimeField(default=utcnow)

    class Meta:
        table_name = "comments"
        indexes = (
            (("video", "create_time"), False),
            (("user",), False),
            (("parent_cid",), False),
            (("source_keyword",), False),
        )


class Favorite(BaseModel):
    """一键收藏主页（功能5）"""
    REVIEW_STATUS = ("pending", "approved", "rejected")  # 待审核/符合条件/不符合条件

    id = AutoField()
    user = ForeignKeyField(User, backref="favorites", on_delete="CASCADE")
    homepage_url = CharField(max_length=500)      # 收藏时的快照（防用户改名）
    nickname_snapshot = CharField(max_length=100)
    # 来源
    source_keyword = CharField(null=True, max_length=200)
    source_topic = CharField(null=True, max_length=200)
    source_video_url = CharField(null=True, max_length=500)
    trigger_comment = TextField(null=True)        # 触发收藏的那条评论
    # 管理
    note = TextField(null=True)                   # 自定义备注
    tags = CharField(null=True, max_length=300)   # 逗号分隔标签
    review_status = CharField(max_length=20, default="pending")
    created_at = DateTimeField(default=utcnow)

    class Meta:
        table_name = "favorites"
        indexes = (
            (("user",), True),                    # 同一用户自动去重
            (("review_status",), False),
            (("source_keyword",), False),
        )


class ErrorLog(BaseModel):
    """采集错误日志"""
    id = AutoField()
    task = ForeignKeyField(SearchTask, null=True, backref="errors", on_delete="SET NULL")
    level = CharField(max_length=20, default="error")
    stage = CharField(max_length=100)             # search/videos/comments/replies/profile
    message = TextField()
    detail = TextField(null=True)
    created_at = DateTimeField(default=utcnow)

    class Meta:
        table_name = "error_logs"
        indexes = ((("task",), False),)


TABLES = [Keyword, Topic, SearchTask, Video, User, Comment, Favorite, ErrorLog]


def init_database(path: str) -> None:
    db.init(path)
    db.connect()
    db.create_tables(TABLES)
    db.close()
