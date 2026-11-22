# -*- coding: utf-8 -*-
"""构建立体地层长江图 + 两书日历热力图（自包含单文件 HTML）。

用法（项目根目录）:
    python proto/build_strata_heatmap.py

产物: proto/strata_heatmap.html
数据来源（只读）:
    data/works_v1/works.json        17 篇篇目
    data/events_v2/入蜀記_events.json  156 条
    data/events_v2/吳船錄_events.json  110 条
    data/base/places.json            地名坐标
"""
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

WORKS = json.load(open(os.path.join(ROOT, "data/works_v1/works.json"), encoding="utf-8"))
LU = json.load(open(os.path.join(ROOT, "data/events_v2/入蜀記_events.json"), encoding="utf-8"))
FAN = json.load(open(os.path.join(ROOT, "data/events_v2/吳船錄_events.json"), encoding="utf-8"))
PLACES = {p["id"]: p for p in json.load(open(os.path.join(ROOT, "data/base/places.json"), encoding="utf-8"))}

CN = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10,
      "十一":11,"十二":12,"閏":""}

CN_DAY = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,
          "十":10,"十一":11,"十二":12,"十三":13,"十四":14,"十五":15,"十六":16,
          "十七":17,"十八":18,"十九":19,"二十":20,"廿":20,"三十":30}

def cn_day(s):
    if not s:
        return None
    s = s.replace("日", "").strip()
    # 合記「二十二至二十四日」取首日
    if "至" in s:
        s = s.split("至")[0].strip()
    if s.isdigit():
        return int(s)
    if s in CN_DAY:
        return CN_DAY[s]
    if "十" in s:
        a, b = s.split("十")
        tens = CN_DAY.get(a, 1) if a else 1
        ones = CN_DAY.get(b, 0) if b else 0
        return tens * 10 + ones
    return CN_DAY.get(s)

def month_num(m):
    if not m:
        return None
    m2 = m.replace("閏", "").replace("月", "").strip()
    return CN_DAY.get(m2)

MONTH_NAME = {5:"五月",6:"六月",7:"七月",8:"八月",9:"九月",10:"十月",11:"十一月",12:"十二月"}

def month_label(e):
    raw = (e.get("month") or "").replace("月", "").strip()
    if raw.startswith("閏"):
        return "閏五月"
    m = month_num(e.get("month"))
    return MONTH_NAME.get(m, e.get("month") or "")

# 作品 → 坐标（优先 places 表；表内无坐标的用已知今地近似，note 标注）
FALLBACK = {
    "w-chi-bi-fu": (29.87, 113.80, "黃州赤壁"),
    "w-hou-chi-bi-fu": (29.87, 113.80, "黃州赤壁"),
    "w-shi-zhong-shan-ji": (29.70, 116.00, "湖口石鐘山"),
    "w-you-jin-shan-si": (32.21, 119.44, "鎮江金山"),
    "w-jin-shan-ye-xi": (32.21, 119.44, "鎮江金山"),
    "w-jin-shan-jing-du": (32.21, 119.44, "鎮江金山"),
    "w-ru-shu-ji": (30.00, 120.58, "山陰啟程"),
    "w-wu-chuan-lu": (30.67, 103.80, "成都啟程"),
}

def work_coord(w):
    pl = PLACES.get(w.get("place_id") or "")
    if pl and pl.get("lon") is not None:
        return pl["lat"], pl["lon"], pl.get("modern_name") or pl["name"]
    if w["id"] in FALLBACK:
        return FALLBACK[w["id"]]
    return None

# 作者分组（按 works 表 author_id 归类）
AUTHOR_META = [
    {"key": "liu",   "person": "p-liu-zong-yuan", "name": "柳宗元", "era": "唐 · 773–819",
     "color": "#6a9455", "colorSoft": "#eef3ea"},
    {"key": "su",    "person": "p-su-shi",        "name": "蘇軾",   "era": "北宋 · 1037–1101",
     "color": "#8f6bb0", "colorSoft": "#f1ecf5"},
    {"key": "lu",    "person": "p-lu-you",        "name": "陸游",   "era": "南宋 · 1125–1210",
     "color": "#b0741c", "colorSoft": "#f8efdd"},
    {"key": "fan",   "person": "p-fan-chengda",   "name": "范成大", "era": "南宋 · 1126–1193",
     "color": "#2c7da0", "colorSoft": "#e4eff4"},
    {"key": "zhang", "person": "p-zhang-dai",     "name": "張岱",   "era": "明末 · 1597–1679",
     "color": "#b05a5a", "colorSoft": "#f6e7e7"},
]

