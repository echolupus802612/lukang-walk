"""替地点找官方照片 → docs/photos/<id>.webp，出处记在 data/photos.json

用法：python -I -B tools/build_photos.py <项目根目录> <观光署 AttractionList.json>

来源优先顺序：
  0. data/photos.json 的 "commons"：人工挑的维基共享资源（Wikimedia Commons）档名，作者与授权从 API 取得
  1. 文化部文化资产局 开放资料的代表图（data/raw/boch_*.json 的 representImage）
  2. 交通部观光署 观光资讯资料库的景点图片（第一张）
每张裁成 16:10、宽 720，存 WebP。原图下载到 art/photos/raw/（不进版控）。
data/photos.json 里 "skip" 列出的编号不配照片（人工看过觉得不对的）。
"""
import hashlib, io, json, math, re, sys, time, urllib.parse, urllib.request
from pathlib import Path
from PIL import Image, ImageOps

W, H = 720, 450
CENTER = (24.0565, 120.4335)
UA = {"User-Agent": "lukang-walk-prototype/0.1 (photo build script)"}


def hv(a, b):
    R = 6371000
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(h), math.sqrt(1 - h))


def norm(n):
    return re.sub(r"[\s()（）・·]|^彰化縣?|^鹿港", "", n or "")


def same(a, b):
    a, b = norm(a), norm(b)
    return bool(a and b) and (a == b or a in b or b in a)


def candidates(root, attr_path):
    boch = []
    for f in ("boch_1.1.json", "boch_1.2.json", "boch_3.1.json"):
        for x in json.loads((root / "data" / "raw" / f).read_text(encoding="utf-8")):
            img = x.get("representImage") or {}
            try:
                la, lo = float(x["latitude"]), float(x["longitude"])
            except (KeyError, TypeError, ValueError):
                continue
            if img.get("original") and hv(CENTER, (la, lo)) < 6000:
                boch.append((x["caseName"], (la, lo), img["original"]))
    attr = []
    for x in json.loads(Path(attr_path).read_text(encoding="utf-8-sig"))["Attractions"]:
        if not x.get("Images") or not x.get("PositionLat"):
            continue
        ll = (float(x["PositionLat"]), float(x["PositionLon"]))
        if hv(CENTER, ll) < 6000:
            attr.append((x["AttractionName"], ll, x["Images"][0]["URL"]))
    return boch, attr


def commons_info(title):
    """维基共享资源档案 → (缩图网址, 作者, 授权, 档案页网址)"""
    q = urllib.parse.urlencode({"action": "query", "titles": title, "prop": "imageinfo", "format": "json",
                                "iiprop": "url|extmetadata", "iiurlwidth": 1280})
    for attempt in range(5):
        try:
            r = json.load(urllib.request.urlopen(urllib.request.Request(
                "https://commons.wikimedia.org/w/api.php?" + q, headers=UA), timeout=60))
            break
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(10 * (attempt + 1))
    ii = list(r["query"]["pages"].values())[0]["imageinfo"][0]
    m = ii.get("extmetadata", {})
    artist = re.sub(r"<[^>]+>", "", m.get("Artist", {}).get("value", "")).strip()
    return ii["thumburl"], artist, m.get("LicenseShortName", {}).get("value", ""), ii["descriptionurl"]


def fetch(url, dest):
    if dest.exists():
        return dest.read_bytes()
    q = urllib.request.Request(urllib.parse.quote(url, safe=":/?=&%()"), headers=UA)
    data = urllib.request.urlopen(q, timeout=60).read()
    dest.write_bytes(data)
    return data


def main():
    root, attr_path = Path(sys.argv[1]), sys.argv[2]
    places = json.loads((root / "data" / "lukang.json").read_text(encoding="utf-8"))
    meta_path = root / "data" / "photos.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    skip = {int(k) for k in meta.get("skip", {})}
    raw, out = root / "art" / "photos" / "raw", root / "docs" / "photos"
    raw.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    boch, attr = candidates(root, attr_path)
    photos = {}
    for p in places:
        if p["id"] in skip:
            continue
        ll = (p["lat"], p["lng"])
        pick, extra = None, {}
        title = meta.get("commons", {}).get(str(p["id"]))
        if title:
            url, artist, lic, page = commons_info(title)
            pick = ("Wikimedia Commons", url, title)
            extra = {"author": artist, "license": lic, "page": page}
            time.sleep(1)
        for name, at, url in ([] if pick else boch):
            if same(name, p["name"]) and hv(at, ll) < 300:
                pick = ("文化部文化資產局", url, name)
                break
        if not pick:
            for name, at, url in attr:
                if same(name, p["name"]) and hv(at, ll) < 300:
                    pick = ("交通部觀光署觀光資訊資料庫", url, name)
                    break
        if not pick:
            continue
        credit, url, matched = pick
        try:
            key = hashlib.md5(url.encode()).hexdigest()[:8]   # 换了来源就重新下载，不会拿到旧图
            data = fetch(url, raw / f"{p['id']}_{key}{Path(url).suffix.lower() or '.jpg'}")
            im = ImageOps.exif_transpose(Image.open(io.BytesIO(data))).convert("RGB")
        except Exception as e:  # 网址失效或不是图片就略过
            print(f"{p['id']:3d} {p['name']} 下载失败：{e}")
            continue
        ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.45)).save(out / f"{p['id']}.webp", "WEBP", quality=72, method=6)
        photos[str(p["id"])] = {"credit": credit, "url": url, "matched": matched, **extra}
        print(f"{p['id']:3d} {p['name']} ← {credit}（{matched}）")
    # 清掉已不再配照片的旧檔
    for f in out.glob("*.webp"):
        if f.stem not in photos:
            f.unlink()
    meta = {"_note": meta.get("_note", "地點照片出處（build_photos.py 產生）；skip＝人工排除、不配照片的編號"),
            "skip": meta.get("skip", {}), "commons": meta.get("commons", {}), "photos": photos}
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    kb = sum(f.stat().st_size for f in out.glob("*.webp")) // 1024
    print(f"共 {len(photos)} 張，{kb} KB")


if __name__ == "__main__":
    main()
