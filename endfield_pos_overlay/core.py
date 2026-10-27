"""Pure logic: frame parsing, shared state, view composition, preferences, geometry.

Nothing in this module touches tkinter or the network, so it is fully unit-testable.
"""
from __future__ import annotations

import json
import math
import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from . import i18n

STALE_AFTER_S = 5.0          # no new position for this long -> numbers turn grey

DEFAULT_GEOMETRY = "340x150+120+120"
DEFAULT_FONT_SIZE = 20
DEFAULT_ALPHA = 0.9
MIN_W, MIN_H = 180, 80
FONT_MIN, FONT_MAX = 8, 120
HEIGHT_PAD = 16              # window height ~= HEIGHT_PER_PT_PX * font pt * px-per-pt + HEIGHT_PAD
HEIGHT_PER_PT_PX = 4.8       # three big rows + two small rows + spacing, in "pixels of one pt"
PX_PER_PT_96 = 96 / 72       # tk scaling at 96 DPI (larger on high-DPI screens; asked from tk at start)

ORDERS = ("raw", "blender")
LANG_CHOICES = ("auto", "zh", "en")

SAMPLE_FRAME = (
    '{"type":1012,"data":{"pos":{"x":505.20776,"y":234.22778,"z":1100.9303},'
    '"levelId":"map02_lv010","isOnline":true,"mapId":"map02"},"msgId":"kWcXldjf"}'
)


# ============================================================================ frames
@dataclass(frozen=True)
class Position:
    """Raw game position (Unity convention: y is height) and where it is."""

    x: float
    y: float
    z: float
    map_id: str
    level_id: str
    is_online: bool


@dataclass(frozen=True)
class Frame:
    """An accepted frame. kind: pos (1012) / init (1011) / off (1013) / relay (open|close)."""

    kind: str
    pos: Optional[Position] = None
    event: str = ""


def parse_frame(text: str | bytes) -> Optional[Frame]:
    """Parse what the userscript relayed. Returns None for anything we do not want; never raises."""
    try:
        if isinstance(text, bytes):
            text = text.decode("utf-8")
        obj = json.loads(text)
    except (UnicodeDecodeError, ValueError):
        return None
    if not isinstance(obj, dict):
        return None
    kind = obj.get("type")
    if kind == "relay":
        event = obj.get("event")
        return Frame("relay", event=event) if event in ("open", "close") else None
    if isinstance(kind, bool) or not isinstance(kind, int):
        return None
    if kind == 1011:
        return Frame("init")
    if kind == 1013:
        return Frame("off")
    if kind != 1012:
        return None
    data = obj.get("data")
    if not isinstance(data, dict):
        return None
    pos = data.get("pos")
    if not isinstance(pos, dict):
        return None
    try:
        x, y, z = float(pos["x"]), float(pos["y"]), float(pos["z"])
    except (KeyError, TypeError, ValueError):
        return None
    if not all(math.isfinite(v) for v in (x, y, z)):
        return None
    return Frame(
        "pos",
        pos=Position(
            x=x, y=y, z=z,
            map_id=str(data.get("mapId") or ""),
            level_id=str(data.get("levelId") or ""),
            is_online=bool(data.get("isOnline", True)),
        ),
    )


def to_blender(x: float, y: float, z: float) -> tuple[float, float, float]:
    """Game (x, y=height, z) -> Blender Z-up (x, y, z) = (pos.x, pos.z, pos.y)."""
    return (x, z, y)


def ordered_triple(pos: Position, order: str) -> tuple[float, float, float]:
    """The three numbers in display order ("raw" = game order, "blender" = x z y)."""
    return to_blender(pos.x, pos.y, pos.z) if order == "blender" else (pos.x, pos.y, pos.z)


def format_coords(triple: tuple[float, float, float]) -> str:
    """Clipboard format: space separated, two decimals."""
    return " ".join(f"{v:.2f}" for v in triple)


# ============================================================================ shared state
@dataclass(frozen=True)
class Snapshot:
    """Read-only copy of State for the UI thread."""

    pos: Optional[Position]
    last_pos_at: Optional[float]
    frames: int
    relay_open: Optional[bool]
    sync_on: bool


@dataclass
class State:
    """Written by the HTTP thread, read by the UI thread; every field is only touched under lock."""

    lock: threading.Lock = field(default_factory=threading.Lock)
    pos: Optional[Position] = None
    last_pos_at: Optional[float] = None
    frames: int = 0
    relay_open: Optional[bool] = None   # None = unknown yet
    sync_on: bool = True                # False after 1013 (POS_OFF)

    def apply(self, frame: Frame, now: float) -> None:
        with self.lock:
            self.frames += 1
            if frame.kind == "pos" and frame.pos is not None:
                self.pos = frame.pos
                self.last_pos_at = now
                self.relay_open = True
                self.sync_on = True
            elif frame.kind == "off":
                self.sync_on = False
            elif frame.kind == "init":
                self.sync_on = True
            elif frame.kind == "relay":
                self.relay_open = frame.event == "open"

    def snapshot(self) -> Snapshot:
        with self.lock:
            return Snapshot(self.pos, self.last_pos_at, self.frames, self.relay_open, self.sync_on)


