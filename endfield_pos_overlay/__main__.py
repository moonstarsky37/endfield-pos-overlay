"""Entry point: python -m endfield_pos_overlay"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from . import __version__, i18n, osutil
from .core import load_prefs
from .server import DEFAULT_PORT, start_server


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="endfield-pos-overlay",
        description="Always-on-top overlay for the live position relayed from the official Endfield web map.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"receiver port (default {DEFAULT_PORT})")
    parser.add_argument("--lang", choices=("auto", "zh", "en"), default=None, help="UI language (overrides saved choice)")
    parser.add_argument("--alpha", type=float, default=None, help="window opacity 0.2-1.0 (overrides saved choice)")
    parser.add_argument("--state-file", type=Path, default=None,
                        help=f"where window size/position are saved (default {osutil.default_state_path()})")
    parser.add_argument("--exit-after", type=float, default=None, metavar="SECONDS", help="quit after N seconds (smoke tests)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_arg_parser().parse_args(argv)

    prefs_path = args.state_file or osutil.default_state_path()
    prefs = load_prefs(prefs_path)
    if args.lang:
        prefs.lang = args.lang
    if args.alpha is not None and 0.2 <= args.alpha <= 1.0:
        prefs.alpha = args.alpha

    from .app import OverlayApp, show_fatal  # noqa: PLC0415  (imports tkinter)
    from .core import State  # noqa: PLC0415

    osutil.enable_dpi_awareness()
    state = State()
    lang = i18n.resolve_lang(prefs.lang)
    try:
        server = start_server(state, args.port)
    except OSError as exc:
        t = i18n.strings(lang)
        show_fatal(t["app_title"], t["port_busy"].format(port=args.port, err=exc))
        return 1

    import tkinter as tk  # noqa: PLC0415

    root = tk.Tk()
    try:
        OverlayApp(root, state, prefs, prefs_path, args.exit_after)
        root.mainloop()
    finally:
        server.shutdown()
        server.server_close()
        try:
            root.destroy()
        except tk.TclError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
