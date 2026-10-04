"""
app.py - Main GUI application for Star Citizen Symlink Manager.
"""

import os
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

from .theme import (
    COLOR_BG_DARK,
    COLOR_CARD_BG,
    COLOR_CARD_BORDER,
    COLOR_ACCENT,
    COLOR_ACCENT_HOVER,
    COLOR_ACCENT_MUTED,
    COLOR_GOLD,
    COLOR_GOLD_HOVER,
    COLOR_SUCCESS,
    COLOR_WARNING,
    COLOR_DANGER,
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
)
from .components import (
    StorageMetricCard,
    ChannelCard,
    LogConsole,
)


class SCSymlinkManagerApp(ctk.CTk):
    """Star Citizen Symlink Manager main window."""

    def __init__(self):
        super().__init__()

        # Window configuration
        self.title("Star Citizen Symlink Manager")
        self.geometry("1020x820")
        self.minsize(880, 680)

        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=COLOR_BG_DARK)

        # State
        self.sc_root = ""
        self.channels_data = {}
        self.backups_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..", "backups")
        )
        os.makedirs(self.backups_dir, exist_ok=True)

        self.prefer_symlink = is_admin()  # Auto-prefer symlink if elevated

        self._build_layout()
        self._initial_detect()

    def _build_layout(self):
        # 1. Top Header
        self._build_header()

        # 2. Path Selector Bar
        self._build_path_bar()

        # 3. Main Content Notebook / Tabs
        self.tabview = ctk.CTkTabview(
            self,
            fg_color=COLOR_BG_DARK,
            segmented_button_fg_color="#131A29",
            segmented_button_selected_color=COLOR_ACCENT,
            segmented_button_selected_hover_color=COLOR_ACCENT_HOVER,
            segmented_button_unselected_color="#1E293B",
            segmented_button_unselected_hover_color="#334155",
            text_color=COLOR_TEXT_PRIMARY,
        )
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(0, 6))

        self.tab_channels = self.tabview.add("🛰️  Channels & Storage")
        self.tab_controls = self.tabview.add("🎮  Controls & Keybinds")
        self.tab_shaders = self.tabview.add("🧹  Shader & Cache")
        self.tab_guide = self.tabview.add("📖  How-To & Guide")

        self._build_channels_tab()
        self._build_controls_tab()
        self._build_shaders_tab()
        self._build_guide_tab()

        # 4. Activity Log Console (Collapsible at bottom)
        self.console = LogConsole(self)
        self.console.pack(fill="x", padx=16, pady=(0, 10))

    def _build_header(self):
        header_frame = ctk.CTkFrame(self, fg_color="#0D131F", height=60, corner_radius=0)
        header_frame.pack(fill="x", pady=(0, 10))

        # Title container
        title_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=18, pady=8)

        title_lbl = ctk.CTkLabel(
            title_box,
            text="STAR CITIZEN SYMLINK MANAGER",
            font=FONT_TITLE,
            text_color=COLOR_TEXT_PRIMARY
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = ctk.CTkLabel(
            title_box,
            text="Multi-Channel SSD Space Saver • Delta Patcher Optimization Tool",
            font=FONT_SMALL,
            text_color=COLOR_ACCENT
        )
        subtitle_lbl.pack(anchor="w")

        # Right Header Widgets (Admin status, RSI Launcher launcher)
        right_box = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_box.pack(side="right", padx=18, pady=8)

        # Admin Badge
        self.admin_badge = ctk.CTkLabel(
            right_box,
            text="🛡️ ADMIN" if is_admin() else "⚠️ STANDARD USER",
            font=FONT_SMALL,
            fg_color="#064E3B" if is_admin() else "#78350F",
            text_color=COLOR_SUCCESS if is_admin() else COLOR_WARNING,
            corner_radius=4,
            padx=10,
            pady=4
        )
        self.admin_badge.pack(side="left", padx=(0, 8))

        if not is_admin():
            elevate_btn = ctk.CTkButton(
                right_box,
                text="Elevate to Admin",
                font=FONT_SMALL,
                width=110,
                height=26,
                fg_color="#B45309",
                hover_color=COLOR_GOLD_HOVER,
                command=self._on_elevate
            )
            elevate_btn.pack(side="left", padx=(0, 8))

        # Launch RSI button
        launch_rsi_btn = ctk.CTkButton(
            right_box,
            text="🚀 Open RSI Launcher",
            font=FONT_SMALL,
            width=130,
            height=26,
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._launch_rsi
        )
        launch_rsi_btn.pack(side="left")

    def _build_path_bar(self):
        path_box = ctk.CTkFrame(self, fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=8)
        path_box.pack(fill="x", padx=16, pady=(0, 10))

        # Top row: path label + input + browse + detect
        top_row = ctk.CTkFrame(path_box, fg_color="transparent")
        top_row.pack(fill="x", padx=12, pady=(8, 4))

        lbl = ctk.CTkLabel(top_row, text="Install Directory:", font=FONT_BODY_BOLD, text_color=COLOR_TEXT_PRIMARY)
        lbl.pack(side="left", padx=(0, 8))

        self.path_entry = ctk.CTkEntry(
            top_row,
            font=FONT_MONO,
            fg_color="#06090F",
            text_color=COLOR_TEXT_PRIMARY,
            border_color=COLOR_CARD_BORDER,
            height=30
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.path_entry.bind("<Return>", lambda e: self._on_path_changed())

        browse_btn = ctk.CTkButton(
            top_row,
            text="📁 Browse...",
            font=FONT_SMALL,
            width=80,
            height=30,
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._on_browse
        )
        browse_btn.pack(side="left", padx=(0, 6))

        detect_btn = ctk.CTkButton(
            top_row,
            text="🔍 Auto-Detect",
            font=FONT_SMALL,
            width=90,
            height=30,
            fg_color=COLOR_ACCENT_MUTED,
            hover_color=COLOR_ACCENT_HOVER,
            command=self._on_auto_detect
        )
        detect_btn.pack(side="left", padx=(0, 6))

        open_dir_btn = ctk.CTkButton(
            top_row,
            text="📂 Open",
            font=FONT_SMALL,
            width=65,
            height=30,
            fg_color="#1E293B",
            hover_color="#334155",
            command=lambda: self._open_in_explorer(self.sc_root)
        )
        open_dir_btn.pack(side="left")

        # Bottom info row: Drive info & Running processes
        self.drive_info_lbl = ctk.CTkLabel(
            path_box,
            text="Drive status: Detecting...",
            font=FONT_SMALL,
            text_color=COLOR_TEXT_MUTED
        )
        self.drive_info_lbl.pack(anchor="w", padx=12, pady=(0, 6))

    # --- TAB 1: CHANNELS & STORAGE ---
    def _build_channels_tab(self):
        tab = self.tab_channels

        # 1. Storage Metric Cards row
        metrics_frame = ctk.CTkFrame(tab, fg_color="transparent")
        metrics_frame.pack(fill="x", pady=(0, 8))

        self.metric_used = StorageMetricCard(
            metrics_frame,
            title="Physical Disk Used",
            value="-- GB",
            subtitle="Actual SSD space consumed",
            accent_color=COLOR_TEXT_PRIMARY
        )
        self.metric_used.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.metric_channels = StorageMetricCard(
            metrics_frame,
            title="Channels Active",
            value="-- Channels",
            subtitle="Playable in RSI Launcher",
            accent_color=COLOR_ACCENT
        )
        self.metric_channels.pack(side="left", fill="x", expand=True, padx=3)

        self.metric_saved = StorageMetricCard(
            metrics_frame,
            title="SSD Space Saved",
            value="-- GB",
            subtitle="Saved via Symlinks & Junctions",
            accent_color=COLOR_SUCCESS
        )
        self.metric_saved.pack(side="left", fill="x", expand=True, padx=(6, 0))

        # 2. Presets Action Bar
        preset_box = ctk.CTkFrame(tab, fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=8)
        preset_box.pack(fill="x", pady=(0, 8))

        p_label_row = ctk.CTkFrame(preset_box, fg_color="transparent")
        p_label_row.pack(fill="x", padx=12, pady=(8, 4))

        ctk.CTkLabel(p_label_row, text="QUICK PRESETS & CONFIGURATIONS", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(side="left")

        # Preset buttons row
        btn_row = ctk.CTkFrame(preset_box, fg_color="transparent")
        btn_row.pack(fill="x", padx=12, pady=(0, 10))

        reddit_btn = ctk.CTkButton(
            btn_row,
            text="⭐ Reddit Method (Unified Base)",
            font=FONT_SMALL,
            fg_color="#0F52BA",
            hover_color="#1E40AF",
            command=self._apply_reddit_preset
        )
        reddit_btn.pack(side="left", padx=(0, 6))

        indep_btn = ctk.CTkButton(
            btn_row,
            text="⚡ Independent LIVE + Shared Test",
            font=FONT_SMALL,
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._apply_independent_preset
        )
        indep_btn.pack(side="left", padx=(0, 6))

        direct_btn = ctk.CTkButton(
            btn_row,
            text="🔗 Direct Link to LIVE",
            font=FONT_SMALL,
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._apply_direct_preset
        )
        direct_btn.pack(side="left", padx=(0, 6))

        add_custom_btn = ctk.CTkButton(
            btn_row,
            text="➕ Custom Channel",
            font=FONT_SMALL,
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._on_add_custom_channel
        )
        add_custom_btn.pack(side="right")

        # 3. Scrollable Channels List
        self.channels_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color="transparent",
            label_text="CHANNELS DIRECTORY OVERVIEW",
            label_font=FONT_SMALL,
            label_text_color=COLOR_TEXT_MUTED
        )
        self.channels_scroll.pack(fill="both", expand=True)

    # --- TAB 2: CONTROLS & KEYBINDS ---
    def _build_controls_tab(self):
        tab = self.tab_controls

        # Top banner
        banner = ctk.CTkFrame(tab, fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=8)
        banner.pack(fill="x", pady=(0, 10))

        b_content = ctk.CTkFrame(banner, fg_color="transparent")
        b_content.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(b_content, text="HOTAS, HOSAS & Keybinding Protection", font=FONT_HEADING, text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(
            b_content,
            text="Never lose your joystick mappings, actionmaps.xml, or custom character presets again when verifying or wiping versions.",
            font=FONT_BODY,
            text_color=COLOR_TEXT_SECONDARY
        ).pack(anchor="w", pady=(2, 8))

        btn_row = ctk.CTkFrame(b_content, fg_color="transparent")
        btn_row.pack(fill="x")

        backup_btn = ctk.CTkButton(
            btn_row,
            text="🛡️ 1-Click Backup Controls",
            font=FONT_BODY_BOLD,
            fg_color=COLOR_SUCCESS,
            hover_color="#059669",
            command=self._backup_controls_now
        )
        backup_btn.pack(side="left", padx=(0, 8))

        restore_btn = ctk.CTkButton(
            btn_row,
            text="🔄 Restore Controls to Channel",
            font=FONT_BODY_BOLD,
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._restore_controls_dialog
        )
        restore_btn.pack(side="left")

        # Backup History Box
        self.backups_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color="transparent",
            label_text="BACKUP HISTORY & SNAPSHOTS",
            label_font=FONT_SMALL,
            label_text_color=COLOR_TEXT_MUTED
        )
        self.backups_scroll.pack(fill="both", expand=True)
        self._refresh_backups_list()

    # --- TAB 3: SHADER & CACHE ---
    def _build_shaders_tab(self):
        tab = self.tab_shaders

        banner = ctk.CTkFrame(tab, fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=8)
        banner.pack(fill="x", pady=(0, 10))

        b_content = ctk.CTkFrame(banner, fg_color="transparent")
        b_content.pack(fill="x", padx=14, pady=12)

        ctk.CTkLabel(b_content, text="Shader Cache & USER Temporary Data Cleaner", font=FONT_HEADING, text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
        ctk.CTkLabel(
            b_content,
            text="Switching between LIVE, PTU, or EPTU with symlinks can cause graphics glitches if outdated shaders linger. Cleaning fixes 90% of crashes.",
            font=FONT_BODY,
            text_color=COLOR_TEXT_SECONDARY
        ).pack(anchor="w", pady=(2, 8))

        btn_row = ctk.CTkFrame(b_content, fg_color="transparent")
        btn_row.pack(fill="x")

        clean_old_btn = ctk.CTkButton(
            btn_row,
            text="🧹 Clean Old Shaders (Keep Latest)",
            font=FONT_BODY_BOLD,
            fg_color=COLOR_ACCENT_MUTED,
            hover_color=COLOR_ACCENT_HOVER,
            command=lambda: self._clean_shaders(keep_latest=True)
        )
        clean_old_btn.pack(side="left", padx=(0, 8))

        clean_all_btn = ctk.CTkButton(
            btn_row,
            text="💥 Wipe All Shaders",
            font=FONT_BODY_BOLD,
            fg_color="#450A0A",
            hover_color="#7F1D1D",
            text_color="#FCA5A5",
            command=lambda: self._clean_shaders(keep_latest=False)
        )
        clean_all_btn.pack(side="left", padx=(0, 8))

        safe_user_btn = ctk.CTkButton(
            btn_row,
            text="🛡️ Safe Purge USER Cache (Preserves Controls)",
            font=FONT_BODY_BOLD,
            fg_color="#1E293B",
            hover_color="#334155",
            command=self._clean_user_cache_dialog
        )
        safe_user_btn.pack(side="left")

        # Scrollable list of detected shader caches
        self.shaders_scroll = ctk.CTkScrollableFrame(
            tab,
            fg_color="transparent",
            label_text="DETECTED SHADER CACHES IN %LOCALAPPDATA%\\STAR CITIZEN",
            label_font=FONT_SMALL,
            label_text_color=COLOR_TEXT_MUTED
        )
        self.shaders_scroll.pack(fill="both", expand=True)
        self._refresh_shaders_list()

    # --- TAB 4: HOW-TO & GUIDE ---
    def _build_guide_tab(self):
        tab = self.tab_guide

        guide_scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent")
        guide_scroll.pack(fill="both", expand=True)

        guide_text = """# How Symbolic Links Save Hundreds of Gigabytes in Star Citizen

### 🚀 The Problem:
Star Citizen client installations are massive (100GB to 150GB+ each). With channels like **LIVE**, **PTU**, **EPTU**, and **TECH-PREVIEW**, testing all of them independently requires allocating 400GB to 600GB+ of valuable high-speed SSD space.

However, **90% to 95% of Star Citizen assets (Data.p4k, textures, audio) are identical** between channels!

---

### 💡 The Solution (Symbolic Links / NTFS Junctions):
Instead of duplicating 150GB four times:
1. One master folder (named `Game` or `LIVE`) holds the actual ~150GB game data.
2. The other channels (`PTU`, `EPTU`, `TECH-PREVIEW`, `HOTFIX`) are **symbolic links** pointing to that master folder.
3. Windows presents each link to the RSI Launcher as an independent directory with its own path, but under the hood, they all share the exact same SSD blocks!

---

### 🎮 How to Play & Switch Channels:
1. Configure your channels using this manager (e.g. click **"Reddit Method (Unified Base)"**).
2. Open the **RSI Launcher**.
3. Select whichever channel you want to play (e.g. **EPTU**).
4. Click **VERIFY FILES** (or Update).
   - The launcher will only download the tiny delta difference (usually 2GB - 8GB instead of 150GB!).
5. Click **LAUNCH GAME** and enjoy!
6. When you want to switch back to another channel, simply switch the dropdown in RSI Launcher and click **Verify**.

---

### 🛡️ Safety & Controls Protection:
- **Never lose keybindings**: Use the **"Controls & Keybinds"** tab to take a 1-click backup of all your joystick layouts and actionmaps.
- **Safe Unlinking**: The manager's unlinking feature only removes the link entry itself—it **never deletes files** inside your actual game directory.
- **NTFS Required**: Windows symbolic links and junctions require an NTFS or ReFS drive (FAT32/exFAT drives are not supported).
"""
        textbox = ctk.CTkTextbox(
            guide_scroll,
            font=FONT_BODY,
            fg_color=COLOR_CARD_BG,
            text_color=COLOR_TEXT_PRIMARY,
            wrap="word",
            height=500
        )
        textbox.pack(fill="both", expand=True, padx=4, pady=4)
        textbox.insert("1.0", guide_text)
        textbox.configure(state="disabled")

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

    def _refresh_all(self):
        """Refreshes path validation, drive info, channels, and metrics."""
        path = self.path_entry.get().strip()
        if not path or not os.path.isdir(path):
            self.drive_info_lbl.configure(text="Drive status: Invalid or unselected directory path.")
            return

        self.sc_root = os.path.normpath(path)

        # Drive Info
        d_info = get_drive_info(self.sc_root)
        fs_type = d_info.get("fs_type", "Unknown")
        free_gb = d_info.get("free_gb", 0)
        total_gb = d_info.get("total_gb", 0)
        drive_str = f"Volume: {d_info.get('drive')} ({fs_type}) • Free Space: {free_gb} GB / {total_gb} GB Total"

        # Check running processes
        procs = get_running_sc_processes()
        if procs:
            proc_names = ", ".join(set(p["name"] for p in procs))
            drive_str += f" | ⚠️ Running: {proc_names}"

        self.drive_info_lbl.configure(text=drive_str)

        # Scan Channels
        self.channels_data = scan_all_channels(self.sc_root)

        # Update Metrics
        stats = calculate_storage_stats(self.channels_data)
        self.metric_used.update_values(f"{stats['physical_used_gb']} GB")
        self.metric_channels.update_values(f"{stats['active_channels']} Channels", f"{stats['symlink_count']} Symlinked")
        self.metric_saved.update_values(f"~{stats['saved_gb']} GB Saved", f"Virtual: {stats['virtual_total_gb']} GB")

        # Populate Channels Grid
        self._render_channel_cards()

    def _render_channel_cards(self):
        # Clear existing cards
        for widget in self.channels_scroll.winfo_children():
            widget.destroy()

        if not self.channels_data:
            lbl = ctk.CTkLabel(
                self.channels_scroll,
                text="No channels found. Use the presets above or 'Add Custom Channel' to create your first link.",
                font=FONT_BODY,
                text_color=COLOR_TEXT_MUTED
            )
            lbl.pack(pady=20)
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
        logs = apply_reddit_preset(self.sc_root, prefer_symlink=self.prefer_symlink)
        for line in logs:
            self.console.log(line)
        self._refresh_all()

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
        logs = apply_independent_live_preset(self.sc_root, prefer_symlink=self.prefer_symlink)
        for line in logs:
            self.console.log(line)
        self._refresh_all()

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
        logs = apply_direct_live_preset(self.sc_root, prefer_symlink=self.prefer_symlink)
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
        for widget in self.backups_scroll.winfo_children():
            widget.destroy()

        backups = list_backups(self.backups_dir)
        if not backups:
            lbl = ctk.CTkLabel(
                self.backups_scroll,
                text="No backups yet. Click '1-Click Backup Controls' above to create a snapshot of your bindings.",
                font=FONT_BODY,
                text_color=COLOR_TEXT_MUTED
            )
            lbl.pack(pady=20)
            return

        for b in backups:
            card = ctk.CTkFrame(self.backups_scroll, fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=6)
            card.pack(fill="x", pady=3, padx=2)

            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", padx=12, pady=8)

            ctk.CTkLabel(left, text=b["filename"], font=FONT_BODY_BOLD, text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkLabel(
                left,
                text=f"{b['file_count']} files • {b['size_kb']} KB • Created: {b['created_at']}",
                font=FONT_SMALL,
                text_color=COLOR_TEXT_MUTED
            ).pack(anchor="w")

            actions = ctk.CTkFrame(card, fg_color="transparent")
            actions.pack(side="right", padx=12, pady=8)

            restore_btn = ctk.CTkButton(
                actions,
                text="Restore",
                width=65,
                height=26,
                font=FONT_SMALL,
                fg_color=COLOR_ACCENT_MUTED,
                hover_color=COLOR_ACCENT_HOVER,
                command=lambda p=b["path"]: self._restore_specific_backup(p)
            )
            restore_btn.pack(side="left", padx=4)

            open_btn = ctk.CTkButton(
                actions,
                text="Open Zip",
                width=65,
                height=26,
                font=FONT_SMALL,
                fg_color="#1E293B",
                hover_color="#334155",
                command=lambda p=b["path"]: self._open_in_explorer(p)
            )
            open_btn.pack(side="left")

    def _restore_specific_backup(self, zip_path: str):
        # Choose target channel
        channels = [name for name, ch in self.channels_data.items() if ch["exists"]]
        if not channels:
            channels = ["Game", "LIVE"]

        # Prompt channel choice
        dialog = ctk.CTkInputDialog(
            text=f"Enter destination channel name to restore into ({', '.join(channels)}):",
            title="Restore Keybindings"
        )
        target_ch = dialog.get_input()
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
        for widget in self.shaders_scroll.winfo_children():
            widget.destroy()

        caches = inspect_shader_caches()
        if not caches:
            lbl = ctk.CTkLabel(
                self.shaders_scroll,
                text="No shader caches found in %LOCALAPPDATA%\\Star Citizen.",
                font=FONT_BODY,
                text_color=COLOR_TEXT_MUTED
            )
            lbl.pack(pady=20)
            return

        total_mb = sum(c["size_mb"] for c in caches)
        header_card = ctk.CTkFrame(self.shaders_scroll, fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=6)
        header_card.pack(fill="x", pady=3, padx=2)

        ctk.CTkLabel(
            header_card,
            text=f"Found {len(caches)} cache directories totaling {round(total_mb, 1)} MB ({round(total_mb/1024, 2)} GB)",
            font=FONT_BODY_BOLD,
            text_color=COLOR_ACCENT
        ).pack(padx=12, pady=8, anchor="w")

        for c in caches:
            card = ctk.CTkFrame(self.shaders_scroll, fg_color=COLOR_CARD_BG, border_color=COLOR_CARD_BORDER, border_width=1, corner_radius=6)
            card.pack(fill="x", pady=2, padx=2)

            left = ctk.CTkFrame(card, fg_color="transparent")
            left.pack(side="left", padx=12, pady=6)

            tag_text = f"Version: {c['version_tag']}" if c['version_tag'] != c['name'] else c['name']
            ctk.CTkLabel(left, text=tag_text, font=FONT_BODY_BOLD, text_color=COLOR_TEXT_PRIMARY).pack(anchor="w")
            ctk.CTkLabel(left, text=f"{c['size_mb']} MB • {c['path']}", font=FONT_SMALL, text_color=COLOR_TEXT_MUTED).pack(anchor="w")

    def _clean_shaders(self, keep_latest: bool):
        confirm = messagebox.askyesno(
            "Confirm Cleaning",
            "Are you sure you want to clean shader caches?\n"
            "(Game shaders will automatically recompile smoothly when you next launch Star Citizen.)"
        )
        if not confirm:
            return

        cleaned, freed_mb, msg = clear_shader_caches(keep_latest=keep_latest)
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

        ok, msg = clean_user_cache_safe(target_dir)
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
