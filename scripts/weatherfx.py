"""天气的视觉层：状态图标、状态徽标、背景动效。

所有动效都是 SVG 里内嵌的 CSS，位置写在 transform 属性上（这样静态渲染器也
能摆对位置），动画写在 style 上（浏览器里才会动）。
"""
from __future__ import annotations

import random

from svgkit import Canvas
from themes import mix

# 每个状态的强调色（Catppuccin 键名）
ACCENT = {
    "clear": "yellow",
    "cloudy": "overlay1",
    "rain": "sky",
    "snow": "sapphire",
    "fog": "overlay0",
    "thunder": "mauve",
    "typhoon": "red",
}
ICON = {"clear": "☀", "cloudy": "☁", "rain": "☂", "snow": "☃",
        "fog": "〰", "thunder": "⚡", "typhoon": "⚠"}

# 大字横幅的渐变：天气变，色温也跟着变（调色板键名，深浅两套自动换算）
BANNER = {
    "clear": ["yellow", "peach", "pink", "mauve"],          # 暖
    "cloudy": ["overlay2", "subtext0", "lavender", "blue"],  # 灰蓝
    "rain": ["teal", "sky", "blue", "sapphire"],             # 冷
    "snow": ["sky", "sapphire", "blue", "lavender"],         # 冰
    "fog": ["overlay0", "overlay1", "lavender", "sapphire"],  # 雾灰
    "thunder": ["mauve", "blue", "sapphire"],                # 电
    "typhoon": ["maroon", "red", "mauve", "peach"],          # 警报红
}
DEFAULT_BANNER = ["teal", "sky", "blue", "mauve"]


def banner_stops(P: dict, w: dict) -> list[str]:
    """横幅渐变的四个色标。"""
    state = w.get("state", "")
    if not state:                                   # 没天气数据 → 原来的配色
        keys = DEFAULT_BANNER
    elif state == "typhoon":
        # Catppuccin 的 red/maroon 偏粉，警报感不够，这里单独钉死一组真·警报红
        return ["#7f1d1d", "#b91c1c", "#e11d48", "#f97316"]
    elif state == "clear" and not w.get("is_day", True):
        keys = ["lavender", "blue", "sapphire", "sky"]   # 晴夜
    else:
        keys = BANNER.get(state, DEFAULT_BANNER)
    return [P[k] for k in keys]

BEAUFORT = [(0.3, 0), (1.6, 1), (3.4, 2), (5.5, 3), (8.0, 4), (10.8, 5), (13.9, 6),
            (17.2, 7), (20.8, 8), (24.5, 9), (28.5, 10), (32.7, 11), (37.0, 12)]


def beaufort(kmh: float) -> int:
    for limit, level in BEAUFORT:
        if kmh < limit * 3.6:
            return level
    return 12


def accent_key(w: dict) -> str:
    """强调色的调色板名字（可以直接写进 [sky b] 这种标记里）。"""
    if w.get("severity", 0) >= 2:
        return "red"
    return ACCENT.get(w.get("state", "clear"), "yellow")


def accent(P: dict, w: dict) -> str:
    """强调色的具体色值（画图形用）。"""
    return P[accent_key(w)]


def chip(c: Canvas, P: dict, w: dict, x_right: float, y: float, size: float = 14) -> str:
    """右上角的天气徽标：☀ 晴 15.7°C ／ ⚠ 台风级大风 阵风 10 级"""
    from term import Term, cells, plain

    t = Term(c, P, 0, y, size=size, lh=1.5)
    state = w.get("state", "clear")
    icon = ICON.get(state, "·")
    color = accent_key(w)
    label = w.get("label", "")
    temp = w.get("temp")
    alert = w.get("alert", "")

    parts = f"[{color} b]{icon}[/] [{color} b]{label}[/]"
    if temp is not None:
        parts += f" [overlay1]{temp:.1f}°C[/]"
    if alert:
        if w.get("severity", 0) >= 2:
            level = beaufort(max(w.get("wind", 0), w.get("gust", 0)))
            parts += f" [red b]· {alert}[/] [overlay1]{level} 级[/]"
        else:
            parts += f" [{color} b]· {alert}[/]"

    t.x = x_right - cells(plain(parts)) * t.cw
    return t.markup(0, 0, parts)[0]


def scene(c: Canvas, P: dict, w: dict, box: tuple[float, float, float, float], seed: int = 17) -> str:
    """在 box 区域里画背景天气。返回 svg 片段（调用方负责放到底层）。"""
    x0, y0, x1, y1 = box
    state = w.get("state", "clear")
    sev = w.get("severity", 0)
    if state == "clear":
        return _clear(c, P, w, box, seed)
    if state == "cloudy":
        return _cloudy(c, P, box, seed)
    if state == "rain":
        return _rain(c, P, box, seed, density=34)
    if state == "snow":
        return _snow(c, P, box, seed)
    if state == "fog":
        return _fog(c, P, box)
    if state == "thunder":
        return _rain(c, P, box, seed, density=38) + _bolt(c, P, box, seed)
    if state == "typhoon":
        return (_rain(c, P, box, seed, density=64, heavy=True)
                + _swirl(c, P, box) + _alert_glow(c, P, box))
    return ""


