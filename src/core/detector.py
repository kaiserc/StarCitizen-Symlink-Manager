"""
detector.py - Detection of Star Citizen installation paths, RSI Launcher executables,
and drive volume information.
"""

import os
import re
import string
import ctypes
from ctypes import wintypes
from typing import List, Optional, Dict, Any


def is_valid_sc_dir(path: str) -> bool:
    """
    Checks if a given folder is a valid StarCitizen root directory.
    A valid StarCitizen directory typically contains channels like LIVE, PTU, EPTU,
    or a base folder like Game, or has child folders with Data.p4k or Bin64.
    """
    if not path or not os.path.isdir(path):
        return False

    # Check for known channel or base directory names
    known_channels = {"LIVE", "PTU", "EPTU", "TECH-PREVIEW", "HOTFIX", "GAME"}
    try:
        entries = {e.upper() for e in os.listdir(path)}
        if any(c in entries for c in known_channels):
            return True
        # Also check if it's named StarCitizen
        if os.path.basename(os.path.normpath(path)).lower() == "starcitizen":
            return True
    except (PermissionError, OSError):
        pass

    return False


def detect_from_rsi_logs() -> List[str]:
    """Scans RSI launcher logs in %APPDATA% to find configured game directories."""
    paths = []
    appdata = os.environ.get("APPDATA", "")
    log_dir = os.path.join(appdata, "rsilauncher", "logs")

    if not os.path.isdir(log_dir):
        return paths

    try:
        log_files = [
            os.path.join(log_dir, f)
            for f in os.listdir(log_dir)
            if f.endswith(".log")
        ]
        log_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)

        # Pattern matches e.g. "at C:\Program Files\Roberts Space Industries\StarCitizen"
        pattern = re.compile(
            r'(?:at|in|path)\s+["\']?([A-Za-z]:\\[^"\'\n]+?\\StarCitizen)',
            re.IGNORECASE
        )

        for log_file in log_files[:5]:  # inspect 5 most recent logs
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    for line in f:
                        match = pattern.search(line)
                        if match:
                            candidate = match.group(1).strip()
                            if is_valid_sc_dir(candidate) and candidate not in paths:
                                paths.append(candidate)
            except Exception:
                continue
    except Exception:
        pass

    return paths


def detect_from_registry() -> List[str]:
    """Inspects Windows Registry for RSI / Star Citizen installation keys."""
    paths = []
    try:
        import winreg

        registry_locations = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Roberts Space Industries\StarCitizen"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Roberts Space Industries\StarCitizen"),
            (winreg.HKEY_CURRENT_USER, r"Software\Roberts Space Industries\StarCitizen"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\StarCitizen"),
        ]

        for hkey, subkey in registry_locations:
            try:
                with winreg.OpenKey(hkey, subkey) as key:
                    for val_name in ["InstallLocation", "Path", "Install_Dir", ""]:
                        try:
                            val, _ = winreg.QueryValueEx(key, val_name)
                            if val and is_valid_sc_dir(val) and val not in paths:
                                paths.append(val)
                        except FileNotFoundError:
                            pass
            except FileNotFoundError:
                pass
    except Exception:
        pass

    return paths


def detect_from_common_paths() -> List[str]:
    """Checks well-known installation locations across all detected drive letters."""
    paths = []
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in string.ascii_uppercase:
        if bitmask & 1:
            drives.append(f"{letter}:\\")
        bitmask >>= 1

    common_subdirs = [
        r"Program Files\Roberts Space Industries\StarCitizen",
        r"Games\Star Citizen\StarCitizen",
        r"Games\StarCitizen",
        r"Roberts Space Industries\StarCitizen",
        r"StarCitizen",
    ]

    for drive in drives:
        for subdir in common_subdirs:
            candidate = os.path.join(drive, subdir)
            if is_valid_sc_dir(candidate) and candidate not in paths:
                paths.append(candidate)

    return paths


def detect_all_sc_installations() -> List[str]:
    """
    Finds all Star Citizen installations, deduplicated and ordered by likelihood.
    """
    results: List[str] = []

    # 1. From RSI Logs (most authoritative for currently used path)
    for p in detect_from_rsi_logs():
        norm = os.path.normpath(p)
        if norm not in results:
            results.append(norm)

    # 2. From Common Paths
    for p in detect_from_common_paths():
        norm = os.path.normpath(p)
        if norm not in results:
            results.append(norm)

    # 3. From Registry
    for p in detect_from_registry():
        norm = os.path.normpath(p)
        if norm not in results:
            results.append(norm)

    return results


