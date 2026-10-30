#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本地 feed 产物同步到公开 feed 库（跨仓库推送）。
环境变量：FEED_PUSH_TOKEN（有目标库 contents:write 的 PAT）、FEED_REPO（owner/repo）。
未配置则静默跳过。"""
import base64, json, os, urllib.request, urllib.error

REPO = os.environ.get("FEED_REPO", "")
TOK = os.environ.get("FEED_PUSH_TOKEN", "")
if not REPO or not TOK:
    print("未配置 FEED_REPO/FEED_PUSH_TOKEN，跳过同步")
    raise SystemExit(0)


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request("https://api.github.com" + path, data=data, method=method,
        headers={"Authorization": "Bearer " + TOK, "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=30) as x:
            return x.getcode(), json.load(x)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")[:200]
    except Exception as e:
        return "net", str(e)


ok = 0
for f in ("feed.xml", "feed.json", "daily_essence.json"):
    if not os.path.exists(f):
        continue
    c, j = req("GET", f"/repos/{REPO}/contents/{f}?ref=main")
    sha = j.get("sha") if isinstance(j, dict) and "sha" in j else None
    body = {"message": "sync " + f,
            "content": base64.b64encode(open(f, "rb").read()).decode(),
            "branch": "main"}
    if sha:
        body["sha"] = sha
    c2, _ = req("PUT", f"/repos/{REPO}/contents/{f}", body)
    print(f, "同步:", c2)
    if c2 in (200, 201):
        ok += 1
print("完成", ok)
