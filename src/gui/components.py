"""
components.py - Reusable CustomTkinter UI widgets for Star Citizen Symlink Manager.
"""

import os
import subprocess
import customtkinter as ctk
from typing import Callable, Optional, Dict, Any, List

from .theme import (
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_CARD_HOVER,
    COLOR_ACCENT,
    COLOR_ACCENT_HOVER,
    COLOR_ACCENT_MUTED,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
    COLOR_MUTED,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    FONT_TITLE,
    FONT_SUBTITLE,
    FONT_HEADING,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_MONO,
    FONT_MONO_SMALL,
)


class StorageMetricCard(ctk.CTkFrame):
    """Card displaying a single KPI metric (e.g., Space Saved, Active Channels)."""

    def __init__(self, master, title: str, value: str, subtitle: str, accent_color: str = COLOR_ACCENT, **kwargs):
        super().__init__(
            master,
            fg_color=COLOR_CARD_BG,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=8,
            **kwargs
        )

        self.title_lbl = ctk.CTkLabel(
            self,
            text=title.upper(),
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED
        )
        self.title_lbl.pack(anchor="w", padx=14, pady=(10, 2))

        self.value_lbl = ctk.CTkLabel(
            self,
            text=value,
            font=("Segoe UI", 20, "bold"),
            text_color=accent_color
        )
        self.value_lbl.pack(anchor="w", padx=14, pady=(0, 2))

        self.subtitle_lbl = ctk.CTkLabel(
            self,
            text=subtitle,
            font=FONT_SMALL,
            text_color=COLOR_TEXT_SECONDARY
        )
        self.subtitle_lbl.pack(anchor="w", padx=14, pady=(0, 10))

    def update_values(self, value: str, subtitle: str = None):
        self.value_lbl.configure(text=value)
        if subtitle:
            self.subtitle_lbl.configure(text=subtitle)