# ------------------------------------------------------------------ 晴

def _clear(c: Canvas, P: dict, w: dict, box, seed: int) -> str:
    x0, y0, x1, y1 = box
    rnd = random.Random(seed)
    out = []
    night = not w.get("is_day", True)
    if not night:
        gid = c.uid("sun")
        c.define(gid, f'<radialGradient id="{gid}"><stop offset="0" stop-color="{P["yellow"]}" '
                      f'stop-opacity=".30"/><stop offset="1" stop-color="{P["yellow"]}" stop-opacity="0"/>'
                      f'</radialGradient>')
        c.style("@keyframes breathe{0%,100%{opacity:.55}50%{opacity:.95}}")
        out.append(f'<circle cx="{x1 - 90:.0f}" cy="{y0 + 60:.0f}" r="150" fill="url(#{gid})" '
                   f'transform="translate(0,0)" style="animation:breathe 9s ease-in-out infinite"/>')
    color = P["overlay1"] if night else P["yellow"]
    for _ in range(12):
        x, y = rnd.uniform(x0 + 20, x1 - 20), rnd.uniform(y0 + 10, y1 - 20)
        dur, delay = rnd.uniform(9, 16), -rnd.uniform(0, 14)
        op = rnd.uniform(0.18, 0.4)
        r = rnd.uniform(1.1, 2.2)
        out.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="{color}" opacity="{op:.2f}" '
                   f'style="animation:floatup {dur:.1f}s linear {delay:.1f}s infinite"/>')
    c.style(f"@keyframes floatup{{0%{{transform:translate(0,10px)}}100%{{transform:translate(6px,-60px)}}}}")
    return "".join(out)


# ------------------------------------------------------------------ 多云

def _cloudy(c: Canvas, P: dict, box, seed: int) -> str:
    from term import Term

    x0, y0, x1, y1 = box
    rnd = random.Random(seed)
    t = Term(c, P, 0, 0, size=54, lh=1)
    out = []
    for i in range(7):
        x, y = rnd.uniform(x0 - 60, x1), rnd.uniform(y0 + 6, y1 - 50)
        dur, delay = rnd.uniform(26, 44), -rnd.uniform(0, 40)
        op = rnd.uniform(0.16, 0.32)
        glyphs = t.text(0, 0, "☁", "overlay2")
        out.append(f'<g transform="translate({x:.0f},{y:.0f})" opacity="{op:.2f}" '
                   f'style="animation:drift {dur:.1f}s linear {delay:.1f}s infinite">{glyphs}</g>')
    c.style(f"@keyframes drift{{0%{{transform:translateX(-80px)}}100%{{transform:translateX(960px)}}}}")
    return "".join(out)


# ------------------------------------------------------------------ 雨 / 雪

def _rain(c: Canvas, P: dict, box, seed: int, density: int = 34, heavy: bool = False) -> str:
    x0, y0, x1, y1 = box
    rnd = random.Random(seed)
    h = y1 - y0
    color = P["sapphire"] if P["name"] == "light" else P["sky"]
    if heavy:
        color = P["subtext0"] if P["name"] == "light" else P["overlay1"]
    out = []
    for i in range(density):
        x = rnd.uniform(x0 - 20, x1 + 20)
        y = rnd.uniform(y0, y1 - 30)
        ln = rnd.uniform(16, 32) * (1.9 if heavy else 1.0)
        dur = rnd.uniform(0.75, 1.6) * (0.55 if heavy else 1.0)
        delay = -rnd.uniform(0, dur * 2)
        op = rnd.uniform(0.22, 0.5) * (0.75 if heavy else 1.0)
        wd = 1.4 if heavy else 1.2
        slope = -5 if not heavy else -13
        out.append(
            f'<g transform="translate({x:.0f},{y:.0f})" style="animation:rainfall {dur:.2f}s linear {delay:.2f}s infinite">'
            f'<line x1="0" y1="0" x2="{slope}" y2="{ln:.0f}" stroke="{color}" stroke-width="{wd}" '
            f'stroke-linecap="round" opacity="{min(0.62, op):.2f}"/></g>'
        )
    c.style(f"@keyframes rainfall{{0%{{transform:translateY(-70px)}}100%{{transform:translateY({h + 90:.0f}px)}}}}")
    return "".join(out)


