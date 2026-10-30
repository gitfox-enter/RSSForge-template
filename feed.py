#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RSSForge 后处理层：读 items_latest.json → 过滤+价格打分 → 出 feed.xml / feed.json / daily_essence.json
纯标准库，不 import crawler 包，避免破坏抓取管线。
用法: python feed.py [输入json] [输出目录]
"""
import json, re, os, sys, hashlib, datetime
from xml.sax.saxutils import escape

INPUT = sys.argv[1] if len(sys.argv) > 1 else "items_latest.json"
OUTDIR = sys.argv[2] if len(sys.argv) > 2 else "."
TOP_FEED = 300
TOP_ESSENCE = 20

# 导航/分类/列表页（不是 deal）：直接丢
NAV_PATTERNS = ("category-", "weibo-chaohua", "/things/", "forumdisplay",
                "/tag/", "mod=forumdisplay", "mod=forumdisplay")

# 功能性/分类噪音文字（来自各站 skip 词 + 实测泄漏的站点/分类名）
SKIP_WORDS = {
    "首页", "关于", "联系我们", "搜索", "登录", "注册", "下一页", "上一页",
    "更多", "最新", "热门", "分类", "标签", "回复", "评论", "浏览", "推荐",
    "点赞", "收藏", "设为首页", "快捷导航", "返回顶部", "返回首页", "关于我们",
    "葫芦侠三楼", "小刀娱乐网", "更新较慢活动", "免费赚钱中心", "爱Q生活网",
    "生活", "活动", "娱乐", "其它", "其他", "综合", "资源", "软件", "游戏",
}

PRICE_RE = re.compile(
    r'(\d+(\.\d+)?\s*(元|块|￥|¥|刀)|(\d+(\.\d+)?)\s*折|券后|到手|免邮|0元|白菜|'
    r'神价|历史低价|半价|立减|满减|百亿补贴|直降|特价|秒杀)',
    re.I)
DEAL_KW = re.compile(r'(券|优惠|活动|福利|捡漏|羊毛|线报|红包|抽奖|补贴|好价)', re.I)


def is_nav(url):
    u = url.lower()
    return any(p in u for p in NAV_PATTERNS)


def parse_time(t):
    if not t:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(t.strip(), fmt)
        except Exception:
            pass
    return None


def load_items(path):
    try:
        d = json.load(open(path, encoding="utf-8"))
    except Exception as e:
        print("读取失败:", e)
        return []
    if isinstance(d, dict):
        return d.get("items", [])
    if isinstance(d, list):
        return d
    return []


def refine(items):
    out, seen = [], set()
    for it in items:
        url = (it.get("url") or "").strip()
        text = (it.get("text") or "").strip()
        if not url or not text:
            continue
        if is_nav(url):
            continue
        if text in SKIP_WORDS:
            continue
        if len(text) < 3:
            continue
        if text in seen:
            continue
        seen.add(text)
        has_price = bool(PRICE_RE.search(text))
        has_deal = bool(DEAL_KW.search(text))
        dt = parse_time(it.get("time") or it.get("first_seen_at"))
        score = (2 if has_price else 0) + (1 if has_deal else 0)
        rec = dict(it)
        rec["text"], rec["url"] = text, url
        rec["has_price"], rec["score"], rec["_dt"] = has_price, score, dt
        out.append(rec)
    return out


def sort_key(x):
    dt = x.get("_dt")
    ts = dt.timestamp() if dt else 0
    return (x.get("score", 0), ts)


def rfc822(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0800") if dt else ""


def build(items):
    items = sorted(items, key=sort_key, reverse=True)
    feed_items = items[:TOP_FEED]
    essence = [x for x in items if x.get("has_price")][:TOP_ESSENCE]
    if not essence:
        essence = items[:TOP_ESSENCE]
    return feed_items, essence


def write_xml(feed_items, outdir):
    p = ['<?xml version="1.0" encoding="UTF-8"?>',
         '<rss version="2.0"><channel>',
         '<title>RSSForge 羊毛线报</title>',
         '<link>https://github.com/gitfox-enter/RSSForge</link>',
         '<description>RSSForge 精炼羊毛线报（已过滤导航页/乱码，价格优先）</description>',
         '<language>zh-CN</language>']
    for it in feed_items:
        guid = hashlib.md5(it["url"].encode()).hexdigest()
        p.append('<item>')
        p.append('<title>%s</title>' % escape(it["text"][:120]))
        p.append('<link>%s</link>' % escape(it["url"]))
        p.append('<guid isPermaLink="false">%s</guid>' % guid)
        pub = rfc822(it.get("_dt"))
        if pub:
            p.append('<pubDate>%s</pubDate>' % pub)
        p.append('<description>%s | %s</description>' % (
            escape(it.get("source") or ""), escape((it.get("time") or "")[:19])))
        p.append('</item>')
    p.append('</channel></rss>')
    open(os.path.join(outdir, "feed.xml"), "w", encoding="utf-8").write("\n".join(p))


def write_json(feed_items, essence, outdir):
    payload = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "count": len(feed_items),
        "items": [{"text": i["text"], "url": i["url"], "source": i.get("source"),
                  "time": i.get("time"), "has_price": i.get("has_price")}
                 for i in feed_items],
    }
    json.dump(payload, open(os.path.join(outdir, "feed.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    ess = [{"text": i["text"], "url": i["url"], "source": i.get("source"), "time": i.get("time")}
           for i in essence]
    json.dump({"items": ess}, open(os.path.join(outdir, "daily_essence.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


def main():
    items = load_items(INPUT)
    refined = refine(items)
    feed_items, essence = build(refined)
    write_xml(feed_items, OUTDIR)
    write_json(feed_items, essence, OUTDIR)
    print("输入 %d → 精炼 %d → feed %d → 精华 %d" % (
        len(items), len(refined), len(feed_items), len(essence)))


if __name__ == "__main__":
    main()
