"""合併鹿港地標：文資局（古蹟/歷史建築/文化景觀）+ OSM + 中文維基 → data/lukang.json

用法：python -I -B tools/build_data.py <raw目錄> <輸出json>
所有座標都是 WGS-84（文資局、OSM、維基皆然），台灣不需要做座標轉換。
"""
import json, math, re, sys
from pathlib import Path

CENTER = (24.0565, 120.4335)   # 鹿港老街一帶
RADIUS = 4500                  # 只收鹿港鎮範圍

EXCLUDE = re.compile(
    r"學校|國小|國小|國中|高中|高級中學|大學|學院|幼兒園|醫院|診所|衛生所|殯儀|納骨|靈骨|公墓|墓園|"
    r"停車|加油|便利|超市|量販|百貨|銀行|郵局|派出所|警察|分局|公所|戶政|地政|消防|"
    r"飯店|旅館|民宿|酒店|汽車|機車|工業區|交流道|國道|省道|縣道|快速道路|"
    r"小學|兒童|有應公|百姓公|電廠|試驗所|火車站|"
    r"(鎮|鄉|里|村|區|市|縣)$|線$|^鹿港$"
)
CATS = [
    ("shop",      r"齋|餅|店$|老舖"),
    ("worship",   r"宮|廟|寺|祠|堂|殿|壇|庵|教會|聖母|媽祖|土地公|福德"),
    ("history",   r"行$|廳$|古蹟|遺址|舊址|故居|古厝|宅|第|居|館舍|書院|城|砲台|碑"),
    ("structure", r"橋|樓|巷|街|井|門|坊|亭|塔|牌|厝|屋|倉|車站|驛"),
    ("nature",    r"公園|樹|榕|林|溪|港|海|濕地|埤|池"),
    ("culture",   r"館|藝|文化|館"),
]


def haversine(a, b):
    R = 6371000
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def classify(name, hint=""):
    core = re.sub(r"^(彰化縣?)?鹿港", "", name)   # 「鹿港」的「港」別誤判成自然
    for cat, pat in CATS:
        if re.search(pat, core):
            return cat
    return hint or "other"


def clean_desc(text, name="", limit=90):
    if not text:
        return ""
    t = re.sub(r"\s+", "", str(text))
    sents = re.findall(r"[^。]+。", t) or [t]
    core = re.sub(r"^(彰化縣?)?鹿港", "", name)[:4]
    # 優先選提到這個地點本身的句子，避免開頭是整段鹿港背景
    pick = next((x for x in sents if core and core in x), sents[0])
    return pick if len(pick) <= limit else pick[:limit] + "…"


def load_boch(raw):
    out = []
    for fn, kind in [("boch_1.1.json", "古蹟"), ("boch_1.2.json", "歷史建築"), ("boch_3.1.json", "文化景觀")]:
        p = raw / fn
        if not p.exists():
            continue
        for x in json.loads(p.read_text(encoding="utf-8")):
            try:
                lat, lng = float(x["latitude"]), float(x["longitude"])
            except (KeyError, TypeError, ValueError):
                continue
            if haversine(CENTER, (lat, lng)) > RADIUS:
                continue
            name = x.get("caseName", "").strip()
            desc = clean_desc(x.get("pastHistory") or x.get("briefDescribe"), name)
            types = x.get("assetsTypes", "")
            hint = "worship" if "寺廟" in types or "宗祠" in types else "history"
            out.append(dict(name=name, lat=lat, lng=lng, src="boch", tag=kind,
                            cat=classify(name, hint), desc=desc, rank=3))
    return out


def load_osm(raw):
    p = raw / "osm_lukang.json"
    out = []
    for e in json.loads(p.read_text(encoding="utf-8"))["elements"]:
        t = e.get("tags", {})
        name = t.get("name:zh-Hant") or t.get("name:zh") or t.get("name")
        if e["type"] == "node":
            lat, lng = e.get("lat"), e.get("lon")
        else:
            c = e.get("center") or {}
            lat, lng = c.get("lat"), c.get("lon")
        if lat is None:
            continue
        if not name:
            if t.get("man_made") == "water_well":
                name = "無名古井"
            else:
                continue
        hint = ("worship" if t.get("amenity") == "place_of_worship" else
                "nature" if t.get("natural") or t.get("leisure") else
                "structure" if t.get("man_made") else "history" if t.get("historic") else "")
        out.append(dict(name=name.strip(), lat=lat, lng=lng, src="osm", tag="",
                        cat=classify(name, hint), desc="", rank=2))
    return out


