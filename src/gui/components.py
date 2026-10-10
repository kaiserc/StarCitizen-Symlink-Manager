"""
components.py - Reusable CustomTkinter UI widgets for Star Citizen Symlink Manager.
"""

import tkinter as tk
import customtkinter as ctk
from typing import Callable, Dict, Any, List, Optional, Sequence

from .theme import (
    COLOR_BG_INPUT,
    COLOR_BTN,
    COLOR_BTN_HOVER,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_ACCENT,
    COLOR_ACCENT_HOVER,
    COLOR_ACCENT_MUTED,
    COLOR_ACCENT_GLOW,
    COLOR_GOLD,
    COLOR_GOLD_MUTED,
    COLOR_SUCCESS,
    COLOR_SUCCESS_BG,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_DANGER_BG,
    COLOR_DANGER_HOVER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    FONT_HEADING,
    FONT_SECTION,
    FONT_METRIC,
    FONT_BODY,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    FONT_BTN,
    FONT_MONO,
    FONT_MONO_SMALL,
)
from .tooltip import Tooltip
from .help_text import tip


# --- Small helpers -----------------------------------------------------------

def add_tip(widget, key: str, extra_widgets: Optional[Sequence] = None) -> Optional[Tooltip]:
    """Attaches the tooltip registered under ``key`` in help_text.TIPS."""
    title, body = tip(key)
    if not title:
        return None
    return Tooltip(widget, title, body, extra_widgets=extra_widgets)


def hud_button(master, text: str, command=None, variant: str = "secondary", tip_key: str = None, **kwargs):
    """
    Consistently styled button.
    variant: 'primary' (vibrant cyan), 'secondary' (neutral), 'success', 'danger', 'gold', 'ghost'
    """
    styles = {
        "primary":   dict(fg_color=COLOR_ACCENT, hover_color=COLOR_ACCENT_HOVER, text_color="#04080F",
                          border_color=COLOR_ACCENT, border_width=0),
        "secondary": dict(fg_color=COLOR_BTN, hover_color=COLOR_BTN_HOVER, text_color=COLOR_TEXT_PRIMARY,
                          border_color=COLOR_CARD_BORDER, border_width=1),
        "success":   dict(fg_color=COLOR_SUCCESS_BG, hover_color="#104E3A", text_color=COLOR_SUCCESS,
                          border_color=COLOR_SUCCESS, border_width=1),
        "danger":    dict(fg_color=COLOR_DANGER_BG, hover_color=COLOR_DANGER_HOVER, text_color="#FFB3BB",
                          border_color="#7A2632", border_width=1),
        "gold":      dict(fg_color=COLOR_GOLD, hover_color="#F2C66D", text_color="#140E02",
                          border_color=COLOR_GOLD, border_width=0),
        "ghost":     dict(fg_color="transparent", hover_color=COLOR_BTN, text_color=COLOR_TEXT_SECONDARY,
                          border_width=0),
    }
    opts = dict(styles.get(variant, styles["secondary"]))
    opts.setdefault("corner_radius", 4)
    opts.setdefault("font", FONT_BTN)
    opts.setdefault("height", 36)
    opts.update(kwargs)
    btn = ctk.CTkButton(master, text=text, command=command, **opts)
    if tip_key:
        add_tip(btn, tip_key)
    return btn


def badge(master, text: str, fg: str, bg: str, tip_key: str = None) -> ctk.CTkLabel:
    lbl = ctk.CTkLabel(
        master, text=text, font=FONT_SMALL_BOLD, fg_color=bg, text_color=fg,
        corner_radius=4, padx=12, pady=3, height=26,
    )
    if tip_key:
        add_tip(lbl, tip_key)
    return lbl


