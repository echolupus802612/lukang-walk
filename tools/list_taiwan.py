"""全台地點列表：依「以景點、觀光地點、公園為主」的規則，逐筆標出收或不收、理由。只出列表，不產生網頁資料。

用法：python -I -B tools/list_taiwan.py <專案根目錄> <觀光署 AttractionList.json> <輸出 csv>

規則：
- 文化部文化資產局（古蹟、歷史建築、文化景觀）全收；在校園、醫院、宿舍、墓園、機關裡的，或資料寫明不開放的，不收
- 交通部觀光署景點：去掉暫停或關閉的、觀光工廠、店家與商圈夜市、休閒農場與露營區、範圍很大走不到一個點的、學校機關交通設施
- 廟宇只來自上面兩個來源（文資身分或觀光署列為景點），不另外收小廟
- 兩個來源的同一處合併成一筆（文資優先）
OpenStreetMap 還沒納入（全台查詢伺服器今天一直滿載），所以觀光署沒列的公園暫時不在表上。
"""
import csv, json, re, sys, unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_data import EXCLUDE, haversine, norm          # noqa: E402
from survey_taiwan import BIG, GATE, city, grid_key, neighbors   # noqa: E402

HUGE = re.compile(r"國家公園|國家風景區|森林遊樂區")
BIG2 = re.compile(BIG.pattern + r"|遊憩區|休憩區|保護區|賞鳥區|自行車道|自行車路線|鐵馬道|綠廊|綠道|環島|特定區|保育區|景觀區|地質區")

# 開放資料裡偶有簡體字與相容區的異體碼（看起來一樣、編碼不同），讀進來就轉成繁體標準字
# 左邊是簡體字，用 Unicode 編碼寫，檔案裡才不會出現簡體字
TRAD = str.maketrans({"\u54cd": "響", "\u732e": "獻", "\u664b": "晉", "\u5374": "卻", "\u9879": "項", "\u7ccd": "餈"})


def trad(t):
    return unicodedata.normalize("NFC", t or "").translate(TRAD)


CLOSED = re.compile(r"暫停|暫時|封閉|關閉|整修|停止開放|未修復")
FACTORY = re.compile(r"觀光工廠|夢工廠")
NOT_FACTORY = re.compile(r"燈塔|觀景台|文化園區|港$|碼頭|博物館|紀念館")
SHOP = re.compile(r"市場|花市|玉市|夜市|商圈|商店街|購物|百貨|商場|[Oo]utlet|影城|市集|小吃|美食|餐廳|咖啡|[Cc]af[eé]|CAFE|書店|本舖|"
                  r"工作室|工作坊|工房|畫室|工藝之家|產銷|合作社|婚紗街|成衣街|麵線|飯店|酒店|食堂")
SELL = re.compile(r"販售|專賣|店內|老闆|門市|不接受散客")
# 名稱看得出是公共場所的，說明裡提到販售也不算店家（美術館有商店、老街有店家）
PUBLIC = re.compile(r"公園|博物館|美術館|文化中心|紀念館|故事館|文物館|老街|街$|街區|漁港|港$|碼頭|遊客中心|車站|古道|步道|"
                    r"糖廠|園區|灣$|教堂|海岸|中心$|宮|廟|寺")
