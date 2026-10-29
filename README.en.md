# Endfield Position Overlay (endfield-pos-overlay)

[繁體中文](README.md)

Shows the character position that the official *Arknights: Endfield* web map (`https://game.skport.com/map/endfield`) syncs, in a small always-on-top, draggable, resizable window. Click the numbers to copy them. Purpose: compare the in-game position with map or 3D scene data without switching windows.

![The overlay in the top-right corner of the game](docs/images/demo-vista.jpg)

> Unofficial tool, not affiliated with GRYPHLINE / Hypergryph. Read-only: it does not modify, block or send any game or website data. Positions go only to `127.0.0.1` on the same computer.

## How it works

```
Official map page (browser, logged in, "Sync position" ON)
   │  a userscript copies the position messages the page already receives (about 1/s)
   ▼
http://127.0.0.1:27600/pos   ← local receiver opened by the overlay app
   ▼
always-on-top window
```

| Part | What it is |
|---|---|
| `userscript/endfield-pos-relay.user.js` | Userscript for Tampermonkey / Violentmonkey; Chrome, Edge and Firefox |
| Overlay app | Windows: `endfield-pos-overlay.exe`; macOS: `.app`; or the source with Python 3.10+ |

## Install

Three steps: Tampermonkey → the userscript → the overlay app. Each step ends with a **Check** line.

### 1. Userscript manager

