# RSSForge（模板）

把 GitHub 变成你自己的 RSS 生成器：fork → 加订阅 → Actions 定时抓取 → 生成 feed.xml → 任何 RSS 阅读器直接订阅。**零服务器、完全免费。**

## 快速开始（5 分钟）

1. 右上角 **Fork** 本仓库（fork 后到 Actions 页点 "I understand my workflows, go ahead and enable them"）
2. 编辑 `sites.yaml`，照 `sites.yaml.example` 的格式加站点
3. **Actions → "站点抓取（仅抓取模式）" → Run workflow** 手动跑一次（之后每 30 分钟自动跑）
4. 你的订阅地址（直接贴进 Folo / Inoreader / 任何阅读器）：

```
https://raw.githubusercontent.com/<你的用户名>/RSSForge/main/feed.xml
```

## 它做了什么

- `crawl.py` 抓各站列表页（羊毛/线报/折扣站点）
- `feed.py` 精炼：过滤分类导航页、乱码、过短文本；命中价格（x元/x折/券后/到手）的排前面；去重
- 产出三件套：`feed.xml`（全量流）、`feed.json`、`daily_essence.json`（带价格的每日 top20）
- Actions 每 30 分钟自动循环，结果直接提交回你自己的仓库

## 可选：把 feed 同步到另一个公开库

想让原始数据私有、feed 公开：

1. 建一个公开库放 feed
2. 本仓库 Settings → Secrets → Actions 新建 `FEED_PUSH_TOKEN`（一个有目标库 contents:write 的 PAT）
3. Settings → Actions → Variables 新建 `FEED_REPO` = `你的用户名/那个公开库`

之后每次运行会自动把 feed.xml 推到公开库（`tools/sync_feed.py`）。

## 提醒

- 抓取行为遵守各站规则，频率已很低（每站点每小时≤1 页），别改成疯狂轮询
- GPL/自用随意；抓取内容版权归原站