FARM = re.compile(r"休閒農場|農場|農園|果園|牧場|茶園|莊園|農莊|休閒農業區|露營|草莓園|香草")
KEEP = re.compile(r"公園|村$|園區|院區|保存區|聚落|貓公所")   # 觀光署的「某某村」多半是彩繪村、漁村這類景點，不是行政區
NOT_WORSHIP = re.compile(r"紀念堂|公會堂|中山堂|講堂|禮堂|會堂|食堂|澡堂|浴堂|中正堂")
WORSHIP = re.compile(r"宮|廟|寺|祠|堂|殿|壇|庵|巖|教會|天主堂|禮拜堂|媽祖|土地公|福德|代天府|王爺府")
PARK = re.compile(r"公園|綠地|植物園|森林園區|花園|河濱|廣場")
MUSEUM = re.compile(r"博物館|美術館|文物館|紀念館|文化館|故事館|藝文|文化中心|展示館|劇場|戲院|藝術村|文創|園區|館$")
STREET = re.compile(r"老街|街$|巷|街屋")
NATURE = {2, 11, 16, 24, 26}
ORDER = ["臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣",
         "嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣", "宜蘭縣", "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣"]


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
            types = "".join(t.get("name", "") for t in (x.get("assetsTypes") or []) if isinstance(t, dict))
            rows.append(dict(name=trad(x.get("caseName", "")).strip(), lat=lat, lng=lng, src="文資", tag=kind,
                             city=city(ad.get("cityName")), town=(ad.get("distName") or "").strip(),
                             desc=len(desc), img=bool((x.get("representImage") or {}).get("original")),
                             open=str(x.get("openUpTime") or ""), types=types, cls=set(), rank=3,
                             texts=[t for t in (re.sub(r"\s+", "", trad(str(x.get(k) or ""))) for k in
                                                ("briefDescribe", "pastHistory", "buildingFeatures")) if t],
                             imgs=[u for u in [(x.get("representImage") or {}).get("original")] if u]))
    for x in json.loads(Path(attr_path).read_text(encoding="utf-8-sig"))["Attractions"]:
        try:
            lat, lng = float(x["PositionLat"]), float(x["PositionLon"])
        except (KeyError, TypeError, ValueError):
            continue
        pa = x.get("PostalAddress") or {}
        imgs = x.get("Images") or []
        rows.append(dict(name=trad(x.get("AttractionName")).strip(), lat=lat, lng=lng, src="觀光署", tag="",
                         city=city(pa.get("City")), town=(pa.get("Town") or "").strip(),
                         desc=len(re.sub(r"\s+", "", x.get("Description") or "")),
                         img=bool(imgs) and "notfound" not in imgs[0].get("URL", ""),
                         text=(x.get("Description") or "") + str(x.get("ServiceTimeInfo") or ""),
                         open=str(x.get("ServiceTimeInfo") or ""), types="", cls=set(x.get("AttractionClasses") or []),
                         status=x.get("ServiceStatus"), rank=2,
                         texts=[t for t in [re.sub(r"\s+", "", trad(x.get("Description")))] if t],
                         imgs=[i["URL"] for i in imgs if i.get("URL") and "notfound" not in i["URL"]][:1]))
    return [r for r in rows if 21.8 < r["lat"] < 26.5 and 118 < r["lng"] < 122.2]


def merge(rows):
    rows = sorted(rows, key=lambda r: -r["rank"])
    kept, grid, dup = [], defaultdict(list), 0
    for it in rows:
        hit = None
        for k in neighbors(grid, it["lat"], it["lng"], 250):
            d = haversine((it["lat"], it["lng"]), (k["lat"], k["lng"]))
            a, b = norm(it["name"]), norm(k["name"])
            if (d < 10 and not (it["src"] == k["src"] == "文資")) or (d < 250 and a and b and (a in b or b in a)):
                hit = k
                break
        if hit:
            dup += 1
            hit["also"] = sorted({*hit.get("also", []), it["src"]} - {hit["src"]})
            hit["desc"] = max(hit["desc"], it["desc"])
            hit["img"] = hit["img"] or it["img"]
            hit["cls"] |= it["cls"]
            hit["texts"] = hit["texts"] + it["texts"]   # 簡介可以參考兩個來源
            hit["imgs"] = hit["imgs"] + it["imgs"]       # 照片：文資優先，沒有再用觀光署
            hit["city"] = hit["city"] or it["city"]
            hit["town"] = hit["town"] or it["town"]
            continue
        kept.append(it)
        grid[grid_key(it["lat"], it["lng"])].append(it)
    return kept, dup


