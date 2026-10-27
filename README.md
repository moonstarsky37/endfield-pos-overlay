# Endfield 座標浮窗（endfield-pos-overlay）

[English](README.en.md)

把官方《明日方舟：終末地》網頁地圖（`https://game.skport.com/map/endfield`）同步到的角色座標，顯示在一個**永遠置頂、可拖曳、可縮放**的小視窗裡，邊玩邊看、點一下就複製。

![遊戲畫面右上角的座標浮窗](docs/images/demo-vista.jpg)

> 非官方工具，與 GRYPHLINE / Hypergryph 無關。只讀：不改、不擋、不送出任何遊戲或網站資料；座標只送到你自己電腦上的 `127.0.0.1`。

## 運作方式

```
官方地圖網頁（你的瀏覽器，已登入、按了「同步位置」）
   │  使用者腳本攔下頁面自己收到的位置訊息（約每秒一筆）
   ▼
http://127.0.0.1:27600/pos   ← 浮窗程式在本機開的接收埠
   ▼
置頂浮窗
```

兩個零件：

| 零件 | 說明 |
|---|---|
| `userscript/endfield-pos-relay.user.js` | 瀏覽器使用者腳本（Tampermonkey / Violentmonkey），Chrome、Edge、Firefox 都可以 |
| 浮窗程式 | Windows：`endfield-pos-overlay.exe`；macOS：`.app`；或用 Python 3.10+ 直接跑原始碼 |

## 安裝

### 1. 瀏覽器裝使用者腳本管理器

