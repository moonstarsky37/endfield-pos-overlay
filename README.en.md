# Endfield Position Overlay (endfield-pos-overlay)

[繁體中文](README.md)

Shows your live character position from the official *Arknights: Endfield* web map (`https://game.skport.com/map/endfield`) in a small **always-on-top, draggable, resizable** window. Glance at it while playing; click to copy.

```
Wuling · map02_lv010             online
X        505.21
Y        234.23
Z       1100.93
0.4 s ago                game order  ◢
```

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

### 1. A userscript manager

| Browser | Extension | Extra step |
|---|---|---|
| Chrome | [Tampermonkey](https://chromewebstore.google.com/detail/dhdgffkkebhmkfjojejmpbldmpobfkfo) | Extensions → Tampermonkey → Details → turn on **Allow User Scripts** (older Chrome: turn on *Developer mode*) |
| Edge | [Tampermonkey](https://microsoftedge.microsoft.com/addons/detail/iikmkjmpaadaobahmlepeloendndfphd) | Same: Extensions → Details → *Allow user scripts*, or *Developer mode* |
| Firefox | [Tampermonkey](https://addons.mozilla.org/firefox/addon/tampermonkey/) or [Violentmonkey](https://addons.mozilla.org/firefox/addon/violentmonkey/) | none |

### 2. The userscript

Click **[install endfield-pos-relay.user.js](https://raw.githubusercontent.com/moonstarsky37/endfield-pos-overlay/main/userscript/endfield-pos-relay.user.js)**; the extension shows an install page → *Install*. Updates are picked up automatically.

### 3. The overlay app

From [Releases](../../releases):

- **Windows**: `endfield-pos-overlay-windows.exe`, run it from anywhere. SmartScreen may say "Windows protected your PC" (the exe is not code-signed) → *More info* → *Run anyway*.
- **macOS**: `endfield-pos-overlay-macos.zip`, unzip and move the `.app` to Applications. The first time, **right-click → Open** (the app is not notarized).

Or run from source (standard library only, nothing to install): `python run_overlay.py`, or double-click `start-overlay.cmd` / `start-overlay.command`.

## Use

1. Start the overlay. It shows "Waiting for the map page…".
2. Open the [official map](https://game.skport.com/map/endfield), log in, press **Sync position**. A small badge at the bottom-right of the page says "Position relay: sending".
3. The overlay updates about once a second.

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

| Symptom | Fix |
|---|---|
| "Cannot listen on 127.0.0.1:27600" at start | Another overlay is running or the port is taken. Close it or use `--port 27601` (and set the same port in the userscript menu) |
| Badge: "cannot reach 127.0.0.1:27600" | The overlay app is not running |
| Badge: "hook failed" | The script's `@sandbox` was changed to `DOM`; keep `@sandbox raw` and reload the page |
| No badge, overlay keeps waiting | Chrome / Edge: *Allow User Scripts* is off, or the script is disabled. Fix and reload the map |
| Overlay keeps "Waiting for the map page…" | Log in and press *Sync position*; reload and press again if needed |
| Overlay hidden in game | Use **borderless window** mode; exclusive fullscreen covers every topmost window. macOS fullscreen apps live in their own Space, same effect |
| Numbers grey | No data for 5 s: the tab was put to sleep or disconnected |

The last word on the badge (`inject` / `page` / `sandbox`) tells how the script hooked in; include it, plus browser and extension versions, when reporting a problem.

## Limits

- Data only flows while the map tab is open and *Sync position* is on.
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