def decide(r):
    """回傳（建議, 理由）"""
    n = r["name"]
    if r["src"] == "文資":
        if GATE.search(n):
            return "不收", "在校園、醫院、宿舍、墓園或機關裡，平常不一定進得去"
        if re.search(r"不開放|無規劃開放|不對外開放|未開放", r["open"]):
            return "不收", "文資資料寫不開放"
        return "收", ""
    if r.get("status") not in (None, 1) or CLOSED.search(n):
        return "不收", "暫停開放或封閉"
    if FACTORY.search(n) or (14 in r["cls"] and not NOT_FACTORY.search(n)):
        return "不收", "觀光工廠"
    if SHOP.search(n) or (not r["cls"] & {3, 25} and not PUBLIC.search(n) and SELL.search(r.get("text", ""))):
        return "不收", "店家、商圈或夜市（要看營業時間）"
    if FARM.search(n):
        return "不收", "休閒農場、果園或露營區（範圍大，多要收費）"
    # 國家風景區裡的廟、館也會被觀光署標成「國家風景區類」，所以只看名稱，不看分類
    if HUGE.search(n) or (BIG2.search(n) and not PARK.search(n)):
        return "不收", "範圍很大，走不到一個明確的點"
    if EXCLUDE.search(n) and not KEEP.search(n):
        return "不收", "學校、醫院、機關或交通設施"
    return "收", ""


def kind(r):
    n = r["name"]
    # 觀光署的「廟宇類」分類不可靠（鹿港日茂行、隘門都被標成廟宇類），所以只看名稱和文資的類別
    worship = (WORSHIP.search(n) and not NOT_WORSHIP.search(n)) or re.search(r"寺廟|宗祠|教堂", r["types"])
    if worship:
        return "廟宇／教堂"
    if PARK.search(n) or r["cls"] & {15, 19}:
        return "公園綠地"
    if MUSEUM.search(n) or r["cls"] & {5, 25}:
        return "博物館／藝文"
    if STREET.search(n):
        return "老街／巷弄"
    if r["src"] == "文資" or 3 in r["cls"]:
        return "古蹟／老建築"
    if r["cls"] & NATURE:
        return "自然景觀"
    return "其他景點"


def main():
    root, attr_path, out = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
    rows, dup = merge(load(root, attr_path))
    for r in rows:
        r["建議"], r["理由"] = decide(r)
        r["類型"] = kind(r)
    take = [r for r in rows if r["建議"] != "不收"]
    g = defaultdict(list)
    for r in take:
        g[grid_key(r["lat"], r["lng"])].append(r)
    for r in rows:
        r["n1k"] = sum(1 for q in neighbors(g, r["lat"], r["lng"], 1000)
                       if haversine((r["lat"], r["lng"]), (q["lat"], q["lng"])) <= 1000)
    rank = {c: i for i, c in enumerate(ORDER)}
    rows.sort(key=lambda r: (r["建議"] == "不收", rank.get(r["city"], 99), r["town"], r["類型"], r["name"]))
    with open(out, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["建議", "理由", "縣市", "鄉鎮", "名稱", "類型", "文資身分", "來源", "附近1公里內可收的點",
                    "有簡介", "有照片", "緯度", "經度"])
        for r in rows:
            w.writerow([r["建議"], r["理由"], r["city"], r["town"], r["name"], r["類型"], r["tag"],
                        "、".join([r["src"], *r.get("also", [])]), r["n1k"],
                        "有" if r["desc"] >= 20 else "", "有" if r["img"] else "", round(r["lat"], 6), round(r["lng"], 6)])
    st = dict(合併掉的重複=dup, 列表筆數=len(rows), 建議=dict(Counter(r["建議"] for r in rows)),
              不收理由=dict(Counter(r["理由"] for r in rows if r["建議"] == "不收")),
              收的類型=dict(Counter(r["類型"] for r in take)),
              收的縣市=dict(sorted(Counter(r["city"] for r in take).items(), key=lambda kv: rank.get(kv[0], 99))))
    out.with_suffix(".stats.json").write_text(json.dumps(st, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(st, ensure_ascii=False))


if __name__ == "__main__":
    main()
