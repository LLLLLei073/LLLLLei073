"""主页上的每一张图。每个函数返回一段 SVG。"""
from __future__ import annotations

from datetime import date, datetime, timedelta

import ascii_art as art
import weatherfx
from svgkit import Canvas
from term import Term, cells, plain, resolve
from themes import gradient, mix

W = 840            # 所有卡片同宽，GitHub 会按栏宽缩放
MARGIN = 10        # 留给窗口阴影
TITLE_H = 34
PAD = 24

MONTHS = ["1月", "2月", "3月", "4月", "5月", "6月", "7月", "8月", "9月", "10月", "11月", "12月"]

# Codeforces 段位配色（对应 Catppuccin 键名：灰→绿→青→蓝→紫→橙→红）
CF_COLORS = {
    "newbie": "overlay1", "pupil": "green", "specialist": "teal", "expert": "blue",
    "candidate master": "mauve", "master": "peach", "international master": "peach",
    "grandmaster": "red", "international grandmaster": "red", "legendary grandmaster": "red",
}


def cf_color(rating: int) -> str:
    """按 CF 官方段位阈值给颜色。"""
    if rating < 1200:
        return "overlay1"
    if rating < 1400:
        return "green"
    if rating < 1600:
        return "teal"
    if rating < 1900:
        return "blue"
    if rating < 2100:
        return "mauve"
    if rating < 2400:
        return "peach"
    return "red"


# ----------------------------------------------------------------- 小工具

def window(c: Canvas, P: dict, h: float, title: str) -> tuple[float, float]:
    """画一个撑满画布的终端窗口，返回内容区左上角。"""
    x, y, w = MARGIN, MARGIN, c.w - 2 * MARGIN
    wh = h - 2 * MARGIN
    dark = P["name"] == "dark"
    c.define(
        "shadow",
        '<filter id="shadow" x="-6%" y="-8%" width="112%" height="125%">'
        f'<feDropShadow dx="0" dy="5" stdDeviation="6" flood-color="{P["shadow"]}" '
        f'flood-opacity="{0.45 if dark else 0.13}"/></filter>',
    )
    c.add(
        f'<rect x="{x}" y="{y}" width="{w}" height="{wh}" rx="12" fill="{P["base"]}" filter="url(#shadow)"/>',
        f'<path d="M{x},{y + TITLE_H} V{y + 12} a12,12 0 0 1 12,-12 H{x + w - 12} a12,12 0 0 1 12,12 V{y + TITLE_H} Z" '
        f'fill="{P["mantle"]}"/>',
        f'<path d="M{x},{y + TITLE_H} H{x + w}" stroke="{P["crust"]}" stroke-width="1"/>',
        f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{wh - 1}" rx="11.5" fill="none" '
        f'stroke="{P["surface0"]}"/>',
    )
    for i, col in enumerate(("red", "yellow", "green")):
        c.add(f'<circle cx="{x + 20 + i * 20}" cy="{y + TITLE_H / 2}" r="6" fill="{P[col]}"/>')
    t = Term(c, P, 0, y + (TITLE_H - 12.5 * 1.4) / 2, size=12.5, lh=1.4)
    t.x = x + (w - cells(title) * t.cw) / 2
    c.add(t.text(0, 0, title, "subtext0"))
    return x + PAD, y + TITLE_H + 16


def prompt(cfg: dict) -> str:
    return (f"[mauve b]{cfg['profile']['name']}[/][overlay1]@[/][pink b]github[/] "
            f"[teal b]~[/] [green b]❯[/] ")


def _pct(t: float, total: float) -> str:
    return f"{t / total * 100:.3f}%"


def keyframes(c: Canvas, name: str, stops: list[tuple[float, str]], total: float, timing: str = "linear",
              extra: str = "") -> str:
    body = "".join(f"{_pct(t, total)}{{{v}}}" for t, v in stops)
    c.style(f"@keyframes {name}{{{body}}}.{name}{{animation:{name} {total:.2f}s {timing} infinite;{extra}}}")
    return name


# ----------------------------------------------------------------- 顶部横幅

