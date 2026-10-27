"""OS-specific helpers: state file location, fonts, DPI, virtual screen."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

APP_DIR_NAME = "endfield-pos-overlay"
STATE_FILE_NAME = "state.json"

IS_WIN = sys.platform == "win32"
IS_MAC = sys.platform == "darwin"


def config_dir() -> Path:
    if IS_WIN:
        base = os.environ.get("APPDATA")
        if base:
            return Path(base) / APP_DIR_NAME
        return Path.home() / "AppData" / "Roaming" / APP_DIR_NAME
    if IS_MAC:
        return Path.home() / "Library" / "Application Support" / APP_DIR_NAME
    base = os.environ.get("XDG_CONFIG_HOME")
    return (Path(base) if base else Path.home() / ".config") / APP_DIR_NAME


def default_state_path() -> Path:
    return config_dir() / STATE_FILE_NAME


# Preferred fonts per platform; the first one tk knows wins.
NUMBER_FONTS = {
    "win": ("Consolas", "Cascadia Mono", "Courier New"),
    "mac": ("Menlo", "SF Mono", "Monaco", "Courier"),
    "other": ("DejaVu Sans Mono", "Liberation Mono", "Courier"),
}
UI_FONTS = {
    "win": ("Microsoft JhengHei UI", "Microsoft JhengHei", "Segoe UI"),
    "mac": ("PingFang TC", "Heiti TC", "Helvetica Neue", "Helvetica"),
    "other": ("Noto Sans CJK TC", "Noto Sans", "DejaVu Sans"),
}


def _platform_key() -> str:
    return "win" if IS_WIN else ("mac" if IS_MAC else "other")


def pick_font(available: set[str], candidates: tuple[str, ...]) -> str:
    """First candidate tk knows; otherwise tk's default family name."""
    lowered = {name.lower(): name for name in available}
    for name in candidates:
        if name.lower() in lowered:
            return lowered[name.lower()]
    return "TkDefaultFont"


def fonts(root: Any) -> tuple[str, str]:
    """(number font family, UI font family) for this machine."""
    from tkinter import font as tkfont  # noqa: PLC0415

    try:
        available = set(tkfont.families(root))
    except Exception:
        available = set()
    key = _platform_key()
    num = pick_font(available, NUMBER_FONTS[key])
    ui = pick_font(available, UI_FONTS[key])
    if num == "TkDefaultFont":
        num = "TkFixedFont"
    return num, ui


def enable_dpi_awareness() -> None:
    """Windows: stop the system from bitmap-scaling the window (blurry text)."""
    if not IS_WIN:
        return
    try:
        import ctypes  # noqa: PLC0415

        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # type: ignore[attr-defined]
    except Exception:
        pass


def virtual_screen(root: Any) -> tuple[int, int, int, int]:
    """(x, y, w, h) of all monitors combined; falls back to the main screen."""
    if IS_WIN:
        try:
            import ctypes  # noqa: PLC0415

            user32 = ctypes.windll.user32  # type: ignore[attr-defined]
            sx, sy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
            sw, sh = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
            if sw > 0 and sh > 0:
                return sx, sy, sw, sh
        except Exception:
            pass
    try:
        vw, vh = root.winfo_vrootwidth(), root.winfo_vrootheight()
        vx, vy = root.winfo_vrootx(), root.winfo_vrooty()
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        if vw >= sw and vh >= sh:
            return vx, vy, vw, vh
        return 0, 0, sw, sh
    except Exception:
        return 0, 0, 1920, 1080
