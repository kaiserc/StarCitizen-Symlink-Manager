"""
tooltip.py - Rock-solid, non-overlapping hover tooltips for CustomTkinter / Tkinter.

Features:
- Global Singleton Tooltip Manager: Exactly ONE tooltip can exist at any time across the app.
  Hovering over a new element immediately dismisses any previously visible tooltip.
- Bounding-Box Detection: Uses physical widget screen coordinates (rootx/rooty/width/height)
  rather than fragile winfo_containing() hierarchies. Immune to composite CTk widget events.
- Cursor Collision Avoidance: Tooltip is positioned with a clean gap from both the widget and
  the mouse cursor so the cursor can never accidentally land inside or get stuck on the tooltip.
- Auto-Dismiss:
  * Mouse leaving the widget dismisses immediately.
  * Clicking ANY button or pressing ANY key dismisses immediately.
  * Mouse wheel / scrolling dismisses immediately.
  * Widget unmapping or tab switching dismisses immediately.
  * Auto-hide timer dismisses after 8 seconds of inactivity.
"""

import tkinter as tk
from typing import Optional, Sequence, Tuple

from .theme import (
    COLOR_TOOLTIP_BG,
    COLOR_TOOLTIP_BORDER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_ACCENT,
    FONT_UI_FAMILY,
)


class TooltipManager:
    """Singleton manager ensuring only one tooltip exists application-wide."""

    _active_window: Optional[tk.Toplevel] = None
    _active_owner: Optional["Tooltip"] = None
    _scheduled_id: Optional[str] = None
    _autohide_id: Optional[str] = None
    _bound_roots = set()

    @classmethod
    def register_root(cls, root_window):
        """Attaches dismiss-on-action bindings to the main window once."""
        if not root_window or root_window in cls._bound_roots:
            return
        cls._bound_roots.add(root_window)

        def on_dismiss_action(_event=None):
            cls.hide()

        # Any click, scroll, keypress or window movement dismisses active tooltips
        for seq in ("<ButtonPress>", "<MouseWheel>", "<Button-4>", "<Button-5>", "<KeyPress>", "<Configure>"):
            try:
                root_window.bind(seq, on_dismiss_action, add="+")
            except Exception:
                pass

    @classmethod
    def cancel_scheduled(cls, widget=None):
        if cls._scheduled_id is not None:
            try:
                target = widget or (cls._active_owner.widget if cls._active_owner else None)
                if target:
                    target.after_cancel(cls._scheduled_id)
            except Exception:
                pass
            cls._scheduled_id = None

    @classmethod
    def cancel_autohide(cls):
        if cls._autohide_id is not None:
            try:
                if cls._active_window and cls._active_window.winfo_exists():
                    cls._active_window.after_cancel(cls._autohide_id)
            except Exception:
                pass
            cls._autohide_id = None

    @classmethod
    def hide(cls):
        """Immediately destroys any active tooltip and cancels pending schedules."""
        cls.cancel_scheduled()
        cls.cancel_autohide()

        if cls._active_window is not None:
            try:
                if cls._active_window.winfo_exists():
                    cls._active_window.destroy()
            except Exception:
                pass
            cls._active_window = None

        cls._active_owner = None

    @classmethod
    def schedule(cls, tooltip: "Tooltip", delay: int):
        # If this tooltip is already showing, do nothing
        if cls._active_owner is tooltip and cls._active_window is not None:
            return

        # Cancel any other scheduled tooltip
        cls.cancel_scheduled()

        # If a tooltip is already visible, hide it immediately so there is never an overlap
        if cls._active_window is not None:
            cls.hide()

        cls._active_owner = tooltip
        try:
            cls._scheduled_id = tooltip.widget.after(delay, lambda: cls._show(tooltip))
        except Exception:
            cls._scheduled_id = None

    @classmethod
    def _show(cls, tooltip: "Tooltip"):
        cls._scheduled_id = None

        # Verify widget still exists and is visible on screen
        try:
            if not tooltip.widget.winfo_exists() or not tooltip.widget.winfo_viewable():
                cls.hide()
                return
        except Exception:
            cls.hide()
            return

        # Verify pointer is actually still inside the widget
        if not tooltip.is_pointer_inside():
            cls.hide()
            return

        # Destroy any lingering window
        cls.hide()
        cls._active_owner = tooltip

        try:
            root = tooltip.widget.winfo_toplevel()
        except Exception:
            root = tooltip.widget

        tip = tk.Toplevel(root)
        tip.wm_overrideredirect(True)
        tip.attributes("-topmost", True)
        tip.configure(bg=COLOR_TOOLTIP_BORDER)

        # Entering the tooltip window itself dismisses it immediately
        tip.bind("<Enter>", lambda e: cls.hide())

        inner = tk.Frame(tip, bg=COLOR_TOOLTIP_BG, padx=16, pady=12)
        inner.pack(padx=1, pady=1)

        # Cyan accent rule
        tk.Frame(inner, bg=COLOR_ACCENT, height=2, width=36).pack(anchor="w", pady=(0, 8))

        wlength = max(getattr(tooltip, "wraplength", 420), 420)
        if tooltip.title:
            tk.Label(
                inner,
                text=tooltip.title,
                bg=COLOR_TOOLTIP_BG,
                fg=COLOR_TEXT_PRIMARY,
                font=(FONT_UI_FAMILY, 13, "bold"),
                justify="left",
                anchor="w",
                wraplength=wlength,
            ).pack(anchor="w")

        tk.Label(
            inner,
            text=tooltip.text,
            bg=COLOR_TOOLTIP_BG,
            fg=COLOR_TEXT_SECONDARY if tooltip.title else COLOR_TEXT_PRIMARY,
            font=(FONT_UI_FAMILY, 12),
            justify="left",
            anchor="w",
            wraplength=wlength,
        ).pack(anchor="w", pady=(2 if tooltip.title else 0, 0))

        cls._active_window = tip
        cls._position(tip, tooltip)

        # Auto-dismiss after 8 seconds of continuous display
        try:
            cls._autohide_id = tip.after(8000, cls.hide)
        except Exception:
            cls._autohide_id = None

    @classmethod
    def _position(cls, tip: tk.Toplevel, tooltip: "Tooltip"):
        tip.update_idletasks()
        tw = tip.winfo_reqwidth()
        th = tip.winfo_reqheight()

        try:
            wx = tooltip.widget.winfo_rootx()
            wy = tooltip.widget.winfo_rooty()
            ww = tooltip.widget.winfo_width()
            wh = tooltip.widget.winfo_height()
            px, py = tooltip.widget.winfo_pointerxy()
        except Exception:
            cls.hide()
            return

        try:
            sw = tooltip.widget.winfo_vrootwidth() or tooltip.widget.winfo_screenwidth()
            sh = tooltip.widget.winfo_vrootheight() or tooltip.widget.winfo_screenheight()
        except Exception:
            sw, sh = 1920, 1080

        # Primary placement: aligned with widget left, placed below the widget
        x = wx
        y = wy + wh + 6

        # Make sure the tooltip does not spawn directly under the mouse cursor
        if py >= wy:
            y = max(y, py + 16)

        # If tooltip overflows bottom of screen, flip above the widget
        if y + th > sh - 10:
            y = wy - th - 6
            if py <= wy + wh:
                y = min(y, py - th - 8)

        # Clamp horizontal position within screen bounds
        if x + tw > sw - 12:
            x = max(12, sw - tw - 12)
        if x < 12:
            x = 12

        # Clamp vertical position within screen bounds
        if y < 10:
            y = 10
        elif y + th > sh - 10:
            y = max(10, sh - th - 10)

        tip.wm_geometry(f"+{int(x)}+{int(y)}")


