"""The always-on-top tkinter window. All tk calls happen on the main thread only."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from . import i18n, osutil
from .core import (
    DEFAULT_FONT_SIZE, FONT_MAX, FONT_MIN, MIN_H, MIN_W, PX_PER_PT_96, Prefs, State, View,
    clamp_geometry, compose_view, default_geometry, font_size_for_height, format_coords,
    height_for_font_size, ordered_triple, parse_geometry, save_prefs,
)

POLL_MS = 200

BG = "#0f1115"
BORDER = "#2a2f3a"
FG_NUM = "#e8f0ff"
FG_STALE = "#6b7280"
FG_DIM = "#9aa4b2"
FG_AXIS = "#7fb3ff"
FG_ONLINE = "#5ad1a1"
FG_OFFLINE = "#f06c6c"
FG_FLASH = "#ffd166"


def log(msg: str) -> None:
    """stderr is None under pythonw / windowed builds; tolerate that."""
    import sys  # noqa: PLC0415

    stream = sys.stderr
    if stream is None:
        return
    try:
        stream.write(msg + "\n")
        stream.flush()
    except Exception:
        pass


class OverlayApp:

    def __init__(self, root: Any, state: State, prefs: Prefs, prefs_path: Path,
                 exit_after: Optional[float] = None) -> None:
        import tkinter as tk  # noqa: PLC0415
        from tkinter import font as tkfont  # noqa: PLC0415

        self.tk = tk
        self.root = root
        self.state = state
        self.prefs = prefs
        self.prefs_path = prefs_path
        self.lang = i18n.resolve_lang(prefs.lang)
        self._press: Optional[tuple[int, int, int, int, Any]] = None
        self._dragged = False
        self._grip_start: Optional[tuple[int, int, int, int]] = None
        self._flash_until = 0.0
        self._save_job: Optional[str] = None
        self._last_view: Optional[View] = None
        try:
            self.px_per_pt = float(root.tk.call("tk", "scaling"))
        except Exception:
            self.px_per_pt = PX_PER_PT_96

        root.title(i18n.strings(self.lang)["app_title"])
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        root.attributes("-alpha", prefs.alpha)
        root.configure(bg=BORDER)

        num_family, ui_family = osutil.fonts(root)
        self.font_num = tkfont.Font(family=num_family, size=prefs.font_size, weight="bold")
        self.font_axis = tkfont.Font(family=num_family, size=prefs.font_size, weight="bold")
        self.font_ui = tkfont.Font(family=ui_family, size=prefs.font_size)

        outer = tk.Frame(root, bg=BG, highlightthickness=1, highlightbackground=BORDER)
        outer.pack(fill="both", expand=True)

        top = tk.Frame(outer, bg=BG)
        top.pack(fill="x", padx=6, pady=(4, 0))
        self.lbl_header = tk.Label(top, text="", font=self.font_ui, bg=BG, fg=FG_DIM, anchor="w")
        self.lbl_header.pack(side="left", fill="x", expand=True)
        self.lbl_online = tk.Label(top, text="", font=self.font_ui, bg=BG, fg=FG_DIM, anchor="e")
        self.lbl_online.pack(side="right")

        self.number_widgets: list[Any] = []
        self.lbl_values: list[Any] = []
        self.lbl_axes: list[Any] = []
        for _ in range(3):
            row = tk.Frame(outer, bg=BG)
            row.pack(fill="x", padx=8)
            lbl_axis = tk.Label(row, text="", font=self.font_axis, bg=BG, fg=FG_AXIS, width=2, anchor="w")
            lbl_axis.pack(side="left")
            lbl_val = tk.Label(row, text="--.--", font=self.font_num, bg=BG, fg=FG_NUM, anchor="e")
            lbl_val.pack(side="right", fill="x", expand=True)
            self.lbl_axes.append(lbl_axis)
            self.lbl_values.append(lbl_val)
            self.number_widgets.extend([row, lbl_axis, lbl_val])

        bottom = tk.Frame(outer, bg=BG)
        bottom.pack(fill="x", side="bottom", padx=6, pady=(0, 3))
        self.lbl_status = tk.Label(bottom, text="", font=self.font_ui, bg=BG, fg=FG_DIM, anchor="w")
        self.lbl_status.pack(side="left", fill="x", expand=True)
        self.grip = tk.Canvas(bottom, width=14, height=14, bg=BG, highlightthickness=0,
                              cursor="size_nw_se" if osutil.IS_WIN else "sizing")
        self.grip.pack(side="right", anchor="se")
        self.lbl_order = tk.Label(bottom, text="", font=self.font_ui, bg=BG, fg=FG_DIM, anchor="e")
        self.lbl_order.pack(side="right", padx=(0, 6))
        self._draw_grip()

        self._apply_font_size(prefs.font_size)
        self._place_initially()
        self._build_menu()

        root.bind("<ButtonPress-1>", self._on_press)
        root.bind("<B1-Motion>", self._on_drag)
        root.bind("<ButtonRelease-1>", self._on_release)
        root.bind("<ButtonPress-3>", self._on_context)
        if osutil.IS_MAC:
            # Aqua Tk 8.x reports the right button as Button-2; Ctrl-click is the trackpad habit.
            root.bind("<ButtonPress-2>", self._on_context)
            root.bind("<Control-ButtonPress-1>", self._on_context)
            root.bind("<Command-MouseWheel>", self._on_ctrl_wheel)
        root.bind("<Control-MouseWheel>", self._on_ctrl_wheel)
        self.grip.bind("<ButtonPress-1>", self._grip_press)
        self.grip.bind("<B1-Motion>", self._grip_drag)
        self.grip.bind("<ButtonRelease-1>", self._grip_release)

        if exit_after is not None:
            root.after(max(0, int(exit_after * 1000)), self.quit)
        root.after(POLL_MS, self._tick)

    # ---------------------------------------------------------------- layout
    @property
    def t(self) -> dict[str, str]:
        return i18n.strings(self.lang)

    def _draw_grip(self) -> None:
        self.grip.delete("all")
        for off in (2, 6, 10):
            self.grip.create_line(off, 14, 14, off, fill=FG_DIM)

    def _apply_font_size(self, size: int) -> None:
        size = max(FONT_MIN, min(FONT_MAX, size))
        self.prefs.font_size = size
        self.font_num.configure(size=size)
        self.font_axis.configure(size=max(FONT_MIN, round(size * 0.6)))
        self.font_ui.configure(size=max(7, round(size * 0.42)))

    def _place_initially(self) -> None:
        if self.prefs.geometry == Prefs().geometry:
            parsed = default_geometry(self.px_per_pt)
        else:
            parsed = parse_geometry(self.prefs.geometry) or default_geometry(self.px_per_pt)
        w, h, x, y = clamp_geometry(*parsed, osutil.virtual_screen(self.root))
        self._set_geometry(w, h, x, y)

    def _set_geometry(self, w: int, h: int, x: int, y: int) -> None:
        self.prefs.geometry = f"{w}x{h}{x:+d}{y:+d}"
        self.root.geometry(self.prefs.geometry)

    def _current_geometry(self) -> tuple[int, int, int, int]:
        self.root.update_idletasks()
        return self.root.winfo_width(), self.root.winfo_height(), self.root.winfo_x(), self.root.winfo_y()

    # ---------------------------------------------------------------- menu
    def _build_menu(self) -> None:
        tk = self.tk
        t = self.t
        self.var_order = tk.StringVar(value=self.prefs.order)
        self.var_alpha = tk.IntVar(value=int(round(self.prefs.alpha * 100)))
        self.var_lang = tk.StringVar(value=self.prefs.lang)
        menu = tk.Menu(self.root, tearoff=0)
        menu.add_command(label=t["menu_copy"], command=self.copy_coords)
        menu.add_separator()
        menu.add_radiobutton(label=t["menu_order_raw"], variable=self.var_order, value="raw",
                             command=self._on_order_change)
        menu.add_radiobutton(label=t["menu_order_blender"], variable=self.var_order, value="blender",
                             command=self._on_order_change)
        menu.add_separator()
        alpha_menu = tk.Menu(menu, tearoff=0)
        for pct in (70, 80, 90, 100):
            alpha_menu.add_radiobutton(label=f"{pct} %", variable=self.var_alpha, value=pct,
                                       command=self._on_alpha_change)
        menu.add_cascade(label=t["menu_alpha"], menu=alpha_menu)
        menu.add_command(label=t["menu_font_bigger"], command=lambda: self._step_font(+2))
        menu.add_command(label=t["menu_font_smaller"], command=lambda: self._step_font(-2))
        menu.add_command(label=t["menu_reset"], command=self.reset_geometry)
        lang_menu = tk.Menu(menu, tearoff=0)
        lang_menu.add_radiobutton(label=t["menu_lang_auto"], variable=self.var_lang, value="auto",
                                  command=self._on_lang_change)
        lang_menu.add_radiobutton(label="繁體中文", variable=self.var_lang, value="zh", command=self._on_lang_change)
        lang_menu.add_radiobutton(label="English", variable=self.var_lang, value="en", command=self._on_lang_change)
        menu.add_cascade(label=t["menu_lang"], menu=lang_menu)
        menu.add_separator()
        menu.add_command(label=t["menu_quit"], command=self.quit)
        self.menu = menu

    def _on_context(self, event: Any) -> str:
        try:
            self.menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.menu.grab_release()
        return "break"

    def _on_order_change(self) -> None:
        self.prefs.order = self.var_order.get()
        self._last_view = None
        self._schedule_save()

    def _on_alpha_change(self) -> None:
        self.prefs.alpha = self.var_alpha.get() / 100.0
        self.root.attributes("-alpha", self.prefs.alpha)
        self._schedule_save()

    def _on_lang_change(self) -> None:
        self.prefs.lang = self.var_lang.get()
        self.lang = i18n.resolve_lang(self.prefs.lang)
        self.root.title(self.t["app_title"])
        self.menu.destroy()
        self._build_menu()
        self._last_view = None
        self._schedule_save()

    def reset_geometry(self) -> None:
        self._apply_font_size(DEFAULT_FONT_SIZE)
        self._set_geometry(*clamp_geometry(*default_geometry(self.px_per_pt), osutil.virtual_screen(self.root)))
        self._schedule_save()

    # ---------------------------------------------------------------- drag / click
    def _on_press(self, event: Any) -> None:
        self._press = (event.x_root, event.y_root, self.root.winfo_x(), self.root.winfo_y(), event.widget)
        self._dragged = False

    def _on_drag(self, event: Any) -> None:
        if self._press is None:
            return
        px, py, wx, wy, _ = self._press
        dx, dy = event.x_root - px, event.y_root - py
        if abs(dx) + abs(dy) >= 3:
            self._dragged = True
        if self._dragged:
            self.root.geometry(f"{wx + dx:+d}{wy + dy:+d}")

    def _on_release(self, event: Any) -> None:
        if self._press is None:
            return
        widget = self._press[4]
        self._press = None
        if self._dragged:
            self._set_geometry(*self._current_geometry())
            self._schedule_save()
        elif widget in self.number_widgets:
            self.copy_coords()

    # ---------------------------------------------------------------- resize
    def _grip_press(self, event: Any) -> str:
        w, h, _, _ = self._current_geometry()
        self._grip_start = (event.x_root, event.y_root, w, h)
        return "break"

    def _grip_drag(self, event: Any) -> str:
        if self._grip_start is None:
            return "break"
        px, py, w0, h0 = self._grip_start
        w = max(MIN_W, w0 + (event.x_root - px))
        h = max(MIN_H, h0 + (event.y_root - py))
        _, _, x, y = self._current_geometry()
        self._set_geometry(w, h, x, y)
        self._apply_font_size(font_size_for_height(h, self.px_per_pt))
        return "break"

    def _grip_release(self, event: Any) -> str:
        self._grip_start = None
        self._schedule_save()
        return "break"

    def _step_font(self, step: int) -> None:
        size = max(FONT_MIN, min(FONT_MAX, self.prefs.font_size + step))
        self._apply_font_size(size)
        w, _, x, y = self._current_geometry()
        self._set_geometry(w, height_for_font_size(size, self.px_per_pt), x, y)
        self._schedule_save()

    def _on_ctrl_wheel(self, event: Any) -> str:
        if event.delta:
            self._step_font(1 if event.delta > 0 else -1)
        return "break"

    # ---------------------------------------------------------------- copy
    def copy_coords(self) -> None:
        snap = self.state.snapshot()
        if snap.pos is None:
            return
        text = format_coords(ordered_triple(snap.pos, self.prefs.order))
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
        except self.tk.TclError:
            return
        self._flash_until = time.monotonic() + 1.2
        self._last_view = None

    # ---------------------------------------------------------------- periodic refresh
    def _tick(self) -> None:
        try:
            self._refresh()
        finally:
            self.root.after(POLL_MS, self._tick)

    def _refresh(self) -> None:
        now = time.monotonic()
        view = compose_view(self.state.snapshot(), now, self.prefs.order, self.lang)
        flashing = now < self._flash_until
        if view == self._last_view and not flashing and self.lbl_status.cget("fg") != FG_FLASH:
            return
        self._last_view = view
        self.lbl_header.configure(text=view.header)
        self.lbl_online.configure(text=view.online_text, fg=FG_ONLINE if view.online else FG_OFFLINE)
        fg = FG_STALE if view.stale else FG_NUM
        for lbl, value in zip(self.lbl_values, view.values):
            lbl.configure(text=value, fg=fg)
        for lbl, axis in zip(self.lbl_axes, ("X", "Y", "Z")):
            lbl.configure(text=axis)
        if flashing:
            self.lbl_status.configure(text=self.t["copied"], fg=FG_FLASH)
        else:
            self.lbl_status.configure(text=view.status,
                                      fg=FG_OFFLINE if (view.has_pos and not view.online) else FG_DIM)
        self.lbl_order.configure(
            text=self.t["order_blender_short"] if self.prefs.order == "blender" else self.t["order_raw_short"])

    # ---------------------------------------------------------------- save / quit
    def _schedule_save(self) -> None:
        if self._save_job is not None:
            self.root.after_cancel(self._save_job)
        self._save_job = self.root.after(400, self._flush_save)

    def _flush_save(self) -> None:
        self._save_job = None
        err = save_prefs(self.prefs_path, self.prefs)
        if err:
            log(f"[overlay] {err}")

    def quit(self) -> None:
        if self._save_job is not None:
            self.root.after_cancel(self._save_job)
            self._save_job = None
        err = save_prefs(self.prefs_path, self.prefs)
        if err:
            log(f"[overlay] {err}")
        self.root.quit()


def show_fatal(title: str, message: str) -> None:
    log(f"[overlay] {message}")
    try:
        import tkinter as tk  # noqa: PLC0415
        from tkinter import messagebox  # noqa: PLC0415

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(title, message)
        root.destroy()
    except Exception:
        pass