def header(cfg: dict, P: dict, weather: dict | None = None) -> str:
    w = weather or {}
    rows = art.banner(cfg["profile"]["banner"])
    bw = max(len(r) for r in rows)
    inner = W - 2 * MARGIN - 2 * PAD
    size = min(20.0, inner / bw / 0.6)
    line = 14 * 1.5
    cmds = cfg["header"]["commands"]

    # 先算高度
    cmd_rows = sum(1 + len(x["output"]) for x in cmds) + 0.45 * (len(cmds) - 1)
    top = MARGIN + TITLE_H + 16
    y_banner = top + line * 1.9 + size * 1.0
    y_sub = y_banner + (len(rows) - 1) * size * 1.32 + size * 1.3
    y_cmd = y_sub + line * 2.0
    H = y_cmd + cmd_rows * line + PAD + MARGIN

    c = Canvas(W, H)
    ox, oy = window(c, P, H, cfg["header"]["title"])

    # 天气背景：画在最底层，裁在窗口内容区里
    fx0, fy0, fx1, fy1 = MARGIN + 2, MARGIN + TITLE_H + 2, W - MARGIN - 2, H - MARGIN - 2
    cid = c.uid("fxclip")
    c.define(cid, f'<clipPath id="{cid}"><rect x="{fx0}" y="{fy0}" width="{fx1 - fx0:.0f}" '
                  f'height="{fy1 - fy0:.0f}" rx="10"/></clipPath>')
    c.add(f'<g clip-path="url(#{cid})">{weatherfx.scene(c, P, w, (fx0, fy0, fx1, fy1))}</g>')

    small = Term(c, P, ox, oy + line * 0.2, size=14, lh=1.5)
    c.add(small.text(0, 0, cfg["header"]["last_login"].format(date=date.today().strftime("%a %b %d")), "overlay1"))
    if w:
        c.add(weatherfx.chip(c, P, w, W - MARGIN - PAD, oy + line * 0.2))

    # 大字：先画阴影字符，再把所有实心块拼成一条路径上渐变
    bt = Term(c, P, 0, y_banner, size=size, lh=1.32)
    bt.x = (W - bw * bt.cw) / 2
    stops = weatherfx.banner_stops(P, w)
    gid = c.uid("bgrad")
    c.define(gid, f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{bt.x:.0f}" '
                  f'x2="{bt.x + bw * bt.cw:.0f}" y1="0" y2="0">'
                  + "".join(f'<stop offset="{i / (len(stops) - 1):.2f}" stop-color="{s}"/>'
                            for i, s in enumerate(stops)) + "</linearGradient>")

    f, g, _, _ = resolve("█", True)
    bx0, by0, _, by1 = f.bbox(g)          # 实心块的包围盒（em）
    shade, rects = [], []
    for r, ln in enumerate(rows):
        col = 0
        while col < len(ln):
            if ln[col] == "█":
                start = col
                while col < len(ln) and ln[col] == "█":
                    col += 1
                rects.append((bt.col_x(start), bt.row_y(r) + by0 * size,
                              (col - start) * bt.cw, (by1 - by0) * size))
            else:
                ch = ln[col]
                if ch != " ":
                    shade.append(bt.text(col, r, ch, mix(gradient(stops, col / max(1, bw - 1)), P["base"], 0.45)))
                col += 1
    d = "".join(f"M{x:.2f},{y:.2f}h{w:.2f}v{h:.2f}h{-w:.2f}Z" for x, y, w, h in rects)
    c.add("".join(shade), f'<path d="{d}" fill="url(#{gid})"/>')

    # 一道高光扫过大字
    clip = c.uid("bclip")
    c.define(clip, f'<clipPath id="{clip}"><path d="{d}"/></clipPath>')
    shine = c.uid("shine")
    c.define(shine, f'<linearGradient id="{shine}" x1="0" x2="1">'
                    f'<stop offset="0" stop-color="#fff" stop-opacity="0"/>'
                    f'<stop offset=".5" stop-color="#fff" stop-opacity="{0.55 if P["name"] == "dark" else 0.7}"/>'
                    f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>')
    total_sweep = 7.0
    x0 = bt.x - 180
    x1 = bt.x + bw * bt.cw + 40
    keyframes(c, "sweep", [(0, f"transform:translateX({x0:.0f}px)"),
                           (total_sweep * 0.24, f"transform:translateX({x1:.0f}px)"),
                           (total_sweep, f"transform:translateX({x1:.0f}px)")], total_sweep, "ease-in-out",
              extra=f"transform:translateX({x0:.0f}px)")
    c.add(f'<g clip-path="url(#{clip})"><rect x="{x0:.0f}" y="{by0 * size:.0f}" width="140" '
          f'height="{(len(rows) * size * 1.32):.0f}" fill="url(#{shine})" class="sweep"/></g>')

    # 副标题
    st = Term(c, P, 0, y_sub, size=14, lh=1.5)
    m = cfg["header"]["subtitle"]
    st.x = (W - cells(plain(m)) * st.cw) / 2
    c.add(st.markup(0, 0, m)[0])

    # 打字机
    c.add(_typing(c, cfg, P, ox, y_cmd, line, cmds))
    return c.svg(cfg["header"]["title"] + " banner")


def _typing(c: Canvas, cfg: dict, P: dict, ox: float, y: float, line: float, cmds: list) -> str:
    per_char, gap_out, hold, gap_next, start = 0.055, 0.35, 2.6, 0.45, 0.4
    t = start
    seq = []
    for item in cmds:
        n = cells(item["cmd"])
        seq.append((t, item, n))
        t += n * per_char + gap_out + hold + gap_next
    total = t

    tt = Term(c, P, ox, y, size=14, lh=1.5)
    pm = prompt(cfg)
    out = [tt.markup(0, 0.0, pm)[0]]
    pcols = cells(plain(pm))

    row = 0.0
    cursor_pts: list[tuple[float, float, float]] = []
    for k, (t0, item, n) in enumerate(seq):
        cmd = item["cmd"]
        t_typed = t0 + cells(cmd) * per_char
        t_out = t_typed + gap_out
        t_clear = t_out + hold

        if k:
            out.append(tt.markup(0, row, pm)[0])

        # 命令行：用 clip 的宽度动画把它一个字一个字「打」出来
        cid = c.uid("cp")
        x_start = tt.col_x(pcols)
        w_line = tt.col_x(pcols + cells(cmd)) - x_start
        c.define(cid, f'<clipPath id="{cid}"><rect class="ty{k}" x="{x_start:.1f}" '
                      f'y="{tt.row_y(row) - 14:.1f}" width="{w_line:.1f}" height="19"/></clipPath>')
        c.style(
            f"@keyframes ty{k}k{{0%{{transform:scaleX(0)}}{_pct(t0, total)}{{transform:scaleX(0)}}"
            f"{_pct(t_typed, total)}{{transform:scaleX(1)}}100%{{transform:scaleX(1)}}}}"
            f".ty{k}{{transform-origin:{x_start:.1f}px {tt.row_y(row):.1f}px;"
            f"animation:ty{k}k {total:.2f}s steps({cells(cmd)},end) infinite;transform:scaleX(1)}}"
        )
        out.append(f'<g clip-path="url(#{cid})">{tt.text(pcols, row, cmd, "text")}</g>')

        for j, o in enumerate(item["output"]):
            cls = f"o{k}_{j}"
            c.style(f"@keyframes {cls}k{{0%{{opacity:0}}{_pct(t_out, total)}{{opacity:0}}"
                    f"{_pct(t_out + 0.01, total)}{{opacity:1}}100%{{opacity:1}}}}"
                    f".{cls}{{opacity:1;animation:{cls}k {total:.2f}s step-end infinite}}")
            out.append(f'<g class="{cls}">{tt.markup(0, row + 1 + j, o)[0]}</g>')

        cursor_pts.append((t0, tt.col_x(pcols), tt.row_y(row)))
        cursor_pts.append((t_typed, tt.col_x(pcols + n), tt.row_y(row)))
        row += 1 + len(item["output"])
        if k < len(seq) - 1:
            row += 0.45

    # 光标：沿时间轴移动 + 闪烁
    stops = [(tm, f"transform:translate({x:.1f}px,{yy:.1f}px)") for tm, x, yy in cursor_pts]
    last_row = row - (0.45 if len(seq) > 1 else 0)
    end_x, end_y = cursor_pts[-1][1], cursor_pts[-1][2]
    keyframes(c, "curmove", stops, total, "linear", extra="")
    c.style(".blink{animation:blink 1.06s step-end infinite}@keyframes blink{50%{opacity:0}}", key="blink")
    out.append(
        f'<g class="curmove" transform="translate({end_x:.1f},{end_y:.1f})">'
        f'<rect class="blink" x="0" y="-14" width="{tt.cw:.1f}" '
        f'height="19" rx="2" fill="{P["rosewater"]}" opacity=".9"/></g>'
    )
    return "".join(out)


# ----------------------------------------------------------------- neofetch

INFO_COL = 0


def neofetch(cfg: dict, P: dict, stats: dict, weather: dict | None = None,
             cf: dict | None = None) -> str:
    info = info_lines(cfg, stats, weather or {}, cf or {})
    size, lh = 14, 1.45
    rows_needed = 2 + len(info) + 1
    H = MARGIN * 2 + TITLE_H + 16 + rows_needed * size * lh + 12
    c = Canvas(W, H)
    ox, oy = window(c, P, H, "neofetch")
    t = Term(c, P, ox, oy, size=size, lh=lh)
    c.add(t.markup(0, 0, prompt(cfg) + "neofetch")[0])

    # 左边的猫咪卡片
    bw, bh = 292, 240
    mid = (t.row_y(2) + t.row_y(2 + len(info))) / 2
    by = mid - bh / 2
    c.add(f'<rect x="{ox:.1f}" y="{by:.1f}" width="{bw}" height="{bh}" rx="10" fill="{P["surface0"]}" '
          f'opacity="{0.55 if P["name"] == "light" else 0.35}"/>')
    cat = Term(c, P, 0, by + 118, size=32, lh=1.24)
    cat_w = max(cells(x) for x in art.SIT) * cat.cw
    cat.x = ox + (bw - cat_w) / 2
    er, ec = art.SIT_EYE_POS
    for r, line in enumerate(art.SIT):
        if r == er:                     # 眼睛单独画，这里挖空
            line = line[:ec] + " " * 3 + line[ec + 3:]
        c.add(cat.text(0, r, line, "mauve", bold=True))
    # 眼睛会眨
    # 关键：step-end 在「没有关键帧」的时间段会一直保持上一个值，
    # 所以每一帧必须在自己的时间窗结束时显式写一个 opacity:0，否则上一帧会赖着不走，
    # 四帧叠在同一个位置 → 看起来就是穿模。
    names = list(art.SIT_EYES)
    timeline = [("normal", 3.2), ("blink", 0.14), ("normal", 0.2), ("blink", 0.14), ("normal", 2.4),
                ("look", 1.1), ("normal", 1.6), ("happy", 1.4)]
    total = sum(d for _, d in timeline)
    for k, n in enumerate(names):
        wins, tt = [], 0.0
        for nm, d in timeline:
            if nm == n:
                wins.append((tt, tt + d))
            tt += d
        stops = [(0.0, 1 if wins and abs(wins[0][0]) < 1e-9 else 0)]
        for a, b in wins:
            stops.append((a, 1))
            stops.append((b, 0))
        stops.sort(key=lambda s: s[0])
        body = "".join(f"{_pct(min(t, total), total)}{{opacity:{v}}}" for t, v in stops)
        c.style(f"@keyframes eye{k}k{{{body}}}"
                f".eye{k}{{opacity:{1 if k == 0 else 0};animation:eye{k}k {total:.1f}s step-end infinite}}")
        c.add(f'<g class="eye{k}">{cat.text(ec, er, art.SIT_EYES[n], "mauve", bold=True)}</g>')
    tag = Term(c, P, ox + 14, by + 26, size=12)
    c.add(tag.text(0, 0, "MEOW", "pink", bold=True))
    sub = Term(c, P, ox + 14, by + bh - 14, size=11.5)
    c.add(sub.text(0, 0, "~(=^･ω･^=)~", "overlay1"))

    # 右边信息
    global INFO_COL
    INFO_COL = int((bw + 26) / t.cw)
    for r, m in enumerate(info):
        if isinstance(m, str):
            c.add(t.markup(INFO_COL, 2 + r, m)[0])
        else:
            c.add(m(t, INFO_COL, 2 + r))
    return c.svg("neofetch — about me and GitHub stats")


def _uptime(days: int) -> str:
    y, d = divmod(days, 365)
    parts = []
    if y:
        parts.append(f"{y} year{'s' if y > 1 else ''}")
    parts.append(f"{d} day{'s' if d != 1 else ''}")
    return ", ".join(parts)


def info_lines(cfg: dict, s: dict, w: dict | None = None, cf: dict | None = None) -> list:
    w, cf = w or {}, cf or {}
    login = cfg["profile"]["login"]
    k = lambda name: f"[mauve b]{name:<11}[/]"     # noqa: E731
    num = lambda v: f"[peach b]{v:,}[/]"           # noqa: E731
    dot = " [overlay1]·[/] "
    lines: list = [
        f"[pink b]{cfg['profile']['name']}[/][overlay1]@[/][mauve b]github[/]",
        f"[overlay0]{'─' * (len(cfg['profile']['name']) + 7)}[/]",
    ]
    for key, val in cfg["neofetch"]["about"]:
        lines.append(k(key) + val)

    # Codeforces
    if cf.get("rating") is not None:
        color = CF_COLORS.get(cf.get("rank", ""), "overlay1")
        cf_line = f"{k('codeforces')}[{color} b]{cf['rating']}[/]"
        if cf.get("max_rating"):
            cf_line += f"[overlay1] (max {cf['max_rating']})[/]"
        if cf.get("rank"):
            cf_line += f"[overlay1]{dot}[/][{color}]{cf['rank']}[/]"
        if cf.get("solved"):
            cf_line += f"[overlay1]{dot}[/][peach b]{cf['solved']}[/][overlay1] solved[/]"
        lines.append(cf_line)

    # 今天的天气
    if w.get("state"):
        accent = weatherfx.ACCENT.get(w["state"], "yellow")
        if w.get("severity", 0) >= 2:
            accent = "red"
        icon = weatherfx.ICON.get(w["state"], "·")
        line = f"{k('weather')}[{accent}] {icon} {w.get('label', '')}[/]"
        if w.get("temp") is not None:
            line += f" [peach b]{w['temp']:.1f}°C[/]"
        if w.get("humidity") is not None:
            line += f"[overlay1]{dot}湿度 {w['humidity']}%[/]"
        if w.get("severity", 0) >= 2 and w.get("alert"):
            line += f" {dot}[red b]⚠ {w['alert']}[/]"
        elif w.get("city"):
            line += f"[overlay1]{dot}{w['city']}[/]"
        lines.append(line)
    lines += [
        k("uptime") + _uptime(s["days"]),
        k("repos") + num(s.get("repos", 0)) + " public" + dot + f"[yellow b]★[/] {num(s.get('stars', 0))}",
        k("contribs") + num(s.get("contributions", 0)) + " in the last year",
        k("streak") + num(s.get("streak", 0)) + f" day{'s' if s.get('streak', 0) != 1 else ''}"
        + f" [overlay1](best {s.get('best_streak', 0)})[/]",
    ]

    total = sum(v for _, v in s.get("languages", [])) or 1
    langs = [(n, v) for n, v in s.get("languages", []) if v / total >= 0.01][:4]
    accents = ["sky", "mauve", "pink", "teal", "peach", "yellow"]
    if langs:
        def bar(t: Term, col: float, row: float, langs=langs):
            n, out, x = 28, [], 0
            tot = sum(v for _, v in langs)
            widths = [max(1, round(v / tot * n)) for _, v in langs]
            widths[0] += n - sum(widths)
            out.append(t.markup(col, row, k("languages"))[0])
            for (name, _), wdt, a in zip(langs, widths, accents):
                out.append(t.text(col + 10 + x, row, "█" * wdt, a))
                x += wdt
            return "".join(out)

        def legend(t: Term, col: float, row: float, langs=langs):
            tot = sum(v for _, v in langs)
            m = "  ".join(f"[{a}]●[/] {name} [overlay1]{v / tot * 100:.0f}%[/]"
                          for (name, v), a in zip(langs[:3], accents))
            return t.markup(col + 10, row, m)[0]

        lines += [bar, legend]
    else:
        lines.append(k("languages") + "[overlay1]no public code yet[/]")
    lines.append("")

    def palette(t: Term, col: float, row: float):
        out = []
        for i, a in enumerate(["red", "peach", "yellow", "green", "teal", "sky", "blue", "mauve"]):
            out.append(t.text(col + i * 4, row, "███", a))
        return "".join(out)

    lines.append(palette)
    return lines


# ----------------------------------------------------------------- 热力图

def heat_cell(P: dict, x: float, y: float, size: float, level: int) -> str:
    if level == 0:
        return f'<circle cx="{x + size / 2:g}" cy="{y + size / 2:g}" r="1.4" fill="{P["surface2"]}"/>'
    return (f'<rect x="{x:g}" y="{y:g}" width="{size:g}" height="{size:g}" rx="2" '
            f'fill="{P["heat"][min(4, level)]}"/>')


def activity(cfg: dict, P: dict, stats: dict) -> str:
    weeks = stats["weeks"][-53:]
    nweeks = len(weeks)
    pitch, size_cell, label_w = 14, 12, 28
    y_grid = MARGIN + TITLE_H + 16 + 2 * 14 * 1.5
    y_cells = y_grid + 22
    y_sum = y_cells + 7 * pitch + 14
    H = y_sum + 14 * 1.5 + 18 + MARGIN
    c = Canvas(W, H)
    ox, oy = window(c, P, H, cfg["activity"]["title"])
    t = Term(c, P, ox, oy, size=14, lh=1.5)
    c.add(t.markup(0, 0, prompt(cfg) + cfg["activity"]["cmd"])[0])

    grid_x0 = round(ox + label_w)
    lt = Term(c, P, grid_x0, y_grid, size=11.5, lh=1.4)
    last_month = date.fromisoformat(weeks[0][0][0]).month
    for wi, week in enumerate(weeks):
        d0 = date.fromisoformat(week[0][0])
        if d0.month != last_month and wi < nweeks - 2:
            c.add(lt.text(wi * pitch / lt.cw, 0, MONTHS[d0.month - 1], "subtext0"))
        last_month = d0.month
    dt = Term(c, P, ox, y_cells, size=11.5, lh=pitch / 11.5)
    for r, lab in ((1, "一"), (3, "三"), (5, "五")):
        c.add(dt.text(0, r, lab, "overlay1"))

    for wi, week in enumerate(weeks):
        x = grid_x0 + wi * pitch
        for iso, level in week:
            wd = (date.fromisoformat(iso).weekday() + 1) % 7   # 周日 = 0
            c.add(heat_cell(P, x, round(y_cells + wd * pitch), size_cell, level))

    bt = Term(c, P, ox, y_sum, size=14, lh=1.5)
    streak = stats.get("streak", 0)
    s = (f"[green b]{stats.get('contributions', 0):,}[/] contributions in the last year [overlay1]·[/] "
         f"best streak [peach b]{stats.get('best_streak', 0)}[/] days")
    c.add(bt.markup(0, 0, s)[0])
    right = W - MARGIN - PAD
    lx = right - (2 * 2 + 5 * 16 + 2 * 8) - 8
    cy = bt.row_y(0) + (bt.lh - size_cell) / 2
    out = [Term(c, P, lx, y_sum, size=14, lh=1.5).text(0, 0, "少", "overlay1")]
    x = lx + 2 * bt.cw + 6
    for lv in range(5):
        out.append(heat_cell(P, round(x), round(cy), size_cell, lv))
        x += 16
    out.append(Term(c, P, x + 2, y_sum, size=14, lh=1.5).text(0, 0, "多", "overlay1"))
    c.add("".join(out))
    return c.svg("contribution heatmap")


# ----------------------------------------------------------------- 结尾

def footer(cfg: dict, P: dict, weather: dict | None = None) -> str:
    w = weather or {}
    H = MARGIN * 2 + TITLE_H + 16 + 14 * 1.45 * 9 + 4
    c = Canvas(W, H)
    ox, oy = window(c, P, H, cfg["footer"]["title"])
    t = Term(c, P, ox, oy, size=14, lh=1.45)
    c.add(t.markup(0, 0, prompt(cfg) + "exit")[0])
    cx, cy = 2, 4
    for r, line in enumerate(art.SLEEP):
        c.add(t.text(cx, cy + r, line, "lavender", bold=True))

    # 睡着的 z，一帧帧往外飘
    frames = art.SLEEP_Z
    total = 0.8 * len(frames)
    for k, frame in enumerate(frames):
        cls = f"z{k}"
        a, b = k * 0.8 / total * 100, (k + 1) * 0.8 / total * 100
        c.style(f"@keyframes {cls}k{{0%{{opacity:{1 if k == 0 else 0}}}"
                f"{a:.1f}%{{opacity:1}}{b:.1f}%{{opacity:1}}100%{{opacity:0}}}}"
                f".{cls}{{opacity:{1 if k == 2 else 0};animation:{cls}k {total:.1f}s step-end infinite}}")
        z = "".join(t.text(cx + col, cy + r - 1, ch, ["teal", "sky", "blue"][i % 3], bold=True)
                    for i, (r, col, ch) in enumerate(frame))
        c.add(f'<g class="{cls}">{z}</g>')

    tx = cx + len(art.SLEEP[0]) + 4
    flines = list(cfg["footer"]["lines"])
    if w.get("state") and flines:
        accent = "red" if w.get("severity", 0) >= 2 else weatherfx.ACCENT.get(w["state"], "yellow")
        icon = weatherfx.ICON.get(w["state"], "·")
        tail = f" [overlay0]·[/] [{accent}]{icon} {w.get('label', '')}[/]"
        if w.get("temp") is not None:
            tail += f" [overlay1]{w['temp']:.1f}°C[/]"
        flines[-1] = flines[-1] + tail
    for r, m in enumerate(flines):
        c.add(t.markup(tx, cy - 1 + r * 1.2, m.format(date=date.today().isoformat()))[0])
    c.add(t.markup(0, 9, "[overlay1][[Process completed][/]")[0])
    return c.svg("see you next time")


# ----------------------------------------------------------------- Codeforces：rating 趋势

def cf_rating(cfg: dict, P: dict, cf: dict) -> str:
    hist = [p for p in cf.get("contests", []) if isinstance(p.get("rating"), int)]
    handle = cf.get("handle", "")

    size, lh = 14, 1.5
    plot_h = 168
    H = MARGIN * 2 + TITLE_H + 16 + 2 * size * lh + 30 + plot_h + 26
    c = Canvas(W, H)
    ox, oy = window(c, P, H, "codeforces — rating")

    t = Term(c, P, ox, oy, size=size, lh=lh)
    c.add(t.markup(0, 0, prompt(cfg) + f"cf rating {handle}")[0])

    if len(hist) < 2:
        c.add(t.markup(0, 1, "[overlay1]还没打过比赛，等第一场[/]")[0])
        return c.svg("codeforces rating")

    cur = cf.get("rating") or hist[-1]["rating"]
    mx = cf.get("max_rating") or max(p["rating"] for p in hist)
    summary = (f"[{cf_color(cur)} b]{cur}[/] [overlay1](max {mx})[/] "
               f"[overlay1]·[/] [{cf_color(cur)}]{cf.get('rank', '')}[/] "
               f"[overlay1]·[/] {len(hist)} 场")
    c.add(t.markup(0, 1, summary)[0])

    # 画布：左边留给刻度
    x0, x1 = ox + 92, W - MARGIN - PAD
    y0 = oy + 2 * size * lh + 26
    y1 = y0 + plot_h

    ratings = [p["rating"] for p in hist]
    lo = int(min(ratings) // 200 * 200)
    hi = int(-(-max(ratings) // 200) * 200)
    if hi - lo < 400:
        hi = lo + 400

    def yy(r: float) -> float:
        return y1 - (r - lo) / (hi - lo) * (y1 - y0)

    times = [p["t"] for p in hist]
    t0, t1 = times[0], times[-1] or times[0] + 1

    def xx(ts: float) -> float:
        return x0 + (ts - t0) / max(1, t1 - t0) * (x1 - x0)

    # 横向网格 + 刻度
    step = 200 if hi - lo <= 1600 else 400
    r = lo
    while r <= hi:
        y = yy(r)
        c.add(f'<line x1="{x0}" y1="{y:.1f}" x2="{x1}" y2="{y:.1f}" stroke="{P["overlay0"]}" '
              f'stroke-width="1" opacity="0.28"/>')
        label = str(r)
        lt = Term(c, P, 0, y + 4, size=11.5)
        lt.x = x0 - 10 - cells(label) * lt.cw
        c.add(lt.text(0, 0, label, "overlay1"))
        r += step

    # 面积（线下方）+ 折线（按段位分段上色）
    pts = [(xx(p["t"]), yy(p["rating"])) for p in hist]
    area = (f"M{pts[0][0]:.1f},{y1:.1f} " + " ".join(f"L{x:.1f},{y:.1f}" for x, y in pts)
            + f" L{pts[-1][0]:.1f},{y1:.1f} Z")
    gid = c.uid("cfa")
    c.define(gid, f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
                  f'<stop offset="0" stop-color="{P["blue"]}" stop-opacity=".22"/>'
                  f'<stop offset="1" stop-color="{P["blue"]}" stop-opacity="0"/></linearGradient>')
    c.add(f'<path d="{area}" fill="url(#{gid})"/>')

    for i in range(1, len(pts)):
        color = cf_color(hist[i]["rating"])
        c.add(f'<line x1="{pts[i - 1][0]:.1f}" y1="{pts[i - 1][1]:.1f}" x2="{pts[i][0]:.1f}" '
              f'y2="{pts[i][1]:.1f}" stroke="{P[color]}" stroke-width="2" stroke-linecap="round"/>')

    for i, (x, y) in enumerate(pts):
        color = cf_color(hist[i]["rating"])
        rr = 4.2 if i == len(pts) - 1 else 2.4
        c.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr}" fill="{P[color]}" '
              f'stroke="{P["base"]}" stroke-width="{1.2 if i == len(pts) - 1 else 0}"/>')

    # 最高 rating 的虚线
    if mx > lo:
        ym = yy(mx)
        c.add(f'<line x1="{x0}" y1="{ym:.1f}" x2="{x1}" y2="{ym:.1f}" stroke="{P["peach"]}" '
              f'stroke-width="1" stroke-dasharray="4 4" opacity=".55"/>')
        label = f"max {mx}"
        mt = Term(c, P, 0, ym - 6, size=11)
        mt.x = x1 - cells(label) * mt.cw
        c.add(mt.text(0, 0, label, "peach"))

    # 首尾日期
    first_label = datetime.fromtimestamp(t0).strftime("%y.%m")
    left = Term(c, P, x0, y1 + 18, size=11.5)
    c.add(left.text(0, 0, first_label, "overlay1"))
    last_label = datetime.fromtimestamp(t1).strftime("%y.%m")
    right = Term(c, P, 0, y1 + 18, size=11.5)
    right.x = x1 - cells(last_label) * right.cw
    c.add(right.text(0, 0, last_label, "overlay1"))

    return c.svg("codeforces rating")


# ----------------------------------------------------------------- Codeforces：做题热力图

def cf_heat(cfg: dict, P: dict, cf: dict) -> str:
    daily: dict = cf.get("daily", {})
    today = date.today()
    last_sun = today - timedelta(days=(today.weekday() + 1) % 7)
    first = last_sun - timedelta(weeks=52)

    pitch, cell, label_w = 14, 12, 28
    y_grid = MARGIN + TITLE_H + 16 + 14 * 1.5
    y_cells = y_grid + 22
    y_sum = y_cells + 7 * pitch + 14
    H = y_sum + 14 * 1.5 + 18 + MARGIN
    c = Canvas(W, H)
    ox, oy = window(c, P, H, "codeforces — solved")

    t = Term(c, P, ox, oy, size=14, lh=1.5)
    c.add(t.markup(0, 0, prompt(cfg) + "cf solved --year")[0])

    grid_x0 = round(ox + label_w)
    lt = Term(c, P, grid_x0, y_grid, size=11.5, lh=1.4)
    last_month = first.month
    for wi in range(53):
        w0 = first + timedelta(weeks=wi)
        if w0.month != last_month and wi < 51:
            c.add(lt.text(wi * pitch / lt.cw, 0, MONTHS[w0.month - 1], "subtext0"))
        last_month = w0.month

    dt = Term(c, P, ox, y_cells, size=11.5, lh=pitch / 11.5)
    for r, lab in ((1, "一"), (3, "三"), (5, "五")):
        c.add(dt.text(0, r, lab, "overlay1"))

    best_day, best_n = "", 0
    for wi in range(53):
        for wd in range(7):
            d = first + timedelta(weeks=wi, days=wd)
            if d > today:
                continue
            n = int(daily.get(d.isoformat(), 0))
            level = 0 if n <= 0 else min(4, n)
            if n > best_n:
                best_day, best_n = d.isoformat(), n
            c.add(heat_cell(P, grid_x0 + wi * pitch, round(y_cells + wd * pitch), cell, level))

    bt = Term(c, P, ox, y_sum, size=14, lh=1.5)
    s = (f"[peach b]{cf.get('solved', 0):,}[/] solved [overlay1]·[/] "
         f"[green b]{len(daily):,}[/] 天有做题 [overlay1]·[/] 单日最多 [blue b]{best_n}[/] 道")
    c.add(bt.markup(0, 0, s)[0])

    right = W - MARGIN - PAD
    lx = right - (2 * 2 + 5 * 16 + 2 * 8) - 8
    cy = bt.row_y(0) + (bt.lh - cell) / 2
    out = [Term(c, P, lx, y_sum, size=14, lh=1.5).text(0, 0, "少", "overlay1")]
    x = lx + 2 * bt.cw + 6
    for lv in range(5):
        out.append(heat_cell(P, round(x), round(cy), cell, lv))
        x += 16
    out.append(Term(c, P, x + 2, y_sum, size=14, lh=1.5).text(0, 0, "多", "overlay1"))
    c.add("".join(out))
    return c.svg("codeforces solved heatmap")
