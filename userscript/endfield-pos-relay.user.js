// ==UserScript==
// @name         Endfield Position Relay
// @name:zh-TW   Endfield 座標中繼
// @namespace    endfield-pos-overlay
// @version      0.2.0
// @description  Relays your live position from the official Endfield web map to the local overlay app (127.0.0.1). Read-only.
// @description:zh-TW 把官方 Endfield 網頁地圖收到的角色位置轉送到本機浮窗程式（127.0.0.1）。只讀不寫。
// @license      MIT
// @homepageURL  https://github.com/moonstarsky37/endfield-pos-overlay
// @supportURL   https://github.com/moonstarsky37/endfield-pos-overlay/issues
// @updateURL    https://raw.githubusercontent.com/moonstarsky37/endfield-pos-overlay/main/userscript/endfield-pos-relay.user.js
// @downloadURL  https://raw.githubusercontent.com/moonstarsky37/endfield-pos-overlay/main/userscript/endfield-pos-relay.user.js
// @match        https://game.skport.com/map/*
// @run-at       document-start
// @sandbox      raw
// @grant        GM_xmlhttpRequest
// @grant        GM.xmlHttpRequest
// @grant        GM_getValue
// @grant        GM_setValue
// @grant        GM_registerMenuCommand
// @grant        unsafeWindow
// @connect      127.0.0.1
// @noframes
// ==/UserScript==

