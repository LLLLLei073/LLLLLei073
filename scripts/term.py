"""把一段文字画成 SVG 路径。

GitHub 的 README 图片跑在沙箱 iframe 里，加载不了网络安全字体（web font），
所以这里用 fontTools 把每个字形转成 <path>，字重靠变量字体的 wght 轴来调。
一个字符只定义一次，之后用 <use> 引用，文件不会炸。

中日韩字符按「两个格子」算宽，跟真终端一致，中英混排才不会错位。
"""
from __future__ import annotations

import os
import re
import unicodedata
import urllib.request
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

from svgkit import Canvas

# 钉死在一个 commit 上，URL 永远不会漂移
GOOGLE_FONTS = "https://raw.githubusercontent.com/google/fonts/47d54ca1ebb14fd864695f1d39dc734f39017c33/ofl/"

FONTS = {
    "mono": ("jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf", {"wght": 450}),
    "mono_b": ("jetbrainsmono/JetBrainsMono%5Bwght%5D.ttf", {"wght": 760}),
    "cjk": ("notosanssc/NotoSansSC%5Bwght%5D.ttf", {"wght": 450}),
    "cjk_b": ("notosanssc/NotoSansSC%5Bwght%5D.ttf", {"wght": 750}),
    "thai": ("notosansthai/NotoSansThai%5Bwdth,wght%5D.ttf", {"wght": 450, "wdth": 100}),
}
CHAIN = {False: ["mono", "cjk", "thai"], True: ["mono_b", "cjk_b", "thai"]}

ASC, DESC = 1.02, 0.30      # JetBrains Mono 的行高度量（em）
CELL = 0.6                   # JetBrains Mono 的步进宽度（em）
Y_NUDGE = {"cjk": 0.05, "cjk_b": 0.05}   # 中文旁边站英文时会显低，抬一点


def _n(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def _font_dir() -> Path:
    d = Path(os.environ.get("FONT_CACHE") or (Path(__file__).resolve().parent.parent / "vendor/fonts"))
    d.mkdir(parents=True, exist_ok=True)
    return d


class Font:
    def __init__(self, key: str, path: Path, location):
        self.key = key
        self.tt = TTFont(str(path), lazy=True)
        self.cmap = self.tt.getBestCmap()
        self.upm = self.tt["head"].unitsPerEm
        self.gs = self.tt.getGlyphSet(location=location) if location else self.tt.getGlyphSet()

    def has(self, ch: str) -> bool:
        return ord(ch) in self.cmap

    def advance(self, g: str) -> float:
        return self.gs[g].width / self.upm

    def path(self, g: str, size: float) -> str:
        s = size / self.upm
        pen = SVGPathPen(self.gs, ntos=_n)
        self.gs[g].draw(TransformPen(pen, (s, 0, 0, -s, 0, 0)))
        return pen.getCommands()

    def bbox(self, g: str) -> tuple[float, float, float, float]:
        """字形包围盒，单位是 em（y 轴已经翻成屏幕方向）。"""
        from fontTools.pens.boundsPen import BoundsPen

        bp = BoundsPen(self.gs)
        self.gs[g].draw(bp)
        x0, y0, x1, y1 = bp.bounds
        return x0 / self.upm, -y1 / self.upm, x1 / self.upm, -y0 / self.upm


_LOADED: dict[str, Font] = {}


def font(key: str) -> Font:
    if key not in _LOADED:
        rel, loc = FONTS[key]
        name = rel.split("/")[-1].replace("%5B", "[").replace("%5D", "]")
        dest = _font_dir() / name
        if not dest.exists():
            print(f"  下载字体 {name} ...", flush=True)
            tmp = dest.with_name(dest.name + ".part")
            with urllib.request.urlopen(GOOGLE_FONTS + rel, timeout=300) as r, open(tmp, "wb") as f:
                f.write(r.read())
            tmp.rename(dest)
        _LOADED[key] = Font(key, dest, loc)
    return _LOADED[key]


_MISSING: set[str] = set()


def resolve(ch: str, bold: bool = False):
    """挑字体，返回 (字体, 字形名, 步进, 占几格)。"""
    for k in CHAIN[bold]:
        f = font(k)
        if f.has(ch):
            g = f.cmap[ord(ch)]
            adv = f.advance(g)
            wide = unicodedata.east_asian_width(ch) in ("W", "F") or adv > 0.78
            return f, g, adv, 2 if wide else 1
    if ch not in _MISSING:          # emoji 之类：画方块，跟真终端一样
        _MISSING.add(ch)
        print(f"  警告：没有字体包含 {ch!r} (U+{ord(ch):04X})，用 □ 代替")
    return resolve("□", bold)


def cells(s: str) -> int:
    return sum(resolve(ch)[3] for ch in s)


def plain(s: str) -> str:
    """去掉 [color] 标记，只留字。"""
    return _TAG.sub("", s)


_TAG = re.compile(r"\[([a-z_0-9]+)( b)?\]|\[/\]")


class Term:
    """等宽「终端」排版器。列 → x，行 → y，全部对齐到格子。"""

    def __init__(self, c: Canvas, P: dict, x: float, y: float, size: float = 14, lh: float = 1.5):
        self.c, self.P = c, P
        self.x, self.y = x, y
        self.size, self.lh = size, lh
        self.cw = CELL * size

    def col_x(self, col: float) -> float:
        return self.x + col * self.cw

    def row_y(self, row: float) -> float:
        return self.y + row * self.size * self.lh

    def text(self, col: float, row: float, s: str, color: str, bold: bool = False,
             cls: str = "", attrs: str = "") -> str:
        x0, baseline = self.col_x(col), self.row_y(row)
        out, x = [], x0
        for ch in s:
            if ch == " ":
                x += self.cw
                continue
            f, g, adv, _ = resolve(ch, bold)
            gid = f"{f.key}{int(self.size * 10)}-{re.sub(r'[^A-Za-z0-9_-]', '_', g)}"
            if gid not in self.c.defs:
                self.c.define(gid, f'<path id="{gid}" d="{f.path(g, self.size)}"/>')
            y = baseline + Y_NUDGE.get(f.key, 0) * self.size
            k = f' class="{cls}"' if cls else ""
            a = f" {attrs}" if attrs else ""
            out.append(f'<use{k} href="#{gid}" x="{_n(x)}" y="{_n(y)}" fill="{self.P.get(color, color)}"{a}/>')
            x += adv * self.size
        return "".join(out)

    def markup(self, col: float, row: float, s: str, row_step: float = 1.0) -> tuple[str, float]:
        """[pink]字[/]、[pink b]粗体[/]、[[ 表示一个真正的 [ —— 返回 (svg, 下一行的 row)。"""
        s = s.replace("[[", "\x00")          # 先藏起来，免得被当成标记
        out, x, r, cur, bold = [], col, row, "text", False
        pos = 0
        for m in _TAG.finditer(s):
            chunk = s[pos:m.start()].replace("\x00", "[")
            if chunk:
                out.append(self.text(x, r, chunk, cur, bold))
                x += cells(chunk)
            pos = m.end()
            if m.group(0) == "[/]":
                cur, bold = "text", False
            else:
                cur, bold = m.group(1), bool(m.group(2))
        tail = s[pos:].replace("\x00", "[")
        if tail:
            out.append(self.text(x, r, tail, cur, bold))
            x += cells(tail)
        return "".join(out), r + row_step
