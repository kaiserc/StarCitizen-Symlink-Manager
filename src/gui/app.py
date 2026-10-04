"""
app.py - Main GUI application for Star Citizen Symlink Manager.
"""

import os
import re
import sys
import subprocess
import threading
from tkinter import filedialog, messagebox
import customtkinter as ctk

from src.core.detector import (
    detect_all_sc_installations,
    detect_rsi_launcher_exe,
    get_drive_info,
    is_valid_sc_dir,
)
from src.core.symlink_ops import (
    is_admin,
    restart_as_admin,
    create_link_auto,
    safe_unlink,
    safe_rename,
)
from src.core.channel_mgr import (
    STANDARD_CHANNELS,
    scan_all_channels,
    calculate_storage_stats,
    apply_reddit_preset,
    apply_independent_live_preset,
    apply_direct_live_preset,
)
from src.core.keybind_mgr import (
    backup_controls,
    restore_controls,
    list_backups,
    discover_control_files,
)
from src.core.shader_mgr import (
    inspect_shader_caches,
    clear_shader_caches,
    clean_user_cache_safe,
)
from src.core.process_guard import (
    get_running_sc_processes,
)

from . import assets
from .theme import (
    COLOR_BG_DARK,
    COLOR_BG_SIDEBAR,
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
    COLOR_SUCCESS,
    COLOR_SUCCESS_BG,
    COLOR_WARNING,
    COLOR_WARNING_BG,
    COLOR_DANGER,
    COLOR_TEXT_PRIMARY,
    COLOR_TEXT_SECONDARY,
    COLOR_TEXT_MUTED,
    FONT_BRAND_FAMILY,
    FONT_HEADING_FAMILY,
    FONT_DISPLAY_FAMILY,
    FONT_UI_FAMILY,
    FONT_MONO_FAMILY,
    FONT_TITLE,
    FONT_SUBTITLE,
    FONT_TAB,
    FONT_HEADING,
    FONT_SUBHEADING,
    FONT_SECTION,
    FONT_METRIC,
    FONT_BODY,
    FONT_BODY_BOLD,
    FONT_SMALL,
    FONT_SMALL_BOLD,
    FONT_CHIP,
    FONT_BTN,
    FONT_MONO,
    FONT_MONO_SMALL,
)
from .components import (
    StorageMetricCard,
    ChannelCard,
    LogConsole,
    HudPanel,
    SectionLabel,
    hud_button,
    badge,
    add_tip,
)
from .tooltip import Tooltip, TooltipManager

# Register bundled fonts before any widgets are created.
assets.load_fonts()

HEADER_HEIGHT = 100