def load_wiki(raw):
    p = raw / "wiki_lukang.json"
    out = []
    for g in json.loads(p.read_text(encoding="utf-8"))["query"]["geosearch"]:
        if g["dist"] > RADIUS:
            continue
        name = re.sub(r"\s*\(.*?\)$", "", g["title"]).strip()
        out.append(dict(name=name, lat=g["lat"], lng=g["lon"], src="wiki", tag="",
                        cat=classify(name), desc="", rank=1))
    return out


def norm(n):
    return re.sub(r"[\s・·()（）]|^鹿港|^彰化縣?", "", n)


def merge(items):
    items.sort(key=lambda x: -x["rank"])     # 文資局優先保留（有簡介）
    kept = []
    for it in items:
        if EXCLUDE.search(it["name"]):
            continue
        dup = None
        for k in kept:
            d = haversine((it["lat"], it["lng"]), (k["lat"], k["lng"]))
            a, b = norm(it["name"]), norm(k["name"])
            if d < 40 or (d < 250 and a and b and (a in b or b in a)):
                dup = k
                break
        if dup:
            dup.setdefault("also", []).append(it["src"])
            continue
        kept.append(it)
    return kept


def assign_ids(rows, reg_path):
    """地點編號一旦發出就永久不變：玩家足跡和到達語音（arrived_<id>.mp3）都認這個號碼。
    編號登記在 place_ids.json（只增不刪）；同名且相距 250m 內視為同一地點，沿用舊號；新地點從最大號往後排。
    下架的地點號碼也留在登記裡，不會被新地點拿去用。"""
    reg = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else []
    used, nxt = set(), max((e["id"] for e in reg), default=0) + 1
    for r in rows:
        hit = next((e for e in reg if e["id"] not in used and norm(e["name"]) == norm(r["name"])
                    and haversine((e["lat"], e["lng"]), (r["lat"], r["lng"])) < 250), None)
        if hit:
            r["id"] = hit["id"]
        else:
            r["id"] = nxt
            nxt += 1
            reg.append({"id": r["id"], "name": r["name"], "lat": round(r["lat"], 6), "lng": round(r["lng"], 6)})
        used.add(r["id"])
    reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=0), encoding="utf-8")


def main():
    raw, out = Path(sys.argv[1]), Path(sys.argv[2])
    boch, osm, wiki = load_boch(raw), load_osm(raw), load_wiki(raw)
    rows = merge(boch + osm + wiki)
    rows.sort(key=lambda r: haversine(CENTER, (r["lat"], r["lng"])))
    assign_ids(rows, out.parent / "place_ids.json")
    # 人工整理：補簡介、移出不適合的地點（編號照樣留在登記裡）
    ov_path = out.parent / "place_overrides.json"
    ov = json.loads(ov_path.read_text(encoding="utf-8")) if ov_path.exists() else {}
    drop = {int(k) for k in ov.get("drop", {})}
    for r in rows:
        o = ov.get("desc", {}).get(str(r["id"]))
        if o:
            r["desc"], r["desc_src"] = o["text"], o["src"]
    rows = [r for r in rows if r["id"] not in drop]
    data = [dict(id=r["id"], name=r["name"], lat=round(r["lat"], 6), lng=round(r["lng"], 6),
                 cat=r["cat"], tag=r["tag"], desc=r["desc"],
                 src=sorted({r["src"], *r.get("also", [])}),
                 **({"desc_src": r["desc_src"]} if r.get("desc_src") else {}))
            for r in rows]
    out.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    from collections import Counter
    print(f"boch {len(boch)} / osm {len(osm)} / wiki {len(wiki)} → 合併後 {len(data)}")
    print("分類", dict(Counter(d["cat"] for d in data)))
    print("有簡介", sum(1 for d in data if d["desc"]))


if __name__ == "__main__":
    main()