strata = []
for meta in AUTHOR_META:
    works = []
    for w in WORKS:
        if w.get("author_id") != meta["person"]:
            continue
        coord = work_coord(w)
        lat, lon, place_name = coord if coord else (None, None, None)
        works.append({
            "id": w["id"],
            "title": w["title"],
            "visit_year": w.get("visit_year"),
            "write_year": w.get("write_year"),
            "date_orig": w.get("date_orig"),
            "situation": w.get("situation"),
            "theme": w.get("theme"),
            "mood": w.get("mood"),
            "genre": w.get("genre"),
            "imagery": w.get("imagery") or [],
            "lon": lon,
            "place": place_name,
            "note": w.get("note"),
        })
    strata.append({**meta, "works": works})

# 路线端点（陆/范两本日记）
routes = {
    "lu":  {"from": 120.58, "to": 109.50, "label": "1170 閏五月—十月：山陰 → 夔州（156 日）"},
    "fan": {"from": 103.80, "to": 120.60, "label": "1177 五月—十月：成都 → 平江（110 日）"},
}

# ---- 日历热力数据 ----
def normalize_events(ev, person):
    out = []
    for e in ev:
        m = month_num(e.get("month"))
        if e.get("day_num") is not None:
            d = e["day_num"]
        else:
            d = cn_day(e.get("day"))
        out.append({
            "id": e["id"],
            "person": person,
            "month": m,
            "monthLabel": month_label(e),
            "isLeap": (e.get("month") or "").startswith("閏"),
            "day": d,
            "date_raw": e.get("date_raw") or "",
            "place": e.get("place"),
            "activity": e.get("activity") or [],
            "weather": e.get("weather") or [],
            "emotion": e.get("emotion") or [],
            "imagery": e.get("imagery") or [],
            "orig": e.get("orig") or "",
            "note": e.get("note") or "",
            "day_src": e.get("day_src"),
        })
    return out

events = normalize_events(LU, "lu") + normalize_events(FAN, "fan")

# 月份顺序（两书行程月份，含闰五月）
MONTH_ORDER = [5, 6, 7, 8, 9, 10, 11, 12]

DATA = {
    "strata": strata,
    "routes": routes,
    "events": events,
    "months": MONTH_ORDER,
    "monthName": MONTH_NAME,
}

HTML = r"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>一條長江，五個時代 — 立體地層圖 · 日曆熱力圖</title>
<style>
:root{
  --bg:#f4f1e8; --panel:#fbf9f2; --line:#d8d2c2; --line2:#e6e1d3;
  --text:#33302a; --dim:#6d675c; --dim2:#98917f;
  --liu:#6a9455; --su:#8f6bb0; --lu:#b0741c; --fan:#2c7da0; --zhang:#b05a5a;
}
*{box-sizing:border-box}
html,body{margin:0;background:var(--bg);color:var(--text);
  font-family:"Source Han Serif SC","Noto Serif CJK SC","Microsoft YaHei","SimSun",serif;}
#app{max-width:1320px;margin:0 auto;padding:18px 22px 46px}
header{display:flex;align-items:baseline;gap:16px;flex-wrap:wrap;margin-bottom:8px}
header h1{font-size:22px;margin:0;letter-spacing:.12em;font-weight:600}
header .sub{font-size:12.5px;color:var(--dim)}
#toolbar{display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin:10px 0 14px;font-size:12px;color:var(--dim)}
#toolbar .grp{display:flex;gap:6px;align-items:center}
#toolbar button{font:inherit;font-size:12px;color:var(--dim);background:transparent;border:1px solid var(--line);
  padding:4px 12px;border-radius:3px;cursor:pointer;letter-spacing:.05em}
