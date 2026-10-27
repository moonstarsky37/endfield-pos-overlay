"""Local HTTP receiver: 127.0.0.1 only, POST /pos and GET /health."""
from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Optional

from .core import State, parse_frame

DEFAULT_PORT = 27600
MAX_BODY_BYTES = 65536

# Userscript managers send the request from their extension background, so the Origin is either
# missing or an extension origin. Some managers forward the page origin instead. Any other web
# origin is refused, so random websites cannot inject fake positions.
ALLOWED_ORIGIN_PREFIXES = ("chrome-extension://", "moz-extension://", "safari-web-extension://")
ALLOWED_ORIGINS = ("https://game.skport.com", "null")


def origin_allowed(origin: Optional[str]) -> bool:
    if origin is None or origin == "":
        return True
    origin = origin.strip().rstrip("/")
    return origin in ALLOWED_ORIGINS or origin.startswith(ALLOWED_ORIGIN_PREFIXES)


class RelayServer(ThreadingHTTPServer):
    """No SO_REUSEADDR: on Windows it would let a second overlay bind the same port silently."""

    allow_reuse_address = False
    daemon_threads = True


def make_handler(state: State, clock: Callable[[], float]) -> type[BaseHTTPRequestHandler]:

    class RelayHandler(BaseHTTPRequestHandler):
        server_version = "endfield-pos-overlay"

        def _reply(self, code: int, body: bytes = b"") -> None:
            self.send_response(code)
            if body:
                self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if body:
                self.wfile.write(body)

        def _origin_ok(self) -> bool:
            if origin_allowed(self.headers.get("Origin")):
                return True
            self._reply(403)
            return False

        def do_POST(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0] != "/pos":
                self._reply(404)
                return
            if not self._origin_ok():
                return
            try:
                length = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                length = -1
            if length < 0 or length > MAX_BODY_BYTES:
                self._reply(413)
                return
            body = self.rfile.read(length) if length else b""
            frame = parse_frame(body)
            if frame is not None:
                state.apply(frame, clock())
            self._reply(204)

        def do_GET(self) -> None:  # noqa: N802
            if self.path.split("?", 1)[0] != "/health":
                self._reply(404)
                return
            if not self._origin_ok():
                return
            snap = state.snapshot()
            age = None if snap.last_pos_at is None else round(max(0.0, clock() - snap.last_pos_at), 3)
            payload = {"ok": True, "last_update_age_s": age, "frames": snap.frames}
            self._reply(200, json.dumps(payload).encode("utf-8"))

        def do_OPTIONS(self) -> None:  # noqa: N802
            # No CORS headers on purpose: browser preflights from web pages fail.
            self._reply(405)

        def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
            return

    return RelayHandler


def start_server(state: State, port: int, host: str = "127.0.0.1") -> RelayServer:
    """Bind and serve on a daemon thread. Raises OSError if the port is taken."""
    server = RelayServer((host, port), make_handler(state, time.monotonic))
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.25},
                              name="relay-http", daemon=True)
    thread.start()
    return server