def detect_rsi_launcher_exe() -> Optional[str]:
    """Finds the RSI Launcher executable path if installed across all drives or registry."""
    candidates = []

    # 1. Check all logical drive letters for standard install directories
    try:
        bitmask = ctypes.windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                candidates.append(f"{letter}:\\Program Files\\Roberts Space Industries\\RSI Launcher\\RSI Launcher.exe")
                candidates.append(f"{letter}:\\Roberts Space Industries\\RSI Launcher\\RSI Launcher.exe")
                candidates.append(f"{letter}:\\Games\\RSI Launcher\\RSI Launcher.exe")
            bitmask >>= 1
    except Exception:
        candidates.extend([
            r"C:\Program Files\Roberts Space Industries\RSI Launcher\RSI Launcher.exe",
            r"D:\Program Files\Roberts Space Industries\RSI Launcher\RSI Launcher.exe",
        ])

    # 2. Check LocalAppData (Electron / RSI Launcher 2.0 user install)
    localapp = os.environ.get("LOCALAPPDATA", "")
    if localapp:
        candidates.append(os.path.join(localapp, "Programs", "RSI Launcher", "RSI Launcher.exe"))

    # 3. Check Windows Registry uninstall keys
    try:
        import winreg
        for hkey in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
            for sub in (
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\rsi-launcher",
                r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\rsi-launcher",
                r"SOFTWARE\Roberts Space Industries\RSI Launcher",
            ):
                try:
                    with winreg.OpenKey(hkey, sub) as key:
                        for val_name in ("DisplayIcon", "InstallLocation", "Path", ""):
                            try:
                                val, _ = winreg.QueryValueEx(key, val_name)
                                if val:
                                    clean_val = val.strip('"\'' )
                                    if clean_val.lower().endswith(".exe"):
                                        candidates.insert(0, clean_val)
                                    else:
                                        candidates.insert(0, os.path.join(clean_val, "RSI Launcher.exe"))
                            except FileNotFoundError:
                                pass
                except FileNotFoundError:
                    pass
    except Exception:
        pass

    for c in candidates:
        if c and os.path.isfile(c):
            return os.path.normpath(c)

    return None


def get_drive_info(path: str) -> Dict[str, Any]:
    """
    Retrieves filesystem type, volume label, total space, and free space for the drive
    holding the specified path.
    """
    if not path:
        return {"drive": "", "fs_type": "Unknown", "supports_symlinks": False, "free_gb": 0, "total_gb": 0}

    try:
        drive_root = os.path.splitdrive(os.path.abspath(path))[0] + "\\"
        vol_name_buf = ctypes.create_unicode_buffer(1024)
        fs_name_buf = ctypes.create_unicode_buffer(1024)
        serial_num = wintypes.DWORD()
        max_comp_len = wintypes.DWORD()
        fs_flags = wintypes.DWORD()

        res = ctypes.windll.kernel32.GetVolumeInformationW(
            ctypes.c_wchar_p(drive_root),
            vol_name_buf,
            ctypes.sizeof(vol_name_buf),
            ctypes.byref(serial_num),
            ctypes.byref(max_comp_len),
            ctypes.byref(fs_flags),
            fs_name_buf,
            ctypes.sizeof(fs_name_buf)
        )

        fs_type = fs_name_buf.value if res else "Unknown"
        vol_name = vol_name_buf.value if res else ""
        supports_symlinks = fs_type.upper() in ["NTFS", "REFS"]

        # Free space
        free_bytes = ctypes.c_ulonglong(0)
        total_bytes = ctypes.c_ulonglong(0)
        total_free_bytes = ctypes.c_ulonglong(0)

        ctypes.windll.kernel32.GetDiskFreeSpaceExW(
            ctypes.c_wchar_p(drive_root),
            ctypes.byref(free_bytes),
            ctypes.byref(total_bytes),
            ctypes.byref(total_free_bytes)
        )

        return {
            "drive": drive_root,
            "volume_name": vol_name,
            "fs_type": fs_type,
            "supports_symlinks": supports_symlinks,
            "free_gb": round(free_bytes.value / (1024 ** 3), 1),
            "total_gb": round(total_bytes.value / (1024 ** 3), 1),
        }
    except Exception as e:
        return {
            "drive": "",
            "volume_name": "",
            "fs_type": "Error",
            "supports_symlinks": False,
            "free_gb": 0,
            "total_gb": 0,
            "error": str(e),
        }
