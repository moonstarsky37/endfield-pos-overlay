# Endfield Position Overlay (endfield-pos-overlay)

[繁體中文](README.md)

Shows your live character position from the official *Arknights: Endfield* web map (`https://game.skport.com/map/endfield`) in a small **always-on-top, draggable, resizable** window. Glance at it while playing; click to copy.

![The overlay in the top-right corner of the game](docs/images/demo-vista.jpg)

> Unofficial tool, not affiliated with GRYPHLINE / Hypergryph. Read-only: it never modifies, blocks or sends any game or website data. Positions only go to `127.0.0.1` on your own computer.

## How it works

```
Official map page (your browser, logged in, "Sync position" pressed)
   │  a userscript copies the position messages the page already receives (about 1/s)
   ▼
http://127.0.0.1:27600/pos   ← local receiver opened by the overlay app
   ▼
always-on-top window
```

| Part | What it is |
|---|---|
| `userscript/endfield-pos-relay.user.js` | Userscript for Tampermonkey / Violentmonkey; works in Chrome, Edge and Firefox |
| Overlay app | Windows: `endfield-pos-overlay.exe`; macOS: `.app`; or run the source with Python 3.10+ |

## Install

Three steps: Tampermonkey → the userscript → the overlay app. Each step ends with a **Check** line; doing it saves most of the troubleshooting later.

### 1. A userscript manager

