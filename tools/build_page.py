"""把 data/lukang.json 嵌进 src/app.html → docs/index.html（GitHub Pages 从 docs/ 发布）（单文件，哪里都能打开）

用法：python -I -B tools/build_page.py <项目根目录>
"""
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
places = json.loads((root / "data" / "lukang.json").read_text(encoding="utf-8"))
slim = [{k: p[k] for k in ("id", "name", "lat", "lng", "cat", "tag", "desc")} for p in places]
# 念出來的地名（sn）取自配音任務清單，讓對話框文字和語音一致
jobs_path = root / "art" / "voice" / "jobs.json"
if jobs_path.exists():
    sn = {j["place_id"]: j["text"].removeprefix("到了！是").removesuffix("。")
          for j in json.loads(jobs_path.read_text(encoding="utf-8")) if j.get("place_id")}
    for x in slim:
        if x["id"] in sn and sn[x["id"]] != x["name"]:
            x["sn"] = sn[x["id"]]
# 有照片的地點標上出處代號（文＝文資局、觀＝觀光署、共＝維基共享資源），照片在 docs/photos/<id>.webp
photos_path = root / "data" / "photos.json"
if photos_path.exists():
    ph = json.loads(photos_path.read_text(encoding="utf-8"))["photos"]
    for x in slim:
        c = ph.get(str(x["id"]), {}).get("credit", "")
        if c:
            x["ph"] = "文" if "文化資產" in c else "共" if "Commons" in c else "觀"
blob = json.dumps(slim, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = (root / "src" / "app.html").read_text(encoding="utf-8")
assert "/*DATA*/[]" in html
out = root / "docs" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(html.replace("/*DATA*/[]", blob), encoding="utf-8")
print(f"{len(slim)} 个地点 → {out}（{out.stat().st_size // 1024} KB）")
