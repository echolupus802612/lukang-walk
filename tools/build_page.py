"""把 data/lukang.json 嵌进 src/app.html → docs/index.html（GitHub Pages 从 docs/ 发布）（单文件，哪里都能打开）

用法：python -I -B tools/build_page.py <项目根目录>
"""
import json, sys
from pathlib import Path

root = Path(sys.argv[1])
places = json.loads((root / "data" / "lukang.json").read_text(encoding="utf-8"))
slim = [{k: p[k] for k in ("id", "name", "lat", "lng", "cat", "tag", "desc")} for p in places]
blob = json.dumps(slim, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
html = (root / "src" / "app.html").read_text(encoding="utf-8")
assert "/*DATA*/[]" in html
out = root / "docs" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(html.replace("/*DATA*/[]", blob), encoding="utf-8")
print(f"{len(slim)} 个地点 → {out}（{out.stat().st_size // 1024} KB）")
