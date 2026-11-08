"""抓 Codeforces 数据，写成 codeforces.json。

用官方公开 API（不用 key）：
  user.info     → 当前 rating / 最高 rating / 段位
  user.status   → 所有提交，用来数「过了多少道不同的题」

抓不到就沿用上一次的 codeforces.json；没有就跳过（卡片上不显示这一行）。
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (compatible; profile-card/1.0)"}
API = "https://codeforces.com/api/"


def get(path: str) -> dict:
    req = urllib.request.Request(API + path, headers=UA)
    with urllib.request.urlopen(req, timeout=45) as r:
        j = json.loads(r.read().decode("utf-8"))
    if j.get("status") != "OK":
        raise RuntimeError(j.get("comment") or "Codeforces 返回非 OK")
    return j["result"]


def main():
    cfg = (ROOT / "config.toml").read_text(encoding="utf-8")
    m = re.search(r'^handle\s*=\s*"([^"]+)"', cfg, re.M)
    handle = m.group(1) if m else ""

    out_path = ROOT / "codeforces.json"
    old = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}

    if not handle:
        print("config.toml 里没写 [codeforces] handle，跳过")
        return

    data = dict(old)
    try:
        info = get(f"user.info?handles={handle}")[0]
        data.update({
            "handle": info.get("handle", handle),
            "rating": info.get("rating"),
            "max_rating": info.get("maxRating"),
            "rank": info.get("rank", ""),
            "max_rank": info.get("maxRank", ""),
            "organization": info.get("organization", ""),
            "updated": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M"),
        })
    except Exception as e:                       # noqa: BLE001
        print(f"rating 没抓到（{e}），沿用旧的")
        if not old:
            return

    try:
        subs = get(f"user.status?handle={handle}")
        solved = {(s["problem"].get("contestId"), s["problem"].get("index"))
                  for s in subs if s.get("verdict") == "OK"}
        data["solved"] = len(solved)
        data["submissions"] = len(subs)
    except Exception as e:                       # noqa: BLE001
        print(f"提交记录没抓到（{e}），solved 先不更新")

    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"CF {data.get('handle')}：{data.get('rating')}（最高 {data.get('max_rating')}）"
          f" {data.get('rank')} · solved {data.get('solved', '?')}")


if __name__ == "__main__":
    main()
