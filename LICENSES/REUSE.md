# 第三方代码复用及许可证清单

本项目复用了以下开源项目的代码/设计思路，均保留原许可证。

## 直接复用代码（MIT）
1. **hskyer/douyin-comments** — https://github.com/hskyer/douyin-comments
   复用：Playwright 页面上下文调抖音接口模式、断点续爬思路
2. **Yht20927/douyin-cli** — https://github.com/Yht20927/douyin-cli
   复用：评论/回复/用户作品接口参数、upsert 去重 + first_seen/last_seen 增量表结构设计
3. **Annoyingwinter/douyin-comment-screen** — https://github.com/Annoyingwinter/douyin-comment-screen
   复用：扫码登录等待流程设计
4. **CyberMemoir/douyin-studio** — https://github.com/CyberMemoir/douyin-studio
   复用：搜索工作台 UI 交互参考

## 直接复用代码（Apache-2.0）
5. **Evil0ctal/Douyin_TikTok_Download_API** — https://github.com/Evil0ctal/Douyin_TikTok_Download_API
   复用：主页/作品接口参数与字段映射（sec_uid 稳定主键）

## 依赖库
- peewee（MIT）、pandas（BSD-3-Clause）、Flask（BSD-3-Clause）、Playwright（Apache-2.0）、openpyxl（MIT）、PyYAML（MIT）

## 仅借鉴思路（未复制代码）
- wendell0218/tiktok_crawler（无许可证）：拦截搜索 API 响应的思路
- NanmiCoder/MediaCrawler（非商业许可 1.1）：分页与登录设计思路
- NewComer00/douyin-comment-picker（GPLv2 禁商用）：关键词→视频→评论筛选的产品逻辑

## 明确排除
- creatorhub（无 LICENSE）、alphaply/DouyinComments（无许可证+接口失效）
- TikHub 系（GPL-3.0 / 付费 API）、mashukui/douyin_one_spider（付费墙）
- mashukui/douyin_one_spider、VideoData/DY-Data、erma0/douyin（空壳/已死）