def _snow(c: Canvas, P: dict, box, seed: int) -> str:
    x0, y0, x1, y1 = box
    rnd = random.Random(seed)
    h = y1 - y0
    out = []
    for _ in range(26):
        x, y = rnd.uniform(x0, x1), rnd.uniform(y0 - h * 0.5, y1)
        r = rnd.uniform(2.2, 4.0)
        dur = rnd.uniform(6, 12)
        delay = -rnd.uniform(0, dur)
        op = rnd.uniform(0.35, 0.7)
        spoke = "".join(
            f'<line x1="0" y1="0" x2="{r * 1.7 * dx:.2f}" y2="{r * 1.7 * dy:.2f}"/>'
            for dx, dy in ((0, -1), (0.87, -0.5), (0.87, 0.5), (0, 1), (-0.87, 0.5), (-0.87, -0.5))
        )
        out.append(
            f'<g transform="translate({x:.0f},{y:.0f})" opacity="{op:.2f}" '
            f'style="animation:snowfall {dur:.1f}s linear {delay:.1f}s infinite">'
            f'<g stroke="{P["sapphire"]}" stroke-width="1" stroke-linecap="round">{spoke}</g></g>'
        )
    c.style(f"@keyframes snowfall{{0%{{transform:translate(0,-40px) rotate(0deg)}}"
            f"100%{{transform:translate(24px,{h + 70:.0f}px) rotate(200deg)}}}}")
    return "".join(out)


# ------------------------------------------------------------------ 雾

def _fog(c: Canvas, P: dict, box) -> str:
    x0, y0, x1, y1 = box
    out = []
    for i in range(4):
        y = y0 + (y1 - y0) * (0.2 + i * 0.2)
        dur = 24 + i * 7
        out.append(
            f'<rect x="{x0 - 100:.0f}" y="{y:.0f}" width="{x1 - x0 + 200:.0f}" height="26" rx="13" '
            f'fill="{P["overlay0"]}" opacity="0.10" style="animation:drift {dur}s linear {-i * 9}s infinite"/>'
        )
    c.style("@keyframes drift{0%{transform:translateX(-80px)}100%{transform:translateX(960px)}}")
    return "".join(out)


# ------------------------------------------------------------------ 雷 / 台风

def _bolt(c: Canvas, P: dict, box, seed: int) -> str:
    x0, y0, x1, y1 = box
    rnd = random.Random(seed + 5)
    x = rnd.uniform(x0 + 120, x1 - 200)
    y = y0 + 40
    d = (f"M{x:.0f},{y:.0f} l26,34 l-14,4 l30,36 l-40,-22 l18,-6 l-28,-30 Z")
    c.style("@keyframes flash{0%,90%{opacity:0}91%{opacity:.95}93%{opacity:0}"
            "94%{opacity:.8}96%{opacity:0}100%{opacity:0}}")
    c.define("boltglow", f'<filter id="boltglow" x="-60%" y="-60%" width="220%" height="220%">'
                         f'<feGaussianBlur stdDeviation="7"/></filter>')
    return (f'<path d="{d}" fill="{P["yellow"]}" opacity="0" filter="url(#boltglow)" '
            f'style="animation:flash 6.5s linear infinite"/>'
            f'<path d="{d}" fill="{P["yellow"]}" opacity="0" style="animation:flash 6.5s linear infinite"/>')


def _swirl(c: Canvas, P: dict, box) -> str:
    x0, y0, x1, y1 = box
    cx, cy = x1 - 140, y0 + 120
    c.style("@keyframes spin{to{transform:rotate(360deg)}}")
    c.style("@keyframes drift{0%{transform:translateX(-80px)}100%{transform:translateX(960px)}}")
    out = []
    for r, dur, op in [(62, 16, 0.13), (98, 23, 0.09)]:
        d = (f"M{-r},0 a{r},{r * 0.5:.0f} 0 1,0 {2 * r},0 "
             f"a{r},{r * 0.5:.0f} 0 1,0 {-2 * r},0")
        out.append(f'<g transform="translate({cx},{cy})"><path d="{d}" fill="none" stroke="{P["red"]}" '
                   f'stroke-width="1.2" opacity="{op}" style="animation:spin {dur}s linear infinite"/></g>')
    # 横向风带
    rnd = random.Random(3)
    for _ in range(9):
        x, y = rnd.uniform(x0, x1 - 160), rnd.uniform(y0, y1 - 20)
        ln = rnd.uniform(50, 130)
        op = rnd.uniform(0.12, 0.3)
        out.append(f'<line x1="{x:.0f}" y1="{y:.0f}" x2="{x + ln:.0f}" y2="{y - 6:.0f}" '
                   f'stroke="{P["red"]}" stroke-width="1.1" opacity="{op:.2f}" stroke-linecap="round" '
                   f'style="animation:drift 3s linear infinite"/>')
    return "".join(out)


def _alert_glow(c: Canvas, P: dict, box) -> str:
    x0, y0, x1, y1 = box
    c.style("@keyframes alarm{0%,100%{opacity:.15}50%{opacity:.45}}")
    return (f'<rect x="{x0}" y="{y0}" width="{x1 - x0:.0f}" height="{y1 - y0:.0f}" fill="none" '
            f'stroke="{P["red"]}" stroke-width="2" opacity=".2" style="animation:alarm 2.4s ease-in-out infinite"/>')
