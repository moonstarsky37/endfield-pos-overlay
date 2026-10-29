# Endfield 座標浮窗（endfield-pos-overlay）

[English](README.en.md)

把官方《明日方舟：終末地》網頁地圖（`https://game.skport.com/map/endfield`）同步到的角色座標，顯示在一個置頂、可拖曳、可縮放的小視窗。點一下數字即複製。用途：對照遊戲內位置與地圖或 3D 場景資料時，不必切換視窗。

![遊戲畫面右上角的座標浮窗](docs/images/demo-vista.jpg)

> 非官方工具，與 GRYPHLINE / Hypergryph 無關。只讀取：不修改、不阻擋、不送出任何遊戲或網站資料。座標只送到本機 `127.0.0.1`。

## 運作方式

```
官方地圖網頁（瀏覽器，已登入、「位置同步」切到 ON）
   │  使用者腳本複製頁面本來就收到的位置訊息（約每秒一筆）
   ▼
http://127.0.0.1:27600/pos   ← 浮窗程式在本機開的接收埠
   ▼
置頂浮窗
```

| 零件 | 說明 |
|---|---|
| `userscript/endfield-pos-relay.user.js` | 使用者腳本（Tampermonkey / Violentmonkey），支援 Chrome、Edge、Firefox |
| 浮窗程式 | Windows：`endfield-pos-overlay.exe`；macOS：`.app`；或以 Python 3.10+ 執行原始碼 |

## 安裝

三步：Tampermonkey → 腳本 → 浮窗程式。每一步結尾有一行「確認」。

### 1. 使用者腳本管理器

