"""
keybind_mgr.py - Protects and manages custom Star Citizen HOTAS/HOSAS keybindings,
actionmaps.xml, and custom character presets.
"""

import os
import json
import time
import zipfile
import shutil
from typing import List, Dict, Any, Tuple, Optional


def find_user_directory(channel_path: str) -> Optional[str]:
    """Finds the USER directory inside a channel path (case-insensitive)."""
    if not os.path.isdir(channel_path):
        return None

    # Check common cases: USER, user
    for entry in os.listdir(channel_path):
        if entry.lower() == "user":
            cand = os.path.join(channel_path, entry)
            if os.path.isdir(cand):
                return cand
    return None


def discover_control_files(channel_path: str) -> Dict[str, List[str]]:
    """
    Discovers:
    - Custom exported control mappings (*.xml)
    - Active actionmaps.xml
    - Custom character presets (*.chf)
    """
    results: Dict[str, List[str]] = {
        "mappings": [],
        "actionmaps": [],
        "characters": [],
    }

    user_dir = find_user_directory(channel_path)
    if not user_dir:
        return results

    client_zero = os.path.join(user_dir, "client", "0")
    if not os.path.isdir(client_zero):
        return results

    # 1. Controls/Mappings
    mappings_dir = os.path.join(client_zero, "Controls", "Mappings")
    if os.path.isdir(mappings_dir):
        for f in os.listdir(mappings_dir):
            if f.endswith(".xml"):
                results["mappings"].append(os.path.join(mappings_dir, f))

    # 2. Profiles/default/actionmaps.xml
    actionmaps_p = os.path.join(client_zero, "Profiles", "default", "actionmaps.xml")
    if os.path.isfile(actionmaps_p):
        results["actionmaps"].append(actionmaps_p)

    # 3. Custom characters (*.chf)
    char_dir = os.path.join(client_zero, "customcharacters")
    if os.path.isdir(char_dir):
        for f in os.listdir(char_dir):
            if f.endswith(".chf"):
                results["characters"].append(os.path.join(char_dir, f))

    return results


def backup_controls(sc_root: str, target_backup_dir: str) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Creates a timestamped ZIP backup of all control mappings, actionmaps, and character presets
    from all detected channels.
    """
    os.makedirs(target_backup_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    zip_filename = f"sc_controls_backup_{timestamp}.zip"
    zip_path = os.path.join(target_backup_dir, zip_filename)

    backed_up_files = []
    manifest: Dict[str, Any] = {
        "timestamp": timestamp,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "files": [],
    }

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for entry in os.listdir(sc_root):
                ch_p = os.path.join(sc_root, entry)
                if not (os.path.isdir(ch_p) or os.path.islink(ch_p)):
                    continue

                files_dict = discover_control_files(ch_p)
                for cat, file_list in files_dict.items():
                    for full_p in file_list:
                        # Arcname preserves channel and relative user path
                        rel = os.path.relpath(full_p, sc_root)
                        zf.write(full_p, arcname=rel)
                        backed_up_files.append(rel)
                        manifest["files"].append({
                            "channel": entry,
                            "category": cat,
                            "filename": os.path.basename(full_p),
                            "arcname": rel,
                        })

            # Save manifest inside ZIP
            manifest_json = json.dumps(manifest, indent=2)
            zf.writestr("backup_manifest.json", manifest_json)

        if not backed_up_files:
            if os.path.exists(zip_path):
                os.remove(zip_path)
            return False, "No keybinding or control files were found to back up.", {}

        return True, f"Successfully backed up {len(backed_up_files)} control files to '{zip_filename}'.", manifest
    except Exception as e:
        return False, f"Backup failed: {e}", {}


def list_backups(backup_dir: str) -> List[Dict[str, Any]]:
    """Lists all available control backups with summary metadata."""
    backups = []
    if not os.path.isdir(backup_dir):
        return backups

    for f in os.listdir(backup_dir):
        if f.startswith("sc_controls_backup_") and f.endswith(".zip"):
            full_p = os.path.join(backup_dir, f)
            size_kb = round(os.path.getsize(full_p) / 1024, 1)
            file_count = 0
            manifest_data = {}

            try:
                with zipfile.ZipFile(full_p, "r") as zf:
                    if "backup_manifest.json" in zf.namelist():
                        manifest_data = json.loads(zf.read("backup_manifest.json").decode("utf-8"))
                        file_count = len(manifest_data.get("files", []))
                    else:
                        file_count = len(zf.namelist())
            except Exception:
                pass

            backups.append({
                "filename": f,
                "path": full_p,
                "size_kb": size_kb,
                "file_count": file_count,
                "created_at": manifest_data.get("created_at", time.ctime(os.path.getmtime(full_p))),
            })

    backups.sort(key=lambda x: x["path"], reverse=True)
    return backups


def restore_controls(zip_path: str, target_channel_dir: str) -> Tuple[bool, str]:
    """Restores control files from a ZIP backup into the specified channel."""
    if not os.path.isfile(zip_path):
        return False, f"Backup file not found: {zip_path}"

    if not os.path.isdir(target_channel_dir):
        return False, f"Target channel folder does not exist: {target_channel_dir}"

    target_user_0 = os.path.join(target_channel_dir, "USER", "client", "0")
    mappings_target = os.path.join(target_user_0, "Controls", "Mappings")
    profiles_target = os.path.join(target_user_0, "Profiles", "default")
    chars_target = os.path.join(target_user_0, "customcharacters")

    os.makedirs(mappings_target, exist_ok=True)
    os.makedirs(profiles_target, exist_ok=True)
    os.makedirs(chars_target, exist_ok=True)

    restored = 0
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for item in zf.infolist():
                if item.filename.endswith("/"):
                    continue
                basename = os.path.basename(item.filename)

                # Destination routing
                if "controls" in item.filename.lower() and basename.endswith(".xml"):
                    dest = os.path.join(mappings_target, basename)
                elif basename.lower() == "actionmaps.xml":
                    dest = os.path.join(profiles_target, basename)
                elif basename.lower().endswith(".chf"):
                    dest = os.path.join(chars_target, basename)
                else:
                    continue

                with zf.open(item) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                restored += 1

        return True, f"Successfully restored {restored} control and mapping files."
    except Exception as e:
        return False, f"Restore failed: {e}"
