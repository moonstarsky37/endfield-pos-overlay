"""Offline end-to-end test for the userscript (no login, no real skport traffic).

A fake https://game.skport.com/map/test page and a fake wss://ws.skport.com socket are served by Playwright;
the real overlay HTTP receiver runs in-process. Scenarios:

  page-chromium   userscript in the page world (like Tampermonkey "raw" / Violentmonkey page mode)
  page-firefox    same, in Firefox
  page-csp        page world, but the page's CSP blocks inline scripts -> must fall back to calling the hook directly
  ext-isolated    userscript as an MV3 content script in an ISOLATED world (Tampermonkey "@sandbox DOM"):
                  hooking cannot work there (MV3 blocks inline scripts), so the badge must say "hook failed"
                  instead of pretending, and the page must keep working

Run:  uv run --with playwright python tools/test_userscript.py [scenario ...]
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from endfield_pos_overlay.core import State  # noqa: E402
from endfield_pos_overlay.server import start_server  # noqa: E402

USERSCRIPT = (ROOT / "userscript" / "endfield-pos-relay.user.js").read_text(encoding="utf-8")
PAGE_URL = "https://game.skport.com/map/test"

FAKE_PAGE = """<!doctype html><html><head><meta charset="utf-8"><title>fake map</title></head><body>
<script>
  window.__checks = {};
  const ws = new WebSocket('wss://ws.skport.com/ws/v1/game/endfield/map');
  window.__checks.instanceOf = ws instanceof WebSocket;
  window.__checks.openConst = WebSocket.OPEN === 1;
  window.__got = 0;
  ws.addEventListener('message', () => { window.__got++; });
  ws.addEventListener('open', () => ws.send('hello'));
  const other = new WebSocket('wss://other.example/socket');
  other.addEventListener('message', () => {});
</script></body></html>"""


def frame(i: int) -> str:
    return json.dumps({"type": 1012, "msgId": f"m{i}", "data": {
        "pos": {"x": 100.0 + i, "y": 50.0, "z": 200.0}, "levelId": "map01_lv001", "isOnline": True, "mapId": "map01"}})


def gm_shim_page(port: int) -> str:
    # Page world: GM functions are backed by a Playwright binding that POSTs from Python (no CORS involved).
    return f"""
window.GM_getValue = (k, d) => (k === 'port' ? {port} : d);
window.GM_xmlhttpRequest = (o) => {{
  window.__gmPost(o.url, o.data, JSON.stringify(o.headers || {{}}))
    .then(st => o.onload && o.onload({{status: st}}))
    .catch(() => o.onerror && o.onerror());
}};
"""


def python_post(url: str, data: str, headers_json: str) -> int:
    req = urllib.request.Request(url, data=data.encode("utf-8"), method="POST",
                                 headers={**json.loads(headers_json)})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # ignore system proxy
    try:
        with opener.open(req, timeout=3) as resp:
            return resp.status
    except urllib.error.HTTPError as exc:
        return exc.code
    except OSError:
        return 0


def wire_routes(context, sent: list[str], other_seen: list[str], csp: bool = False) -> None:
    if csp:
        body = FAKE_PAGE.replace("<script>", '<script nonce="n0nce">', 1)
        headers = {"Content-Security-Policy": "script-src 'nonce-n0nce'"}
    else:
        body, headers = FAKE_PAGE, {}
    context.route(PAGE_URL, lambda route: route.fulfill(status=200, content_type="text/html", body=body,
                                                         headers=headers))

    def on_ws(ws):
        # Reply only after the page says hello, so the page's listeners are attached.
        if "ws.skport.com" in ws.url:
            def on_msg(_message):
                ws.send(json.dumps({"type": 1011, "data": {}}))
                for i in range(5):
                    ws.send(json.dumps({"type": 3, "data": {"heartbeat": i}}))  # must be ignored
                    ws.send(frame(i))
                    sent.append(frame(i))
            ws.on_message(on_msg)
        else:
            other_seen.append(ws.url)

    context.route_web_socket(re.compile(r"^wss://"), on_ws)


def wait_for(page, state: State, n: int, timeout: float = 8.0) -> bool:
    # Never time.sleep here: the sync Playwright API only dispatches events while we call into it.
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if state.snapshot().frames >= n:
            return True
        page.wait_for_timeout(100)
    return False


def check(name: str, page, state: State, modes: tuple[str, ...]) -> bool:
    ok = wait_for(page, state, 2)  # init + at least one position (newest-only queue may coalesce the rest)
    page.wait_for_timeout(1000)
    snap = state.snapshot()
    checks = page.evaluate("window.__checks")
    got = page.evaluate("window.__got")
    badge = page.evaluate("[...document.querySelectorAll('div')].map(d => d.textContent).find(t => t && t.includes('relay')) || ''")
    mode = badge.rsplit("· ", 1)[-1] if "· " in badge else ""
    last_x = snap.pos.x if snap.pos else None
    result = (ok and snap.pos is not None and last_x == 104.0 and snap.pos.level_id == "map01_lv001"
              and checks.get("instanceOf") and checks.get("openConst") and got >= 11 and mode in modes
              and "sending" in badge)
    print(f"[{'PASS' if result else 'FAIL'}] {name}: frames={snap.frames} last_x={last_x} page_got={got} "
          f"checks={checks} mode={mode} badge={badge!r}")
    return bool(result)


def run_page(browser_type, name: str, csp: bool = False) -> bool:
    state = State()
    server = start_server(state, 0)
    port = server.server_address[1]
    try:
        browser = browser_type.launch()
        context = browser.new_context(locale="en-US")
        sent: list[str] = []
        other: list[str] = []
        wire_routes(context, sent, other, csp)
        context.expose_function("__gmPost", python_post)
        context.add_init_script(gm_shim_page(port) + "\n" + USERSCRIPT)
        page = context.new_page()
        page.goto(PAGE_URL)
        result = check(name, page, state, ("page",) if csp else ("inject",))
        browser.close()
        return result
    finally:
        server.shutdown()
        server.server_close()


EXT_BACKGROUND = """
chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  fetch(msg.url, {method: 'POST', body: msg.data, headers: msg.headers || {}})
    .then(r => reply({status: r.status})).catch(() => reply({status: 0}));
  return true;
});
"""


def ext_shim(port: int) -> str:
    return f"""
