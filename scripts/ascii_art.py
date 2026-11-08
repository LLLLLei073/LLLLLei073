"""图案：大字横幅（pyfiglet）、像素猫、睡觉的猫。"""
from __future__ import annotations

import pyfiglet


def banner(text: str) -> list[str]:
    rows = pyfiglet.figlet_format(text, font="ansi_shadow", width=400).rstrip("\n").split("\n")
    rows = [r.rstrip() for r in rows]
    while rows and not rows[-1].strip():
        rows.pop()
    return rows


# ---------------------------------------------------------------- 小坐猫（三行，等宽友好）
SIT = [r" /\_/\ ", r"( o.o )", r" > ^ < "]
SIT_EYES = {"normal": "o.o", "blink": "-.-", "happy": "^.^", "look": "o.O"}
SIT_EYE_POS = (1, 2)

# ---------------------------------------------------------------- 睡觉的猫
SLEEP = [
    r"   /\_/\         ",
    r"  ( -.- )_______ ",
    r"   \  ω        )~",
    r"   (,,)_(,,)___/ ",
]
SLEEP_Z = [
    [(0, 10, "z")],
    [(0, 10, "z"), (-1, 12, "Z")],
    [(0, 10, "z"), (-1, 12, "Z"), (-2, 14, "z")],
    [(-1, 12, "Z"), (-2, 14, "z")],
]
