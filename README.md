# 鹿港散步籤（原型）

抽一支散步籤，籤筒精用那支籤替你指路；走到了才解籤，揭曉是哪裡。

- 線上試玩：https://echolupus802612.github.io/lukang-walk/ （需允許定位與動作感測；不在鹿港時自動進入模擬模式）
- 模擬模式：網址加 `#sim`，按住「▲ 朝籤走」前進

## 結構

| 路徑 | 內容 |
|---|---|
| `src/app.html` | 頁面原始碼（資料以 `/*DATA*/[]` 佔位） |
| `data/lukang.json` | 鹿港鎮內 72 個地點（WGS-84） |
| `tools/build_data.py` | 合併文資局、OSM、維基 → `data/lukang.json`（原始下載不進版控） |
| `tools/build_page.py` | 把資料嵌入頁面 → `docs/index.html`（GitHub Pages 從 `docs/` 發布） |

```
python -I -B tools/build_page.py .
```

## 資料來源與授權

- 文化部文化資產局 開放資料（古蹟、歷史建築、文化景觀），政府資料開放授權條款
- © OpenStreetMap contributors，ODbL：本 repo 內的派生資料 `data/lukang.json` 同樣以 ODbL 提供
- 維基百科 地理座標查詢（條目名稱與座標）
