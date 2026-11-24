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
| `art/prompts/` | 角色動作的生圖提示詞（Codex image_gen） |
| `tools/build_sprites.py` | 把 `art/gen/` 的 2×2 動作表切成橫排精靈圖 → `docs/sprites/*.webp`（原圖不進版控） |

角色動作：idle 停著、walk 走動、point 指側邊（左邊用鏡像）、pointup 指前方、pull 拉扯（目標在背後）、care 關心（停太久／訊號差）、cheer 歡呼（到達）、bye 不捨（收工）。

```
python -I -B tools/build_page.py .
```

## 資料來源與授權

- 文化部文化資產局 開放資料（古蹟、歷史建築、文化景觀），政府資料開放授權條款
- © OpenStreetMap contributors，ODbL：本 repo 內的派生資料 `data/lukang.json` 同樣以 ODbL 提供
- 維基百科 地理座標查詢（條目名稱與座標）
- 角色（狼耳少年）為作者自有 VTuber 形象，`docs/sprites/` 圖檔保留所有權利，不在上述開放授權內
