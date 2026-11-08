"""抓当天天气，写成 weather.json（主页卡片按它切换「晴 / 雨 / 台风」等形态）。

数据源 Open-Meteo：免费、不用 API key、GitHub Actions 里能直接访问。
纬度经度在 config.toml 的 [weather] 里改，默认杭州。

诚实说明：
  * 「台风」这一档是**按风速推的**（≥10 级），不是官方台风预警。
    想要官方口径得接气象局接口，那种接口通常要 key 且不稳定，所以这里没做。
  * 抓不到就沿用上一次的 weather.json，不会让流水线挂掉。
"""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
UA = {"User-Agent": "Mozilla/5.0 (compatible; profile-card/1.0)"}

# WMO 天气代码 → 我们的状态；label 是给人看的中文
WMO = {
    0: ("clear", "晴"),
    1: ("clear", "大致晴朗"),
    2: ("cloudy", "多云"),
    3: ("cloudy", "阴"),
    45: ("fog", "有雾"),
    48: ("fog", "雾凇"),
    51: ("rain", "毛毛雨"),
    53: ("rain", "小雨"),
    55: ("rain", "中雨"),
    56: ("rain", "冻毛毛雨"),
    57: ("rain", "冻雨"),
    61: ("rain", "小雨"),
    63: ("rain", "中雨"),
    65: ("rain", "大雨"),
    66: ("rain", "冻雨"),
    67: ("rain", "强冻雨"),
    71: ("snow", "小雪"),
    73: ("snow", "中雪"),
    75: ("snow", "大雪"),
    77: ("snow", "米雪"),
    80: ("rain", "阵雨"),
    81: ("rain", "强阵雨"),
    82: ("rain", "暴雨"),
    85: ("snow", "阵雪"),
    86: ("snow", "强阵雪"),
    95: ("thunder", "雷阵雨"),
    96: ("thunder", "雷阵雨伴冰雹"),
    99: ("thunder", "强雷暴伴冰雹"),
}

# 风速（km/h）：17.2 m/s = 8 级，24.5 m/s = 10 级
GALE = 62.0
TYPHOON = 89.0


def classify(code: int, wind_kmh: float, gust_kmh: float, precip: float) -> tuple[str, str, int, str]:
    """返回 (state, label, severity, alert)。severity: 0 正常 / 1 注意 / 2 严重。"""
    state, label = WMO.get(code, ("cloudy", "未知"))
    top = max(wind_kmh, gust_kmh * 0.75)
    severity, alert = 0, ""

    if top >= TYPHOON or (top >= GALE and precip >= 5.0):
        state = "typhoon"
        severity = 2
        alert = "台风级大风" if top >= TYPHOON else "强风暴雨"
    elif top >= GALE:
        severity = 1
        alert = "大风"
    elif code in (65, 82, 95, 96, 99):
        severity = 1
        alert = {65: "大雨", 82: "暴雨", 95: "雷暴", 96: "雷暴", 99: "强雷暴"}[code]

    return state, label, severity, alert


def main():
    cfg = (ROOT / "config.toml").read_text(encoding="utf-8")

    def cfgval(key: str, default: str) -> str:
        m = re.search(rf'^{key}\s*=\s*"([^"]*)"', cfg, re.M)
        return m.group(1) if m else default

    city = cfgval("city", "杭州")
    lat = float(cfgval("latitude", "30.26"))
    lon = float(cfgval("longitude", "120.14"))
    tz = cfgval("timezone", "Asia/Shanghai")
    force = cfgval("force", "")

    out_path = ROOT / "weather.json"
    old = json.loads(out_path.read_text(encoding="utf-8")) if out_path.exists() else {}

    if force:                                    # 手动钉死，方便调试和演示
        state = force
        label = {"clear": "晴", "cloudy": "多云", "rain": "下雨", "snow": "下雪",
                 "fog": "有雾", "thunder": "雷阵雨", "typhoon": "台风"}.get(force, force)
        data = dict(old)
        data.update({"city": city, "state": state, "label": label, "forced": True,
                     "severity": 2 if force == "typhoon" else 0,
                     "alert": "手动指定" if force else "",
                     "updated": datetime.now().strftime("%Y-%m-%d %H:%M")})
        out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"天气被 config 钉死为：{hat(state)} {label}")
        return

    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,relative_humidity_2m,apparent_temperature,"
        "precipitation,weather_code,wind_speed_10m,wind_gusts_10m,is_day"
        f"&timezone={tz.replace('/', '%2F')}"
    )
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=30) as r:
            j = json.loads(r.read().decode("utf-8"))
        cur = j["current"]
        code = int(cur["weather_code"])
        wind = float(cur["wind_speed_10m"])
        gust = float(cur.get("wind_gusts_10m", 0) or 0)
        precip = float(cur.get("precipitation", 0) or 0)
        state, label, severity, alert = classify(code, wind, gust, precip)
        data = {
            "city": city,
            "code": code,
            "state": state,
            "label": label,
            "severity": severity,
            "alert": alert,
            "temp": round(float(cur["temperature_2m"]), 1),
            "feels": round(float(cur["apparent_temperature"]), 1),
            "humidity": int(cur["relative_humidity_2m"]),
            "wind": round(wind, 1),
            "gust": round(gust, 1),
            "precip": round(precip, 1),
            "is_day": bool(cur.get("is_day", 1)),
            "updated": cur.get("time", ""),
            "forced": False,
        }
    except Exception as e:                       # noqa: BLE001
        print(f"天气没抓到（{e}），沿用上一次的 weather.json")
        if not old:
            out_path.write_text(json.dumps({
                "city": city, "state": "clear", "label": "晴", "severity": 0, "alert": "",
                "temp": 20, "humidity": 60, "wind": 5, "gust": 10, "precip": 0,
                "is_day": True, "updated": "", "forced": False,
            }, ensure_ascii=False, indent=1), encoding="utf-8")
            print("  没有旧数据，先写了一个默认的「晴」")
        return

    out_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{city} {hat(state)} {label} {data['temp']}°C · 湿度 {data['humidity']}% · 风 {data['wind']} km/h"
          + (f" · ⚠ {alert}" if alert else ""))


def hat(state: str) -> str:
    return {"clear": "☀", "cloudy": "☁", "rain": "☂", "snow": "☃",
            "fog": "〰", "thunder": "⚡", "typhoon": "⚠"}.get(state, "·")


if __name__ == "__main__":
    main()