| 瀏覽器 | 擴充套件 | 額外設定 |
|---|---|---|
| Chrome | [Tampermonkey](https://chromewebstore.google.com/detail/dhdgffkkebhmkfjojejmpbldmpobfkfo) | 擴充功能 → Tampermonkey → 詳細資料 → 打開「**允許使用者指令碼**」（舊版 Chrome 是打開右上角「開發人員模式」） |
| Edge | [Tampermonkey](https://microsoftedge.microsoft.com/addons/detail/iikmkjmpaadaobahmlepeloendndfphd) | 同上：擴充功能 → 詳細資料 → 「允許使用者指令碼」；或打開「開發人員模式」 |
| Firefox | [Tampermonkey](https://addons.mozilla.org/firefox/addon/tampermonkey/) 或 [Violentmonkey](https://addons.mozilla.org/firefox/addon/violentmonkey/) | 無 |

### 2. 安裝腳本

點這個連結：**[安裝 endfield-pos-relay.user.js](https://raw.githubusercontent.com/moonstarsky37/endfield-pos-overlay/main/userscript/endfield-pos-relay.user.js)**，擴充套件會跳出安裝畫面 → 按「安裝」。之後腳本有新版會自動更新。

**不要**把 `.user.js` 下載下來雙擊：它不是程式，雙擊會跳出「Windows Script Host」錯誤。一定要在瀏覽器裡點連結，由 Tampermonkey 安裝。

（離線安裝：把 `.user.js` 檔拖進瀏覽器視窗，或在擴充套件的「新增腳本」貼上內容。）

### 3. 下載浮窗程式

到 [Releases](../../releases) 下載：

- **Windows**：`endfield-pos-overlay-windows.exe`，放哪都可以，雙擊執行。
  第一次執行 SmartScreen 可能顯示「Windows 已保護您的電腦」（程式沒有付費簽章）→「其他資訊」→「仍要執行」。
- **macOS**：`endfield-pos-overlay-macos.zip`，解壓後把 `.app` 拖到「應用程式」。
  第一次開啟要**按右鍵 →「打開」**（程式沒有經過 Apple 公證）。

會 Python 的話也可以直接跑原始碼（只用標準函式庫，不用裝任何套件）：

```
python run_overlay.py
```

Windows 可雙擊 `start-overlay.cmd`，macOS 可雙擊 `start-overlay.command`。

## 使用

1. 開浮窗程式。視窗出現，顯示「等待網頁同步位置…」。
2. 瀏覽器開 [官方地圖](https://game.skport.com/map/endfield)、登入、按「**同步位置**」。
   頁面右下角會有一行小字「座標中繼：送出中」。
3. 約一秒一筆，浮窗開始更新。

![邊玩邊看座標：浮窗可拖到畫面任何位置](docs/images/demo-ingame.jpg)

| 操作 | 效果 |
|---|---|
| 左鍵拖曳 | 移動視窗 |
| 右下角 ◢ 拖曳 | 改大小，字跟著縮放 |
| Ctrl + 滾輪（macOS：⌘ + 滾輪） | 調字級 |
| 左鍵點一下數字 | 複製 `x y z` 到剪貼簿 |
| 右鍵（macOS：右鍵或 Control + 點） | 選單：複製、座標順序、透明度、字級、重設、語言、結束 |

- 座標預設是**遊戲原始順序**（`x y z`，`y` 是高度）。右鍵可切成 **Blender 順序**（`x z y`，Z 朝上）。
- 超過 5 秒沒有新資料，數字會變灰；網頁斷線時顯示「網頁已離線」。
- 設定（位置、大小、字級、透明度、順序、語言）會自動儲存：
  Windows `%APPDATA%\endfield-pos-overlay\state.json`；macOS `~/Library/Application Support/endfield-pos-overlay/state.json`。

### 命令列參數

```
--port 27600        接收埠（改了的話，腳本也要改：擴充套件選單 →「設定浮窗接收埠」）
--lang auto|zh|en   介面語言
--alpha 0.9         透明度 0.2–1.0
--state-file PATH   設定檔位置
```

## 疑難排解

| 狀況 | 處理 |
|---|---|
| 雙擊 `.user.js` 跳出「Windows Script Host」錯誤（800A0404） | 這個檔案不能雙擊執行。先裝 Tampermonkey（安裝第 1、2 步），再在瀏覽器裡點安裝連結（第 3 步） |
| 浮窗一啟動就跳「無法在 127.0.0.1:27600 開啟接收埠」 | 已經有一個浮窗在跑，或埠被別的程式占用。關掉舊的，或換埠（`--port 27601`，腳本選單也要改） |
| 頁面徽章「連不到 127.0.0.1:27600」 | 浮窗沒開，先開浮窗 |
| 頁面徽章「掛鉤失敗」 | 腳本的 `@sandbox` 被改成 `DOM` 了；在 Tampermonkey 編輯腳本，保持 `@sandbox raw`，然後重新整理頁面 |
| 看不到徽章、浮窗一直等待 | Chrome / Edge 沒打開「允許使用者指令碼」；或腳本沒啟用。開好後重新整理地圖頁 |
| 浮窗一直「等待網頁同步位置…」 | 地圖頁要先登入並按「同步位置」；沒反應就重新整理頁面再按一次 |
| 浮窗在遊戲裡看不到 | 遊戲改成「**無邊框視窗**」模式；獨占全螢幕會蓋掉所有置頂視窗。macOS 的全螢幕 App 也一樣（在另一個桌面空間） |
| 數字變灰 | 超過 5 秒沒新資料：瀏覽器分頁被休眠或斷線。把地圖分頁留在前景或關掉該分頁的省電休眠 |

徽章最後的小字（`inject` / `page` / `sandbox`）是腳本用哪種方式掛上的，回報問題時請一併附上，並註明瀏覽器與擴充套件版本。

## 限制

- 只有地圖分頁開著、而且已按「同步位置」時才有資料。
- 一秒一筆是官方伺服器的推送頻率，浮窗不會更快。
- 官方網站改版可能讓腳本失效；請開 issue。
- macOS 版沒有在實機上完整驗證過，歡迎回報。
- 區域英文名尚未收錄（英文介面先顯示區域代號），歡迎 PR 補上官方英文名。

## 安全

- 浮窗只聽 `127.0.0.1`（外部電腦連不到）。
- 只接受使用者腳本管理器送來的請求；其他網站送的請求一律拒絕（防止別的網頁塞假座標）。
- 腳本不讀、不送你的登入資訊；只轉送位置訊息（type 1011 / 1012 / 1013）。

## 開發

```
python -m unittest                                               # 單元測試（標準函式庫）
uv run --with playwright python tools/test_userscript.py         # 腳本端對端測試（假地圖頁 + 假 WebSocket）
```

打包由 GitHub Actions 處理（`.github/workflows/build.yml`）：推 `v*` tag 就會建 Windows exe 與 macOS app 並發佈 Release。

## 授權

MIT