@dataclass(frozen=True)
class View:
    """Strings to show; plain data so it can be tested without a window."""

    header: str
    online_text: str
    online: bool
    values: tuple[str, str, str]
    status: str
    stale: bool
    has_pos: bool


def compose_view(snap: Snapshot, now: float, order: str, lang: str) -> View:
    """Turn a snapshot into UI text (no tk)."""
    t = i18n.strings(lang)
    if snap.pos is None or snap.last_pos_at is None:
        return View(t["no_position"], "", False, ("--.--", "--.--", "--.--"), t["waiting"], True, False)
    pos = snap.pos
    age = max(0.0, now - snap.last_pos_at)
    offline = (snap.relay_open is False) or (not snap.sync_on) or (not pos.is_online)
    header = i18n.place_header(pos.map_id, pos.level_id, lang)
    values = tuple(f"{v:.2f}" for v in ordered_triple(pos, order))
    age_text = i18n.format_age(age, lang)
    if offline:
        return View(header, t["offline"], False, values, t["page_offline"].format(age=age_text), True, True)  # type: ignore[arg-type]
    return View(header, t["online"], True, values, age_text, age > STALE_AFTER_S, True)  # type: ignore[arg-type]


# ============================================================================ preferences
@dataclass
class Prefs:
    """What goes into the state file."""

    geometry: str = DEFAULT_GEOMETRY
    font_size: int = DEFAULT_FONT_SIZE
    alpha: float = DEFAULT_ALPHA
    order: str = "raw"
    lang: str = "auto"

    def to_dict(self) -> dict[str, Any]:
        return {
            "geometry": self.geometry, "font_size": self.font_size, "alpha": self.alpha,
            "order": self.order, "lang": self.lang,
        }


GEOMETRY_RE = re.compile(r"^(\d+)x(\d+)([+-]\d+)([+-]\d+)$")


def parse_geometry(text: Any) -> Optional[tuple[int, int, int, int]]:
    """'WxH+X+Y' -> (w, h, x, y); None if malformed."""
    m = GEOMETRY_RE.match(text.strip()) if isinstance(text, str) else None
    if not m:
        return None
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))


def clamp_geometry(w: int, h: int, x: int, y: int, screen: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    """Keep the window inside the virtual screen (sx, sy, sw, sh) and above the minimum size."""
    sx, sy, sw, sh = screen
    w = max(MIN_W, min(w, max(MIN_W, sw)))
    h = max(MIN_H, min(h, max(MIN_H, sh)))
    x = max(sx, min(x, sx + sw - w))
    y = max(sy, min(y, sy + sh - h))
    return w, h, x, y


def prefs_from_dict(raw: Any) -> Prefs:
    """Tolerate missing fields, wrong types and out-of-range values: each falls back to default."""
    prefs = Prefs()
    if not isinstance(raw, dict):
        return prefs
    geometry = raw.get("geometry")
    if isinstance(geometry, str) and parse_geometry(geometry):
        prefs.geometry = geometry
    size = raw.get("font_size")
    if isinstance(size, int) and not isinstance(size, bool) and FONT_MIN <= size <= FONT_MAX:
        prefs.font_size = size
    alpha = raw.get("alpha")
    if isinstance(alpha, (int, float)) and not isinstance(alpha, bool) and 0.2 <= float(alpha) <= 1.0:
        prefs.alpha = float(alpha)
    order = raw.get("order")
    if order in ORDERS:
        prefs.order = order
    lang = raw.get("lang")
    if lang in LANG_CHOICES:
        prefs.lang = lang
    return prefs


def load_prefs(path: Path) -> Prefs:
    try:
        return prefs_from_dict(json.loads(path.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return Prefs()


def save_prefs(path: Path, prefs: Prefs) -> Optional[str]:
    """Write the state file. Returns an error message instead of raising."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(prefs.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        return None
    except OSError as exc:
        return f"cannot write {path}: {exc}"


def font_size_for_height(height: int, px_per_pt: float = PX_PER_PT_96) -> int:
    """Window height -> font size (used while dragging the resize grip)."""
    return max(FONT_MIN, min(FONT_MAX, round((height - HEIGHT_PAD) / (HEIGHT_PER_PT_PX * px_per_pt))))


def height_for_font_size(size: int, px_per_pt: float = PX_PER_PT_96) -> int:
    """Font size -> window height (used by Ctrl/Cmd + wheel and the menu)."""
    return max(MIN_H, round(size * HEIGHT_PER_PT_PX * px_per_pt + HEIGHT_PAD))


def default_geometry(px_per_pt: float = PX_PER_PT_96) -> tuple[int, int, int, int]:
    """First-run / reset geometry, scaled by DPI so text is not clipped on high-DPI screens."""
    parsed = parse_geometry(DEFAULT_GEOMETRY)
    assert parsed is not None
    w, _h, x, y = parsed
    scale = max(0.5, px_per_pt / PX_PER_PT_96)
    return round(w * scale), height_for_font_size(DEFAULT_FONT_SIZE, px_per_pt), x, y
