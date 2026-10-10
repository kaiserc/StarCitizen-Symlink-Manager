"""
help_text.py - Centralised tooltip / help copy so wording stays consistent and easy to edit.

Each entry is either a plain string or a (title, body) tuple.
"""

TIPS = {
    # --- Header ---------------------------------------------------------------
    "admin_badge_admin": (
        "Running as Administrator",
        "True symbolic links can be created. Links will be made as symlinks by default.",
    ),
    "admin_badge_user": (
        "Running as Standard User",
        "Symbolic links need Admin rights or Windows Developer Mode, so this app will create "
        "NTFS Directory Junctions instead. Junctions work identically for the RSI Launcher.",
    ),
    "elevate": (
        "Restart as Administrator",
        "Relaunches the app with a UAC prompt so it can create true symbolic links. "
        "Not required - junctions work fine for same-drive setups.",
    ),
    "launch_rsi": (
        "Open RSI Launcher",
        "Starts the RSI Launcher. After changing links, select a channel in the launcher and "
        "click 'Verify Files' to download only the small delta patch.",
    ),

    # --- Path bar -------------------------------------------------------------
    "path_entry": (
        "Star Citizen Root Folder",
        "The folder that CONTAINS your channel folders (LIVE, PTU, EPTU...), usually "
        "...\\Roberts Space Industries\\StarCitizen. Press Enter after typing to rescan.",
    ),
    "browse": "Pick your StarCitizen root folder manually.",
    "auto_detect": (
        "Auto-Detect",
        "Searches RSI Launcher logs, the registry and common drive paths to find your install.",
    ),
    "open_root": "Open the StarCitizen root folder in Windows Explorer.",
    "drive_info": (
        "Drive Status",
        "Links require an NTFS or ReFS formatted drive. Also warns if StarCitizen.exe or the "
        "RSI Launcher are running, which can lock files.",
    ),

    # --- Metrics --------------------------------------------------------------
    "metric_used": (
        "Physical Disk Used",
        "Space taken by real (non-linked) channel folders. Linked channels add almost nothing.",
    ),
    "metric_channels": (
        "Channels Active",
        "Number of channels the RSI Launcher can see and play, including linked ones.",
    ),
    "metric_saved": (
        "SSD Space Saved (estimate)",
        "Each working link saves roughly one full install (~100-150 GB). "
        "'Virtual' is how much space you would need without links.",
    ),
    "storage_visualizer": (
        "Storage Allocation & Virtual Mapping",
        "Visual breakdown of your physical Star Citizen SSD storage vs virtual space mapped by symlinks.\n\n"
        "• Cyan bar: Physical SSD blocks consumed by actual game data.\n"
        "• Striped Green bar: Hundreds of gigabytes saved through delta symlinks & junctions.",
    ),

    # --- Presets --------------------------------------------------------------
    "preset_reddit": (
        "Reddit Method - Unified Base  (max savings)",
        "Creates one real 'Game' folder (renames your LIVE folder if needed) and links LIVE, PTU, "
        "EPTU, TECH-PREVIEW and HOTFIX to it. ~150 GB total for every channel.\n\n"
        "Trade-off: switching channels requires a 'Verify Files' delta download each time.",
    ),
    "preset_independent": (
        "Independent LIVE + Shared Test",
        "Leaves LIVE untouched as its own real folder, so it's always ready to play. "
        "EPTU, TECH-PREVIEW and HOTFIX are linked to PTU.\n\n"
        "Uses ~2 installs of space; best if you play LIVE regularly and dip into test builds.",
    ),
    "preset_direct": (
        "Direct Link to LIVE",
        "Keeps your real 'LIVE' folder as the master and links PTU, EPTU, TECH-PREVIEW and "
        "HOTFIX directly to it. No 'Game' folder is created.",
    ),
    "preset_custom": (
        "Add Custom Channel",
        "Create a link for an event/special channel such as 4.0_PREVIEW. It will point at "
        "'Game' if present, otherwise 'LIVE'.",
    ),
    "preset_backup_note": (
        "Existing real folders are never deleted - they are renamed to "
        "<NAME>_backup_<timestamp> so you can recover or remove them later."
    ),

    # --- Channel card ---------------------------------------------------------
    "badge_symlink": (
        "Symbolic Link",
        "This folder is a pointer to another folder. It uses no extra disk space.",
    ),
    "badge_junction": (
        "NTFS Junction",
        "A directory junction - works like a symlink for the launcher and doesn't need Admin. "
        "Uses no extra disk space.",
    ),
    "badge_real": (
        "Real Directory",
        "A normal folder holding actual game files and consuming full disk space.",
    ),
    "badge_missing": (
        "Not Installed",
        "This channel folder doesn't exist yet. Pick a target and click Link to create it.",
    ),
    "badge_broken": (
        "Broken Link",
        "The folder this link points to no longer exists. Re-link it to a valid target or Unlink it.",
    ),
    "badge_master": (
        "Master Base",
        "Other channels link to this folder - it holds the real game data. Don't delete it!",
    ),
    "target_dropdown": (
        "Link Target",
        "Choose which real folder this channel should share game files with.",
    ),
    "link_btn": (
        "Link Channel",
        "Make this channel point at the selected target. Replaces an existing link; "
        "a real folder in the way will cause an error rather than be overwritten.",
    ),
    "unlink_btn": (
        "Unlink (safe)",
        "Removes only the link itself. Files in the target folder are never deleted.",
    ),
    "open_channel": "Open this channel folder in Windows Explorer.",
    "disk_footprint": (
        "Disk Footprint",
        "Size of the data this channel uses. For links this is the target's size "
        "(shared, not duplicated).",
    ),
    "version": (
        "Build Version",
        "Read from build_manifest.id. 'Unknown' means the launcher hasn't installed/verified it yet.",
    ),

    # --- Controls tab ---------------------------------------------------------
    "backup_controls": (
        "1-Click Backup",
        "Zips your keybinds (actionmaps.xml), joystick/HOTAS mappings and character presets "
        "(.chf) into a timestamped archive in the 'backups' folder.",
    ),
    "restore_controls": (
        "Restore Latest Backup",
        "Restores the most recent backup into a channel of your choice. Existing files with the "
        "same names are overwritten.",
    ),
    "backup_restore": "Restore this snapshot into a channel.",
    "backup_open": "Show this backup ZIP in Windows Explorer.",

    # --- Shaders tab ----------------------------------------------------------
    "clean_old_shaders": (
        "Clean Old Shaders",
        "Deletes every shader cache except the most recent one in "
        "%LOCALAPPDATA%\\Star Citizen. Safe - caches rebuild automatically.",
    ),
    "wipe_shaders": (
        "Wipe All Shaders",
        "Deletes ALL shader caches. The first launch afterwards will take longer while shaders "
        "recompile. Best fix for graphical glitches after a patch.",
    ),
    "safe_user_purge": (
        "Safe USER Cache Purge",
        "Clears temporary data in <channel>\\USER\\client\\0 (shaders, perf captures, recordings) "
        "while keeping Controls, actionmaps.xml and custom characters.",
    ),
    "refresh": "Rescan the install folder and refresh everything.",
    "clear_log": "Clear the activity log (doesn't affect any files).",
}


def tip(key: str):
    """Returns (title, body) or (text, None) for a tooltip key."""
    value = TIPS.get(key, "")
    if isinstance(value, tuple):
        return value
    return value, None
