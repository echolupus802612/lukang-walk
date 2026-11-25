# 散步吧（原型）

出門散步吧：狼耳小嚮導替你挑一個附近的地方、替你指路，到達後才揭曉是哪裡。全台約 5,200 個地點，鹿港老街一帶是人工整理過的試點。

- 線上試玩：https://echolupus802612.github.io/lukang-walk/ （需允許定位與動作感測；附近 5 公里內沒有收錄的地點時，自動在鹿港天后宮前進入模擬模式）
- 模擬模式：網址加 `#sim`，按住「▲ 往目的地走」前進

## iPhone App

在 Mac 用裝有 iOS 17 或更新 SDK 的 Xcode 開啟 `ios/LukangWalk.xcodeproj`，選擇 **LukangWalk** 方案和一台 iPhone 模擬器，按 **⌘R**。專案已附字型、地點、照片、語音與授權頁。從原始碼建置 App 可直接使用這些檔案。

工程以 iOS 17.0 為最低部署版本。雲端編譯使用 Xcode 26.3。若 Xcode 16.4 的 iOS 18.5 模擬器啟動時回報 `libswiftWebKit.dylib` 遺失，請選擇更新的模擬器執行環境。[WebKit 問題紀錄](https://bugs.webkit.org/show_bug.cgi?id=293831)

要在自己的 iPhone 上試走，在 target 的 **Signing & Capabilities → Team** 選擇自己的開發團隊，接上手機後按 **⌘R**。預設 Bundle ID 為 `io.github.echolupus802612.lukangwalk`，若簽署時顯示識別碼已被註冊，請改成團隊可用的識別碼。

- **在桌前試玩**。在 **Product → Scheme → Edit Scheme → Run → Arguments** 新增 `-simulate-walk`，用 Debug 組態執行。選「近」並按「出門散步吧」，按住「▲ 往目的地走」直到地點卡出現，按「再走一趟」即可繼續。移除參數後，下一次啟動會使用手機定位。
- **實地試走**。出發時允許「使用 App 期間」與「準確位置」。實走用 iPhone 的定位與指南針，方向不可靠時改顯示絕對方位。到達後或按「收工」會關閉感測器與螢幕常亮。實走與模擬的足跡分開存在 App。
- **更新內容**。改動畫面或地點後執行 `python -B tools/build_page.py .`。改動照片、署名或字型授權後，執行 `python -B tools/build_ios_credits.py`。若新增介面用字或地點簡介，可用 `tools/build_fonts.py` 更新離線字型子集。

Mac 可在專案根目錄用以下命令檢查模擬器建置。

```sh
xcodebuild -project ios/LukangWalk.xcodeproj -scheme LukangWalk \
  -configuration Debug -destination 'generic/platform=iOS Simulator' build
```

## 結構

| 路徑 | 內容 |
|---|---|
| `src/app.html` | 頁面原始碼（資料以 `/*DATA*/[]` 佔位） |
| `data/lukang.json` | 鹿港一帶 68 個地點（WGS-84，人工整理） |
| `data/taiwan.json` | 全台其他地方的地點（鹿港老街 4.5 公里外），`tools/build_taiwan.py` 產生 |
| `tools/list_taiwan.py` | 全台選點規則：以景點、觀光地點、公園為主，逐筆標出收或不收與理由 → `survey/全台地點列表.csv` |
| `tools/build_taiwan.py` | 依上面的規則取「收」的地點 → `data/taiwan.json`；編號登記在 `data/place_ids_tw.json`（從 1001 起，只增不刪） |
| `data/desc_tw.json` | 全台地點簡介：依文資局、觀光署的來源原文濃縮成 2～3 句（Codex 依 `art/prompts/desc_tw.txt` 撰寫） |
| `tools/build_photos_tw.py` | 全台地點照片：文資局代表圖優先，其次觀光署景點圖，縮成 480×300 WebP → `docs/photos/<id>.webp`；出處記在 `data/photos_tw.json` |
| `survey/` | 全台資料試算報告、地點列表與統計 |
| `tools/build_data.py` | 合併文資局、OSM、維基 → `data/lukang.json`（原始下載不進版控） |
| `data/place_overrides.json` | 人工整理：地點簡介（附出處）、移出的地點；`build_data.py` 重跑時套用。草稿與審閱見 `data/desc_draft.md` |
| `data/place_ids.json` | 鹿港地點永久編號登記（只增不刪）；足跡認這個號碼，重跑資料不會換號 |
| `tools/build_photos.py` | 抓地點照片（人工指定的創用 CC 照片優先，其次文資局代表圖、觀光署景點圖），裁成 16:10 → `docs/photos/<id>.webp`；每張出處記在 `data/photos.json` |
| `tools/build_page.py` | 把資料嵌入頁面 → `docs/index.html`（GitHub Pages 從 `docs/` 發布） |
| `art/prompts/` | 角色動作的生圖提示詞（Codex image_gen） |
| `tools/build_sprites.py` | 把 `art/gen/` 的 2×2 動作表切成橫排精靈圖 → `docs/sprites/*.webp`（原圖不進版控） |
| `tools/voice_jobs.py` | 產生配音任務清單 `art/voice/jobs.json`（台詞、表演指令） |
| `tools/voice_gen.py` | 用 BreezeBlue `breeze-tts-2` 生成中文語音 → `docs/voice/*.mp3`（金鑰在本機讀取，不進版控） |

語音共 16 段：15 段固定台詞，加上所有地點共用的到達台詞「到啦～就是這裡！」（`voice/arrived.mp3`）。音色為 BreezeBlue Sparks（`voc_cfnf6vu2sp2p`），`language_code=zh`。音檔載不到時退回系統語音。

角色動作：idle 停著、walk 走動、point 指側邊（左邊用鏡像）、pointup 指前方、pull 拉扯（目標在背後）、care 關心（停太久／訊號差）、cheer 歡呼（到達）、bye 不捨（收工）。

```
python -I -B tools/build_page.py .
```

## 資料來源與授權

- 文化部文化資產局 開放資料（古蹟、歷史建築、文化景觀），政府資料開放授權條款
- © OpenStreetMap contributors，ODbL：本 repo 內的派生資料 `data/lukang.json` 同樣以 ODbL 提供
- 維基百科 地理座標查詢（條目名稱與座標）；部分地點簡介依維基條目內容改寫，CC BY-SA 4.0
- 交通部觀光署「景點 - 觀光資訊資料庫」（全台地點、簡介來源）、內政部「全國宗教資訊系統資料-寺廟」，政府資料開放授權條款（鹿港簡介見 `data/place_overrides.json`；全台簡介依文資局與觀光署原文濃縮，見 `data/desc_tw.json`）
- 地點照片（`docs/photos/`）：文化部文化資產局 開放資料代表圖、交通部觀光署 觀光資訊資料庫景點圖片、維基共享資源與 Flickr 的創用 CC 照片（見下表），每張的原始網址見 `data/photos.json`（鹿港）與 `data/photos_tw.json`（全台，縮小後使用，未逐張人工核對）
- 角色（狼耳少年）為作者自有 VTuber 形象，`docs/sprites/` 圖檔保留所有權利，不在上述開放授權內

### 創用 CC 授權照片

以下照片取自 Wikimedia Commons 與 Flickr，經裁切、縮小後使用；改作後的檔案沿用原授權（CC BY-SA 者同樣以 CC BY-SA 提供）。

| 檔案 | 地點 | 原始檔案 | 作者 | 授權 |
|---|---|---|---|---|
| `6.webp` | 真耶穌教會 | Wikimedia Commons：[202607 真耶穌教會鹿港教會 01.jpg](https://commons.wikimedia.org/wiki/File:202607_%E7%9C%9F%E8%80%B6%E7%A9%8C%E6%95%99%E6%9C%83%E9%B9%BF%E6%B8%AF%E6%95%99%E6%9C%83_01.jpg) | Jonashtand | CC BY-SA 4.0 |
| `13.webp` | 鹿港天主教堂 | Flickr：[Flickr 照片](https://www.flickr.com/photos/120532743@N04/14162484637) | 古攝古香 | CC BY 2.0 |
| `18.webp` | 鹿港牛墟頭景靈宮 | Wikimedia Commons：[鹿港景靈宮門殿.jpg](https://commons.wikimedia.org/wiki/File:%E9%B9%BF%E6%B8%AF%E6%99%AF%E9%9D%88%E5%AE%AE%E9%96%80%E6%AE%BF.jpg) | Outlookxp | CC BY-SA 4.0 |
| `20.webp` | 鹿港福靈宮 | Wikimedia Commons：[鹿港福靈宮正面照.jpg](https://commons.wikimedia.org/wiki/File:%E9%B9%BF%E6%B8%AF%E7%A6%8F%E9%9D%88%E5%AE%AE%E6%AD%A3%E9%9D%A2%E7%85%A7.jpg) | Outlookxp | CC BY-SA 4.0 |
| `21.webp` | 后宅闔港潤澤宮李殿王 | Flickr：[Flickr 照片](https://www.flickr.com/photos/120532743@N04/14169722267) | 古攝古香 | CC BY 2.0 |
| `25.webp` | 泊仔寮洽義堂 | Wikimedia Commons：[泊仔寮洽義堂門殿.jpg](https://commons.wikimedia.org/wiki/File:%E6%B3%8A%E4%BB%94%E5%AF%AE%E6%B4%BD%E7%BE%A9%E5%A0%82%E9%96%80%E6%AE%BF.jpg) | Outlookxp | CC BY-SA 4.0 |
| `27.webp` | 施姓宗祠 | Flickr：[Flickr 照片](https://www.flickr.com/photos/120532743@N04/14169584228) | 古攝古香 | CC BY 2.0 |
| `29.webp` | 玉渠宮 | Wikimedia Commons：[鹿港玉渠宮一景.jpg](https://commons.wikimedia.org/wiki/File:%E9%B9%BF%E6%B8%AF%E7%8E%89%E6%B8%A0%E5%AE%AE%E4%B8%80%E6%99%AF.jpg) | Outlookxp | CC BY-SA 4.0 |
| `30.webp` | 鹿港辜宅 | Wikimedia Commons：[鹿港民俗文物館 Lugang Folk Arts Museum - panoramio.jpg](https://commons.wikimedia.org/wiki/File:%E9%B9%BF%E6%B8%AF%E6%B0%91%E4%BF%97%E6%96%87%E7%89%A9%E9%A4%A8_Lugang_Folk_Arts_Museum_-_panoramio.jpg) | lienyuan lee | CC BY 3.0 |
| `35.webp` | 威靈廟(鹿港大將爺) | Wikimedia Commons：[鹿港威靈廟斜照.jpg](https://commons.wikimedia.org/wiki/File:%E9%B9%BF%E6%B8%AF%E5%A8%81%E9%9D%88%E5%BB%9F%E6%96%9C%E7%85%A7.jpg) | Outlookxp | CC BY-SA 4.0 |
| `36.webp` | 鹿港陸濟堂 | Flickr：[Flickr 照片](https://www.flickr.com/photos/120532743@N04/14361224102) | 古攝古香 | CC BY 2.0 |
| `37.webp` | 集英宮 | Wikimedia Commons：[鐵皮屋遮雨棚下的鹿港集英宮.jpg](https://commons.wikimedia.org/wiki/File:%E9%90%B5%E7%9A%AE%E5%B1%8B%E9%81%AE%E9%9B%A8%E6%A3%9A%E4%B8%8B%E7%9A%84%E9%B9%BF%E6%B8%AF%E9%9B%86%E8%8B%B1%E5%AE%AE.jpg) | Outlookxp | CC BY-SA 4.0 |
| `49.webp` | 郭厝保安宮 | Wikimedia Commons：[鹿港郭厝保安宮.jpg](https://commons.wikimedia.org/wiki/File:%E9%B9%BF%E6%B8%AF%E9%83%AD%E5%8E%9D%E4%BF%9D%E5%AE%89%E5%AE%AE.jpg) | Sean Chiu | CC BY-SA 4.0 |
| `51.webp` | 鹿港紫極殿 | Wikimedia Commons：[鹿港紫極殿正面照.jpg](https://commons.wikimedia.org/wiki/File:%E9%B9%BF%E6%B8%AF%E7%B4%AB%E6%A5%B5%E6%AE%BF%E6%AD%A3%E9%9D%A2%E7%85%A7.jpg) | Outlookxp | CC BY-SA 4.0 |
| `55.webp` | 文德宮 | Wikimedia Commons：[鹿港文德宮斜照.jpg](https://commons.wikimedia.org/wiki/File:%E9%B9%BF%E6%B8%AF%E6%96%87%E5%BE%B7%E5%AE%AE%E6%96%9C%E7%85%A7.jpg) | Outlookxp | CC BY-SA 4.0 |
| `57.webp` | 台灣基督長老教會鹿港教會 | Flickr：[Flickr 照片](https://www.flickr.com/photos/120532743@N04/14325847146) | 古攝古香 | CC BY 2.0 |
| `60.webp` | 文開書院 | Wikimedia Commons：[文開書院三川門.jpg](https://commons.wikimedia.org/wiki/File:%E6%96%87%E9%96%8B%E6%9B%B8%E9%99%A2%E4%B8%89%E5%B7%9D%E9%96%80.jpg) | Outlookxp | CC BY-SA 4.0 |
| `65.webp` | 鹿港護安宮 | Wikimedia Commons：[鹿港護安宮正面照.jpg](https://commons.wikimedia.org/wiki/File:%E9%B9%BF%E6%B8%AF%E8%AD%B7%E5%AE%89%E5%AE%AE%E6%AD%A3%E9%9D%A2%E7%85%A7.jpg) | Outlookxp | CC BY-SA 4.0 |