| Browser | Extension | Extra setting |
|---|---|---|
| Chrome | [Tampermonkey](https://chromewebstore.google.com/detail/dhdgffkkebhmkfjojejmpbldmpobfkfo) | Paste `chrome://extensions/?id=dhdgffkkebhmkfjojejmpbldmpobfkfo` into the address bar (Tampermonkey's *Details* page) and turn on **Allow User Scripts**. Older Chrome without that switch: turn on *Developer mode* at the top right of `chrome://extensions` |
| Edge | [Tampermonkey](https://microsoftedge.microsoft.com/addons/detail/iikmkjmpaadaobahmlepeloendndfphd) | Paste `edge://extensions/?id=iikmkjmpaadaobahmlepeloendndfphd` and turn on *Allow user scripts*, or *Developer mode* |
| Firefox | [Tampermonkey](https://addons.mozilla.org/firefox/addon/tampermonkey/) or [Violentmonkey](https://addons.mozilla.org/firefox/addon/violentmonkey/) | none |

The same page opens from a right-click on the Tampermonkey icon → *Manage extension*. Screenshots of each step: Tampermonkey FAQ, [Permission to execute userscripts](https://www.tampermonkey.net/faq.php?q=Q209).

**Check**: *Allow User Scripts* on Tampermonkey's *Details* page is on. When it is off, the script installs but does not run, and no error is shown. The *Service worker* / *Inspect views* links on the same page are unrelated to this tool.

### 2. Userscript

Open the **[install link](https://raw.githubusercontent.com/moonstarsky37/endfield-pos-overlay/main/userscript/endfield-pos-relay.user.js)** in the browser; Tampermonkey shows an install page, press *Install*. Later updates are applied by Tampermonkey.

- A page titled *Reinstall* means the script is already installed. *Installed version* older than the link's version: *Reinstall*; same version: *Cancel*.
- The link only downloads a file and no install page appears: step 1 is incomplete (Tampermonkey not installed, or *Allow User Scripts* off).
- `.user.js` is not an executable. Double-clicking it on Windows shows a "Windows Script Host" error dialog.
- Offline install: drag the `.user.js` file into the browser window, or paste its contents into Tampermonkey's *Create a new script*.

**Check**: the script list under the Tampermonkey icon contains "Endfield Position Relay" with its switch on.

### 3. Overlay app

From [Releases](../../releases):

- Windows: `endfield-pos-overlay-windows.exe`, a single file, double-click to run. The exe is not code-signed; SmartScreen may show "Windows protected your PC": *More info* → *Run anyway*.
- macOS: `endfield-pos-overlay-macos.zip`, unzip and move the `.app` to Applications. The app is not notarized; open it the first time with right-click → *Open*.

Or run from source (Python 3.10+, standard library only): `python run_overlay.py`, or `start-overlay.cmd` / `start-overlay.command`.

**Check**: a small black window appears with "Waiting for the map page…".

## Use

1. Start the overlay.
2. Open the [official map](https://game.skport.com/map/endfield), log in, switch *Sync position* to ON. Locale URLs (`/zh-tw/map/…`, `/en/map/…`) work the same.
3. All three of the following at once means it works:

| Where | State |
|---|---|
| Bottom-right of the map page | a small line "Position relay: sending" |
| Tampermonkey icon | the number 1 (one script running on this page) |
| Overlay | updates about once a second |

![In-game use: drag the overlay anywhere on screen](docs/images/demo-ingame.jpg)

| Action | Effect |
|---|---|
| Left-drag | move |
| Drag the ◢ corner | resize; text scales with it |
| Ctrl + wheel (macOS: ⌘ + wheel) | text size |
| Click the numbers | copy `x, y, z` (e.g. `-314.00, 323.00, 400.00`) |
| Right-click (macOS: right-click or Control-click) | menu: copy, coordinate order, opacity, text size, reset, language, quit |

- Default order is the game's own (`x y z`, `y` is height). The menu switches to Blender order (`x z y`, Z up).
- Numbers turn grey after 5 s without data; "Page offline" is shown when the page disconnects.
- Settings are saved to `%APPDATA%\endfield-pos-overlay\state.json` (Windows) or `~/Library/Application Support/endfield-pos-overlay/state.json` (macOS).

Options: `--port 27600` (when changed, set the same value in the userscript menu → *Set overlay port*), `--lang auto|zh|en`, `--alpha 0.9`, `--state-file PATH`.

## Troubleshooting

Open `http://127.0.0.1:27600/health` in the browser. A normal response looks like `{"ok": true, "last_update_age_s": 0.3, "frames": 123}`; `frames` is the number of messages the overlay has received.

| Symptom | Cause | Fix |
|---|---|---|
| No small line at the bottom-right of the map page | the script is not running on this page | redo the *Check* of install steps 1 and 2. The script must be 0.2.1 or newer (older versions did not match locale URLs); open the install link again to update |
| Line says "cannot reach 127.0.0.1:27600" | the overlay is not running | start the overlay |
| Line says "waiting" | *Sync position* is not ON | switch it ON |
| `/health` does not open | the overlay is not running | start the overlay |
| `frames` in `/health` is 0 | the script has not sent anything | same as "no small line" |
| Overlay stays on "Waiting for the map page…" | any of the above | check the rows above |
| Double-clicking `.user.js` shows a "Windows Script Host" error | the file is not an executable | install Tampermonkey (step 1), then open the install link in the browser (step 2) |
| "Cannot listen on 127.0.0.1:27600" at start | another overlay is running or the port is taken | close the other overlay, or use `--port 27601` and set the same port in the userscript menu |
| Line says "hook failed" | the script's `@sandbox` was changed to `DOM` | edit the script in Tampermonkey, keep `@sandbox raw`, reload the page |
| Overlay not visible in game | exclusive fullscreen covers every topmost window | use borderless window mode. macOS fullscreen apps live in their own Space, same effect |
| Numbers grey | no data for 5 s; the tab was put to sleep or disconnected | keep the map tab in the foreground, or disable tab sleeping for it |

Server-side check: on the map page press F12 → Network → WS → `map` → Messages. Messages with `"type":1012` every second mean the site is sending positions and the problem is in the script or the overlay; none means *Sync position* did not take effect, toggle it off and on.

The last word on the line (`inject` / `page` / `sandbox`) is how the script hooked in. Include that line, the `/health` response, and the browser and Tampermonkey versions when reporting a problem.

## Limits

- Data only flows while the map tab is open and *Sync position* is ON.
- One update per second is the official server's rate.
- A redesign of the official site may break the script.
- The macOS build has not been fully tested on real hardware.
- English region names are not included; the English UI shows the region id.

## Security

- The overlay listens on `127.0.0.1` only; other computers cannot connect.
- It only accepts requests from userscript managers; requests from other websites get 403, so no web page can inject fake positions.
- The userscript does not read or forward login data; it only relays position messages (types 1011 / 1012 / 1013).

## Development

```
python -m unittest
uv run --with playwright python tools/test_userscript.py   # fake map page + fake WebSocket, Chromium & Firefox
```

GitHub Actions (`.github/workflows/build.yml`) builds the Windows exe and macOS app and publishes a Release on every `v*` tag.

## License

MIT