class Tooltip:
    """Shows a styled mobiGlas popup after hovering ``widget`` for ``delay`` ms."""

    def __init__(
        self,
        widget,
        text: str,
        body: Optional[str] = None,
        delay: int = 400,
        wraplength: int = 380,
        extra_widgets: Optional[Sequence] = None,
    ):
        self.widget = widget
        self.extra_widgets = list(extra_widgets) if extra_widgets else []
        self.title = text if body else None
        self.text = body if body else text
        self.delay = delay
        self.wraplength = wraplength

        # Ensure root dismiss handlers are installed
        try:
            root = widget.winfo_toplevel()
            TooltipManager.register_root(root)
        except Exception:
            pass

        # Bind events to primary widget and any extra composite children
        targets = [self.widget] + self.extra_widgets
        for w in targets:
            self._bind_target(w)

    def _bind_target(self, target):
        for seq, cb in (
            ("<Enter>", self._on_enter),
            ("<Leave>", self._on_leave),
            ("<ButtonPress>", self._on_dismiss),
            ("<Unmap>", self._on_dismiss),
            ("<Destroy>", self._on_dismiss),
        ):
            try:
                target.bind(seq, cb, add="+")
            except (ValueError, TypeError, tk.TclError):
                target.bind(seq, cb, add=True)

    def update_text(self, text: str, body: Optional[str] = None):
        self.title = text if body else None
        self.text = body if body else text

    def is_pointer_inside(self) -> bool:
        """Geometric bounding-box check: is mouse cursor currently inside this widget or extras?"""
        targets = [self.widget] + self.extra_widgets
        try:
            px, py = self.widget.winfo_pointerxy()
        except Exception:
            return False

        for w in targets:
            try:
                if not w.winfo_exists() or not w.winfo_viewable():
                    continue
                wx = w.winfo_rootx()
                wy = w.winfo_rooty()
                ww = w.winfo_width()
                wh = w.winfo_height()
                if (wx <= px < wx + ww) and (wy <= py < wy + wh):
                    return True
            except Exception:
                continue
        return False

    def _on_enter(self, _event=None):
        TooltipManager.schedule(self, self.delay)

    def _on_leave(self, _event=None):
        # Check after a brief moment (30ms) to allow pointer movement between subwidgets
        try:
            self.widget.after(30, self._check_leave)
        except Exception:
            TooltipManager.hide()

    def _check_leave(self):
        if not self.is_pointer_inside():
            if TooltipManager._active_owner is self:
                TooltipManager.hide()
            elif TooltipManager._scheduled_id is not None and TooltipManager._active_owner is self:
                TooltipManager.cancel_scheduled(self.widget)

    def _on_dismiss(self, _event=None):
        TooltipManager.hide()
