"""
shader_mgr.py - Manages and safely cleans Star Citizen shader caches
and USER directory temporary cache files while preserving custom controls.
"""

import os
import shutil
from typing import List, Dict, Any, Tuple


def get_shader_cache_dir() -> str:
    """Returns the Star Citizen shader cache directory in %LOCALAPPDATA%."""
    localapp = os.environ.get("LOCALAPPDATA", "")
    return os.path.join(localapp, "Star Citizen")


def get_dir_size_mb(path: str) -> float:
    """Calculates size of directory in megabytes."""
    total = 0
    try:
        for root, dirs, files in os.walk(path):
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(root, f))
                except OSError:
                    pass
    except Exception:
        pass
    return round(total / (1024 * 1024), 1)


def inspect_shader_caches() -> List[Dict[str, Any]]:
    """
    Scans %LOCALAPPDATA%\\Star Citizen for all versioned shader caches.
    Returns list of items with folder name, path, size_mb, and last modified date.
    """
    cache_dir = get_shader_cache_dir()
    results = []

    if not os.path.isdir(cache_dir):
        return results

    try:
        entries = os.listdir(cache_dir)
        for entry in entries:
            full_p = os.path.join(cache_dir, entry)
            if os.path.isdir(full_p) and (entry.startswith("starcitizen_") or entry == "crashes"):
                size_mb = get_dir_size_mb(full_p)
                mtime = os.path.getmtime(full_p)

                # Extract version tag if present
                version_tag = entry
                if entry.startswith("starcitizen_(") and ")_" in entry:
                    version_tag = entry.split("starcitizen_(")[1].split(")_")[0]

                results.append({
                    "name": entry,
                    "version_tag": version_tag,
                    "path": full_p,
                    "size_mb": size_mb,
                    "mtime": mtime,
                    "is_crashes": (entry == "crashes"),
                })
    except Exception:
        pass

    results.sort(key=lambda x: x["mtime"], reverse=True)
    return results


def clear_shader_caches(paths_to_delete: List[str] = None, keep_latest: bool = False) -> Tuple[int, float, str]:
    """
    Cleans specified shader cache folders or all shader caches.
    If keep_latest is True, retains the newest cache folder.
    Returns (cleaned_count, total_freed_mb, status_message).
    """
    caches = inspect_shader_caches()
    if not caches:
        return 0, 0.0, "No shader caches found."

    if paths_to_delete is None:
        if keep_latest and len(caches) > 1:
            # Keep the newest *shader* cache. The 'crashes' folder is often the most recently
            # modified entry, so it must not be mistaken for the active cache.
            newest = next((c for c in caches if not c.get("is_crashes")), None)
            targets = [c for c in caches if c is not newest]
        else:
            targets = caches
    else:
        targets = [c for c in caches if c["path"] in paths_to_delete]

    cleaned_count = 0
    freed_mb = 0.0

    for item in targets:
        try:
            size = item["size_mb"]
            shutil.rmtree(item["path"], ignore_errors=True)
            if not os.path.exists(item["path"]):
                cleaned_count += 1
                freed_mb += size
        except Exception:
            pass

    return cleaned_count, round(freed_mb, 1), f"Cleaned {cleaned_count} cache directories ({round(freed_mb, 1)} MB freed)."


def clean_user_cache_safe(channel_path: str) -> Tuple[bool, str]:
    """
    Cleans the USER temporary cache inside a channel, following CIG's official recommendation:
    Removes shaders, performance captures, and temp data,
    while STRICTLY PRESERVING:
    - USER\\client\\0\\Controls (Joystick and keyboard keybindings)
    - USER\\client\\0\\Profiles\\default\\actionmaps.xml
    - USER\\client\\0\\customcharacters (Character presets)
    """
    if not os.path.isdir(channel_path):
        return False, "Channel directory not found."

    # Use 'Client' to match Star Citizen's official casing
    user_client_0 = os.path.join(channel_path, "USER", "Client", "0")
    if not os.path.isdir(user_client_0):
        # Fallback for alternative casings
        user_client_0 = os.path.join(channel_path, "user", "client", "0")
        if not os.path.isdir(user_client_0):
            return True, "No USER cache found to clean."

    # Directories that are SAFE to wipe
    safe_to_wipe_dirs = [
        "shaders",
        "autoperfcaptures",
        "combatrecordings",
        "PowerPresets",
        "frontend",
    ]

    # Files that are SAFE to wipe
    safe_to_wipe_files = [
        "ConsoleHistory.txt",
    ]

    cleaned_items = 0
    for d in safe_to_wipe_dirs:
        p = os.path.join(user_client_0, d)
        if os.path.isdir(p):
            try:
                shutil.rmtree(p, ignore_errors=True)
                if not os.path.exists(p):
                    cleaned_items += 1
            except Exception:
                pass

    for f in safe_to_wipe_files:
        p = os.path.join(user_client_0, f)
        if os.path.isfile(p):
            try:
                os.remove(p)
                cleaned_items += 1
            except Exception:
                pass

    return True, f"Safely purged temporary cache items ({cleaned_items} directories/files). Keybindings and character presets were fully preserved."
