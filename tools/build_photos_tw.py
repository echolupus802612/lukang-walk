"""全台地點照片 → docs/photos/<id>.webp（縮小版），出處記在 data/photos_tw.json

用法：python -I -B tools/build_photos_tw.py <專案根目錄>
照片網址來自 build_taiwan.py 產生的 data/raw/tw_photo_urls.json（文資局代表圖優先，其次觀光署景點圖）。
全台地點太多，沒辦法逐張人工核對，所以只縮小、不挑圖：裁成 16:10、480×300、WebP 品質 60（每張約 20～30 KB）。
原圖快取在 art/photos/raw_tw/（不進版控）。已經有輸出檔的會跳過，中斷後可以接著跑。
"""
import hashlib, io, json, sys, threading, time, urllib.parse, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from PIL import Image, ImageOps

W, H = 480, 300
UA = {"User-Agent": "sanpo-walk-prototype/0.1 (photo build script)"}


def credit(url):
    return "文化部文化資產局" if "boch.gov.tw" in url else "交通部觀光署觀光資訊資料庫"


def fetch(url, cache):
    key = hashlib.md5(url.encode()).hexdigest()[:10]
    f = cache / f"{key}{Path(urllib.parse.urlparse(url).path).suffix.lower()[:5] or '.jpg'}"
    if f.exists():
        return f.read_bytes()
    q = urllib.request.Request(urllib.parse.quote(url, safe=":/?=&%()~+,;@!$'*"), headers=UA)
    for attempt in range(2):
        try:
            data = urllib.request.urlopen(q, timeout=40).read()
            f.write_bytes(data)
            return data
        except Exception:
            if attempt:
                raise
            time.sleep(3)


def main():
    root = Path(sys.argv[1])
    urls = json.loads((root / "data" / "raw" / "tw_photo_urls.json").read_text(encoding="utf-8"))
    out, cache = root / "docs" / "photos", root / "art" / "photos" / "raw_tw"
    out.mkdir(parents=True, exist_ok=True)
    cache.mkdir(parents=True, exist_ok=True)
    meta_path = root / "data" / "photos_tw.json"
    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    lock, fails, done = threading.Lock(), {}, [0]

    def one(item):
        pid, cands = item
        dest = out / f"{pid}.webp"
        if dest.exists() and pid in meta:
            return
        err = "沒有照片網址"
        for u in cands:
            try:
                im = ImageOps.exif_transpose(Image.open(io.BytesIO(fetch(u, cache)))).convert("RGB")
                ImageOps.fit(im, (W, H), Image.LANCZOS, centering=(0.5, 0.45)).save(dest, "WEBP", quality=60, method=6)
                with lock:
                    meta[pid] = {"credit": credit(u), "url": u}
                    fails.pop(pid, None)
                break
            except Exception as e:
                err = f"{type(e).__name__}: {e}"[:120]
        else:
            with lock:
                fails[pid] = err
        with lock:
            done[0] += 1
            if done[0] % 200 == 0:
                print(done[0], "處", flush=True)
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=0), encoding="utf-8")

    with ThreadPoolExecutor(6) as ex:
        list(ex.map(one, urls.items()))
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=0), encoding="utf-8")
    (root / "art" / "photos" / "tw_failed.json").write_text(json.dumps(fails, ensure_ascii=False, indent=0), encoding="utf-8")
    kb = sum((out / f"{k}.webp").stat().st_size for k in meta if (out / f"{k}.webp").exists()) // 1024
    print(f"有照片 {len(meta)} 處，失敗 {len(fails)}，共 {kb} KB")


if __name__ == "__main__":
    main()
