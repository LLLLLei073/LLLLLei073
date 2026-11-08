"""把 README 用到的每一张图画出来。

    python scripts/gen.py                    # 画全部（assets/ 和 profile/）
    python scripts/gen.py --out /tmp/preview # 画到别处看看效果

数据来自仓库根目录的 stats.json（由 update-stats 任务更新）；
静态图片（横幅、结尾）不依赖它。
"""
from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cards  # noqa: E402
from themes import THEMES  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def write(path: Path, svg: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(svg, encoding="utf-8")
    print(f"  {path.relative_to(path.parent.parent)}  ({len(svg) // 1024} KB)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT), help="assets/ 与 profile/ 写到哪里")
    a = ap.parse_args()
    out = Path(a.out)

    with open(ROOT / "config.toml", "rb") as f:
        cfg = tomllib.load(f)
    stats = json.loads((ROOT / "stats.json").read_text(encoding="utf-8"))
    weather_file = ROOT / "weather.json"
    weather = json.loads(weather_file.read_text(encoding="utf-8")) if weather_file.exists() else {}
    if weather:
        print(f"天气：{weather.get('label', '')} {weather.get('temp', '?')}°C（{weather.get('state', '')}）")

    for theme, P in THEMES.items():
        print(f"[{theme}]")
        write(out / "assets" / f"header-{theme}.svg", cards.header(cfg, P, weather))
        write(out / "profile" / f"neofetch-{theme}.svg", cards.neofetch(cfg, P, stats, weather))
        write(out / "profile" / f"activity-{theme}.svg", cards.activity(cfg, P, stats))
        write(out / "assets" / f"footer-{theme}.svg", cards.footer(cfg, P, weather))


if __name__ == "__main__":
    main()