class HudPanel(ctk.CTkFrame):
    """Card with a thin cyan accent strip on the left edge (mobiGlas panel look)."""

    def __init__(self, master, accent: str = COLOR_ACCENT, **kwargs):
        kwargs.setdefault("fg_color", COLOR_CARD_BG)
        kwargs.setdefault("border_color", COLOR_CARD_BORDER)
        kwargs.setdefault("border_width", 1)
        kwargs.setdefault("corner_radius", 6)
        super().__init__(master, **kwargs)
        self._strip = ctk.CTkFrame(self, fg_color=accent, width=3, corner_radius=0)
        self._strip.place(x=1, rely=0.12, relheight=0.76)

    def set_accent(self, color: str):
        self._strip.configure(fg_color=color)


class SectionLabel(ctk.CTkFrame):
    """Uppercase section title with a fading rule, e.g. ── QUICK PRESETS ─────"""

    def __init__(self, master, text: str, help_key: str = None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        ctk.CTkFrame(self, fg_color=COLOR_ACCENT, width=16, height=2, corner_radius=0).pack(side="left", padx=(0, 8))
        lbl = ctk.CTkLabel(self, text=text.upper(), font=FONT_SECTION, text_color=COLOR_TEXT_SECONDARY)
        lbl.pack(side="left")
        if help_key:
            info = ctk.CTkLabel(self, text="ⓘ", font=FONT_SMALL, text_color=COLOR_ACCENT, cursor="question_arrow")
            info.pack(side="left", padx=(6, 0))
            add_tip(info, help_key)
        ctk.CTkFrame(self, fg_color=COLOR_CARD_BORDER, height=1, corner_radius=0).pack(
            side="left", fill="x", expand=True, padx=(8, 0))


class StorageMetricCard(HudPanel):
    """Card displaying a single KPI metric (e.g., Space Saved, Active Channels)."""

    def __init__(self, master, title: str, value: str, subtitle: str, accent_color: str = COLOR_ACCENT,
                 tip_key: str = None, **kwargs):
        super().__init__(master, accent=accent_color, **kwargs)

        self.title_lbl = ctk.CTkLabel(self, text=title.upper(), font=FONT_SECTION, text_color=COLOR_TEXT_MUTED)
        self.title_lbl.pack(anchor="w", padx=(18, 14), pady=(12, 0))

        self.value_lbl = ctk.CTkLabel(self, text=value, font=FONT_METRIC, text_color=accent_color)
        self.value_lbl.pack(anchor="w", padx=(18, 14), pady=(2, 0))

        self.subtitle_lbl = ctk.CTkLabel(self, text=subtitle, font=FONT_SMALL, text_color=COLOR_TEXT_SECONDARY)
        self.subtitle_lbl.pack(anchor="w", padx=(18, 14), pady=(2, 12))

        if tip_key:
            add_tip(self, tip_key, extra_widgets=(self.title_lbl, self.value_lbl, self.subtitle_lbl))

    def update_values(self, value: str, subtitle: str = None):
        self.value_lbl.configure(text=value)
        if subtitle:
            self.subtitle_lbl.configure(text=subtitle)


class StorageEfficiencyVisualizer(HudPanel):
    """
    Sleek mobiGlas HUD storage allocation visualizer showing physical disk
    consumption vs virtual space mapped by symlinks with smooth ease-out animation.
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, accent=COLOR_ACCENT, **kwargs)
        self._current_phys_pct = 0.0
        self._target_phys_pct = 0.0
        self._current_saved_pct = 0.0
        self._target_saved_pct = 0.0
        self._anim_job = None

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="x", padx=(18, 14), pady=(10, 10))

        # 1. Top row: Section title + Efficiency Multiplier Badge
        top_row = ctk.CTkFrame(container, fg_color="transparent")
        top_row.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            top_row,
            text="STORAGE ALLOCATION & VIRTUAL MAPPING",
            font=FONT_SECTION,
            text_color=COLOR_TEXT_SECONDARY,
        ).pack(side="left")

        self.badge_lbl = ctk.CTkLabel(
            top_row,
            text="0% SAVED · 1.0x MULTIPLIER",
            font=FONT_SMALL_BOLD,
            text_color=COLOR_SUCCESS,
            fg_color=COLOR_SUCCESS_BG,
            corner_radius=4,
            padx=10,
            pady=2,
            height=24,
        )
        self.badge_lbl.pack(side="right")
        add_tip(self.badge_lbl, "storage_visualizer")

        # 2. Middle bar: Canvas with custom rendering
        self.canvas = tk.Canvas(
            container,
            height=22,
            bg=COLOR_BG_INPUT,
            bd=0,
            highlightthickness=1,
            highlightbackground=COLOR_CARD_BORDER,
        )
        self.canvas.pack(fill="x", pady=(2, 8))
        self.canvas.bind("<Configure>", lambda e: self._redraw())
        add_tip(self.canvas, "storage_visualizer")

        # 3. Bottom Legend / Detail row
        legend_row = ctk.CTkFrame(container, fg_color="transparent")
        legend_row.pack(fill="x")

        # Column 1: Physical
        c1 = ctk.CTkFrame(legend_row, fg_color="transparent")
        c1.pack(side="left", padx=(0, 20))
        dot1 = ctk.CTkFrame(c1, fg_color=COLOR_ACCENT, width=8, height=8, corner_radius=4)
        dot1.pack(side="left", padx=(0, 6))
        self.lbl_phys = ctk.CTkLabel(
            c1,
            text="Physical Footprint: -- GB",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.lbl_phys.pack(side="left")

        # Column 2: Saved
        c2 = ctk.CTkFrame(legend_row, fg_color="transparent")
        c2.pack(side="left", padx=(0, 20))
        dot2 = ctk.CTkFrame(c2, fg_color=COLOR_SUCCESS, width=8, height=8, corner_radius=4)
        dot2.pack(side="left", padx=(0, 6))
        self.lbl_saved = ctk.CTkLabel(
            c2,
            text="Virtual Mapped / Saved: -- GB",
            font=FONT_SMALL,
            text_color=COLOR_SUCCESS,
        )
        self.lbl_saved.pack(side="left")

        # Column 3: Total playable
        c3 = ctk.CTkFrame(legend_row, fg_color="transparent")
        c3.pack(side="right")
        dot3 = ctk.CTkFrame(c3, fg_color=COLOR_TEXT_MUTED, width=8, height=8, corner_radius=4)
        dot3.pack(side="left", padx=(0, 6))
        self.lbl_total = ctk.CTkLabel(
            c3,
            text="Virtual Total: -- GB",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
        )
        self.lbl_total.pack(side="right")

    def update_storage(self, physical_gb: float, virtual_gb: float, saved_gb: float):
        """Updates storage numbers and triggers smooth animation of the allocation bar."""
        if virtual_gb <= 0:
            phys_pct = 0.0
            saved_pct = 0.0
            multiplier = 1.0
        else:
            phys_pct = min(100.0, max(0.0, (physical_gb / virtual_gb) * 100.0))
            saved_pct = min(100.0, max(0.0, (saved_gb / virtual_gb) * 100.0))
            multiplier = round(virtual_gb / physical_gb, 1) if physical_gb > 0 else 1.0

        self.lbl_phys.configure(text=f"Physical Footprint: {physical_gb:.1f} GB ({phys_pct:.0f}%)")
        self.lbl_saved.configure(text=f"Virtual Mapped / Saved: ~{saved_gb:.1f} GB ({saved_pct:.0f}%)")
        self.lbl_total.configure(text=f"Virtual Playable Space: {virtual_gb:.1f} GB")

        badge_txt = f"{saved_pct:.1f}% SAVED · {multiplier:.1f}x SSD MULTIPLIER" if saved_gb > 0 else "100% PHYSICAL · 1.0x MULTIPLIER"
        badge_fg = COLOR_SUCCESS if saved_gb > 0 else COLOR_TEXT_SECONDARY
        badge_bg = COLOR_SUCCESS_BG if saved_gb > 0 else COLOR_BTN
        self.badge_lbl.configure(text=badge_txt, text_color=badge_fg, fg_color=badge_bg)

        self._target_phys_pct = phys_pct
        self._target_saved_pct = saved_pct

        self._start_animation()

    def _start_animation(self):
        if self._anim_job is not None:
            try:
                self.after_cancel(self._anim_job)
            except Exception:
                pass
            self._anim_job = None
        self._step_animation()

    def _step_animation(self):
        # Smooth exponential approach (ease-out)
        diff_p = self._target_phys_pct - self._current_phys_pct
        diff_s = self._target_saved_pct - self._current_saved_pct

        if abs(diff_p) < 0.2 and abs(diff_s) < 0.2:
            self._current_phys_pct = self._target_phys_pct
            self._current_saved_pct = self._target_saved_pct
            self._redraw()
            self._anim_job = None
            return

        self._current_phys_pct += diff_p * 0.22
        self._current_saved_pct += diff_s * 0.22
        self._redraw()
        self._anim_job = self.after(16, self._step_animation)

    def _redraw(self):
        self.canvas.delete("all")
        w = self.canvas.winfo_width()
        h = self.canvas.winfo_height()
        if w <= 10 or h <= 4:
            return

        # Background track
        self.canvas.create_rectangle(0, 0, w, h, fill=COLOR_BG_INPUT, outline="")

        total_pct = self._current_phys_pct + self._current_saved_pct
        if total_pct <= 0:
            return

        phys_w = int((self._current_phys_pct / 100.0) * w)
        saved_w = int((self._current_saved_pct / 100.0) * w)

        # 1. Physical bar (Cyber Cyan)
        if phys_w > 0:
            self.canvas.create_rectangle(0, 0, phys_w, h, fill=COLOR_ACCENT, outline="")

        # 2. Virtual Saved bar (Emerald Green)
        if saved_w > 0:
            x_start = phys_w
            x_end = min(w, phys_w + saved_w)
            self.canvas.create_rectangle(x_start, 0, x_end, h, fill=COLOR_SUCCESS, outline="")

            # Subtle futuristic diagonal hatches across saved segment
            step = 14
            for x in range(x_start - h, x_end + step, step):
                self.canvas.create_line(
                    max(x_start, x), h,
                    min(x_end, x + h), 0,
                    fill="#156447",
                    width=2
                )

        # Subtle divider hairline between physical and virtual if both exist
        if phys_w > 0 and saved_w > 0:
            self.canvas.create_line(phys_w, 0, phys_w, h, fill="#04080F", width=2)


class ChannelCard(HudPanel):
    """Card displaying a single Star Citizen release channel's status, target, and controls."""

    def __init__(
        self,
        master,
        channel_data: Dict[str, Any],
        available_targets: List[str],
        on_link_callback: Callable[[str, str], None],
        on_unlink_callback: Callable[[str], None],
        on_open_callback: Callable[[str], None],
        **kwargs
    ):
        super().__init__(master, **kwargs)
        self.channel_data = channel_data
        self.available_targets = available_targets
        self.on_link_callback = on_link_callback
        self.on_unlink_callback = on_unlink_callback
        self.on_open_callback = on_open_callback

        self._build_ui()

    def _build_ui(self):
        name = self.channel_data.get("name", "UNKNOWN")
        link_type = self.channel_data.get("link_type", "missing")
        is_link = self.channel_data.get("is_link", False)
        target_raw = self.channel_data.get("target_raw", "")
        target_exists = self.channel_data.get("target_exists", False)
        version_info = self.channel_data.get("version_info", {})
        size_gb = self.channel_data.get("size_gb", 0.0)
        is_master = self.channel_data.get("is_master_base", False)
        symlinks_pointing = self.channel_data.get("symlinks_pointing_here", [])

        # Status -> (badge text, fg, bg, accent strip, tooltip key)
        if is_link and not target_exists:
            status = ("BROKEN LINK", COLOR_DANGER, COLOR_DANGER_BG, COLOR_DANGER, "badge_broken")
        elif link_type == "symlink":
            status = ("SYMLINK", COLOR_SUCCESS, COLOR_SUCCESS_BG, COLOR_SUCCESS, "badge_symlink")
        elif link_type == "junction":
            status = ("JUNCTION", COLOR_SUCCESS, COLOR_SUCCESS_BG, COLOR_SUCCESS, "badge_junction")
        elif link_type == "real_dir":
            status = ("REAL FOLDER", COLOR_TEXT_SECONDARY, COLOR_BTN, COLOR_GOLD if is_master else COLOR_ACCENT,
                      "badge_real")
        else:
            status = ("NOT INSTALLED", COLOR_TEXT_MUTED, "#111B2B", COLOR_CARD_BORDER, "badge_missing")
        badge_text, badge_fg, badge_bg, strip, badge_tip = status
        self.set_accent(strip)

        # Top row: Channel Name + badges
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=(18, 14), pady=(12, 4))

        ctk.CTkLabel(top_row, text=name, font=FONT_HEADING, text_color=COLOR_TEXT_PRIMARY).pack(side="left")

        if is_master:
            badge(top_row, "★ MASTER BASE", COLOR_GOLD, COLOR_GOLD_MUTED, "badge_master").pack(side="left", padx=10)

        badge(top_row, badge_text, badge_fg, badge_bg, badge_tip).pack(side="right")

        # Detail description row
        if is_link:
            target_desc = f"→  {target_raw}"
            if not target_exists:
                target_desc += "   (target missing!)"
            desc_color = COLOR_ACCENT if target_exists else COLOR_DANGER
        elif is_master:
            pointing_str = ", ".join(symlinks_pointing) if symlinks_pointing else "None"
            target_desc = f"Shared by:  {pointing_str}"
            desc_color = COLOR_GOLD
        elif link_type == "real_dir":
            target_desc = "Standalone folder - not shared with other channels"
            desc_color = COLOR_TEXT_MUTED
        else:
            target_desc = "Folder does not exist yet - link it to a target below"
            desc_color = COLOR_TEXT_MUTED

        ctk.CTkLabel(self, text=target_desc, font=FONT_BODY, text_color=desc_color).pack(
            anchor="w", padx=(18, 14), pady=(0, 4))

        # Metadata row: Version info & Size
        meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        meta_frame.pack(fill="x", padx=(18, 14), pady=(0, 8))

        branch = version_info.get("branch", "")
        ver = version_info.get("version", "")
        if branch or ver:
            v_text = f"Build  {branch}  ·  {ver}" if ver else f"Build  {branch}"
        else:
            v_text = "Build  unknown"

        v_lbl = ctk.CTkLabel(meta_frame, text=v_text, font=FONT_MONO, text_color=COLOR_TEXT_MUTED)
        v_lbl.pack(side="left")
        add_tip(v_lbl, "version")

        size_text = f"~{size_gb} GB" if size_gb > 0 else "--"
        if is_link and size_gb > 0:
            size_text += " (shared)"
        size_lbl = ctk.CTkLabel(meta_frame, text=f"Footprint  {size_text}", font=FONT_MONO,
                                text_color=COLOR_TEXT_MUTED)
        size_lbl.pack(side="right")
        add_tip(size_lbl, "disk_footprint")

        # Divider
        ctk.CTkFrame(self, fg_color=COLOR_CARD_BORDER, height=1, corner_radius=0).pack(
            fill="x", padx=(18, 14), pady=(0, 10))

        # Bottom Actions row
        actions_row = ctk.CTkFrame(self, fg_color="transparent")
        actions_row.pack(fill="x", padx=(18, 14), pady=(0, 12))

        ctk.CTkLabel(actions_row, text="Link to", font=FONT_SMALL_BOLD, text_color=COLOR_TEXT_SECONDARY).pack(
            side="left", padx=(0, 8))

        filtered_targets = [t for t in self.available_targets if t != name]
        if not filtered_targets:
            filtered_targets = ["Game", "LIVE"]

        self.target_dropdown = ctk.CTkOptionMenu(
            actions_row,
            values=filtered_targets,
            width=150,
            height=36,
            corner_radius=4,
            font=FONT_BODY,
            dropdown_font=FONT_BODY,
            fg_color=COLOR_BG_INPUT,
            button_color=COLOR_BTN,
            button_hover_color=COLOR_BTN_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            dropdown_fg_color=COLOR_CARD_BG,
            dropdown_hover_color=COLOR_ACCENT_GLOW,
        )
        # Preselect the current target if this is a link, else prefer 'Game'
        current = target_raw.replace("\\", "/").rstrip("/").split("/")[-1] if is_link and target_raw else ""
        if current in filtered_targets:
            default_target = current
        else:
            default_target = "Game" if "Game" in filtered_targets else filtered_targets[0]
        self.target_dropdown.set(default_target)
        self.target_dropdown.pack(side="left", padx=(0, 8))
        add_tip(self.target_dropdown, "target_dropdown")

        hud_button(actions_row, "Re-link" if is_link else "Link", self._on_link_clicked,
                   variant="primary", tip_key="link_btn", width=92, height=36).pack(side="left", padx=(0, 6))

        if is_link:
            hud_button(actions_row, "Unlink", lambda: self.on_unlink_callback(name),
                       variant="danger", tip_key="unlink_btn", width=92, height=36).pack(side="left", padx=(0, 6))

        if self.channel_data.get("exists", False):
            hud_button(actions_row, "Open Folder", lambda: self.on_open_callback(self.channel_data.get("path", "")),
                       variant="ghost", tip_key="open_channel", width=120, height=36).pack(side="right")

    def _on_link_clicked(self):
        target = self.target_dropdown.get()
        name = self.channel_data.get("name", "")
        self.on_link_callback(name, target)