class SCSymlinkManagerApp(ctk.CTk):
    """Star Citizen Symlink Manager main window."""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("Star Citizen Symlink Manager")
        self.geometry("1160x880")
        self.minsize(1040, 720)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COLOR_BG_DARK)
        if os.path.isfile(assets.APP_ICON_PATH):
            try:
                self.iconbitmap(assets.APP_ICON_PATH)
            except Exception:
                pass

        # State
        self.sc_root = ""
        self.channels_data = {}
        self.backups_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "backups")
        )
        os.makedirs(self.backups_dir, exist_ok=True)

        self.prefer_symlink = is_admin()  # Auto-prefer symlink if elevated

        self._build_layout()
        TooltipManager.register_root(self)
        self._initial_detect()

    def _build_layout(self):
        # 1. Top Header (art banner)
        self._build_header()

        # 5. Footer (packed early with side=bottom so it always stays visible)
        self._build_footer()

        # 4. Activity Log Console (bottom, collapsible)
        self.console = LogConsole(self)
        self.console.pack(side="bottom", fill="x", padx=16, pady=(0, 6))

        # 2. Path Selector Bar + status strip
        self._build_path_bar()

        # 3. Main Content Tabs
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=COLOR_BG_DARK,
            corner_radius=6,
            border_width=0,
            segmented_button_fg_color=COLOR_BG_SIDEBAR,
            segmented_button_selected_color=COLOR_ACCENT_MUTED,
            segmented_button_selected_hover_color=COLOR_ACCENT_HOVER,
            segmented_button_unselected_color=COLOR_BG_SIDEBAR,
            segmented_button_unselected_hover_color=COLOR_BTN_HOVER,
            text_color=COLOR_TEXT_PRIMARY,
            command=lambda: TooltipManager.hide(),
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(0, 6))
        self.tabview._segmented_button.configure(font=FONT_TAB, height=42)

        self.tab_channels = self.tabview.add("  CHANNELS & STORAGE  ")
        self.tab_controls = self.tabview.add("  CONTROLS & KEYBINDS  ")
        self.tab_shaders = self.tabview.add("  SHADERS & CACHE  ")
        self.tab_guide = self.tabview.add("  HOW IT WORKS  ")

        self._build_channels_tab()
        self._build_controls_tab()
        self._build_shaders_tab()
        self._build_guide_tab()

    # --- HEADER ---------------------------------------------------------------
    def _build_header(self):
        bg_path = assets.header_background_path()
        header_bg = self._sample_left_color(bg_path) or COLOR_BG_SIDEBAR

        header_frame = ctk.CTkFrame(self, fg_color=header_bg, height=HEADER_HEIGHT, corner_radius=0)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        # Background art, anchored right so the planet/nebula stays visible at any width
        self._header_img = assets.load_cover_image(bg_path, (1500, HEADER_HEIGHT), fade_left_to=header_bg)
        if self._header_img:
            ctk.CTkLabel(header_frame, text="", image=self._header_img, fg_color=header_bg).place(
                relx=1.0, rely=0, anchor="ne")

        # Bottom cyan hairline
        ctk.CTkFrame(header_frame, fg_color=COLOR_ACCENT_MUTED, height=1, corner_radius=0).place(
            relx=0, rely=1.0, relwidth=1.0, anchor="sw")

        content = ctk.CTkFrame(header_frame, fg_color=header_bg)
        content.place(x=18, rely=0.5, anchor="w")

        self._emblem_img = assets.load_image(assets.emblem_path(), (58, 58))
        if self._emblem_img:
            ctk.CTkLabel(content, text="", image=self._emblem_img, fg_color=header_bg).pack(
                side="left", padx=(0, 14))

        title_box = ctk.CTkFrame(content, fg_color=header_bg)
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="STAR CITIZEN  //  SYMLINK MANAGER",
            font=FONT_TITLE,
            text_color=COLOR_TEXT_PRIMARY,
            fg_color=header_bg,
        ).pack(anchor="w")

        ctk.CTkLabel(
            title_box,
            text="Play LIVE, PTU, EPTU & Tech-Preview from a single install",
            font=FONT_SUBTITLE,
            text_color=COLOR_ACCENT,
            fg_color=header_bg,
        ).pack(anchor="w")

        # StreamDock-style HUD status & Global Action Controls (right side of header)
        self.right_header = ctk.CTkFrame(header_frame, fg_color="transparent")
        self.right_header.place(relx=0.985, rely=0.5, anchor="e")

        # 1. Unified Storage Efficiency KPI Chip
        self.chip_storage = ctk.CTkFrame(
            self.right_header,
            fg_color=COLOR_CARD_BG,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=4,
        )
        self.chip_storage.pack(side="left", padx=(0, 10))
        self.c1_dot = ctk.CTkFrame(self.chip_storage, fg_color=COLOR_ACCENT, width=8, height=8, corner_radius=4)
        self.c1_dot.pack(side="left", padx=(10, 8), pady=10)
        c1_txt = ctk.CTkFrame(self.chip_storage, fg_color="transparent")
        c1_txt.pack(side="left", padx=(0, 14), pady=4)
        self.chip_storage_lbl = ctk.CTkLabel(c1_txt, text="CHANNELS", font=FONT_CHIP, text_color=COLOR_TEXT_PRIMARY)
        self.chip_storage_lbl.pack(anchor="w")
        self.chip_storage_sub = ctk.CTkLabel(c1_txt, text="DETECTING...", font=FONT_MONO_SMALL, text_color=COLOR_TEXT_MUTED)
        self.chip_storage_sub.pack(anchor="w")
        add_tip(self.chip_storage, "metric_saved", extra_widgets=(self.c1_dot, c1_txt, self.chip_storage_lbl, self.chip_storage_sub))

        # 2. Elevation Action / Status
        if not is_admin():
            hud_button(self.right_header, "⚡ Elevate to Admin", self._on_elevate, variant="gold",
                       tip_key="elevate", width=145, height=38).pack(side="left", padx=(0, 8))
        else:
            b = badge(self.right_header, "● ADMINISTRATOR", COLOR_SUCCESS, COLOR_SUCCESS_BG,
                      "admin_badge_admin")
            b.pack(side="left", padx=(0, 8))

        # 3. Global Launcher Action
        hud_button(self.right_header, "Open RSI Launcher  ↗", self._launch_rsi, variant="secondary",
                   tip_key="launch_rsi", width=165, height=38).pack(side="left")

    @staticmethod
    def _sample_left_color(path):
        """Average colour of the banner's left edge so overlaid widgets blend seamlessly."""
        if not path:
            return None
        try:
            from PIL import Image
            img = Image.open(path).convert("RGB")
            strip = img.crop((0, 0, max(1, img.width // 20), img.height)).resize((1, 1))
            r, g, b = strip.getpixel((0, 0))
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return None

    # --- FOOTER ---------------------------------------------------------------
    def _build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=COLOR_BG_SIDEBAR, corner_radius=0, height=34)
        footer.pack(side="bottom", fill="x")

        self._community_img = assets.load_image(assets.community_badge_path(), (70, 20))
        if self._community_img:
            ctk.CTkLabel(footer, text="", image=self._community_img).pack(side="left", padx=(14, 8), pady=4)

        notice = ctk.CTkLabel(
            footer,
            text="Unofficial community tool  ·  Not affiliated with Cloud Imperium Games",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED,
        )
        notice.pack(side="left", padx=(14 if not self._community_img else 0, 0))
        Tooltip(notice, "Trademark Notice", assets.FANKIT_NOTICE)

        mode = "Symlink mode (Elevated)" if self.prefer_symlink else "Junction mode (Standard)"
        mode_lbl = ctk.CTkLabel(footer, text=mode, font=FONT_SMALL, text_color=COLOR_TEXT_MUTED)
        mode_lbl.pack(side="right", padx=14)
        add_tip(mode_lbl, "admin_badge_admin" if self.prefer_symlink else "admin_badge_user")

    # --- PATH BAR -------------------------------------------------------------
    def _build_path_bar(self):
        path_box = HudPanel(self)
        path_box.pack(fill="x", padx=16, pady=(12, 8))

        # Top row: path label + input + browse + detect
        top_row = ctk.CTkFrame(path_box, fg_color="transparent")
        top_row.pack(fill="x", padx=(18, 14), pady=(12, 4))

        lbl = ctk.CTkLabel(top_row, text="INSTALL FOLDER", font=FONT_SECTION, text_color=COLOR_TEXT_SECONDARY)
        lbl.pack(side="left", padx=(0, 10))
        add_tip(lbl, "path_entry")

        self.path_entry = ctk.CTkEntry(
            top_row,
            font=FONT_MONO,
            fg_color=COLOR_BG_INPUT,
            text_color=COLOR_TEXT_PRIMARY,
            border_color=COLOR_CARD_BORDER,
            corner_radius=4,
            placeholder_text="e.g. C:\\Program Files\\Roberts Space Industries\\StarCitizen",
            height=38
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.path_entry.bind("<Return>", lambda e: self._on_path_changed())
        add_tip(self.path_entry, "path_entry")

        hud_button(top_row, "Auto-Detect", self._on_auto_detect, variant="primary",
                   tip_key="auto_detect", width=115, height=38).pack(side="left", padx=(0, 6))
        hud_button(top_row, "Browse…", self._on_browse, tip_key="browse", width=95, height=38).pack(side="left", padx=(0, 6))
        hud_button(top_row, "Open", lambda: self._open_in_explorer(self.sc_root),
                   tip_key="open_root", width=75, height=38).pack(side="left", padx=(0, 6))
        hud_button(top_row, "⟳", self._refresh_all, tip_key="refresh", width=40, height=38,
                   font=(FONT_UI_FAMILY, 15, "bold")).pack(side="left")

        # Bottom row: drive info (clean, full width, with drive status)
        bottom_row = ctk.CTkFrame(path_box, fg_color="transparent")
        bottom_row.pack(fill="x", padx=(18, 14), pady=(4, 10))

        self.drive_info_lbl = ctk.CTkLabel(
            bottom_row,
            text="Drive status: Detecting...",
            font=FONT_BODY,
            text_color=COLOR_TEXT_MUTED
        )
        self.drive_info_lbl.pack(side="left")
        add_tip(self.drive_info_lbl, "drive_info")

    # --- TAB 1: CHANNELS & STORAGE ---
    def _build_channels_tab(self):
        tab = self.tab_channels

        # 1. Storage Metric Cards row
        metrics_frame = ctk.CTkFrame(tab, fg_color="transparent")
        metrics_frame.pack(fill="x", pady=(4, 10))

        self.metric_used = StorageMetricCard(
            metrics_frame,
            title="Physical Disk Used",
            value="-- GB",
            subtitle="Actual SSD space consumed",
            accent_color=COLOR_TEXT_PRIMARY,
            tip_key="metric_used",
        )
        self.metric_used.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.metric_channels = StorageMetricCard(
            metrics_frame,
            title="Channels Active",
            value="--",
            subtitle="Playable in RSI Launcher",
            accent_color=COLOR_ACCENT,
            tip_key="metric_channels",
        )
        self.metric_channels.pack(side="left", fill="x", expand=True, padx=3)

        self.metric_saved = StorageMetricCard(
            metrics_frame,
            title="SSD Space Saved",
            value="-- GB",
            subtitle="Saved via Symlinks & Junctions",
            accent_color=COLOR_SUCCESS,
            tip_key="metric_saved",
        )
        self.metric_saved.pack(side="left", fill="x", expand=True, padx=(6, 0))

        # 2. Presets Action Bar
        SectionLabel(tab, "Quick Presets", help_key="preset_backup_note").pack(fill="x", pady=(0, 6))

        btn_row = ctk.CTkFrame(tab, fg_color="transparent")
        btn_row.pack(fill="x", pady=(0, 12))

        hud_button(btn_row, "★  Reddit Method · Unified Base", self._apply_reddit_preset,
                   variant="gold", tip_key="preset_reddit", height=40).pack(side="left", padx=(0, 8))
        hud_button(btn_row, "Independent LIVE + Shared Test", self._apply_independent_preset,
                   tip_key="preset_independent", height=40).pack(side="left", padx=(0, 8))
        hud_button(btn_row, "Direct Link to LIVE", self._apply_direct_preset,
                   tip_key="preset_direct", height=40).pack(side="left", padx=(0, 8))
        hud_button(btn_row, "+  Custom Channel", self._on_add_custom_channel, variant="primary",
                   tip_key="preset_custom", height=40).pack(side="right")

        # 3. Scrollable Channels List
        SectionLabel(tab, "Channel Directories").pack(fill="x", pady=(0, 4))
        self.channels_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color="transparent",
            scrollbar_button_color=COLOR_BTN,
            scrollbar_button_hover_color=COLOR_BTN_HOVER,
        )
        self.channels_scroll.pack(fill="both", expand=True)

    # --- TAB 2: CONTROLS & KEYBINDS ---
    def _build_controls_tab(self):
        tab = self.tab_controls

        banner = HudPanel(tab, accent=COLOR_SUCCESS)
        banner.pack(fill="x", pady=(4, 10))

        b_content = ctk.CTkFrame(banner, fg_color="transparent")
        b_content.pack(fill="x", padx=(18, 14), pady=14)

        ctk.CTkLabel(b_content, text="HOTAS, HOSAS & Keybinding Protection", font=FONT_HEADING, text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(
            b_content,
            text="Snapshot your joystick mappings, actionmaps.xml and character presets before verifying or wiping a channel.",
            font=FONT_BODY,
            text_color=COLOR_TEXT_SECONDARY,
            wraplength=920,
            justify="left",
        ).pack(anchor="w", pady=(4, 12))

        btn_row = ctk.CTkFrame(b_content, fg_color="transparent")
        btn_row.pack(fill="x")

        hud_button(btn_row, "Backup Controls Now", self._backup_controls_now, variant="success",
                   tip_key="backup_controls", height=40).pack(side="left", padx=(0, 8))
        hud_button(btn_row, "Restore Latest Backup…", self._restore_controls_dialog,
                   tip_key="restore_controls", height=40).pack(side="left")

        # Backup History Box
        SectionLabel(tab, "Backup History").pack(fill="x", pady=(0, 4))
        self.backups_scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent",
            scrollbar_button_color=COLOR_BTN, scrollbar_button_hover_color=COLOR_BTN_HOVER,
        )
        self.backups_scroll.pack(fill="both", expand=True)
        self._refresh_backups_list()

    # --- TAB 3: SHADER & CACHE ---
    def _build_shaders_tab(self):
        tab = self.tab_shaders

        banner = HudPanel(tab, accent=COLOR_ACCENT)
        banner.pack(fill="x", pady=(4, 10))

        b_content = ctk.CTkFrame(banner, fg_color="transparent")
        b_content.pack(fill="x", padx=(18, 14), pady=14)

        ctk.CTkLabel(b_content, text="Shader Cache & USER Data Cleaner", font=FONT_HEADING, text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(
            b_content,
            text="Stale shaders left over from another channel are the #1 cause of glitches and crashes after switching. "
                 "Caches rebuild automatically on next launch.",
            font=FONT_BODY,
            text_color=COLOR_TEXT_SECONDARY,
            wraplength=920,
            justify="left",
        ).pack(anchor="w", pady=(4, 12))

        btn_row = ctk.CTkFrame(b_content, fg_color="transparent")
        btn_row.pack(fill="x")

        hud_button(btn_row, "Clean Old Shaders", lambda: self._clean_shaders(keep_latest=True),
                   variant="primary", tip_key="clean_old_shaders", height=40).pack(side="left", padx=(0, 8))
        hud_button(btn_row, "Safe Purge USER Cache", self._clean_user_cache_dialog,
                   tip_key="safe_user_purge", height=40).pack(side="left", padx=(0, 8))
        hud_button(btn_row, "Wipe All Shaders", lambda: self._clean_shaders(keep_latest=False),
                   variant="danger", tip_key="wipe_shaders", height=40).pack(side="right")

        # Scrollable list of detected shader caches
        SectionLabel(tab, "Detected caches in %LOCALAPPDATA%\\Star Citizen").pack(fill="x", pady=(0, 4))
        self.shaders_scroll = ctk.CTkScrollableFrame(
            tab, fg_color="transparent",
            scrollbar_button_color=COLOR_BTN, scrollbar_button_hover_color=COLOR_BTN_HOVER,
        )
        self.shaders_scroll.pack(fill="both", expand=True)
        self._refresh_shaders_list()

    # --- TAB 4: HOW-TO & GUIDE ---
    def _build_guide_tab(self):
        tab = self.tab_guide

        guide_text = """# How symbolic links save hundreds of gigabytes

### The problem
Star Citizen client installations are massive (100 GB to 150 GB+ each). With channels like **LIVE**, **PTU**, **EPTU** and **TECH-PREVIEW**, keeping all of them installed independently needs 400 - 600 GB+ of fast SSD space.

However, **90% to 95% of Star Citizen assets (Data.p4k, textures, audio) are identical** between channels!

### The solution: symbolic links / NTFS junctions
Instead of duplicating 150 GB four times:
1. One master folder (named `Game` or `LIVE`) holds the actual ~150 GB of game data.
2. The other channels (`PTU`, `EPTU`, `TECH-PREVIEW`, `HOTFIX`) are **links** pointing to that master folder.
3. Windows presents each link to the RSI Launcher as an independent folder, but under the hood they all share the exact same SSD blocks.

### How to play & switch channels
1. Configure your channels with this manager (e.g. click **Reddit Method · Unified Base**).
2. Open the **RSI Launcher**.
3. Select whichever channel you want to play (e.g. **EPTU**).
4. Click **Verify Files** (or Update) - only the delta is downloaded (usually 2 - 8 GB instead of 150 GB).
5. Click **Launch Game**.
6. To switch back, pick the other channel in the launcher and **Verify** again.

### Safety & controls protection
- **Never lose keybindings:** use the **Controls & Keybinds** tab for a 1-click backup of joystick layouts and actionmaps.
- **Safe unlinking:** unlinking only removes the link entry itself - it **never deletes files** inside your real game folder.
- **Real folders are kept:** presets rename existing real folders to `NAME_backup_<timestamp>` instead of deleting them.
- **NTFS required:** links need an NTFS or ReFS drive (FAT32 / exFAT is not supported).

### Tip
Hover over any button, badge or metric in this app to see what it does.
"""
        textbox = ctk.CTkTextbox(
            tab,
            font=FONT_BODY,
            fg_color=COLOR_CARD_BG,
            border_color=COLOR_CARD_BORDER,
            border_width=1,
            corner_radius=6,
            text_color=COLOR_TEXT_SECONDARY,
            wrap="word",
            scrollbar_button_color=COLOR_BTN,
        )
        textbox.pack(fill="both", expand=True, padx=2, pady=(4, 2))
        self._render_markdown(textbox, guide_text)
        textbox.configure(state="disabled")

    @staticmethod
    def _render_markdown(textbox: ctk.CTkTextbox, md: str):
        """Minimal markdown renderer (headings, bold, inline code, lists) for the guide tab."""
        tb = textbox._textbox  # raw tk.Text: CTk forbids 'font' in tag_config
        try:
            scale = ctk.ScalingTracker.get_widget_scaling(textbox)
        except Exception:
            scale = 1.0
        px = lambda s: -int(round(s * scale))
        tb.configure(padx=28, pady=20, spacing1=4, spacing3=4)
        tb.tag_configure("h1", font=(FONT_HEADING_FAMILY, px(26), "bold"), foreground=COLOR_TEXT_PRIMARY, spacing3=14)
        tb.tag_configure("h3", font=(FONT_HEADING_FAMILY, px(18), "bold"), foreground=COLOR_ACCENT, spacing1=20, spacing3=8)
        tb.tag_configure("bold", font=(FONT_UI_FAMILY, px(14), "bold"), foreground=COLOR_TEXT_PRIMARY)
        tb.tag_configure("code", font=(FONT_MONO_FAMILY, px(13)), foreground=COLOR_GOLD, background=COLOR_BG_INPUT)
        tb.tag_configure("list", lmargin1=14, lmargin2=32)
        tb.tag_configure("bullet", foreground=COLOR_ACCENT)

        inline = re.compile(r"(\*\*.+?\*\*|`.+?`)")
        for raw in md.strip().splitlines():
            line = raw.rstrip()
            if line.startswith("# "):
                tb.insert("end", line[2:] + "\n", "h1")
                continue
            if line.startswith("### "):
                tb.insert("end", line[4:].upper() + "\n", "h3")
                continue

            base_tags = ()
            m = re.match(r"^(\d+\.|-)\s+(.*)$", line)
            if m:
                marker = "▸ " if m.group(1) == "-" else f"{m.group(1)} "
                tb.insert("end", marker, ("list", "bullet"))
                line = m.group(2)
                base_tags = ("list",)

            for part in inline.split(line):
                if not part:
                    continue
                if part.startswith("**") and part.endswith("**"):
                    tb.insert("end", part[2:-2], base_tags + ("bold",))
                elif part.startswith("`") and part.endswith("`"):
                    tb.insert("end", f" {part[1:-1]} ", base_tags + ("code",))
                else:
                    tb.insert("end", part, base_tags)
            tb.insert("end", "\n", base_tags)

    # --- Core Logic & Handlers ---

    def _initial_detect(self):
        """Auto-detects installation on startup."""
        installs = detect_all_sc_installations()
        if installs:
            self.sc_root = installs[0]
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, self.sc_root)
            self.console.log(f"[DETECT] Found Star Citizen installation at: {self.sc_root}")
            self._refresh_all()
        else:
            self.console.log("[INFO] No Star Citizen installation auto-detected. Click 'Browse...' to locate your install folder.")
            self._render_channel_cards()

    def _refresh_all(self):
        """Refreshes path validation, drive info, channels, and metrics."""
        path = self.path_entry.get().strip()
        if not path or not os.path.isdir(path):
            self.drive_info_lbl.configure(text="Drive status: Invalid or unselected directory path.",
                                          text_color=COLOR_WARNING)
            return

        self.sc_root = os.path.normpath(path)

        # Drive Info
        d_info = get_drive_info(self.sc_root)
        fs_type = d_info.get("fs_type", "Unknown")
        free_gb = d_info.get("free_gb", 0)
        total_gb = d_info.get("total_gb", 0)
        drive_str = f"Volume {d_info.get('drive')}  ·  {fs_type}  ·  {free_gb} GB free of {total_gb} GB"
        color = COLOR_TEXT_MUTED
        if str(fs_type).upper() not in ("NTFS", "REFS"):
            drive_str += "  ·  ⚠ links require NTFS/ReFS"
            color = COLOR_WARNING

        # Check running processes
        procs = get_running_sc_processes()
        if procs:
            proc_names = ", ".join(set(p["name"] for p in procs))
            drive_str += f"  ·  ⚠ Running: {proc_names}"
            color = COLOR_WARNING

        self.drive_info_lbl.configure(text=drive_str, text_color=color)

        # Scan Channels
        self.channels_data = scan_all_channels(self.sc_root)

        # Update Metrics
        stats = calculate_storage_stats(self.channels_data)
        self.metric_used.update_values(f"{stats['physical_used_gb']} GB")
        self.metric_channels.update_values(f"{stats['active_channels']}", f"{stats['symlink_count']} linked  ·  playable in launcher")
        self.metric_saved.update_values(f"~{stats['saved_gb']} GB", f"Without links: {stats['virtual_total_gb']} GB")

        # Update Header HUD Status Chip
        if hasattr(self, "chip_storage_lbl") and hasattr(self, "chip_storage_sub"):
            self.chip_storage_lbl.configure(text=f"{stats['active_channels']} CHANNELS ACTIVE")
            self.chip_storage_sub.configure(text=f"~{stats['saved_gb']} GB SAVED")

        # Populate Channels Grid
        self._render_channel_cards()

    def _render_channel_cards(self):
        TooltipManager.hide()
        # Clear existing cards
        for widget in self.channels_scroll.winfo_children():
            widget.destroy()

        if not self.channels_data:
            self._empty_state(
                self.channels_scroll,
                "No channels found",
                "Select your StarCitizen folder above, then use a preset or '+ Custom Channel' to create your first link.",
            )
            return

        # Available target folders for linking (folders that exist)
        available_targets = [
            name for name, ch in self.channels_data.items()
            if ch["exists"]
        ]
        if "Game" not in available_targets:
            available_targets.append("Game")
        if "LIVE" not in available_targets:
            available_targets.append("LIVE")

        for name, data in self.channels_data.items():
            card = ChannelCard(
                self.channels_scroll,
                channel_data=data,
                available_targets=available_targets,
                on_link_callback=self._on_link_channel,
                on_unlink_callback=self._on_unlink_channel,
                on_open_callback=self._open_in_explorer
            )
            card.pack(fill="x", pady=4, padx=2)

    @staticmethod
    def _empty_state(parent, title: str, body: str):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        box.pack(fill="x", pady=30)
        ctk.CTkLabel(box, text=title.upper(), font=FONT_SECTION, text_color=COLOR_TEXT_SECONDARY).pack()
        ctk.CTkLabel(box, text=body, font=FONT_BODY, text_color=COLOR_TEXT_MUTED, wraplength=560).pack(pady=(4, 0))

    def _on_link_channel(self, channel_name: str, target_name: str):
        """Creates or updates a link for a specific channel."""
        if not self.sc_root:
            return

        # Check process lock
        procs = get_running_sc_processes()
        if any("starcitizen" in p["name"].lower() for p in procs):
            if not messagebox.askyesno(
                "Star Citizen Running",
                "Star Citizen is currently running! Creating or modifying links while the game is open can cause file locks. Do you want to proceed anyway?"
            ):
                return

        target_path = os.path.join(self.sc_root, target_name)
        link_path = os.path.join(self.sc_root, channel_name)

        if not os.path.exists(target_path):
            messagebox.showerror("Error", f"Target folder '{target_name}' does not exist.")
            return

        # If channel already exists as a link, unlink it first
        if os.path.islink(link_path) or (channel_name in self.channels_data and self.channels_data[channel_name]["is_link"]):
            safe_unlink(link_path)

        ok, ltype, msg = create_link_auto(target_path, link_path, prefer_symlink=self.prefer_symlink)
        if ok:
            self.console.log(f"[SUCCESS] Linked '{channel_name}' -> '{target_name}' ({ltype}).")
            self._refresh_all()
        else:
            self.console.log(f"[FAILED] Could not link '{channel_name}': {msg}")
            messagebox.showerror("Linking Failed", msg)

    def _on_unlink_channel(self, channel_name: str):
        """Safely removes a channel symlink."""
        link_path = os.path.join(self.sc_root, channel_name)
        if not messagebox.askyesno(
            "Confirm Unlink",
            f"Are you sure you want to remove the link for '{channel_name}'?\n\n(Note: Files in the target directory will NOT be deleted.)"
        ):
            return

        ok, msg = safe_unlink(link_path)
        if ok:
            self.console.log(f"[SUCCESS] {msg}")
            self._refresh_all()
        else:
            self.console.log(f"[ERROR] {msg}")
            messagebox.showerror("Unlink Error", msg)

    # --- Preset Actions ---

    def _apply_reddit_preset(self):
        if not self.sc_root:
            messagebox.showwarning("Notice", "Please select your Star Citizen directory first.")
            return

        confirm = messagebox.askyesno(
            "Apply Reddit Method (Unified Base)",
            "This preset will:\n"
            "1. Establish 'Game' as the master base directory (renaming 'LIVE' if necessary).\n"
            "2. Link LIVE, PTU, EPTU, TECH-PREVIEW, and HOTFIX to 'Game'.\n"
            "3. Allow playing all channels using only ~150GB total SSD space.\n\n"
            "Do you want to proceed?"
        )
        if not confirm:
            return

        self.console.log("[PRESET] Applying Reddit Method (Unified Game Base)...")
        def task():
            logs = apply_reddit_preset(self.sc_root, prefer_symlink=self.prefer_symlink)
            self.after(0, lambda: self._on_preset_done(logs))
        threading.Thread(target=task, daemon=True).start()

    def _apply_independent_preset(self):
        if not self.sc_root:
            messagebox.showwarning("Notice", "Please select your Star Citizen directory first.")
            return

        confirm = messagebox.askyesno(
            "Apply Independent LIVE + Shared Test",
            "This preset keeps 'LIVE' as an independent standalone directory (so you never need to re-verify for live raids),\n"
            "and links all test channels (EPTU, TECH-PREVIEW, HOTFIX) to 'PTU'.\n\n"
            "Do you want to proceed?"
        )
        if not confirm:
            return

        self.console.log("[PRESET] Applying Independent LIVE + Shared Test preset...")
        def task():
            logs = apply_independent_live_preset(self.sc_root, prefer_symlink=self.prefer_symlink)
            self.after(0, lambda: self._on_preset_done(logs))
        threading.Thread(target=task, daemon=True).start()

    def _apply_direct_preset(self):
        if not self.sc_root:
            messagebox.showwarning("Notice", "Please select your Star Citizen directory first.")
            return

        confirm = messagebox.askyesno(
            "Apply Direct Link to LIVE",
            "This preset sets 'LIVE' as the master folder, and links PTU, EPTU, TECH-PREVIEW, and HOTFIX directly to LIVE.\n\n"
            "Do you want to proceed?"
        )
        if not confirm:
            return

        self.console.log("[PRESET] Applying Direct Link to LIVE...")
        def task():
            logs = apply_direct_live_preset(self.sc_root, prefer_symlink=self.prefer_symlink)
            self.after(0, lambda: self._on_preset_done(logs))
        threading.Thread(target=task, daemon=True).start()

    def _on_preset_done(self, logs):
        for line in logs:
            self.console.log(line)
        self._refresh_all()

    def _on_add_custom_channel(self):
        """Prompt dialog to add custom channel name (e.g. 4.0_PREVIEW)."""
        dialog = ctk.CTkInputDialog(
            text="Enter custom channel name (e.g. 4.0_PREVIEW, BAR_CITIZEN):",
            title="Add Custom Channel"
        )
        channel_name = dialog.get_input()
        if not channel_name:
            return

        channel_name = channel_name.strip()
        # Reject path separators / traversal so the link is always created inside sc_root
        if not channel_name or re.search(r'[\\/:*?"<>|]', channel_name) or channel_name in (".", ".."):
            messagebox.showerror("Invalid Name", "Channel names can't contain \\ / : * ? \" < > |")
            return
        target_name = "Game" if "Game" in self.channels_data else "LIVE"
        self._on_link_channel(channel_name, target_name)

    # --- Controls & Backup Handlers ---

    def _backup_controls_now(self):
        if not self.sc_root:
            messagebox.showwarning("Notice", "Please select your Star Citizen directory first.")
            return

        self.console.log("[BACKUP] Backing up keybinding and control files...")
        ok, msg, manifest = backup_controls(self.sc_root, self.backups_dir)
        if ok:
            self.console.log(f"[SUCCESS] {msg}")
            messagebox.showinfo("Backup Succeeded", msg)
            self._refresh_backups_list()
        else:
            self.console.log(f"[ERROR] {msg}")
            messagebox.showerror("Backup Failed", msg)

    def _refresh_backups_list(self):
        TooltipManager.hide()
        for widget in self.backups_scroll.winfo_children():
            widget.destroy()

        backups = list_backups(self.backups_dir)
        if not backups:
            self._empty_state(
                self.backups_scroll,
                "No backups yet",
                "Click 'Backup Controls Now' above to snapshot your keybinds and HOTAS mappings.",
            )
            return

        for b in backups:
            card = HudPanel(self.backups_scroll, accent=COLOR_SUCCESS)
            card.pack(fill="x", pady=4, padx=2)

            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", padx=(18, 14), pady=10)

            ctk.CTkLabel(left, text=b["filename"], font=FONT_SUBHEADING, text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkLabel(
                left,
                text=f"{b['file_count']} files  ·  {b['size_kb']} KB  ·  {b['created_at']}",
                font=FONT_SMALL,
                text_color=COLOR_TEXT_MUTED
            ).pack(anchor="w", pady=(2, 0))

            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(side="right", padx=14, pady=10)

            hud_button(actions, "Restore…", lambda p=b["path"]: self._restore_specific_backup(p),
                       variant="primary", tip_key="backup_restore", width=90, height=32).pack(side="left", padx=4)
            hud_button(actions, "Show ZIP", lambda p=b["path"]: self._open_in_explorer(p),
                       variant="ghost", tip_key="backup_open", width=84, height=32).pack(side="left")

    def _ask_channel(self, title: str, prompt: str, channels):
        """Modal dropdown dialog for picking a channel. Returns the name or None."""
        result = {"value": None}
        dlg = ctk.CTkToplevel(self)
        dlg.title(title)
        dlg.configure(fg_color=COLOR_CARD_BG)
        dlg.resizable(False, False)
        dlg.transient(self)

        ctk.CTkLabel(dlg, text=prompt, font=FONT_BODY, text_color=COLOR_TEXT_PRIMARY,
                     wraplength=340, justify="left").pack(padx=20, pady=(18, 10), anchor="w")
        menu = ctk.CTkOptionMenu(
            dlg, values=channels, width=300, corner_radius=4, font=FONT_BODY,
            fg_color=COLOR_BG_INPUT, button_color=COLOR_BTN, button_hover_color=COLOR_BTN_HOVER,
            dropdown_fg_color=COLOR_CARD_BG, dropdown_hover_color=COLOR_ACCENT_GLOW,
        )
        menu.set(channels[0])
        menu.pack(padx=20, pady=(0, 16))

        row = ctk.CTkFrame(dlg, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 18))

        def ok():
            result["value"] = menu.get()
            dlg.destroy()

        hud_button(row, "Cancel", dlg.destroy, variant="ghost", width=80).pack(side="right")
        hud_button(row, "Restore", ok, variant="primary", width=90).pack(side="right", padx=(0, 6))

        dlg.after(50, lambda: (dlg.grab_set(), dlg.focus_force()))
        dlg.bind("<Return>", lambda e: ok())
        dlg.bind("<Escape>", lambda e: dlg.destroy())
        self.wait_window(dlg)
        return result["value"]

    def _restore_specific_backup(self, zip_path: str):
        # Choose target channel
        channels = [name for name, ch in self.channels_data.items() if ch["exists"]]
        if not channels:
            channels = ["Game", "LIVE"]

        target_ch = self._ask_channel(
            "Restore Keybindings",
            f"Restore '{os.path.basename(zip_path)}' into which channel?\n"
            "Files with the same name will be overwritten.",
            channels,
        )
        if not target_ch:
            return

        dest_dir = os.path.join(self.sc_root, target_ch.strip())
        ok, msg = restore_controls(zip_path, dest_dir)
        if ok:
            self.console.log(f"[RESTORE] {msg} -> {target_ch}")
            messagebox.showinfo("Restore Succeeded", f"{msg} to '{target_ch}'.")
        else:
            self.console.log(f"[ERROR] {msg}")
            messagebox.showerror("Restore Failed", msg)

    def _restore_controls_dialog(self):
        backups = list_backups(self.backups_dir)
        if not backups:
            messagebox.showinfo("No Backups", "No backups found yet. Create a backup first!")
            return
        self._restore_specific_backup(backups[0]["path"])

    # --- Shaders & Cache Handlers ---

    def _refresh_shaders_list(self):
        TooltipManager.hide()
        for widget in self.shaders_scroll.winfo_children():
            widget.destroy()

        caches = inspect_shader_caches()
        if not caches:
            self._empty_state(
                self.shaders_scroll,
                "No shader caches found",
                "Nothing to clean in %LOCALAPPDATA%\\Star Citizen.",
            )
            return

        total_mb = sum(c["size_mb"] for c in caches)
        header_card = HudPanel(self.shaders_scroll, accent=COLOR_ACCENT)
        header_card.pack(fill="x", pady=4, padx=2)

        ctk.CTkLabel(
            header_card,
            text=f"{len(caches)} cache folders  ·  {round(total_mb, 1)} MB  ({round(total_mb/1024, 2)} GB)",
            font=FONT_SUBHEADING,
            text_color=COLOR_ACCENT
        ).pack(padx=(18, 14), pady=10, anchor="w")

        newest = next((c for c in caches if not c.get("is_crashes")), None)
        for c in caches:
            is_kept = c is newest
            card = HudPanel(self.shaders_scroll, accent=COLOR_SUCCESS if is_kept else COLOR_CARD_BORDER)
            card.pack(fill="x", pady=3, padx=2)

            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", padx=(18, 14), pady=8)

            tag_text = f"Version: {c['version_tag']}" if c['version_tag'] != c['name'] else c['name']
            ctk.CTkLabel(left, text=tag_text, font=FONT_SUBHEADING, text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkLabel(left, text=f"{c['size_mb']} MB  ·  {c['path']}", font=FONT_MONO_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w", pady=(2, 0))
            if c.get("is_crashes"):
                b = badge(card, "CRASH DUMPS", COLOR_TEXT_SECONDARY, COLOR_BTN)
                b.pack(side="right", padx=14)
                Tooltip(b, "Crash reports from previous sessions. Safe to delete.")
            if is_kept:
                b = badge(card, "NEWEST · KEPT", COLOR_SUCCESS, COLOR_SUCCESS_BG)
                b.pack(side="right", padx=14)
                Tooltip(b, "'Clean Old Shaders' keeps this most recently used cache.")

    def _clean_shaders(self, keep_latest: bool):
        confirm = messagebox.askyesno(
            "Confirm Cleaning",
            "Are you sure you want to clean shader caches?\n"
            "(Game shaders will automatically recompile smoothly when you next launch Star Citizen.)"
        )
        if not confirm:
            return

        def task():
            cleaned, freed_mb, msg = clear_shader_caches(keep_latest=keep_latest)
            self.after(0, lambda: self._on_clean_shaders_done(msg))

        threading.Thread(target=task, daemon=True).start()

    def _on_clean_shaders_done(self, msg):
        self.console.log(f"[SHADERS] {msg}")
        messagebox.showinfo("Cleaned Shaders", msg)
        self._refresh_shaders_list()

    def _clean_user_cache_dialog(self):
        if not self.sc_root:
            messagebox.showwarning("Notice", "Please select your Star Citizen directory first.")
            return

        # Target channel
        target = "Game" if "Game" in self.channels_data else "LIVE"
        target_dir = os.path.join(self.sc_root, target)

        confirm = messagebox.askyesno(
            "Safe Clean USER Cache",
            f"This will purge temporary caches, shaders, and logs in '{target}/USER',\n"
            f"while strictly PRESERVING your joystick controls, actionmaps.xml, and character presets.\n\n"
            f"Proceed?"
        )
        if not confirm:
            return

        def task():
            ok, msg = clean_user_cache_safe(target_dir)
            self.after(0, lambda: self._on_clean_user_cache_done(msg))

        threading.Thread(target=task, daemon=True).start()

    def _on_clean_user_cache_done(self, msg):
        self.console.log(f"[USER CLEAN] {msg}")
        messagebox.showinfo("USER Cache Cleaned", msg)

    # --- UI Helpers ---

    def _on_browse(self):
        selected = filedialog.askdirectory(title="Select Star Citizen Directory")
        if selected:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, selected)
            self._refresh_all()

    def _on_auto_detect(self):
        installs = detect_all_sc_installations()
        if installs:
            self.sc_root = installs[0]
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, self.sc_root)
            self.console.log(f"[DETECT] Auto-detected Star Citizen at: {self.sc_root}")
            self._refresh_all()
        else:
            messagebox.showinfo("Not Found", "Could not automatically locate Star Citizen directory. Please browse manually.")

    def _on_path_changed(self):
        self._refresh_all()

    def _on_elevate(self):
        if restart_as_admin():
            self.destroy()
        else:
            messagebox.showerror("Elevation Failed", "Could not restart as Administrator. User cancelled UAC prompt.")

    def _open_in_explorer(self, path: str):
        if os.path.exists(path):
            if os.path.isfile(path):
                subprocess.Popen(f'explorer /select,"{os.path.abspath(path)}"')
            else:
                subprocess.Popen(f'explorer "{os.path.abspath(path)}"')

    def _launch_rsi(self):
        exe = detect_rsi_launcher_exe()
        if exe and os.path.isfile(exe):
            self.console.log(f"[LAUNCH] Starting RSI Launcher: {exe}")
            subprocess.Popen([exe])
        else:
            messagebox.showwarning("Not Found", "Could not find RSI Launcher executable.")


def main():
    app = SCSymlinkManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