| 瀏覽器 | 擴充套件 | 額外設定 |
|---|---|---|
| Chrome | [Tampermonkey](https://chromewebstore.google.com/detail/dhdgffkkebhmkfjojejmpbldmpobfkfo) | 網址列貼 `chrome://extensions/?id=dhdgffkkebhmkfjojejmpbldmpobfkfo`（Tampermonkey 的「詳細資料」頁），打開「允許使用者指令碼」。沒有這個開關的舊版 Chrome：在 `chrome://extensions` 右上角打開「開發人員模式」 |
| Edge | [Tampermonkey](https://microsoftedge.microsoft.com/addons/detail/iikmkjmpaadaobahmlepeloendndfphd) | 網址列貼 `edge://extensions/?id=iikmkjmpaadaobahmlepeloendndfphd`，打開「允許使用者指令碼」；或打開「開發人員模式」 |
| Firefox | [Tampermonkey](https://addons.mozilla.org/firefox/addon/tampermonkey/) 或 [Violentmonkey](https://addons.mozilla.org/firefox/addon/violentmonkey/) | 無 |

同一頁也可從瀏覽器右上角的 Tampermonkey 圖示按右鍵 →「管理擴充功能」進入。每一步的截圖見 Tampermonkey FAQ：[Permission to execute userscripts](https://www.tampermonkey.net/faq.php?q=Q209)。

**確認**：Tampermonkey 詳細資料頁的「允許使用者指令碼」為開啟。關閉時腳本可以安裝但不會執行，也不會出現錯誤訊息。同頁的「Service Worker」、「檢視畫面」連結與本工具無關。

### 2. 腳本

在瀏覽器開啟 **[安裝連結](https://raw.githubusercontent.com/moonstarsky37/endfield-pos-overlay/main/userscript/endfield-pos-relay.user.js)**，Tampermonkey 顯示安裝畫面後按「安裝」。之後的更新由 Tampermonkey 自動完成。

- 畫面標題是「重新安裝」：代表已安裝過。「已安裝版本」比連結的版本舊按「重新安裝」，相同按「取消」。
- 連結只下載檔案、沒有安裝畫面：第 1 步未完成（Tampermonkey 未安裝，或「允許使用者指令碼」未開啟）。
- `.user.js` 不是可執行程式。在 Windows 雙擊會出現「Windows Script Host」錯誤視窗。
- 離線安裝：把 `.user.js` 檔拖進瀏覽器視窗，或在 Tampermonkey 的「新增腳本」貼上內容。

**確認**：Tampermonkey 圖示的腳本清單含「Endfield 座標中繼」，開關為開啟。

### 3. 浮窗程式

從 [Releases](../../releases) 下載：

- Windows：`endfield-pos-overlay-windows.exe`，單一檔案，雙擊執行。程式沒有程式碼簽章，SmartScreen 可能顯示「Windows 已保護您的電腦」：按「其他資訊」→「仍要執行」。
- macOS：`endfield-pos-overlay-macos.zip`，解壓縮後把 `.app` 移到「應用程式」。程式未經 Apple 公證，第一次開啟用右鍵 →「打開」。

或以原始碼執行（Python 3.10+，只用標準函式庫）：

```
python run_overlay.py
```

Windows 可雙擊 `start-overlay.cmd`，macOS 可雙擊 `start-overlay.command`。

**確認**：出現黑色小視窗，顯示「等待網頁同步位置…」。

## 使用

1. 啟動浮窗程式。
2. 瀏覽器開啟 [官方地圖](https://game.skport.com/map/endfield)，登入，把「位置同步」切到 ON。帶語言代碼的網址（`/zh-tw/map/…`、`/en/map/…`）同樣適用。
3. 三處同時符合即為成功：

| 位置 | 狀態 |
|---|---|
| 地圖頁右下角 | 一行小字「座標中繼：送出中」 |
| Tampermonkey 圖示 | 數字 1（本頁有一個腳本執行中） |
| 浮窗 | 約每秒更新一次 |

![邊玩邊看座標：浮窗可拖到畫面任何位置](docs/images/demo-ingame.jpg)

| 操作 | 效果 |
|---|---|
| 左鍵拖曳 | 移動視窗 |
| 右下角 ◢ 拖曳 | 改大小，字級隨之縮放 |
| Ctrl + 滾輪（macOS：⌘ + 滾輪） | 調字級 |
| 左鍵點一下數字 | 複製 `x, y, z` 到剪貼簿（例：`-314.00, 323.00, 400.00`） |
| 右鍵（macOS：右鍵或 Control + 點） | 選單：複製、座標順序、透明度、字級、重設、語言、結束 |

- 座標預設為遊戲原始順序（`x y z`，`y` 是高度）。右鍵選單可切成 Blender 順序（`x z y`，Z 朝上）。
- 超過 5 秒沒有新資料，數字變灰；網頁斷線時顯示「網頁已離線」。
- 設定（位置、大小、字級、透明度、順序、語言）自動儲存：
  Windows `%APPDATA%\endfield-pos-overlay\state.json`；macOS `~/Library/Application Support/endfield-pos-overlay/state.json`。

### 命令列參數

```
--port 27600        接收埠（改埠時，腳本選單「設定浮窗接收埠」也要改成同一值）
--lang auto|zh|en   介面語言
--alpha 0.9         透明度 0.2–1.0
--state-file PATH   設定檔位置
```

## 疑難排解

瀏覽器開 `http://127.0.0.1:27600/health`，正常回應類似 `{"ok": true, "last_update_age_s": 0.3, "frames": 123}`；`frames` 是浮窗收到的筆數。

| 狀況 | 原因 | 處理 |
|---|---|---|
| 地圖頁右下角沒有小字 | 腳本未在本頁執行 | 重做安裝第 1、2 步的「確認」。腳本版本需 0.2.1 以上（舊版不匹配帶語言代碼的網址），再開一次安裝連結即更新 |
| 小字「連不到 127.0.0.1:27600」 | 浮窗未啟動 | 啟動浮窗 |
| 小字「等待」 | 「位置同步」未切到 ON | 切到 ON |
| `/health` 打不開 | 浮窗未啟動 | 啟動浮窗 |
| `/health` 的 `frames` 為 0 | 腳本未送出任何資料 | 同「沒有小字」 |
| 浮窗停在「等待網頁同步位置…」 | 以上任一 | 依上列檢查 |
| 雙擊 `.user.js` 出現「Windows Script Host」錯誤 | 檔案不是可執行程式 | 安裝 Tampermonkey（第 1 步），在瀏覽器開安裝連結（第 2 步） |
| 浮窗啟動時顯示「無法在 127.0.0.1:27600 開啟接收埠」 | 已有一個浮窗在執行，或埠被其他程式占用 | 關閉舊浮窗，或換埠（`--port 27601`，腳本選單同步修改） |
| 小字「掛鉤失敗」 | 腳本的 `@sandbox` 被改成 `DOM` | 在 Tampermonkey 編輯腳本，保持 `@sandbox raw`，重新整理頁面 |
| 浮窗在遊戲裡看不到 | 獨占全螢幕蓋住所有置頂視窗 | 遊戲改成「無邊框視窗」模式。macOS 的全螢幕 App 在獨立桌面空間，同樣看不到 |
| 數字變灰 | 超過 5 秒沒有新資料，分頁被休眠或斷線 | 地圖分頁留在前景，或關閉該分頁的省電休眠 |

官網端檢查：地圖頁按 F12 → 網路 → WS → `map` → 訊息。每秒有 `"type":1012` 的訊息代表官網有送座標，問題在腳本或浮窗；沒有則「位置同步」未生效，關閉再開一次。

小字末尾的 `inject` / `page` / `sandbox` 是腳本掛鉤方式。回報問題請附：該行小字、`/health` 回應、瀏覽器與 Tampermonkey 版本。

## 限制

- 只有地圖分頁開著、「位置同步」為 ON 時才有資料。
- 每秒一筆是官方伺服器的推送頻率。
- 官方網站改版可能使腳本失效。
- macOS 版未在實機驗證。
- 區域英文名尚未收錄，英文介面顯示區域代號。

## 安全

- 浮窗只監聽 `127.0.0.1`，其他電腦無法連入。
- 只接受使用者腳本管理器送來的請求；其他網站送的請求回 403，避免其他網頁送入假座標。
- 腳本不讀取、不送出登入資訊；只轉送位置訊息（type 1011 / 1012 / 1013）。

## 開發

```
python -m unittest                                               # 單元測試（標準函式庫）
uv run --with playwright python tools/test_userscript.py         # 腳本端對端測試（假地圖頁 + 假 WebSocket）
```

GitHub Actions（`.github/workflows/build.yml`）在推送 `v*` tag 時建置 Windows exe 與 macOS app 並發佈 Release。

## 授權

MIT
