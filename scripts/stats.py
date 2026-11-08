"""抓 GitHub 上的公开数据，写成 stats.json。

只用公开页面，不需要 token：贡献日历和仓库列表都是 HTML，正则抠出来就行。
抓失败就保持原来的 stats.json 不动，别把流水线搞挂。
"""
from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (compatible; profile-card/1.0)"}


def get(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def streak(levels: dict[str, int]) -> tuple[int, int]:
    today = date.today()
    d = today if levels.get(today.isoformat(), 0) else today - timedelta(days=1)
    cur = 0
    while levels.get(d.isoformat(), 0) > 0:
        cur += 1
        d -= timedelta(days=1)
    best = run = 0
    for k in sorted(levels):
        run = run + 1 if levels[k] > 0 else 0
        best = max(best, run)
    return cur, best


def main():
    cfg = (ROOT / "config.toml").read_text(encoding="utf-8")
    login = re.search(r'^login\s*=\s*"([^"]+)"', cfg, re.M).group(1)
    old = json.loads((ROOT / "stats.json").read_text(encoding="utf-8")) if (ROOT / "stats.json").exists() else {}

    try:
        html = get(f"https://github.com/users/{login}/contributions")
        pairs = re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"\s+(?:id="[^"]*"\s+)?data-level="(\d)"', html)
        if not pairs:
            pairs = re.findall(r'data-date="(\d{4}-\d{2}-\d{2})"[\s\S]{0,300}?data-level="(\d)"', html)
        levels = {d: int(l) for d, l in pairs}
        total = re.search(r"([\d,]+)\s*contributions?\s*in the last year", html)
        if not levels:
            raise ValueError("没解析出贡献日历")

        days = sorted(levels)
        start = date.fromisoformat(days[0])
        start -= timedelta(days=(start.weekday() + 1) % 7)      # 对齐到周日
        end = date.fromisoformat(days[-1])
        flat, d = [], start
        while d <= end:
            flat.append([d.isoformat(), levels.get(d.isoformat(), 0)])
            d += timedelta(days=1)
        weeks = [flat[i:i + 7] for i in range(0, len(flat), 7)]
        weeks = [w for w in weeks if len(w) == 7][-53:]

        cur, best = streak(levels)
        out = dict(old)
        out.update({
            "login": login,
            "days": (date.today() - date.fromisoformat(days[0])).days,
            "contributions": int(total.group(1).replace(",", "")) if total else 0,
            "streak": cur,
            "best_streak": best,
            "weeks": weeks,
        })
    except Exception as e:                       # noqa: BLE001
        print(f"贡献数据没抓到（{e}），沿用旧的 stats.json")
        return

    try:
        repos = get(f"https://github.com/{login}?tab=repositories")
        names = {m for m in re.findall(rf'href="/{login}/([A-Za-z0-9._-]+)"', repos)}
        langs = Counter(re.findall(r'itemprop="programmingLanguage">([^<]+)<', repos))
        out["repos"] = len(names)
        out["languages"] = [[k, v] for k, v in langs.most_common()]
        stars = re.findall(r'aria-label="(\d+) users? starred', repos)
        out["stars"] = sum(int(s) for s in stars)
    except Exception as e:                       # noqa: BLE001
        print(f"仓库数据没抓到（{e}），沿用旧的")

    (ROOT / "stats.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("stats.json 已更新：", {k: out[k] for k in ("repos", "contributions", "streak", "best_streak") if k in out})


if __name__ == "__main__":
    main()
