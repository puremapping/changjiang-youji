# -*- coding: utf-8 -*-
"""从两份 events.json + coords.json 生成自包含的 index.html。

用法（项目根目录）:
    python proto/build.py

产物:
    proto/index.html   单文件，含内联数据、内联字体子集；双击即可打开。

字体子集：若用 uv 环境装了 fonttools + brotli，脚本会从系统 SimHei 重新裁剪一份
只含本数据集所用字符的 WOFF2；否则沿用 _font.woff2 缓存（若无则跳过内联字体，
退回系统字体）。这样换机器 / 换数据也能重跑。
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LU_SRC = os.path.join(ROOT, "data/events_v2/入蜀記_events.json")
FAN_SRC = os.path.join(ROOT, "data/events_v2/吳船錄_events.json")
WORKS_SRC = os.path.join(ROOT, "data/works_v1/works.json")
PERSONS_SRC = os.path.join(ROOT, "data/base/persons.json")
COORD_SRC = os.path.join(HERE, "coords.json")
TMPL = os.path.join(HERE, "_template.html")
FONT_CACHE = os.path.join(HERE, "_font.woff2")
OUT = os.path.join(HERE, "index.html")

FONT_CANDIDATES = [
    "C:/Windows/Fonts/simhei.ttf",
    "C:/Windows/Fonts/msyh.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
]

# 长江示意折线（纬度, 经度, 地名注释）——仅用于地图上的方位参照
RIVER = [
    (29.58, 103.76), (29.35, 104.78), (28.77, 104.63), (28.88, 105.44), (28.50, 105.90),
    (29.20, 106.45), (29.56, 106.58), (29.63, 107.40), (30.00, 107.60), (30.30, 108.03),
    (30.29, 108.53), (30.81, 108.84), (30.99, 109.09), (31.00, 109.55), (30.92, 110.00),
    (30.97, 110.29), (30.70, 111.28), (30.40, 111.60), (30.33, 111.80), (30.30, 112.20),
    (30.14, 112.42), (29.73, 112.56), (29.77, 112.90), (29.60, 113.30), (29.85, 113.55),
    (30.42, 113.60), (30.56, 114.30), (30.55, 114.31), (30.45, 114.60), (30.20, 115.10),
    (30.05, 115.55), (29.85, 115.85), (29.90, 116.10), (29.67, 116.62), (29.72, 116.92),
    (29.97, 117.03), (30.12, 117.20), (30.30, 117.50), (30.55, 117.72), (30.80, 117.95),
    (30.95, 118.15), (31.00, 118.40), (31.33, 118.60), (31.63, 118.90), (31.72, 119.00),
    (31.85, 119.20), (31.80, 119.60), (31.76, 119.95), (32.05, 120.20), (32.20, 119.42),
    (32.25, 119.18),
]


def cnum(s):
    """漢字序数 → int：'十九' → 19；阿拉伯数字直通。"""
    if not s:
        return None
    s = s.strip()
    if s.isdigit():
        return int(s)
    d = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    if s == "十":
        return 10
    if "十" in s:
        a, b = s.split("十")
        return (d.get(a, 1) if a else 1) * 10 + (d.get(b, 0) if b else 0)
    return d.get(s)


def load_events(coords):
    lu = json.load(open(LU_SRC, encoding="utf-8"))
    fan = json.load(open(FAN_SRC, encoding="utf-8"))
    ev = []
    for e in lu:
        mon_raw = e.get("month") or ""
        leap = "閏" in mon_raw
        ev.append({
            "id": e["id"], "person": "lu", "juan": e["juan"],
            "m": cnum(mon_raw.replace("閏", "").replace("月", "")), "d": cnum((e.get("day") or "").replace("日", "")),
            "leap": leap,
            "date": e.get("date_raw") or "",
            "exact": True, "dateSrc": "",            # 入蜀记：日期全部原文直出
            "orig": e["orig"],
            "place": e.get("place"),
            "places": e.get("place_all") or [],
            "activity": e.get("activity") or [],
            "weather": e.get("weather") or [],
            "emotion": e.get("emotion") or [],
            "landscape": e.get("landscape") or [],
            "imagery": e.get("imagery") or [],
            "note": e.get("note") or "",
            "people": [],
        })
    for e in fan:
        exact = e.get("day_src") == "anchor" if "day_src" in e else isinstance(e.get("day_num"), int)
        mon_raw = e.get("month") or ""
        ev.append({
            "id": e["id"], "person": "fan", "juan": e["juan"],
            "m": cnum(mon_raw.replace("閏", "").replace("月", "")), "d": e.get("day_num"),
            "leap": "閏" in mon_raw,
            "date": e.get("date_raw") or "",
            "exact": exact, "dateSrc": "原文錨定" if exact else "據前後日推算",
            "orig": e["orig"],
            "place": e.get("place"),
            "places": e.get("place_all") or [],
            "activity": e.get("activity") or [],
            "weather": e.get("weather") or [],
            "emotion": e.get("emotion") or [],
            "landscape": e.get("landscape") or [],
            "imagery": e.get("imagery") or [],
            "note": e.get("note") or "",
            "people": [[p["name"], p["type"]] for p in (e.get("people") or [])],
        })
    # 只保留主地名（place 字段）有坐标的，才上地图；缺坐标的不画但仍是时间线事件
    places = {}
    for e in ev:
        if not e["place"] or e["place"] not in coords:
            continue
        c = coords[e["place"]]
        s = places.setdefault(e["place"], {"lat": c["lat"], "lon": c["lon"],
                                           "visits": {"lu": [], "fan": []}, "first": e["id"]})
        s["visits"][e["person"]].append(e["id"])
    return ev, places


def build_font_subset(chars):
    """裁剪字体子集；失败则返回 None。"""
    src = next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)
    if not src:
        return None
    with tempfile.TemporaryDirectory() as td:
        cf = os.path.join(td, "chars.txt")
        out = os.path.join(td, "f.woff2")
        open(cf, "w", encoding="utf-8").write("".join(sorted(chars)))
        try:
            subprocess.run([sys.executable, "-m", "fontTools.subset", src,
                            "--text-file=" + cf, "--flavor=woff2", "--output-file=" + out,
                            "--desubroutinize"], check=True, capture_output=True)
        except Exception:
            return None
        return open(out, "rb").read()


def main():
    coords = json.load(open(COORD_SRC, encoding="utf-8"))
    CLUSTERS = json.load(open(os.path.join(HERE, "clusters.json"), encoding="utf-8"))
    # 只保留有坐标的簇
    ev, places = load_events(coords)
    # works + 作者名（篇目视图用）
    works = json.load(open(WORKS_SRC, encoding="utf-8"))
    persons = {p["id"]: p for p in json.load(open(PERSONS_SRC, encoding="utf-8"))}
    for w in works:
        p = persons.get(w.get("author_id") or "")
        w["author_name"] = p["name"] if p else (w.get("author_id") or "")
    WORKS = works
    data = {
        "people": {
            "lu": {"name": "陸游", "title": "入蜀記", "year": "1170 乾道六年", "color": "#e0a34a"},
            "fan": {"name": "范成大", "title": "吳船錄", "year": "1177 淳熙四年", "color": "#5aa9c9"},
        },
        "events": ev,
        "places": places,
        "works": WORKS,
        "river": [[a, b] for a, b in RIVER],
        "clusters": CLUSTERS,
    }
    html = open(TMPL, encoding="utf-8").read()

    # 字体：优先重裁，其次用缓存
    chars = set()
    for e in ev:
        for k in ("orig", "note", "place", "date", "dateSrc"):
            chars |= set(e.get(k) or "")
        for k in ("weather", "emotion", "landscape", "imagery"):
            for v in (e.get(k) or []):
                chars |= set(str(v))
        for p in e["places"]:
            chars |= set(p)
        for p in e["people"]:
            chars |= set(p[0]) | set(p[1])
        chars |= set(e["activity"])
    chars |= set("".join(places))
    for w in WORKS:
        for k in ("title", "genre", "author_name", "mood", "theme", "structure", "style", "note", "situation", "date_orig"):
            chars |= set(str(w.get(k) or ""))
        for i in (w.get("imagery") or []):
            chars |= set(str(i))
    chars |= set(html.split("<body>")[1])           # 页面固定文案
    chars |= set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,;:()[]+-%/·°「」《》、，。（）；！？—…")
    fb = build_font_subset(chars)
    if fb:
        open(FONT_CACHE, "wb").write(fb)
    elif os.path.exists(FONT_CACHE):
        fb = open(FONT_CACHE, "rb").read()
    font_b64 = base64.b64encode(fb).decode() if fb else ""

    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    assert "</script" not in payload.lower()
    html = html.replace("__FONT__", font_b64).replace("__DATA__", payload)
    # 兜底：若字体为空则删掉 @font-face 规则，避免浏览器解析空 base64 报警
    if not font_b64:
        i, j = html.index("@font-face"), html.index("}", html.index("@font-face")) + 1
        html = html[:i] + html[j:]
    open(OUT, "w", encoding="utf-8").write(html)
    mapped = sum(1 for e in ev if e["place"] and e["place"] in coords)
    both = sum(1 for s in places.values() if s["visits"]["lu"] and s["visits"]["fan"])
    print(f"events {len(ev)}  mapped-to-map {mapped}  sites {len(places)}  shared-sites {both}")
    print(f"font {len(font_b64)//1024} KB (base64)   out {len(html) // 1024} KB -> {OUT}")


if __name__ == "__main__":
    main()
