"""全台地點資料：依 list_taiwan.py 的規則取「收」的地點 → data/taiwan.json（給頁面用）

用法：python -I -B tools/build_taiwan.py <專案根目錄> <觀光署 AttractionList.json>
- 鹿港老街一帶（中心 4.5 公里內）沿用人工整理的 data/lukang.json，這裡不重複收
- 編號登記在 data/place_ids_tw.json，從 1001 起，只增不刪（足跡認這個號碼）
- 簡介由 data/desc_tw.json 提供（依來源資料濃縮的 2～3 句）；沒有的先留空
- 另外輸出 data/raw/tw_sources.jsonl（簡介用的來源原文）、data/raw/tw_photo_urls.json（照片原始網址），不進版控
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from build_data import CENTER, RADIUS, haversine, norm   # noqa: E402
import list_taiwan as lt                                  # noqa: E402

CAT = {"廟宇／教堂": "worship", "古蹟／老建築": "history", "老街／巷弄": "structure", "公園綠地": "nature",
       "自然景觀": "scenic", "博物館／藝文": "culture", "其他景點": "other"}


def assign(rows, reg_path):
    reg = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else []
    used, nxt = set(), max([1000] + [e["id"] for e in reg]) + 1
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
    root, attr = Path(sys.argv[1]), sys.argv[2]
    rows, _ = lt.merge(lt.load(root, attr))
    take = []
    for r in rows:
        if lt.decide(r)[0] != "收" or haversine(CENTER, (r["lat"], r["lng"])) <= RADIUS:
            continue
        r["cat"] = CAT[lt.kind(r)]
        take.append(r)
    take.sort(key=lambda r: (r["city"], r["town"], r["name"], r["lat"]))
    assign(take, root / "data" / "place_ids_tw.json")
    dp = root / "data" / "desc_tw.json"
    desc = json.loads(dp.read_text(encoding="utf-8")) if dp.exists() else {}
    data = [dict(id=r["id"], name=r["name"], lat=round(r["lat"], 6), lng=round(r["lng"], 6), cat=r["cat"],
                 tag=r["tag"], desc=desc.get(str(r["id"]), ""), city=r["city"], town=r["town"],
                 src=sorted({r["src"], *r.get("also", [])})) for r in take]
    (root / "data" / "taiwan.json").write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    raw = root / "data" / "raw"
    with open(raw / "tw_sources.jsonl", "w", encoding="utf-8") as f:
        for r in take:
            f.write(json.dumps({"id": r["id"], "name": r["name"], "city": r["city"], "town": r["town"], "tag": r["tag"],
                                "sources": [t[:1500] for t in r["texts"]][:3]}, ensure_ascii=False) + "\n")
    (raw / "tw_photo_urls.json").write_text(json.dumps({str(r["id"]): r["imgs"] for r in take}, ensure_ascii=False),
                                            encoding="utf-8")
    from collections import Counter
    print(len(data), "處", dict(Counter(d["cat"] for d in data)), "有簡介", sum(1 for d in data if d["desc"]),
          "無來源原文", sum(1 for r in take if not r["texts"]), "無照片網址", sum(1 for r in take if not r["imgs"]))


if __name__ == "__main__":
    main()