| Browser | Extension | Extra step |
|---|---|---|
| Chrome | [Tampermonkey](https://chromewebstore.google.com/detail/dhdgffkkebhmkfjojejmpbldmpobfkfo) | Paste `chrome://extensions/?id=dhdgffkkebhmkfjojejmpbldmpobfkfo` into the address bar (that is Tampermonkey's *Details* page) → scroll to **Allow User Scripts** and turn it on. Older Chrome has no such switch: open `chrome://extensions` and turn on *Developer mode* at the top right instead |
| Edge | [Tampermonkey](https://microsoftedge.microsoft.com/addons/detail/iikmkjmpaadaobahmlepeloendndfphd) | Same: paste `edge://extensions/?id=iikmkjmpaadaobahmlepeloendndfphd` → turn on *Allow user scripts*, or *Developer mode* |
| Firefox | [Tampermonkey](https://addons.mozilla.org/firefox/addon/tampermonkey/) or [Violentmonkey](https://addons.mozilla.org/firefox/addon/violentmonkey/) | none |

Cannot find that page: right-click the Tampermonkey icon at the top right of the browser → *Manage extension*; it is the same page. Tampermonkey's FAQ has a screenshot of every step: [Permission to execute userscripts](https://www.tampermonkey.net/faq.php?q=Q209).

**Check**: on Tampermonkey's *Details* page, *Allow User Scripts* is on. If it is off, the script installs fine but never runs, and nothing reports an error. The *Service worker* / *Inspect views* links on that page are for developers and have nothing to do with this tool.

### 2. The userscript

In the browser, click **[install endfield-pos-relay.user.js](https://raw.githubusercontent.com/moonstarsky37/endfield-pos-overlay/main/userscript/endfield-pos-relay.user.js)**; Tampermonkey shows an install page → *Install*. Updates are picked up automatically.

- A page titled **Reinstall** means it is already installed. Compare *Installed version* with the link's version: older → *Reinstall*, same → *Cancel*.
- If the link only downloads a file and no install page appears, step 1 is incomplete (Tampermonkey missing, or *Allow User Scripts* off).
- Do **not** download the `.user.js` and double-click it: it is not a program, and Windows shows a "Windows Script Host" error dialog.
- Offline install: drag the `.user.js` file into the browser window, or paste its contents into Tampermonkey's *Create a new script*.

**Check**: click the Tampermonkey icon at the top right of the browser; the list contains "Endfield Position Relay" and its switch is on.

### 3. The overlay app

From [Releases](../../releases):

- **Windows**: `endfield-pos-overlay-windows.exe`, run it from anywhere. SmartScreen may say "Windows protected your PC" (the exe is not code-signed) → *More info* → *Run anyway*.
- **macOS**: `endfield-pos-overlay-macos.zip`, unzip and move the `.app` to Applications. The first time, **right-click → Open** (the app is not notarized).

Or run from source (standard library only, nothing to install): `python run_overlay.py`, or double-click `start-overlay.cmd` / `start-overlay.command`.

**Check**: a small black window appears saying "Waiting for the map page…".

## Use

1. Start the overlay.
2. Open the [official map](https://game.skport.com/map/endfield), log in, switch **Sync position** to ON.
   Locale URLs (`/zh-tw/map/…`, `/en/map/…`) work too.
3. Look at three places; when all three match, it works:

| Where | What success looks like |
|---|---|
| Bottom-right of the map page | a small line "Position relay: sending" |
| Tampermonkey icon | shows the number 1 (one script running on this page) |
| Overlay | updates about once a second |

![In-game use: drag the overlay anywhere on screen](docs/images/demo-ingame.jpg)

| Action | Effect |
|---|---|
| Left-drag | move |
| Drag the ◢ corner | resize (text scales) |
| Ctrl + wheel (macOS: ⌘ + wheel) | text size |
| Click the numbers | copy `x y z` |
| Right-click (macOS: right-click or Control-click) | menu: copy, coordinate order, opacity, text size, reset, language, quit |

- Default order is the **game's own** (`x y z`, `y` is height). The menu can switch to **Blender order** (`x z y`, Z up).
- Numbers turn grey after 5 s without data; "Page offline" when the page disconnects.
- Settings are saved to `%APPDATA%\endfield-pos-overlay\state.json` (Windows) or `~/Library/Application Support/endfield-pos-overlay/state.json` (macOS).

Options: `--port 27600` (if you change it, also change it in the userscript menu → *Set overlay port*), `--lang auto|zh|en`, `--alpha 0.9`, `--state-file PATH`.

## Troubleshooting

Three places tell you which part is stuck:

| Where | Normal | Otherwise |
|---|---|---|
| Small line at the bottom-right of the map page | "Position relay: sending" | **No line at all**: the script is not running on this page → redo the *Check* of install steps 1 and 2; the script must be 0.2.1 or newer (older versions ignored locale URLs; click the install link again to update). **"cannot reach 127.0.0.1:27600"**: the overlay is not running. **"waiting"**: *Sync position* is not ON |
| Open `http://127.0.0.1:27600/health` in the browser | something like `{"ok": true, "last_update_age_s": 0.3, "frames": 123}` with `frames` above 0 | **Does not open**: the overlay is not running. **`frames` is 0**: the script never sent anything; same as "no line at all" above |
| Overlay | numbers update every second | stuck on "Waiting for the map page…": see the two rows above |

If you know your way around F12: on the map page press F12 → Network → WS → click `map` → Messages. Messages with `"type":1012` arriving every second mean the site is sending positions and the problem is in the script or the overlay; none means *Sync position* did not take effect, toggle it off and on.

| Symptom | Fix |
|---|---|
| Double-clicking `.user.js` shows a "Windows Script Host" error | The file is not meant to be run. Install Tampermonkey (step 1), then open the install link in the browser (step 2) |
| "Cannot listen on 127.0.0.1:27600" at start | Another overlay is running or the port is taken. Close it or use `--port 27601` (and set the same port in the userscript menu) |
| Line says "hook failed" | The script's `@sandbox` was changed to `DOM`; keep `@sandbox raw` and reload the page |
| Overlay hidden in game | Use **borderless window** mode; exclusive fullscreen covers every topmost window. macOS fullscreen apps live in their own Space, same effect |
| Numbers grey | No data for 5 s: the tab was put to sleep or disconnected |

The last word on the line (`inject` / `page` / `sandbox`) tells how the script hooked in. When reporting a problem include that line, the `/health` output, and the browser and Tampermonkey versions.

## Limits

- Data only flows while the map tab is open and *Sync position* is ON.
- One update per second is the official server's rate.
- A redesign of the official site may break the script; please open an issue.
- The macOS build has not been fully tested on real hardware.
- English region names are not included yet (the region id is shown); PRs with the official English names are welcome.

## Security

- The overlay listens on `127.0.0.1` only.
- It only accepts requests from userscript managers; requests from other websites are refused, so no web page can inject fake positions.
- The userscript never reads or forwards your login; it only relays position messages (types 1011 / 1012 / 1013).

## Development

```
python -m unittest
uv run --with playwright python tools/test_userscript.py   # fake map page + fake WebSocket, Chromium & Firefox
```

GitHub Actions (`.github/workflows/build.yml`) builds the Windows exe and macOS app and publishes a Release on every `v*` tag.

## License

MIT
