"""全台資料試算：只出統計，不產生網頁資料。

用法：python -I -B tools/survey_taiwan.py <專案根目錄> <觀光署 AttractionList.json> <輸出資料夾>

來源：文化部文化資產局（data/raw/boch_1.1/1.2/3.1.json，全台）＋ 交通部觀光署 觀光資訊資料庫 景點。
OSM 和維基沒有算進來（全台查詢量大，鹿港版是另外抓的），所以每個地方實際可用的點會比這裡多。
合併、排除規則沿用 build_data.py；另外標出「大範圍」的點（國家公園、步道、山、海灘……），這類走不到一個明確的門口。
"""
import csv, json, math, re, sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_data import EXCLUDE, classify, haversine, norm   # noqa: E402

BIG = re.compile(r"國家公園|國家風景區|風景區|森林遊樂區|遊樂區|自然保護區|保留區|步道|林道|古道|登山|山$|山脈|峰$|"
                 r"海灘|海水浴場|沙灘|海岸|溼地|濕地|水庫|農場|牧場|休閒園區|遊樂園|樂園|高爾夫|溫泉區|部落$")
LUKANG = (24.0565, 120.4335)
GATE = re.compile(r"學校|國小|國中|高中|中學|大學|學院|校舍|校門|醫院|診所|宿舍|寓所|墓|發電廠|營區|眷村|監獄|試驗所|工廠|機關")
NOIMG = re.compile(r"notfound|miss\.jpg|noimage|no_image|default", re.I)


def city(s):
    return (s or "").replace("台", "臺").strip()


def load(root, attr_path):
    rows = []
    for fn, kind in [("boch_1.1.json", "古蹟"), ("boch_1.2.json", "歷史建築"), ("boch_3.1.json", "文化景觀")]:
        for x in json.loads((root / "data" / "raw" / fn).read_text(encoding="utf-8")):
            try:
                lat, lng = float(x["latitude"]), float(x["longitude"])
            except (KeyError, TypeError, ValueError):
                continue
            ad = (x.get("addresses") or [{}])[0]
            desc = re.sub(r"\s+", "", str(x.get("pastHistory") or x.get("briefDescribe") or ""))
            rows.append(dict(name=x.get("caseName", "").strip(), lat=lat, lng=lng, src="boch", tag=kind,
                             city=city(ad.get("cityName")), town=(ad.get("distName") or "").strip(),
                             desc=len(desc), img=bool((x.get("representImage") or {}).get("original")), rank=3))
    for x in json.loads(Path(attr_path).read_text(encoding="utf-8-sig"))["Attractions"]:
        try:
            lat, lng = float(x["PositionLat"]), float(x["PositionLon"])
        except (KeyError, TypeError, ValueError):
            continue
        pa = x.get("PostalAddress") or {}
        desc = re.sub(r"\s+", "", x.get("Description") or "")
        rows.append(dict(name=(x.get("AttractionName") or "").strip(), lat=lat, lng=lng, src="attr", tag="",
                         city=city(pa.get("City")), town=(pa.get("Town") or "").strip(),
                         desc=len(desc), img=bool(x.get("Images")) and not NOIMG.search(x["Images"][0].get("URL", "")), rank=2,
                         status=x.get("ServiceStatus")))
    return rows