#toolbar button.on{color:#fdfbf4;background:var(--text);border-color:var(--text)}
#toolbar .hint{color:var(--dim2);font-size:11.5px;margin-left:auto}
#legend{display:flex;gap:18px;flex-wrap:wrap;font-size:12px;color:var(--dim);margin:4px 0 12px}
#legend .it{display:flex;align-items:center;gap:6px}
#legend .dot{width:10px;height:10px;border-radius:50%}
.card{background:var(--panel);border:1px solid var(--line);border-radius:5px;padding:14px 16px;margin-bottom:20px}
.card h2{font-size:14px;font-weight:600;letter-spacing:.1em;margin:0 0 4px}
.card .cap{font-size:11.5px;color:var(--dim2);margin-bottom:10px;line-height:1.7}
svg{display:block;width:100%}
svg text{user-select:none}
.tip{position:fixed;pointer-events:none;z-index:50;background:#fffdf6;border:1px solid var(--line);
  padding:8px 12px;font-size:12px;line-height:1.7;max-width:350px;display:none;
  box-shadow:0 4px 18px rgba(60,50,20,.18);color:var(--text)}
.tip b{font-size:13px}
.tip .d{color:var(--dim2);font-size:11px}
footer{margin-top:10px;font-size:11.5px;color:var(--dim2);line-height:1.8}
footer .hl{color:var(--dim)}
#heatmap text{font-family:"Microsoft YaHei","PingFang SC","Noto Sans CJK SC",sans-serif}
</style>
</head>
<body>
<div id="app">
  <header>
    <h1>一條長江，五個時代</h1>
    <span class="sub">立體地層長江圖（上） · 兩本日記日曆熱力圖（下）</span>
  </header>

  <div class="card">
    <h2>地 層 圖 — 五層立體長江塊（梯形透視 · 立面厚度）</h2>
    <div class="cap">縱序＝時代（上早下晚），橫軸＝長江流段（西→東）；同一地點對齊同一縱列。每層為梯形頂面，帶右側立面與前底面，向後上方投影，形成塊狀層疊的立體幾何感。</div>
    <div id="legend">
      <span class="it"><span class="dot" style="background:var(--liu)"></span>柳宗元（唐）</span>
      <span class="it"><span class="dot" style="background:var(--su)"></span>蘇軾（北宋）</span>
      <span class="it"><span class="dot" style="background:var(--lu)"></span>陸游（南宋）</span>
      <span class="it"><span class="dot" style="background:var(--fan)"></span>范成大（南宋）</span>
      <span class="it"><span class="dot" style="background:var(--zhang)"></span>張岱（明末）</span>
      <span class="it" style="color:var(--dim2)">● 作品　○ 相遇節點　⟶ 行程路線</span>
    </div>
    <svg id="strata"></svg>
  </div>

  <div class="card">
    <h2>日 曆 熱 力 圖 — 入蜀記 156 日 · 吳船錄 110 日</h2>
    <div class="cap">每人一行月份塊，按現代月曆周列（日～六）排布；格內＝當日事件，可按天氣或情緒著色。農曆未換算公曆，星期列僅為月曆骨架；虛線框＝紀日為推算而非原文明著。點格查看原文。</div>
    <div id="toolbar">
      <div class="grp">
        <button data-m="weather" class="on">天氣</button>
        <button data-m="emotion">情緒</button>
        <button data-m="plain">底色</button>
      </div>
      <span class="hint" id="modeHint"></span>
    </div>
    <svg id="heatmap"></svg>
  </div>

  <footer>
    數據：works_v1（17 篇）· events_v2（266 日）· places（379 條，142 有坐標）。
    江道為示意走向，橫軸按經度線性映射；柳宗元九記均在湘江支流永州段，故同列。
    金山列 1170 年：陸游途經遇范成大（使金過鎮），原文「相別八年」（入蜀記六月二十八日，四源互校）。
    日曆格日期保留原文紀日，農曆未換算公曆；天氣/情緒僅標原文明確出現者，不推衍。
  </footer>
</div>
<div class="tip" id="tip"></div>

