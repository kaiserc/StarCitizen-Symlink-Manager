"""
symlink_ops.py - Low-level Windows symbolic link and NTFS junction operations,
safe unlinking, reparse tag inspection, and privilege management.
"""

import os
import sys
import ctypes
import subprocess
from typing import Tuple, Dict, Any, Optional

IO_REPARSE_TAG_MOUNT_POINT = 0xA0000003  # Junction
IO_REPARSE_TAG_SYMLINK = 0xA000000C      # Symbolic Link


def is_admin() -> bool:
    """Checks if the current process has Windows Administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def is_developer_mode_enabled() -> bool:
    """Checks if Windows Developer Mode is enabled (allowing unprivileged symlinks)."""
    try:
        import winreg
        key_path = r"SOFTWARE\Microsoft\Windows\CurrentVersion\AppModelUnlock"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            val, _ = winreg.QueryValueEx(key, "AllowDevelopmentWithoutDevLicense")
            return val == 1
    except Exception:
        return False


def restart_as_admin() -> bool:
    """Relaunches the current python script or executable with administrative elevation (UAC prompt)."""
    try:
        if getattr(sys, "frozen", False):
            # PyInstaller compiled executable
            exe = sys.executable
            args = ""
        else:
            exe = sys.executable
            args = f'"{os.path.abspath(sys.argv[0])}" ' + " ".join(f'"{a}"' for a in sys.argv[1:])

        # Call ShellExecuteW with 'runas' verb
        ret = ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            exe,
            args,
            None,
            1  # SW_SHOWNORMAL
        )
        if ret > 32:
            return True
        return False
    except Exception:
        return False


def inspect_path(path: str) -> Dict[str, Any]:
    """
    Thoroughly inspects a path to determine if it is a real folder, a directory symlink,
    an NTFS junction, or non-existent.
    """
    result: Dict[str, Any] = {
        "path": path,
        "exists": False,
        "is_dir": False,
        "is_link": False,
        "is_symlink": False,
        "is_junction": False,
        "link_type": "missing",  # 'symlink', 'junction', 'real_dir', 'missing'
        "target_raw": "",
        "target_abs": "",
        "target_exists": False,
        "reparse_tag": 0,
        "size_bytes": 0,
    }

    if not os.path.exists(path) and not os.path.islink(path):
        # Path does not exist
        return result

    result["exists"] = True
    result["is_dir"] = os.path.isdir(path)

    # Check reparse tag
    try:
        stat_res = os.lstat(path)
        tag = getattr(stat_res, "st_reparse_tag", 0)
        result["reparse_tag"] = tag
    except Exception:
        tag = 0

    is_link_val = os.path.islink(path)
    is_junc_val = (tag == IO_REPARSE_TAG_MOUNT_POINT)
    is_sym_val = (tag == IO_REPARSE_TAG_SYMLINK) or is_link_val

    if is_junc_val or is_sym_val:
        result["is_link"] = True
        result["is_symlink"] = is_sym_val
        result["is_junction"] = is_junc_val
        result["link_type"] = "symlink" if is_sym_val else "junction"

        try:
            target = os.readlink(path)
            # Remove Win32 extended path prefixes if present: \\?\ or \??\
            clean_target = target
            for prefix in ["\\\\?\\/", "\\\\?\\\\", "\\??\\/", "\\??\\\\"]:
                if clean_target.startswith(prefix):
                    clean_target = clean_target[len(prefix):]

            result["target_raw"] = clean_target

            # Resolve absolute target
            if os.path.isabs(clean_target):
                result["target_abs"] = os.path.normpath(clean_target)
            else:
                result["target_abs"] = os.path.normpath(os.path.join(os.path.dirname(path), clean_target))

            result["target_exists"] = os.path.exists(result["target_abs"])
        except Exception as e:
            result["target_raw"] = f"Error reading target: {e}"
            result["target_abs"] = ""
            result["target_exists"] = False
    else:
        result["link_type"] = "real_dir"
        result["is_link"] = False

    return result


def create_symbolic_link(target: str, link_name: str) -> Tuple[bool, str]:
    """
    Creates a Directory Symbolic Link (equivalent to mklink /D).
    Requires Admin privileges or Windows Developer Mode.
    """
    if os.path.exists(link_name) or os.path.islink(link_name):
        return False, f"Destination path already exists: '{os.path.basename(link_name)}'"

    try:
        # If target is inside the same parent directory, a relative target is often best
        parent_dir = os.path.dirname(os.path.abspath(link_name))
        target_abs = os.path.abspath(target) if not os.path.isabs(target) else target

        if os.path.dirname(target_abs) == parent_dir:
            target_to_use = os.path.basename(target_abs)
        else:
            target_to_use = target_abs

        os.symlink(target_to_use, link_name, target_is_directory=True)
        return True, f"Successfully created directory symbolic link to '{target_to_use}'."
    except PermissionError:
        return False, "Permission denied. Windows requires Administrator privileges or Developer Mode for symbolic links."
    except OSError as e:
        if getattr(e, "winerror", 0) == 1314:
            return False, "Required privilege not held (Run as Administrator or enable Developer Mode)."
        return False, f"OS Error: {e}"
    except Exception as e:
        return False, f"Failed to create symbolic link: {e}"


def create_junction(target: str, link_name: str) -> Tuple[bool, str]:
    """
    Creates an NTFS Directory Junction (equivalent to mklink /J).
    Works without Administrator elevation on local NTFS volumes.
    """
    if os.path.exists(link_name) or os.path.islink(link_name):
        return False, f"Destination path already exists: '{os.path.basename(link_name)}'"

    target_abs = os.path.abspath(target)
    if not os.path.isdir(target_abs):
        return False, f"Target directory does not exist: '{target_abs}'"

    try:
        import _winapi
        _winapi.CreateJunction(target_abs, os.path.abspath(link_name))
        return True, f"Successfully created directory junction to '{os.path.basename(target_abs)}'."
    except Exception as e:
        # Fallback to cmd mklink /J
        try:
            cmd = f'cmd /c mklink /J "{os.path.abspath(link_name)}" "{target_abs}"'
            proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if proc.returncode == 0:
                return True, f"Successfully created directory junction to '{os.path.basename(target_abs)}'."
            return False, f"mklink /J failed: {proc.stderr.strip() or proc.stdout.strip()}"
        except Exception as ex:
            return False, f"Failed to create junction: {e} / {ex}"


def create_link_auto(target: str, link_name: str, prefer_symlink: bool = True) -> Tuple[bool, str, str]:
    """
    Intelligently creates either a Symbolic Link or an NTFS Junction.
    Returns: (success: bool, link_type_created: str, message: str)
    """
    if prefer_symlink and (is_admin() or is_developer_mode_enabled()):
        ok, msg = create_symbolic_link(target, link_name)
        if ok:
            return True, "symlink", msg
        # If failed due to privilege, fall through to junction

    # Try junction (works without admin rights)
    ok_junc, msg_junc = create_junction(target, link_name)
    if ok_junc:
        return True, "junction", msg_junc

    # If junction failed and we didn't try symlink yet, try symlink
    if not prefer_symlink or not (is_admin() or is_developer_mode_enabled()):
        ok_sym, msg_sym = create_symbolic_link(target, link_name)
        if ok_sym:
            return True, "symlink", msg_sym

    return False, "none", f"Failed to create link: {msg_junc}"


def safe_unlink(link_path: str) -> Tuple[bool, str]:
    """
    Safely removes a symbolic link or directory junction WITHOUT deleting
    any files in the target directory.
    """
    info = inspect_path(link_path)
    if not info["exists"]:
        return False, f"Path does not exist: '{link_path}'"

    if not info["is_link"]:
        return False, (
            f"SAFETY ABORT: '{os.path.basename(link_path)}' is a REAL directory containing actual game files! "
            f"Safe unlink refused to prevent data loss."
        )

    try:
        # For junctions and directory symlinks on Windows, os.unlink removes the link node
        os.unlink(link_path)
        return True, f"Successfully unlinked '{os.path.basename(link_path)}'."
    except Exception as e:
        # Fallback to os.rmdir (which on Windows removes junctions without recursing)
        try:
            os.rmdir(link_path)
            return True, f"Successfully removed link '{os.path.basename(link_path)}'."
        except Exception as ex:
            return False, f"Failed to remove link: {e} / {ex}"


def safe_rename(src: str, dst: str) -> Tuple[bool, str]:
    """Safely renames a directory."""
    if not os.path.exists(src):
        return False, f"Source path does not exist: '{src}'"
    if os.path.exists(dst):
        return False, f"Destination path already exists: '{dst}'"

    try:
        os.rename(src, dst)
        return True, f"Successfully renamed '{os.path.basename(src)}' to '{os.path.basename(dst)}'."
    except Exception as e:
        return False, f"Failed to rename directory: {e}"
