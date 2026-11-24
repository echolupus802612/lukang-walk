# 鹿港散步籤（原型）

抽一支散步籤，籤筒精用那支籤替你指路；走到了才解籤，揭曉是哪裡。

- 線上試玩：https://echolupus802612.github.io/lukang-walk/ （需允許定位與動作感測；不在鹿港時自動進入模擬模式）
- 模擬模式：網址加 `#sim`，按住「▲ 朝籤走」前進

## 結構

| 路徑 | 內容 |
|---|---|
| `src/app.html` | 頁面原始碼（資料以 `/*DATA*/[]` 佔位） |
| `data/lukang.json` | 鹿港一帶 68 個可抽的地點（WGS-84） |
| `tools/build_data.py` | 合併文資局、OSM、維基 → `data/lukang.json`（原始下載不進版控） |
| `data/place_overrides.json` | 人工整理：地點簡介（附出處）、移出抽籤的地點；`build_data.py` 重跑時套用。草稿與審閱見 `data/desc_draft.md` |
| `data/place_ids.json` | 地點永久編號登記（只增不刪）；足跡和到達語音都認這個號碼，重跑資料不會換號 |
| `tools/build_page.py` | 把資料嵌入頁面 → `docs/index.html`（GitHub Pages 從 `docs/` 發布） |
| `art/prompts/` | 角色動作的生圖提示詞（Codex image_gen） |
| `tools/build_sprites.py` | 把 `art/gen/` 的 2×2 動作表切成橫排精靈圖 → `docs/sprites/*.webp`（原圖不進版控） |
| `tools/voice_jobs.py` | 產生配音任務清單 `art/voice/jobs.json`（台詞、表演指令、念出來的地名） |
| `tools/voice_gen.py` | 用 BreezeBlue `breeze-tts-2` 生成中文語音 → `docs/voice/*.mp3`（金鑰在本機讀取，不進版控） |

語音：87 句預錄（固定台詞 15 句＋每個地點一句到達台詞），音色 BreezeBlue Sparks（`voc_cfnf6vu2sp2p`），`language_code=zh`。音檔載不到時退回瀏覽器內建 TTS。

角色動作：idle 停著、walk 走動、point 指側邊（左邊用鏡像）、pointup 指前方、pull 拉扯（目標在背後）、care 關心（停太久／訊號差）、cheer 歡呼（到達）、bye 不捨（收工）。

```
python -I -B tools/build_page.py .
```

## 資料來源與授權

- 文化部文化資產局 開放資料（古蹟、歷史建築、文化景觀），政府資料開放授權條款
- © OpenStreetMap contributors，ODbL：本 repo 內的派生資料 `data/lukang.json` 同樣以 ODbL 提供
- 維基百科 地理座標查詢（條目名稱與座標）；部分地點簡介依維基條目內容改寫
- 交通部觀光署「景點 - 觀光資訊資料庫」、內政部「全國宗教資訊系統資料-寺廟」，政府資料開放授權條款（地點簡介，見 `data/place_overrides.json`）
- 角色（狼耳少年）為作者自有 VTuber 形象，`docs/sprites/` 圖檔保留所有權利，不在上述開放授權內