def grid_key(lat, lng, cell=0.01):   # 約 1.1 公里一格
    return int(lat // cell), int(lng // cell)


def neighbors(grid, lat, lng, r, cell=0.01):
    gi, gj = grid_key(lat, lng, cell)
    k = int(math.ceil(r / 1000)) + 1
    for di in range(-k, k + 1):
        for dj in range(-k, k + 1):
            yield from grid.get((gi + di, gj + dj), [])


def merge(rows):
    rows = sorted(rows, key=lambda x: -x["rank"])
    kept, grid, dropped = [], defaultdict(list), Counter()
    for it in rows:
        if not (21.8 < it["lat"] < 26.5 and 118 < it["lng"] < 122.2):
            dropped["座標不在台灣"] += 1
            continue
        # 文資本身就是認定過的地點，不套名稱排除（否則建國中學紅樓、臺北郵局這類古蹟會被刪掉）；
        # 但在校園、醫院、宿舍、墓園、電廠裡的，能不能進去要人工看
        if it["src"] != "boch" and EXCLUDE.search(it["name"]):
            dropped["名稱排除（觀光署）"] += 1
            continue
        it["gate"] = it["src"] == "boch" and bool(GATE.search(it["name"]))
        if it.get("status") not in (None, 1):
            dropped["觀光署標示非營運"] += 1
            continue
        dup = None
        for k in neighbors(grid, it["lat"], it["lng"], 250):
            d = haversine((it["lat"], it["lng"]), (k["lat"], k["lng"]))
            a, b = norm(it["name"]), norm(k["name"])
            if d < 40 or (d < 250 and a and b and (a in b or b in a)):
                dup = k
                break
        if dup:
            dropped["重複（合併）"] += 1
            dup["also"] = True
            dup["desc"] = max(dup["desc"], it["desc"])
            dup["img"] = dup["img"] or it["img"]
            dup["city"] = dup["city"] or it["city"]
            dup["town"] = dup["town"] or it["town"]
            continue
        it["big"] = bool(BIG.search(it["name"]))
        it["cat"] = classify(it["name"], "history" if it["src"] == "boch" else "")
        kept.append(it)
        grid[grid_key(it["lat"], it["lng"])].append(it)
    return kept, grid, dropped


def pct(a, b):
    return f"{round(100 * a / b)}%" if b else "—"


def main():
    root, attr_path, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    rows = load(root, attr_path)
    raw_n = Counter(r["src"] for r in rows)
    kept, grid, dropped = merge(rows)
    walk = [p for p in kept if not p["big"]]
    wgrid = defaultdict(list)
    for p in walk:
        wgrid[grid_key(p["lat"], p["lng"])].append(p)
    # 每個點 1 公里內有幾個可走的點（含自己）
    for p in walk:
        p["n1k"] = sum(1 for q in neighbors(wgrid, p["lat"], p["lng"], 1000)
                       if haversine((p["lat"], p["lng"]), (q["lat"], q["lng"])) <= 1000)
    gd = lambda p: p["desc"] >= 20   # 有一段像樣的說明（20 字以上）

    # 縣市
    by_city = defaultdict(list)
    for p in kept:
        by_city[p["city"] or "（不明）"].append(p)
    city_rows = []
    for c, ps in by_city.items():
        w = [p for p in ps if not p["big"]]
        city_rows.append(dict(縣市=c, 合併後=len(ps), 文資=sum(p["src"] == "boch" for p in ps),
                              只有觀光署=sum(p["src"] == "attr" for p in ps), 大範圍=len(ps) - len(w),
                              可走點=len(w), 有簡介=pct(sum(gd(p) for p in w), len(w)),
                              有照片=pct(sum(p["img"] for p in w), len(w)),
                              密集點=sum(p["n1k"] >= 10 for p in w), 要看能否進入=sum(p.get("gate", False) for p in w)))
    city_rows.sort(key=lambda r: -r["可走點"])

    # 鄉鎮
    by_town = defaultdict(list)
    for p in walk:
        by_town[(p["city"], p["town"])].append(p)
    town_rows = []
    for (c, t), ps in by_town.items():
        town_rows.append(dict(縣市=c, 鄉鎮=t, 可走點=len(ps), 文資=sum(p["src"] == "boch" for p in ps),
                              有簡介=pct(sum(gd(p) for p in ps), len(ps)), 有照片=pct(sum(p["img"] for p in ps), len(ps)),
                              最密處1公里內=max(p["n1k"] for p in ps)))
    town_rows.sort(key=lambda r: (-r["最密處1公里內"], -r["可走點"]))

    # 散步熱點：1 公里內點最多的地方，熱點中心彼此至少隔 3 公里
    hubs = []
    for p in sorted(walk, key=lambda p: -p["n1k"]):
        if p["n1k"] < 15:
            break
        if any(haversine((p["lat"], p["lng"]), (h["lat"], h["lng"])) < 3000 for h in hubs):
            continue
        hubs.append(p)
    hub_rows = []
    for h in hubs:
        near = [q for q in neighbors(wgrid, h["lat"], h["lng"], 2000)
                if haversine((h["lat"], h["lng"]), (q["lat"], q["lng"])) <= 2000]
        n1 = [q for q in near if haversine((h["lat"], h["lng"]), (q["lat"], q["lng"])) <= 1000]
        hub_rows.append(dict(縣市=h["city"], 鄉鎮=h["town"], 中心附近=h["name"], lat=round(h["lat"], 5), lng=round(h["lng"], 5),
                             **{"1公里內": len(n1), "2公里內": len(near)},
                             有簡介=pct(sum(gd(q) for q in near), len(near)), 有照片=pct(sum(q["img"] for q in near), len(near)),
                             文資佔比=pct(sum(q["src"] == "boch" for q in near), len(near)),
                             廟宇佔比=pct(sum(q["cat"] == "worship" for q in near), len(near))))

    # 鹿港對照：同一套來源（沒有 OSM、維基）在鹿港的結果
    lk = [p for p in walk if haversine(LUKANG, (p["lat"], p["lng"])) <= 4500]
    (out / "鹿港對照.txt").write_text("\n".join(f'{p["src"]}\t{p["cat"]}\t{p["name"]}' for p in sorted(lk, key=lambda p: p["src"])), encoding="utf-8")

    # 檔案大小估算：照現在 docs/index.html 的欄位（每點平均位元組）
    cur = json.loads((root / "data" / "lukang.json").read_text(encoding="utf-8"))
    per = len(json.dumps([{k: p[k] for k in ("id", "name", "lat", "lng", "cat", "tag", "desc")} for p in cur],
                         ensure_ascii=False, separators=(",", ":")).encode()) / len(cur)

    def table(rs, cols):
        s = "| " + " | ".join(cols) + " |\n|" + "---|" * len(cols) + "\n"
        return s + "".join("| " + " | ".join(str(r[c]) for c in cols) + " |\n" for r in rs)

    for name, rs in (("縣市.csv", city_rows), ("鄉鎮.csv", town_rows), ("散步熱點.csv", hub_rows)):
        with open(out / name, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rs[0]))
            w.writeheader()
            w.writerows(rs)

    stats = dict(raw=dict(raw_n), dropped=dict(dropped), kept=len(kept), walk=len(walk),
                 big=len(kept) - len(walk), walk_desc=sum(gd(p) for p in walk), walk_img=sum(p["img"] for p in walk),
                 walk_boch=sum(p["src"] == "boch" for p in walk), gate=sum(p.get("gate", False) for p in walk),
                 desc_len_median=sorted(p["desc"] for p in walk)[len(walk) // 2],
                 desc_over90=sum(p["desc"] > 90 for p in walk), dense=sum(p["n1k"] >= 10 for p in walk),
                 hubs=len(hub_rows), lukang=len(lk), lukang_boch=sum(p["src"] == "boch" for p in lk),
                 bytes_per_place=round(per), est_kb=round(per * len(walk) / 1024),
                 cats=dict(Counter(p["cat"] for p in walk)))
    (out / "stats.json").write_text(json.dumps(stats, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "tables.md").write_text(
        "## 縣市\n\n" + table(city_rows, list(city_rows[0])) +
        "\n## 散步熱點\n\n" + table(hub_rows, [c for c in hub_rows[0] if c not in ("lat", "lng")]) +
        "\n## 鄉鎮（前 40）\n\n" + table(town_rows[:40], list(town_rows[0])), encoding="utf-8")
    print(json.dumps(stats, ensure_ascii=False))


if __name__ == "__main__":
    main()
