"""UI strings (Traditional Chinese / English) and place names."""
from __future__ import annotations

import locale
import os
import sys
from typing import Optional

LANGS = ("zh", "en")

STRINGS: dict[str, dict[str, str]] = {
    "zh": {
        "app_title": "Endfield 座標浮窗",
        "no_position": "尚未收到座標",
        "waiting": "等待網頁同步位置…",
        "online": "線上",
        "offline": "離線",
        "page_offline": "網頁已離線 · {age}",
        "copied": "已複製",
        "order_raw_short": "遊戲順序",
        "order_blender_short": "Blender 順序",
        "menu_copy": "複製座標",
        "menu_order_raw": "遊戲原始順序（x y z，y 是高度）",
        "menu_order_blender": "Blender 順序（x z y，Z 朝上）",
        "menu_alpha": "透明度",
        "menu_font_bigger": "字放大",
        "menu_font_smaller": "字縮小",
        "menu_reset": "重設大小與位置",
        "menu_lang": "語言 / Language",
        "menu_lang_auto": "跟隨系統",
        "menu_quit": "結束",
        "port_busy": "無法在 127.0.0.1:{port} 開啟接收埠（可能已有另一個浮窗在跑）。\n{err}",
        "age_s": "{s:.1f} 秒前",
        "age_m": "{m} 分 {s} 秒前",
    },
    "en": {
        "app_title": "Endfield Position Overlay",
        "no_position": "No position yet",
        "waiting": "Waiting for the map page…",
        "online": "online",
        "offline": "offline",
        "page_offline": "Page offline · {age}",
        "copied": "Copied",
        "order_raw_short": "game order",
        "order_blender_short": "Blender order",
        "menu_copy": "Copy coordinates",
        "menu_order_raw": "Game order (x y z, y = height)",
        "menu_order_blender": "Blender order (x z y, Z up)",
        "menu_alpha": "Opacity",
        "menu_font_bigger": "Larger text",
        "menu_font_smaller": "Smaller text",
        "menu_reset": "Reset size and position",
        "menu_lang": "語言 / Language",
        "menu_lang_auto": "System default",
        "menu_quit": "Quit",
        "port_busy": "Cannot listen on 127.0.0.1:{port} (another overlay may already be running).\n{err}",
        "age_s": "{s:.1f} s ago",
        "age_m": "{m} min {s} s ago",
    },
}

# Map / region names. English region names are left out until someone confirms the official
# in-game English names; unknown entries fall back to the raw id, so new regions never break.
MAP_NAMES: dict[str, dict[str, str]] = {
    "map01": {"zh": "四號谷地", "en": "Valley IV"},
    "map02": {"zh": "武陵", "en": "Wuling"},
}

LEVEL_NAMES: dict[str, dict[str, str]] = {
    "map01_lv001": {"zh": "樞紐區"},
    "map01_lv002": {"zh": "谷地通道"},
    "map01_lv003": {"zh": "阿伯莉採石場"},
    "map01_lv005": {"zh": "源石研究園"},
    "map01_lv006": {"zh": "礦脈源區"},
    "map01_lv007": {"zh": "供能高地"},
    "map02_lv001": {"zh": "景玉谷"},
    "map02_lv002": {"zh": "武陵城"},
    "map02_lv003": {"zh": "清波寨"},
    "map02_lv004": {"zh": "首墩"},
    "map02_lv005": {"zh": "實驗園區"},
    "map02_lv006": {"zh": "藏劍谷"},
    "map02_lv007": {"zh": "應龍關"},
    "map02_lv008": {"zh": "北部禁區"},
    "map02_lv009": {"zh": "雪松林"},
    "map02_lv010": {"zh": "祀的畫"},
}


def resolve_lang(choice: str, system: Optional[str] = None) -> str:
    """'zh' | 'en' | 'auto' -> 'zh' or 'en'."""
    if choice in LANGS:
        return choice
    sys_lang = system if system is not None else system_language()
    return "zh" if sys_lang.lower().startswith("zh") else "en"


def system_language() -> str:
    """Best-effort OS UI language tag like 'zh_TW' or 'en_US'; '' if unknown."""
    if sys.platform == "win32":
        try:
            import ctypes  # noqa: PLC0415

            langid = ctypes.windll.kernel32.GetUserDefaultUILanguage()  # type: ignore[attr-defined]
            return "zh" if (langid & 0x3FF) == 0x04 else "en"
        except Exception:
            pass
    for var in ("LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(var)
        if value:
            return value
    if sys.platform == "darwin":
        try:
            import subprocess  # noqa: PLC0415

            out = subprocess.run(["defaults", "read", "-g", "AppleLanguages"],
                                 capture_output=True, text=True, timeout=2).stdout
            for token in out.replace("(", " ").replace(")", " ").replace(",", " ").split():
                token = token.strip('"')
                if token:
                    return token
        except Exception:
            pass
    try:
        return locale.getlocale()[0] or ""
    except Exception:
        return ""


def strings(lang: str) -> dict[str, str]:
    return STRINGS.get(lang, STRINGS["en"])


def map_name(map_id: str, lang: str) -> str:
    return MAP_NAMES.get(map_id, {}).get(lang) or map_id


def level_name(level_id: str, lang: str) -> str:
    return LEVEL_NAMES.get(level_id, {}).get(lang) or level_id


def place_header(map_id: str, level_id: str, lang: str) -> str:
    parts = [p for p in (map_name(map_id, lang), level_name(level_id, lang)) if p]
    return " · ".join(parts)


def format_age(age_s: float, lang: str) -> str:
    t = strings(lang)
    if age_s < 0:
        age_s = 0.0
    if age_s < 60:
        return t["age_s"].format(s=age_s)
    minutes, seconds = divmod(int(age_s), 60)
    return t["age_m"].format(m=minutes, s=seconds)