class ChannelCard(ctk.CTkFrame):
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
        super().__init__(
            master,
            fg_color=COLOR_CARD_BG,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=8,
            **kwargs
        )
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

        # Top row: Channel Name + Status Badge
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=14, pady=(10, 4))

        # Channel Title
        name_lbl = ctk.CTkLabel(
            top_row,
            text=name,
            font=FONT_HEADING,
            text_color=COLOR_TEXT_PRIMARY
        )
        name_lbl.pack(side="left")

        # Master base indicator
        if is_master:
            master_badge = ctk.CTkLabel(
                top_row,
                text="⭐ MASTER BASE",
                font=FONT_SMALL,
                fg_color="#1E3A8A",
                text_color="#93C5FD",
                corner_radius=4,
                padx=6,
                pady=2
            )
            master_badge.pack(side="left", padx=8)

        # Status badge on right
        if link_type == "symlink":
            badge_text = "🔗 SYMBOLIC LINK"
            badge_bg = "#064E3B"
            badge_fg = COLOR_SUCCESS
        elif link_type == "junction":
            badge_text = "🔗 NTFS JUNCTION"
            badge_bg = "#064E3B"
            badge_fg = COLOR_SUCCESS
        elif link_type == "real_dir":
            badge_text = "📁 REAL DIRECTORY"
            badge_bg = "#1E293B"
            badge_fg = COLOR_TEXT_SECONDARY
        else:
            badge_text = "⚪ NOT INSTALLED"
            badge_bg = "#334155"
            badge_fg = COLOR_TEXT_MUTED

        if is_link and not target_exists:
            badge_text = "⚠️ BROKEN LINK"
            badge_bg = "#7F1D1D"
            badge_fg = COLOR_DANGER

        status_badge = ctk.CTkLabel(
            top_row,
            text=badge_text,
            font=FONT_SMALL,
            fg_color=badge_bg,
            text_color=badge_fg,
            corner_radius=4,
            padx=8,
            pady=2
        )
        status_badge.pack(side="right")

        # Detail description row
        detail_frame = ctk.CTkFrame(self, fg_color="transparent")
        detail_frame.pack(fill="x", padx=14, pady=2)

        if is_link:
            target_desc = f"Points to: → {target_raw}"
            if not target_exists:
                target_desc += " (TARGET MISSING!)"
            desc_color = COLOR_ACCENT if target_exists else COLOR_DANGER
        elif is_master:
            pointing_str = ", ".join(symlinks_pointing) if symlinks_pointing else "None"
            target_desc = f"Master source for: {pointing_str}"
            desc_color = "#38BDF8"
        elif link_type == "real_dir":
            target_desc = "Independent standalone directory (not symlinked)"
            desc_color = COLOR_TEXT_MUTED
        else:
            target_desc = "Channel folder does not exist yet"
            desc_color = COLOR_TEXT_MUTED

        desc_lbl = ctk.CTkLabel(
            detail_frame,
            text=target_desc,
            font=FONT_BODY,
            text_color=desc_color
        )
        desc_lbl.pack(anchor="w")

        # Metadata row: Version info & Size
        meta_frame = ctk.CTkFrame(self, fg_color="transparent")
        meta_frame.pack(fill="x", padx=14, pady=(2, 8))

        branch = version_info.get("branch", "")
        ver = version_info.get("version", "")
        if branch or ver:
            v_text = f"Version: {branch} ({ver})" if ver else f"Version: {branch}"
        else:
            v_text = "Version: Unknown / Not Initialized"

        v_lbl = ctk.CTkLabel(
            meta_frame,
            text=v_text,
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED
        )
        v_lbl.pack(side="left")

        size_text = f"~{size_gb} GB" if size_gb > 0 else "--"
        size_lbl = ctk.CTkLabel(
            meta_frame,
            text=f"Disk footprint: {size_text}",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED
        )
        size_lbl.pack(side="right")

        # Divider
        div = ctk.CTkFrame(self, fg_color=COLOR_CARD_BORDER, height=1)
        div.pack(fill="x", padx=14, pady=(0, 8))

        # Bottom Actions row
        actions_row = ctk.CTkFrame(self, fg_color="transparent")
        actions_row.pack(fill="x", padx=14, pady=(0, 10))

        # Link dropdown & Button
        filtered_targets = [t for t in self.available_targets if t != name]
        if not filtered_targets:
            filtered_targets = ["Game", "LIVE"]

        self.target_dropdown = ctk.CTkOptionMenu(
            actions_row,
            values=filtered_targets,
            width=110,
            height=28,
            font=FONT_SMALL,
            fg_color="#1E293B",
            button_color="#334155",
            button_hover_color="#475569"
        )
        # Set default selection
        default_target = "Game" if "Game" in filtered_targets else filtered_targets[0]
        self.target_dropdown.set(default_target)
        self.target_dropdown.pack(side="left", padx=(0, 6))

        link_btn = ctk.CTkButton(
            actions_row,
            text="🔗 Link",
            width=65,
            height=28,
            font=FONT_SMALL,
            fg_color=COLOR_ACCENT_MUTED,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._on_link_clicked
        )
        link_btn.pack(side="left", padx=(0, 6))

        # Unlink button (enabled if currently a link)
        if is_link:
            unlink_btn = ctk.CTkButton(
                actions_row,
                text="✂️ Unlink",
                width=70,
                height=28,
                font=FONT_SMALL,
                fg_color="#450A0A",
                hover_color="#7F1D1D",
                text_color="#FCA5A5",
                command=lambda: self.on_unlink_callback(name)
            )
            unlink_btn.pack(side="left", padx=(0, 6))

        # Open in Explorer button
        if self.channel_data.get("exists", False):
            open_btn = ctk.CTkButton(
                actions_row,
                text="📂 Open",
                width=65,
                height=28,
                font=FONT_SMALL,
                fg_color="#1E293B",
                hover_color="#334155",
                text_color=COLOR_TEXT_SECONDARY,
                command=lambda: self.on_open_callback(self.channel_data.get("path", ""))
            )
            open_btn.pack(side="right")

    def _on_link_clicked(self):
        target = self.target_dropdown.get()
        name = self.channel_data.get("name", "")
        self.on_link_callback(name, target)


class LogConsole(ctk.CTkFrame):
    """Scrollable, color-coded console for application logs and operations."""

    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color="#0A0E17",
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=8,
            **kwargs
        )

        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=10, pady=(6, 2))

        lbl = ctk.CTkLabel(
            header_frame,
            text="ACTIVITY LOG",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED
        )
        lbl.pack(side="left")

        clear_btn = ctk.CTkButton(
            header_frame,
            text="Clear Log",
            width=60,
            height=20,
            font=("Segoe UI", 8),
            fg_color="#1E293B",
            hover_color="#334155",
            command=self.clear
        )
        clear_btn.pack(side="right")

        self.textbox = ctk.CTkTextbox(
            self,
            font=FONT_MONO_SMALL,
            fg_color="#06090F",
            text_color=COLOR_TEXT_SECONDARY,
            wrap="word",
            height=110,
        )
        self.textbox.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def log(self, text: str):
        self.textbox.configure(state="normal")
        self.textbox.insert("end", f"{text}\n")
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("1.0", "end")
        self.textbox.configure(state="disabled")