class LogConsole(ctk.CTkFrame):
    """Scrollable, color-coded console for application logs and operations."""

    TAG_COLORS = {
        "SUCCESS": COLOR_SUCCESS,
        "RESTORE": COLOR_SUCCESS,
        "ERROR": COLOR_DANGER,
        "FAILED": COLOR_DANGER,
        "WARN": COLOR_WARNING,
        "BACKUP": COLOR_GOLD,
        "PRESET": COLOR_ACCENT,
        "DETECT": COLOR_ACCENT,
        "LAUNCH": COLOR_ACCENT,
    }

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=COLOR_BG_INPUT,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=6,
            **kwargs
        )

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=12, pady=(8, 2))

        dot = ctk.CTkFrame(header_frame, fg_color=COLOR_SUCCESS, width=7, height=7, corner_radius=4)
        dot.pack(side="left", padx=(0, 8))
        ctk.CTkLabel(header_frame, text="ACTIVITY LOG", font=FONT_SECTION, text_color=COLOR_TEXT_MUTED).pack(side="left")

        self.toggle_btn = hud_button(header_frame, "Hide", self.toggle, variant="ghost", width=54, height=22,
                                     font=FONT_SMALL)
        self.toggle_btn.pack(side="right")
        hud_button(header_frame, "Clear", self.clear, variant="ghost", tip_key="clear_log", width=54, height=22,
                   font=FONT_SMALL).pack(side="right", padx=(0, 4))

        self.textbox = ctk.CTkTextbox(
            self,
            font=FONT_MONO,
            fg_color=COLOR_BG_INPUT,
            text_color=COLOR_TEXT_SECONDARY,
            wrap="word",
            height=76,
            border_width=0,
        )
        self.textbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        for tag, color in self.TAG_COLORS.items():
            self.textbox.tag_config(tag, foreground=color)
        self._collapsed = False

    def log(self, text: str):
        tag = None
        if text.startswith("["):
            key = text[1:text.find("]")].split()[0].upper() if "]" in text else ""
            tag = self.TAG_COLORS.get(key) and key
        self.textbox.configure(state="normal")
        if tag:
            self.textbox.insert("end", f"{text}\n", tag)
        else:
            self.textbox.insert("end", f"{text}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")

    def toggle(self):
        if self._collapsed:
            self.textbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))
            self.toggle_btn.configure(text="Hide")
        else:
            self.textbox.pack_forget()
            self.toggle_btn.configure(text="Show")
        self._collapsed = not self._collapsed