var GM_getValue = function (k, d) {{ return k === 'port' ? {port} : d; }};
var GM_xmlhttpRequest = function (o) {{
  chrome.runtime.sendMessage({{url: o.url, data: o.data, headers: o.headers}}, function (r) {{
    if (r && r.status) {{ o.onload && o.onload({{status: r.status}}); }} else {{ o.onerror && o.onerror(); }}
  }});
}};
"""


def run_ext_chromium(pw) -> bool:
    state = State()
    server = start_server(state, 0)
    port = server.server_address[1]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            ext = Path(tmp) / "ext"
            ext.mkdir()
            (ext / "manifest.json").write_text(json.dumps({
                "manifest_version": 3, "name": "relay-test", "version": "1",
                "background": {"service_worker": "bg.js"},
                "host_permissions": ["http://127.0.0.1/*"],
                "content_scripts": [{"matches": ["https://game.skport.com/map/*"], "js": ["cs.js"],
                                     "run_at": "document_start", "world": "ISOLATED"}],
            }), encoding="utf-8")
            (ext / "bg.js").write_text(EXT_BACKGROUND, encoding="utf-8")
            (ext / "cs.js").write_text(ext_shim(port) + "\n" + USERSCRIPT, encoding="utf-8")
            context = pw.chromium.launch_persistent_context(
                str(Path(tmp) / "profile"), headless=True, channel="chromium", locale="en-US",
                args=[f"--disable-extensions-except={ext}", f"--load-extension={ext}"])
            sent: list[str] = []
            other: list[str] = []
            wire_routes(context, sent, other)
            page = context.new_page()
            page.wait_for_timeout(1000)  # let the service worker start
            page.goto(PAGE_URL)
            page.wait_for_timeout(2000)
            got = page.evaluate("window.__got")
            checks = page.evaluate("window.__checks")
            badge = page.evaluate("[...document.querySelectorAll('div')].map(d => d.textContent).find(t => t && t.includes('relay')) || ''")
            result = "hook failed" in badge and got >= 11 and checks.get("instanceOf") and state.snapshot().frames == 0
            print(f"[{'PASS' if result else 'FAIL'}] ext-isolated: page_got={got} checks={checks} badge={badge!r}")
            context.close()
            return result
    finally:
        server.shutdown()
        server.server_close()


def main(argv: list[str]) -> int:
    from playwright.sync_api import sync_playwright  # noqa: PLC0415

    wanted = argv or ["page-chromium", "page-firefox", "page-csp", "ext-isolated"]
    results = []
    with sync_playwright() as pw:
        for name in wanted:
            try:
                if name == "page-chromium":
                    results.append(run_page(pw.chromium, name))
                elif name == "page-firefox":
                    results.append(run_page(pw.firefox, name))
                elif name == "page-csp":
                    results.append(run_page(pw.chromium, name, csp=True))
                elif name == "ext-isolated":
                    results.append(run_ext_chromium(pw))
                else:
                    print(f"unknown scenario {name}")
                    results.append(False)
            except Exception as exc:  # noqa: BLE001
                print(f"[FAIL] {name}: {type(exc).__name__}: {exc}")
                results.append(False)
    print(f"{sum(results)}/{len(results)} scenarios passed")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