/*
  How it works
  ------------
  The map page opens a WebSocket to wss://ws.skport.com/... and, after you press "Sync position", the server
  pushes {"type":1012,"data":{"pos":{x,y,z},"levelId":...,"mapId":...,"isOnline":...}} about once a second.

  1. A small hook runs in the PAGE's JavaScript world and wraps window.WebSocket in a Proxy. Sockets to
     ws.skport.com get extra listeners; frames of type 1011 / 1012 / 1013 are passed on unchanged.
  2. The hook hands each frame to this script with a DOM CustomEvent (strings cross the page / extension
     boundary in Chrome, Edge and Firefox alike).
  3. This script POSTs the frame to http://127.0.0.1:<port>/pos with GM_xmlhttpRequest (not limited by the
     page's CSP or CORS). At most one request is in flight; only the newest pending frame is kept.

  Getting code into the page world differs per userscript manager / browser, so three ways are tried:
    a. inject an inline <script> element (works in Chrome/Edge isolated worlds and Firefox sandboxes);
    b. we are already in the page world (Tampermonkey "raw"/page mode, Violentmonkey page mode): call it directly;
    c. Firefox sandbox where inline scripts are blocked: build the Proxy in the page with cloneInto.
  The badge in the bottom-right corner shows which one worked.

  Guarantees: frames are never modified, blocked or delayed; other sockets are untouched; coordinates are not
  logged to the console; nothing is sent anywhere except 127.0.0.1.
*/
(function () {
  'use strict';

  var VERSION = '0.2.0';
  var DEFAULT_PORT = 27600;
  var WS_HOST = 'ws.skport.com';
  var EVT = 'endfield-pos-relay:frame';
  var FLAG = '__endfieldPosRelayHook';
  var HOOK_ATTR = 'data-endfield-pos-hook';
  var TIMEOUT_MS = 2000;
  var MAX_FRAME_CHARS = 65536;

  // ------------------------------------------------------------------ settings
  function getPort() {
    try {
      if (typeof GM_getValue === 'function') {
        var p = parseInt(GM_getValue('port', DEFAULT_PORT), 10);
        if (p > 0 && p < 65536) return p;
      }
    } catch (_) {}
    return DEFAULT_PORT;
  }
  var PORT = getPort();
  var RELAY_URL = 'http://127.0.0.1:' + PORT + '/pos';

  var ZH = /^zh/i.test((navigator.language || '') + '');
  var TEXT = ZH ? {
    waiting: '座標中繼：等待（按地圖的「同步位置」）',
    sending: '座標中繼：送出中',
    unreachable: '座標中繼：連不到 127.0.0.1:' + PORT + '（浮窗沒開？）',
    nohook: '座標中繼：掛鉤失敗（腳本設定的 @sandbox 請用 raw）',
    setPort: '設定浮窗接收埠',
    promptPort: '浮窗接收埠（預設 ' + DEFAULT_PORT + '）：',
    reload: '已儲存，重新整理頁面後生效。',
  } : {
    waiting: 'Position relay: waiting (press "Sync position" on the map)',
    sending: 'Position relay: sending',
    unreachable: 'Position relay: cannot reach 127.0.0.1:' + PORT + ' (is the overlay running?)',
    nohook: 'Position relay: hook failed (keep the script\'s @sandbox at raw)',
    setPort: 'Set overlay port',
    promptPort: 'Overlay port (default ' + DEFAULT_PORT + '):',
    reload: 'Saved. Reload the page to apply.',
  };

  try {
    if (typeof GM_registerMenuCommand === 'function') {
      GM_registerMenuCommand(TEXT.setPort, function () {
        var v = prompt(TEXT.promptPort, String(PORT));
        if (v === null) return;
        var p = parseInt(v, 10);
        if (p > 0 && p < 65536 && typeof GM_setValue === 'function') {
          GM_setValue('port', p);
          alert(TEXT.reload);
        }
      });
    }
  } catch (_) {}

  // ------------------------------------------------------------------ badge (pointer-events: none)
  var badgeEl = null;
  var badgeState = 'waiting';
  var hookMode = '';
  var badgeIdleTimer = 0;

  function renderBadge() {
    try {
      if (!badgeEl) {
        if (!document.documentElement || !document.body) return;
        badgeEl = document.createElement('div');
        badgeEl.style.cssText = [
          'position:fixed', 'right:6px', 'bottom:6px', 'z-index:2147483647',
          'font:10px/1.4 system-ui,sans-serif', 'background:rgba(0,0,0,.55)',
          'padding:2px 6px', 'border-radius:4px', 'pointer-events:none', 'opacity:.85', 'white-space:nowrap',
        ].join(';');
        document.documentElement.appendChild(badgeEl);
      }
      badgeEl.textContent = (TEXT[badgeState] || TEXT.waiting) + (hookMode ? ' · ' + hookMode : '');
      badgeEl.style.color = badgeState === 'sending' ? '#9be7c4'
        : (badgeState === 'unreachable' || badgeState === 'nohook') ? '#ff9a9a' : '#cfd8e3';
    } catch (_) {}
  }

  function setBadge(state) {
    try {
      badgeState = state;
      if (badgeIdleTimer) { clearTimeout(badgeIdleTimer); badgeIdleTimer = 0; }
      if (state === 'sending') {
        badgeIdleTimer = setTimeout(function () { badgeIdleTimer = 0; setBadge('waiting'); }, 5000);
      }
      renderBadge();
    } catch (_) {}
  }

  // ------------------------------------------------------------------ sender: one in flight, keep newest
  var inflight = false;
  var pending = null;

  function pickGM() {
    if (typeof GM_xmlhttpRequest === 'function') return GM_xmlhttpRequest;
    if (typeof GM === 'object' && GM && typeof GM.xmlHttpRequest === 'function') return GM.xmlHttpRequest;
    return null;
  }

  function pump() {
    if (inflight || pending === null) return;
    var body = pending;
    pending = null;
    inflight = true;
    var settled = false;
    var guard = setTimeout(function () { settle(false); }, TIMEOUT_MS + 500);
    function settle(ok) {
      if (settled) return;
      settled = true;
      clearTimeout(guard);
      inflight = false;
      setBadge(ok ? 'sending' : 'unreachable');
      if (pending !== null) pump();
    }
    try {
      var gm = pickGM();
      if (!gm) { settle(false); return; }
      gm({
        method: 'POST',
        url: RELAY_URL,
        data: body,
        headers: { 'Content-Type': 'application/json' },
        timeout: TIMEOUT_MS,
        onload: function (r) { settle(!!r && r.status >= 200 && r.status < 300); },
        onerror: function () { settle(false); },
        ontimeout: function () { settle(false); },
        onabort: function () { settle(false); },
      });
    } catch (_) {
      settle(false);
    }
  }

  function enqueue(text) {
    try {
      if (typeof text !== 'string' || text.length === 0 || text.length > MAX_FRAME_CHARS) return;
      pending = text;
      pump();
    } catch (_) {}
  }

  // Frames arrive from the page world as CustomEvent details (plain strings).
  window.addEventListener(EVT, function (e) {
    try { enqueue(e && e.detail); } catch (_) {}
  }, false);

  // The hook announces itself with a second event, so detection needs no DOM.
  var hookReady = false;
  window.addEventListener(EVT + ':ready', function () { hookReady = true; }, false);

  // ------------------------------------------------------------------ the page-world hook
  // Must stay self-contained: it is serialised with toString() and run inside the page.
  function pageHook(win, EVT, WS_HOST, FLAG, HOOK_ATTR) {
    if (win[FLAG]) { try { win.dispatchEvent(new win.CustomEvent(EVT + ':ready')); } catch (e) {} return; }
    var Native = win.WebSocket;
    if (typeof Native !== 'function') return;
    var TYPES = { 1011: 1, 1012: 1, 1013: 1 };
    function emit(text) {
      try { win.dispatchEvent(new win.CustomEvent(EVT, { detail: String(text) })); } catch (e) {}
    }
    function onMessage(ev) {
      try {
        var d = ev.data;
        if (typeof d !== 'string' || !d || d.length > 65536 || d.charCodeAt(0) !== 123) return;
        var o = JSON.parse(d);
        if (!o || typeof o.type !== 'number' || !TYPES[o.type]) return;
        emit(d);
      } catch (e) {}
    }
    function onOpen() { emit('{"type":"relay","event":"open"}'); }
    function onClose() { emit('{"type":"relay","event":"close"}'); }
    win.WebSocket = new win.Proxy(Native, {
      construct: function (target, args, newTarget) {
        var ws = Reflect.construct(target, args, newTarget); // native errors still reach the page
        try {
          var url = String(args[0] || ws.url || '');
          if (url.indexOf(WS_HOST) !== -1) {
            ws.addEventListener('message', onMessage);
            ws.addEventListener('open', onOpen);
            ws.addEventListener('close', onClose);
          }
        } catch (e) {}
        return ws;
      },
    });
    win[FLAG] = true;
    try { win.document.documentElement.setAttribute(HOOK_ATTR, '1'); } catch (e) {}
    try { win.dispatchEvent(new win.CustomEvent(EVT + ':ready')); } catch (e) {}
    try {
      win.addEventListener(EVT + ':probe', function () {
        try { win.dispatchEvent(new win.CustomEvent(EVT + ':ready')); } catch (e) {}
      });
    } catch (e) {}
  }

  function hooked() {
    if (hookReady) return true;
    try { return document.documentElement.getAttribute(HOOK_ATTR) === '1'; } catch (_) { return false; }
  }

  var pageWin = (typeof unsafeWindow !== 'undefined' && unsafeWindow) ? unsafeWindow : window;

  // a. inline <script> into the page world
  function tryInject() {
    try {
      var s = document.createElement('script');
      s.textContent = '(' + pageHook.toString() + ')(window,' + JSON.stringify(EVT) + ',' +
        JSON.stringify(WS_HOST) + ',' + JSON.stringify(FLAG) + ',' + JSON.stringify(HOOK_ATTR) + ');';
      // At document-start Chrome may not have created <html> yet; a script appended to the bare
      // document still runs, and removing it right away lets the parser build <html> normally.
      var parent = document.head || document.documentElement || document;
      parent.appendChild(s);
      if (s.parentNode) s.parentNode.removeChild(s);
    } catch (_) {}
    return hooked();
  }

  // A Chromium isolated world (extension content script) exposes chrome.runtime.id; the page world does not.
  // Hooking there would only replace the isolated copy of WebSocket and silently do nothing.
  function inChromiumIsolatedWorld() {
    try { return typeof chrome === 'object' && !!chrome && !!chrome.runtime && !!chrome.runtime.id; } catch (_) { return false; }
  }

  // b. already running in the page world
  function tryDirect() {
    if (pageWin !== window || typeof cloneInto === 'function' || inChromiumIsolatedWorld()) return false;
    try { pageHook(window, EVT, WS_HOST, FLAG, HOOK_ATTR); } catch (_) {}
    return hooked();
  }

  // c. Firefox sandbox: build the Proxy in the page realm, handler cloned in
  function tryFirefoxSandbox() {
    if (pageWin === window || typeof cloneInto !== 'function') return false;
    try {
      if (pageWin[FLAG]) return hooked();
      var Native = pageWin.WebSocket;
      if (typeof Native !== 'function') return false;
      var TYPES = { 1011: 1, 1012: 1, 1013: 1 };
      var onMessage = function (ev) {
        try {
          var d = ev.data;
          if (typeof d !== 'string' || !d || d.length > MAX_FRAME_CHARS || d.charCodeAt(0) !== 123) return;
          var o = JSON.parse(d);
          if (!o || typeof o.type !== 'number' || !TYPES[o.type]) return;
          enqueue(d);
        } catch (_) {}
      };
      var construct = function (target, args) {
        var ws = args.length >= 2 ? new Native(args[0], args[1]) : new Native(args[0]);
        try {
          var url = String(args[0] || '');
          if (url.indexOf(WS_HOST) !== -1) {
            var x = (typeof XPCNativeWrapper === 'function') ? XPCNativeWrapper(ws) : ws;
            x.addEventListener('message', onMessage);
            x.addEventListener('open', function () { enqueue('{"type":"relay","event":"open"}'); });
            x.addEventListener('close', function () { enqueue('{"type":"relay","event":"close"}'); });
          }
        } catch (_) {}
        return ws;
      };
      var handler = cloneInto({ construct: construct }, pageWin, { cloneFunctions: true });
      pageWin.WebSocket = new pageWin.Proxy(Native, handler);
      pageWin[FLAG] = true;
      try { document.documentElement.setAttribute(HOOK_ATTR, '1'); } catch (_) {}
      return true;
    } catch (_) {
      return false;
    }
  }

  // A hook from an earlier run (e.g. a second copy of this script) answers the probe synchronously.
  try { window.dispatchEvent(new CustomEvent(EVT + ':probe')); } catch (_) {}
  if (hooked()) {
    hookMode = 'shared';
  } else if (tryInject()) {
    hookMode = 'inject';
  } else if (tryDirect()) {
    hookMode = 'page';
  } else if (tryFirefoxSandbox()) {
    hookMode = 'sandbox';
  } else {
    badgeState = 'nohook';
    try { console.warn('[endfield-pos-relay ' + VERSION + '] could not hook WebSocket'); } catch (_) {}
  }

  try {
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', renderBadge, { once: true });
    } else {
      renderBadge();
    }
  } catch (_) {}
})();
