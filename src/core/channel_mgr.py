"""
channel_mgr.py - Manages Star Citizen release channels (LIVE, PTU, EPTU, etc.),
channel inspection, manifest parsing, storage savings calculation, and presets.
"""

import os
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from .symlink_ops import (
    inspect_path,
    create_link_auto,
    safe_unlink,
    safe_rename,
)

STANDARD_CHANNELS = ["LIVE", "PTU", "EPTU", "TECH-PREVIEW", "HOTFIX"]


def parse_build_manifest(channel_dir: str) -> Dict[str, str]:
    """
    Parses build_manifest.id if present in the given channel directory.
    Returns branch, version, build date stamp, and build ID.
    """
    manifest_path = os.path.join(channel_dir, "build_manifest.id")
    if not os.path.isfile(manifest_path):
        return {}

    try:
        with open(manifest_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
            info = data.get("Data", {})
            return {
                "branch": info.get("Branch", ""),
                "version": info.get("Version", ""),
                "build_date": info.get("BuildDateStamp", ""),
                "build_id": info.get("BuildId", ""),
            }
    except Exception:
        return {}


def get_fast_directory_size_gb(dir_path: str) -> float:
    """
    Fast estimation of Star Citizen directory size.
    Data.p4k comprises ~90-95% of Star Citizen's disk footprint.
    We check Data.p4k size directly and sample top-level folders (Bin64, Engine, etc.)
    without doing an unbounded recursive disk walk on cold drives.
    """
    if not os.path.isdir(dir_path):
        return 0.0

    p4k_path = os.path.join(dir_path, "Data.p4k")
    total_bytes = 0

    try:
        if os.path.isfile(p4k_path):
            total_bytes += os.path.getsize(p4k_path)
            file_count = 0
            for root, dirs, files in os.walk(dir_path):
                file_count += len(files)
                if file_count > 300:
                    dirs.clear()  # Stop descending into deeper subtrees
                for f in files:
                    if f != "Data.p4k":
                        fp = os.path.join(root, f)
                        try:
                            total_bytes += os.path.getsize(fp)
                        except OSError:
                            pass
        else:
            for root, dirs, files in os.walk(dir_path):
                for f in files:
                    fp = os.path.join(root, f)
                    try:
                        total_bytes += os.path.getsize(fp)
                    except OSError:
                        pass
    except Exception:
        pass

    return round(total_bytes / (1024 ** 3), 1)


def scan_all_channels(sc_root: str) -> Dict[str, Dict[str, Any]]:
    """
    Scans the Star Citizen root directory and discovers:
    - All standard channels (LIVE, PTU, EPTU, TECH-PREVIEW, HOTFIX)
    - Master base directories (like Game)
    - Any custom channels created by the user (e.g. 4.0_PREVIEW)
    """
    results: Dict[str, Dict[str, Any]] = {}

    if not sc_root or not os.path.isdir(sc_root):
        return results

    # Get list of existing entries
    try:
        entries = os.listdir(sc_root)
    except Exception:
        entries = []

    # All known and discovered channel names
    all_channel_names = list(STANDARD_CHANNELS)
    if "Game" in entries and "Game" not in all_channel_names:
        all_channel_names.insert(0, "Game")

    for entry in entries:
        if entry not in all_channel_names and not entry.startswith(".") and "_backup_" not in entry:
            full_p = os.path.join(sc_root, entry)
            # Only include if it's a directory or link
            if os.path.isdir(full_p) or os.path.islink(full_p):
                all_channel_names.append(entry)

    # First pass: inspect all paths
    for name in all_channel_names:
        p = os.path.join(sc_root, name)
        info = inspect_path(p)

        channel_dict = {
            "name": name,
            "path": p,
            "exists": info["exists"],
            "is_dir": info["is_dir"],
            "is_link": info["is_link"],
            "link_type": info["link_type"],  # 'symlink', 'junction', 'real_dir', 'missing'
            "target_raw": info["target_raw"],
            "target_abs": info["target_abs"],
            "target_exists": info["target_exists"],
            "version_info": {},
            "size_gb": 0.0,
            "symlinks_pointing_here": [],
            "is_master_base": False,
        }

        # Inspect build manifest and size
        if info["exists"]:
            target_to_read = info["target_abs"] if info["is_link"] and info["target_exists"] else p
            channel_dict["version_info"] = parse_build_manifest(target_to_read)
            if not info["is_link"]:
                channel_dict["size_gb"] = get_fast_directory_size_gb(p)
            else:
                # If symlink, size is virtually the target size
                if info["target_exists"]:
                    channel_dict["size_gb"] = get_fast_directory_size_gb(info["target_abs"])

        results[name] = channel_dict

    # Second pass: identify which real folders are targets of symlinks
    for name, data in results.items():
        if data["is_link"] and data["target_raw"]:
            target_name = os.path.basename(data["target_raw"])
            if target_name in results:
                results[target_name]["symlinks_pointing_here"].append(name)
                results[target_name]["is_master_base"] = True

    return results


def calculate_storage_stats(channels: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """
    Calculates total physical space used on disk, effective installed channels,
    and estimated SSD space saved by symlinking.
    """
    physical_bytes_gb = 0.0
    active_channels_count = 0
    symlink_count = 0
    average_channel_size_gb = 0.0

    real_sizes = []
    for name, ch in channels.items():
        if ch["exists"]:
            if ch["link_type"] == "real_dir":
                physical_bytes_gb += ch["size_gb"]
                real_sizes.append(ch["size_gb"])
                active_channels_count += 1
            elif ch["is_link"] and ch["target_exists"]:
                symlink_count += 1
                active_channels_count += 1

    # Base reference size is highest real folder or ~105 GB standard
    ref_size = max(real_sizes) if real_sizes and max(real_sizes) > 10 else 105.0

    # Space saved = count of working symlinks * reference size
    saved_gb = round(symlink_count * ref_size, 1)

    return {
        "physical_used_gb": round(physical_bytes_gb, 1),
        "virtual_total_gb": round(physical_bytes_gb + saved_gb, 1),
        "saved_gb": saved_gb,
        "active_channels": active_channels_count,
        "symlink_count": symlink_count,
    }


def detect_active_preset(channels: Dict[str, Dict[str, Any]]) -> str:
    """
    Detects which preset most closely matches the user's current channel layout.
    Returns one of: "reddit", "independent", "direct", or "custom".
    """
    if not channels:
        return "custom"

    # 1. Reddit Method: A custom master base exists (e.g. Game) and LIVE is a link to it
    for name, ch in channels.items():
        if name not in STANDARD_CHANNELS and ch.get("is_master_base", False):
            live_ch = channels.get("LIVE", {})
            if live_ch.get("is_link") and live_ch.get("target_raw", "").endswith(name):
                return "reddit"

    live_ch = channels.get("LIVE", {})
    # If LIVE is not a real dir, and it wasn't the Reddit method, we don't recognize it
    if not live_ch.get("exists") or live_ch.get("link_type") != "real_dir":
        return "custom"

    # 2. Direct Link to LIVE: LIVE is a master base, and test channels point to it
    if live_ch.get("is_master_base", False):
        return "direct"

    # 3. Independent LIVE + Shared Testbed: LIVE is real, and another test channel is a master base
    for name, ch in channels.items():
        if name != "LIVE" and ch.get("is_master_base", False):
            return "independent"

    return "custom"



def apply_reddit_preset(sc_root: str, base_folder_name: str = "Game", prefer_symlink: bool = True) -> List[str]:
    """
    Executes the classic Reddit guide setup:
    1. Checks if base_folder_name (e.g. 'Game') exists. If not, renames existing real 'LIVE'
       (or another real channel) to base_folder_name.
    2. Symlinks LIVE, PTU, EPTU, TECH-PREVIEW, and HOTFIX to base_folder_name.
    Returns log of actions taken.
    """
    logs = []
    channels = scan_all_channels(sc_root)

    base_path = os.path.join(sc_root, base_folder_name)

    # Step 1: Ensure base folder exists as a real directory
    if not os.path.exists(base_path):
        # Look for an existing real channel to rename to Game
        rename_candidate = None
        for cand in ["LIVE", "PTU", "EPTU"]:
            if cand in channels and channels[cand]["link_type"] == "real_dir":
                rename_candidate = cand
                break

        if rename_candidate:
            src = os.path.join(sc_root, rename_candidate)
            ok, msg = safe_rename(src, base_path)
            logs.append(f"[SETUP] {msg}")
            if not ok:
                logs.append(f"[ERROR] Could not rename '{rename_candidate}' to '{base_folder_name}'. Aborting preset.")
                return logs
        else:
            # Create empty base folder
            os.makedirs(base_path, exist_ok=True)
            logs.append(f"[SETUP] Created new base directory '{base_folder_name}'.")
    else:
        logs.append(f"[INFO] Using existing base directory '{base_folder_name}'.")

    # Refresh channel scan
    channels = scan_all_channels(sc_root)

    # Step 2: Link standard channels to base
    targets_to_link = ["LIVE", "PTU", "EPTU", "TECH-PREVIEW", "HOTFIX"]

    for ch_name in targets_to_link:
        ch_path = os.path.join(sc_root, ch_name)
        ch_info = channels.get(ch_name)

        if ch_info and ch_info["exists"]:
            if ch_info["is_link"]:
                if ch_info["target_raw"] == base_folder_name or ch_info["target_abs"] == os.path.normpath(base_path):
                    logs.append(f"[SKIP] '{ch_name}' is already linked to '{base_folder_name}'.")
                    continue
                else:
                    # Unlink old target first
                    safe_unlink(ch_path)
                    logs.append(f"[UPDATE] Removed outdated link for '{ch_name}'.")
            elif ch_info["link_type"] == "real_dir":
                # Real folder: rename to backup
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_name = f"{ch_name}_backup_{timestamp}"
                backup_path = os.path.join(sc_root, backup_name)
                ok, msg = safe_rename(ch_path, backup_path)
                if ok:
                    logs.append(f"[BACKUP] Existing real folder backed up: '{ch_name}' -> '{backup_name}'.")
                else:
                    logs.append(f"[ERROR] Could not back up real folder '{ch_name}': {msg}. Skipping.")
                    continue

        # Create link
        ok, ltype, msg = create_link_auto(base_path, ch_path, prefer_symlink=prefer_symlink)
        if ok:
            logs.append(f"[SUCCESS] Linked '{ch_name}' -> '{base_folder_name}' ({ltype}).")
        else:
            logs.append(f"[FAILED] Could not link '{ch_name}': {msg}")

    return logs


def apply_independent_live_preset(sc_root: str, test_base_name: str = "PTU", prefer_symlink: bool = True) -> List[str]:
    """
    Preset: Independent LIVE + Shared Testbed.
    - LIVE remains an untouched real directory (no re-verifying after testing).
    - PTU is the test master base.
    - EPTU, TECH-PREVIEW, HOTFIX link to PTU.
    """
    logs = []
    channels = scan_all_channels(sc_root)

    test_base_path = os.path.join(sc_root, test_base_name)

    # Determine or verify the test base directory
    if test_base_name in channels and channels[test_base_name]["is_link"]:
        # If PTU is currently a link, check if an existing real master base directory exists (e.g. Game)
        if "Game" in channels and channels["Game"]["link_type"] == "real_dir":
            test_base_path = os.path.join(sc_root, "Game")
            test_base_name = "Game"
            logs.append(f"[INFO] Using existing real directory 'Game' as test base.")
        else:
            target_disp = channels[test_base_name].get("target_raw", "another folder")
            logs.append(
                f"[ERROR] '{test_base_name}' is currently a link pointing to '{target_disp}'. "
                f"An independent testbed requires a separate real installation folder. "
                f"Aborting preset to prevent creating an empty test directory. "
                f"Please install/verify {test_base_name} in the RSI Launcher first or rename a real test folder to '{test_base_name}'."
            )
            return logs
    elif not os.path.exists(test_base_path):
        if "Game" in channels and channels["Game"]["link_type"] == "real_dir":
            test_base_path = os.path.join(sc_root, "Game")
            test_base_name = "Game"
            logs.append(f"[INFO] Using existing real directory 'Game' as test base.")
        else:
            os.makedirs(test_base_path, exist_ok=True)
            logs.append(f"[SETUP] Created new test base directory '{test_base_name}'.")

    # Link test channels to test base
    test_channels = ["EPTU", "TECH-PREVIEW", "HOTFIX"]
    if test_base_name != "PTU":
        test_channels.append("PTU")

    for ch_name in test_channels:
        ch_path = os.path.join(sc_root, ch_name)
        ch_info = channels.get(ch_name)

        if ch_info and ch_info["exists"]:
            if ch_info["is_link"]:
                if ch_info["target_raw"] == test_base_name:
                    logs.append(f"[SKIP] '{ch_name}' is already linked to '{test_base_name}'.")
                    continue
                safe_unlink(ch_path)
            elif ch_info["link_type"] == "real_dir":
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_name = f"{ch_name}_backup_{timestamp}"
                backup_path = os.path.join(sc_root, backup_name)
                ok, msg = safe_rename(ch_path, backup_path)
                if ok:
                    logs.append(f"[BACKUP] Backed up real folder '{ch_name}' to '{backup_name}'.")
                else:
                    logs.append(f"[ERROR] Could not back up '{ch_name}': {msg}")
                    continue

        ok, ltype, msg = create_link_auto(test_base_path, ch_path, prefer_symlink=prefer_symlink)
        if ok:
            logs.append(f"[SUCCESS] Linked '{ch_name}' -> '{test_base_name}' ({ltype}).")
        else:
            logs.append(f"[FAILED] Could not link '{ch_name}': {msg}")

    return logs


def apply_direct_live_preset(sc_root: str, prefer_symlink: bool = True) -> List[str]:
    """
    Preset: Direct Link to LIVE.
    - 'LIVE' is the master folder.
    - PTU, EPTU, TECH-PREVIEW, HOTFIX link directly to LIVE.
    """
    logs = []
    live_path = os.path.join(sc_root, "LIVE")
    channels = scan_all_channels(sc_root)

    # Check if LIVE is a real dir
    live_info = channels.get("LIVE")
    if not live_info or not live_info["exists"]:
        # If Game exists, rename Game to LIVE
        if "Game" in channels and channels["Game"]["link_type"] == "real_dir":
            ok, msg = safe_rename(os.path.join(sc_root, "Game"), live_path)
            logs.append(f"[SETUP] {msg}")
        else:
            logs.append("[ERROR] 'LIVE' real directory not found. Please establish LIVE folder first.")
            return logs
    elif live_info["is_link"]:
        # LIVE is currently a link (e.g. to Game)
        target = live_info["target_abs"]
        if os.path.basename(target).lower() == "game" and os.path.isdir(target):
            # Safe swap: unlink LIVE, rename Game to LIVE
            safe_unlink(live_path)
            ok, msg = safe_rename(target, live_path)
            logs.append(f"[SETUP] Promoted 'Game' to real 'LIVE' directory: {msg}")

    # Re-scan
    channels = scan_all_channels(sc_root)

    for ch_name in ["PTU", "EPTU", "TECH-PREVIEW", "HOTFIX"]:
        ch_path = os.path.join(sc_root, ch_name)
        ch_info = channels.get(ch_name)

        if ch_info and ch_info["exists"]:
            if ch_info["is_link"]:
                if ch_info["target_raw"] == "LIVE":
                    logs.append(f"[SKIP] '{ch_name}' already points to 'LIVE'.")
                    continue
                safe_unlink(ch_path)
            elif ch_info["link_type"] == "real_dir":
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                backup_name = f"{ch_name}_backup_{timestamp}"
                backup_path = os.path.join(sc_root, backup_name)
                ok, msg = safe_rename(ch_path, backup_path)
                if ok:
                    logs.append(f"[BACKUP] Backed up '{ch_name}' to '{backup_name}'.")
                else:
                    logs.append(f"[ERROR] Could not back up '{ch_name}': {msg}")
                    continue

        ok, ltype, msg = create_link_auto(live_path, ch_path, prefer_symlink=prefer_symlink)
        if ok:
            logs.append(f"[SUCCESS] Linked '{ch_name}' -> 'LIVE' ({ltype}).")
        else:
            logs.append(f"[FAILED] Could not link '{ch_name}': {msg}")

    return logs
