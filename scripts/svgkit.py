"""拼一个 SVG 文件用的小工具箱。"""
from __future__ import annotations

from xml.sax.saxutils import escape


class Canvas:
    def __init__(self, w: float, h: float):
        self.w, self.h = w, h
        self.css: list[str] = []
        self._css_keys: set[str] = set()
        self.defs: dict[str, str] = {}
        self.body: list[str] = []
        self._n = 0

    def uid(self, p: str = "u") -> str:
        self._n += 1
        return f"{p}{self._n}"

    def add(self, *parts: str):
        self.body.extend(parts)

    def style(self, css: str, key: str | None = None):
        if key is not None:
            if key in self._css_keys:
                return
            self._css_keys.add(key)
        self.css.append(css)

    def define(self, did: str, content: str):
        self.defs.setdefault(did, content)

    def svg(self, title: str) -> str:
        t = escape(title, {'"': "&quot;"})
        css = "".join(self.css) + "@media (prefers-reduced-motion:reduce){*{animation:none!important}}"
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w:g}" height="{self.h:g}" '
            f'viewBox="0 0 {self.w:g} {self.h:g}" role="img" aria-label="{t}">'
            f"<title>{t}</title><style>{css}</style>"
            f'<defs>{"".join(self.defs.values())}</defs>'
            f'{"".join(self.body)}</svg>'
        )
