# 抖音评论搜索与创作者收藏工具

基于 Playwright 页面上下文采集抖音公开数据：关键词/话题搜索 → 视频 → 评论树（一级+楼中楼）→ 创作者主页 → 一键收藏 → 批量导出。

## 技术栈
- Python 3.12 + Flask（Web UI）
- Playwright（真浏览器，扫码登录一次持久化，页面上下文调抖音接口）
- peewee + SQLite（初期零运维，预留 PostgreSQL 迁移）
- pandas（CSV/Excel/JSON 导出）

## 复用代码及许可证
| 来源 | 许可证 | 复用内容 |
|---|---|---|
| hskyer/douyin-comments | MIT | Playwright 页面上下文采集模式、断点续爬思路 |
| Yht20927/douyin-cli | MIT | 接口参数、upsert 去重+增量表结构设计 |
| Annoyingwinter/douyin-comment-screen | MIT | 扫码登录等待流程 |
| Evil0ctal/Douyin_TikTok_Download_API | Apache-2.0 | 主页/作品接口参数与字段映射 |
| peewee / pandas | MIT / BSD-3 | ORM / 导出 |

## 快速启动（服务器）
```bash
# 1. 安装依赖
pip install -r requirements.txt
playwright install chromium
# 如需 headless 服务器：apt install xvfb

# 2. 配置
cp config.example.yaml config.yaml
# 编辑 config.yaml（如端口、采集间隔）

# 3. 初始化数据库
python scripts/init_db.py

# 4. 扫码登录（首次）
python -m app.collector.browser --login

# 5. 启动 Web 服务
python run.py
# 浏览器打开 http://服务器IP:5000
```

## 目录结构
```
app/
  models.py          # peewee 数据模型
  collector/         # 采集引擎（Playwright）
    browser.py       # 登录 + 持久化浏览器上下文
    search.py        # 关键词/话题搜索
    comments.py      # 一级评论 + 楼中楼回复
    profile.py       # 用户主页 + 作品
  routes/            # Flask 蓝图（10 个页面）
  templates/         # Jinja2 模板
```

## 合规说明
- 只采集登录账号有权访问的公开数据
- 不绕过验证码/访问权限，不采集私密数据
- 采集频率保守，随机延迟，仅建议用小号