<script>
const DATA = __DATA__;
const NS = "http://www.w3.org/2000/svg";
const tip = document.getElementById("tip");
const esc = s => (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
function el(tag, attrs, parent){
  const n=document.createElementNS(NS,tag);
  if(attrs) for(const k in attrs) n.setAttribute(k,attrs[k]);
  (parent||document.getElementById("strata")).appendChild(n); return n;
}
function txt(parent,x,y,s,attrs){
  const t=el("text",Object.assign({x,y},attrs||{}),parent); t.textContent=s; return t;
}
function showTip(ev,html){
  tip.innerHTML=html; tip.style.display="block";
  const w=tip.offsetWidth,h=tip.offsetHeight,pad=14;
  let x=ev.clientX+pad,y=ev.clientY+pad;
  if(x+w>innerWidth-10)x=ev.clientX-w-pad;
  if(y+h>innerHeight-10)y=ev.clientY-h-pad;
  tip.style.left=x+"px";tip.style.top=y+"px";
}
const hideTip=()=>{tip.style.display="none"};

/* ============ 一、立體地層長江圖 ============ */
const LON_RANGE=[103.0,121.6];
const RIVER_PTS=[
  [103.80,"成都"],[107.0,"重慶"],[109.50,"夔州"],[110.3,"巫峽"],[111.3,"峽州"],
  [112.2,"荊州"],[113.80,"黃州"],[116.0,"江州"],[117.4,"安慶"],[118.5,"金陵"],
  [119.44,"金山·鎮江"],[120.58,"山陰"]
];
const STRATA=DATA.strata, ROUTES=DATA.routes;

function drawStrata(){
  const svg=document.getElementById("strata");
  const W=Math.min(1320, document.getElementById("app").clientWidth-44);
  const bandH=128, topPad=58, botPad=46;
  // 立體塊厚度（向右後方投影）
  const DEPTH_X=34, DEPTH_Y=22;
  const H=topPad+STRATA.length*bandH+botPad;
  svg.setAttribute("viewBox",`0 0 ${W+DEPTH_X} ${H}`);
  svg.setAttribute("width",W+DEPTH_X); svg.setAttribute("height",H);
  svg.innerHTML="";
  const padL=150, padR=40;
  // 透視：近（底）端略寬、遠（頂）端略收；頂邊左移、右移收窄
  const px=lon=>padL+(lon-LON_RANGE[0])/(LON_RANGE[1]-LON_RANGE[0])*(W-padL-padR);

  const bands=STRATA.map((a,i)=>({a, top:topPad+i*bandH, bot:topPad+(i+1)*bandH}));

  /* 縱列地名參考線 */
  const gRef=el("g",{},svg);
  RIVER_PTS.forEach(([lon,name])=>{
    const x=px(lon);
    txt(gRef,x,topPad-16,name,{"font-size":11,fill:"#6d675c","text-anchor":"middle","letter-spacing":".04em"});
    el("line",{x1:x,x2:x,y1:topPad-8,y2:H-botPad+6,stroke:"#ece7d6","stroke-width":1,"stroke-dasharray":"2 5"},gRef);
  });

  bands.forEach((b,bi)=>{
    const a=b.a;
    const t=b.top+10, bt=b.bot-10;
    // 梯形頂面四點：頂邊（遠）較窄、左移；底邊（近）較寬、右移
    const TL=[padL+14, t], TR=[W-padR-14, t], BR=[W-padR, bt], BL=[padL, bt];
    // 立體塊：向右後方偏移 DEPTH
    const off=p=>[p[0]+DEPTH_X, p[1]-DEPTH_Y];
    const TL2=off(TL), TR2=off(TR), BR2=off(BR), BL2=off(BL);

    // 分層投影（塊下方淡影）
    el("path",{d:`M${BL[0]+8},${BL[1]+10} L${BR[0]+8},${BR[1]+10} L${BR[0]+DEPTH_X+8},${BR[1]-DEPTH_Y+10} L${BL[0]+DEPTH_X+8},${BL[1]-DEPTH_Y+10} Z`,
      fill:"#000000","fill-opacity":.07},gRef);

    // 右側面（可見立面，顏色壓深）
    el("path",{d:`M${TR[0]},${TR[1]} L${BR[0]},${BR[1]} L${BR2[0]},${BR2[1]} L${TR2[0]},${TR2[1]} Z`,
      fill:a.color, "fill-opacity":.28, stroke:"#c9c0a6","stroke-width":.6},gRef);
    // 前底面（近側立面，再壓深）
    el("path",{d:`M${BL[0]},${BL[1]} L${BR[0]},${BR[1]} L${BR2[0]},${BR2[1]} L${BL2[0]},${BL2[1]} Z`,
      fill:a.color, "fill-opacity":.16, stroke:"#cfc7ae","stroke-width":.6},gRef);
    // 頂面（梯形）
    el("path",{d:`M${TL[0]},${TL[1]} L${TR[0]},${TR[1]} L${BR[0]},${BR[1]} L${BL[0]},${BL[1]} Z`,
      fill:a.colorSoft,stroke:"#d8d0b8","stroke-width":1},gRef);

    // 作者標籤（左側）
    txt(gRef,16,(b.top+b.bot)/2-6,a.name,{"font-size":17,"font-weight":600,fill:a.color,"letter-spacing":".08em"});
    txt(gRef,16,(b.top+b.bot)/2+15,a.era,{"font-size":11,fill:"#98917f","letter-spacing":".05em"});

    // 江道示意線（帶內波浪）
    const riverD=RIVER_PTS.map(([lon],i)=>{
      const x=px(lon);
      const y=(b.top+b.bot)/2+Math.sin(i*1.7)*bandH*0.14;
      return (i?"L":"M")+x.toFixed(1)+" "+y.toFixed(1);
    }).join(" ");
    el("path",{d:riverD,fill:"none",stroke:"#c9d6c9","stroke-width":7,"stroke-linecap":"round","stroke-linejoin":"round","stroke-opacity":.7},gRef);

    // 行程路線（陸/范）
    if(ROUTES[a.key]){
      const r=ROUTES[a.key];
      const x1=px(r.from), x2=px(r.to);
      const yMid=(b.top+b.bot)/2;
      el("path",{d:`M${Math.min(x1,x2)} ${yMid} L${Math.max(x1,x2)} ${yMid}`,
        fill:"none",stroke:a.color,"stroke-width":3,"stroke-opacity":.3,"stroke-dasharray":"10 4"},gRef);
      txt(gRef,Math.min(x1,x2)+8,yMid-14,r.label,{"font-size":10.5,fill:a.color,"fill-opacity":.9,"letter-spacing":".03em"});
    }

    // 作品點
    a.works.forEach((w,idx)=>{
      if(w.lon==null) return;
      const x=px(w.lon);
      const same=a.works.filter(o=>o.lon===w.lon);
      const sIdx=same.indexOf(w);
      const y=(b.top+b.bot)/2 + (same.length>1 ? (sIdx-(same.length-1)/2)*18 : -6);
      const c=el("circle",{cx:x,cy:y,r:7,fill:a.color,stroke:"#fffdf6","stroke-width":1.5,cursor:"pointer"},gRef);
      const tipHtml=`<b style="color:${a.color}">${esc(a.name)}〈${esc(w.title)}〉</b><br>
        <span class="d">${w.genre||""} · 遊歷 ${w.visit_year??"—"}${w.write_year&&w.write_year!==w.visit_year?` · 寫於 ${w.write_year}`:""}</span>
        ${w.place?`<br><span class="d">${esc(w.place)}</span>`:""}
        ${w.situation?`<br><span class="d">${esc(w.situation)}</span>`:""}
        ${w.theme?`<br><span class="d">${esc(w.theme.slice(0,70))}${w.theme.length>70?"…":""}</span>`:""}`;
      c.addEventListener("mouseenter",ev=>showTip(ev,tipHtml));
      c.addEventListener("mousemove",ev=>showTip(ev,tipHtml));
      c.addEventListener("mouseleave",hideTip);
      const lbl=txt(gRef,x+11,y+4,w.title,{"font-size":11,fill:"#33302a","letter-spacing":".02em",cursor:"pointer"});
      lbl.addEventListener("mouseenter",ev=>showTip(ev,tipHtml));
      lbl.addEventListener("mouseleave",hideTip);
    });
  });

  // 1170 金山相遇跨層連線（陸游帶 ↔ 范成大帶）
  const luBand=bands.find(b=>b.a.key==="lu"), fanBand=bands.find(b=>b.a.key==="fan");
  if(luBand&&fanBand){
    const mx=px(119.44);
    const luY=(luBand.top+luBand.bot)/2, fanY=(fanBand.top+fanBand.bot)/2;
    el("line",{x1:mx,y1:luY+10,x2:mx,y2:fanY-10,stroke:"#7a6a4a","stroke-width":1.8,"stroke-dasharray":"4 3"},gRef);
    [luBand,fanBand].forEach(bd=>{
      el("circle",{cx:mx,cy:(bd.top+bd.bot)/2,r:8,fill:"none",stroke:"#7a6a4a","stroke-width":2,"stroke-dasharray":"3 3",cursor:"pointer"},gRef);
    });
    const mt=txt(gRef,mx+12,(luY+fanY)/2+4,"1170 · 金山相遇",{"font-size":12,"fill":"#7a6a4a","letter-spacing":".06em","font-weight":600});
    mt.style.cursor="pointer";
    const mTip=`<b>1170-06-28 · 金山</b><br>陸游入蜀途經，范成大使金過鎮，玉鑑堂設宴。<br>
      原文：<span class="d">「奉使金國起居郎范至能至山，遣人相招食於玉鑑堂。……相別八年」</span><br>
      <span class="d">（《入蜀記》六月二十八日，四源互校一致）</span>`;
    mt.addEventListener("mouseenter",ev=>showTip(ev,mTip));
    mt.addEventListener("mouseleave",hideTip);
  }
}

/* ============ 二、日曆熱力圖 ============ */
const HEAT=document.getElementById("heatmap");
const WX_ORDER=["晴","雨","風","寒","暑","霧"];
const WX_COLOR={"晴":"#e8c46a","雨":"#7fa8c9","風":"#b9c4a8","寒":"#9db6c9","暑":"#d98a6a","霧":"#b7b3a6"};
const EM_ORDER=["憂慮","忧慮","曠達","旷達","追慕","驚嘆","惊叹","憐憫","怜悯"];
const EM_COLOR={"憂慮":"#6a9455","忧慮":"#6a9455","曠達":"#5e9c77","旷達":"#5e9c77",
  "追慕":"#8f6bb0","驚嘆":"#b0741c","惊叹":"#b0741c","憐憫":"#b05a5a","怜悯":"#b05a5a"};
const PERSON_META={
  lu:{name:"陸游",book:"入蜀記",color:"#b0741c"},
  fan:{name:"范成大",book:"吳船錄",color:"#2c7da0"},
};
let heatMode="weather";

function emNorm(s){
  return {"忧虑":"憂慮","旷达":"曠達","惊叹":"驚嘆","怜悯":"憐憫"}[s]||s;
}

function cellColor(e){
  if(heatMode==="plain") return "#efe9d8";
  if(heatMode==="weather"){
    for(const w of WX_ORDER) if(e.weather.includes(w)) return WX_COLOR[w];
    return "#f2eee0";
  }
  // emotion：取第一個受控情緒
  for(const raw of e.emotion){
    const em=emNorm(raw);
    if(EM_COLOR[em]) return EM_COLOR[em];
  }
  return "#f2eee0";
}

const WEEK=["日","一","二","三","四","五","六"];

// 農曆未換算公曆，無法定星期；月曆格按「日序排進周列」，星期列僅作現代日曆骨架。
function drawHeat(){
  const W=Math.min(1320, document.getElementById("app").clientWidth-44);
  HEAT.innerHTML="";
  const padL=110, padR=24, padT=36, padB=36;
  const cellS=26, cellGap=4, cols=7;
  const monthBlockW=cols*cellS+(cols-1)*cellGap;
  const monthGap=18;
  const perRow=4, blockH=150;
  // 每人最多 7 塊 → 兩行；兩人共 4 行
  const blockRows=Math.ceil(7/perRow);
  const rowH=blockRows*blockH+10;
  const H=padT+2*rowH+padB;
  HEAT.setAttribute("viewBox",`0 0 ${W} ${H}`);
  HEAT.setAttribute("width",W); HEAT.setAttribute("height",H);
  const g=el("g",{},HEAT);

  const persons=["lu","fan"];
  persons.forEach((p,ri)=>{
    const meta=PERSON_META[p];
    const y0=padT+ri*rowH;
    txt(g,padL-12,y0+44,meta.name,{"font-size":14,"font-weight":600,fill:meta.color,"text-anchor":"end","letter-spacing":".08em"});
    txt(g,padL-12,y0+62,meta.book,{"font-size":10.5,"fill":"#98917f","text-anchor":"end"});

    const evs=DATA.events.filter(e=>e.person===p&&e.month!=null&&e.day!=null);
    // 月份保持行程出現順序（閏五月單列）
    const monthLabels=[];
    evs.forEach(e=>{ if(!monthLabels.includes(e.monthLabel)) monthLabels.push(e.monthLabel); });

    monthLabels.forEach((ml,mi)=>{
      const evMonth=evs.filter(e=>e.monthLabel===ml).sort((a,b)=>a.day-b.day);
      const br=Math.floor(mi/perRow), bc=mi%perRow;
      const bx=padL+bc*(monthBlockW+monthGap);
      const by=y0+6+br*blockH;
      // 月曆塊背景
      el("rect",{x:bx-8,y:by,width:monthBlockW+16,height:blockH-10,rx:6,fill:"#f6f2e7",stroke:"#e6e1d3","stroke-width":1},g);
      txt(g,bx+monthBlockW/2,by+20,ml,{"font-size":12,"font-weight":600,fill:meta.color,"text-anchor":"middle","letter-spacing":".05em"});
      // 星期表頭
      WEEK.forEach((w,wi)=>{
        txt(g,bx+wi*(cellS+cellGap)+cellS/2,by+38,w,{"font-size":9.5,"fill":"#98917f","text-anchor":"middle"});
      });
      // 日序填入周列（每 7 格一行）
      evMonth.forEach((e,ci)=>{
        const r=Math.floor(ci/cols), c=ci%cols;
        const x=bx+c*(cellS+cellGap), y=by+46+r*(cellS+cellGap);
        const fill=cellColor(e);
        const isEst=e.day_src&&e.day_src!=="anchor"&&e.day_src!=="head";
        const rect=el("rect",{x,y,width:cellS,height:cellS,rx:4,fill,
          stroke:isEst?"#8a8574":"#d8d2c2","stroke-width":isEst?1.4:0.7,
          "stroke-dasharray":isEst?"3 2":"none",cursor:"pointer"},g);
        txt(g,x+cellS/2,y+cellS/2+3.5,Math.min(e.day,31),{"font-size":10,"fill":"#4a463c","text-anchor":"middle"});
        const tipHtml=`<b style="color:${meta.color}">${meta.name} · ${esc(e.date_raw)}</b><br>
          <span class="d">${e.place?esc(e.place):"原文未著地名"}</span>
          ${e.weather.length?`<br><span class="d">天氣：${e.weather.map(esc).join("、")}</span>`:""}
          ${e.emotion.length?`<br><span class="d">情緒：${e.emotion.map(emNorm).map(esc).join("、")}</span>`:""}
          ${e.activity.length?`<br><span class="d">活動：${e.activity.map(esc).join("、")}</span>`:""}
          <br><span class="d">${esc(e.orig.slice(0,90))}${e.orig.length>90?"…":""}</span>`;
        rect.addEventListener("mouseenter",ev=>showTip(ev,tipHtml));
        rect.addEventListener("mousemove",ev=>showTip(ev,tipHtml));
        rect.addEventListener("mouseleave",hideTip);
      });
    });
  });

  // 圖例
  let lx=padL;
  const legendItems=heatMode==="weather"
    ? WX_ORDER.map(w=>[w,WX_COLOR[w]])
    : ["曠達","追慕","驚嘆","憂慮","憐憫"].map(em=>[em,EM_COLOR[em]]);
  legendItems.forEach(([name,color])=>{
    el("rect",{x:lx,y:H-padB+12,width:13,height:13,rx:2,fill:color},g);
    txt(g,lx+18,H-padB+23,name,{"font-size":11,"fill":"#6d675c"});
    lx+=18+name.length*12+20;
  });
  if(heatMode!=="plain"){
    txt(g,lx,H-padB+23,"　｜　虛線框＝紀日推算",{"font-size":10.5,"fill":"#98917f"});
  }
  document.getElementById("modeHint").textContent=
    heatMode==="weather"?"格色＝當日所記天氣（多重標記取首項）":
    heatMode==="emotion"?"格色＝當日所記情緒（多重標記取首項）":"格色不著維度，僅標記行程日";
}

/* 模式切換 */
document.querySelectorAll("#toolbar button[data-m]").forEach(b=>{
  b.onclick=()=>{
    heatMode=b.dataset.m;
    document.querySelectorAll("#toolbar button[data-m]").forEach(x=>x.classList.toggle("on",x===b));
    drawHeat();
  };
});

drawStrata(); drawHeat();
let rt=null;
addEventListener("resize",()=>{clearTimeout(rt);rt=setTimeout(()=>{drawStrata();drawHeat();},120);});
</script>
</body>
</html>
"""

payload = json.dumps(DATA, ensure_ascii=False, separators=(",", ":"))
assert "</script" not in payload.lower()
out = HTML.replace("__DATA__", payload)
out_path = os.path.join(HERE, "strata_heatmap.html")
open(out_path, "w", encoding="utf-8").write(out)

# 控制台核对数字
print(f"strata 作者数: {len(strata)}")
for s in strata:
    print(f"  {s['name']}: {len(s['works'])} 篇")
print(f"events: {len(events)} (lu {len([e for e in events if e['person']=='lu'])}, "
      f"fan {len([e for e in events if e['person']=='fan'])})")
print(f"out: {out_path}  ({len(out)//1024} KB)")
