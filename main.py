"""
main.py - Entry point for Star Citizen Symlink Manager.
Supports both interactive GUI mode and scriptable CLI mode.
"""

import os
import sys

# Ensure COM Single Threaded Apartment (STA) mode on Windows for native file dialogs
sys.coinit_flags = 2

import argparse

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.core.detector import detect_all_sc_installations
from src.core.channel_mgr import (
    scan_all_channels,
    calculate_storage_stats,
    apply_reddit_preset,
    apply_independent_live_preset,
    apply_direct_live_preset,
)
from src.core.keybind_mgr import backup_controls, list_backups
from src.core.shader_mgr import clear_shader_caches, clean_user_cache_safe
from src.core.process_guard import get_running_sc_processes


def run_cli(args):
    """Runs requested actions in CLI mode."""
    print("=== STAR CITIZEN SYMLINK MANAGER (CLI) ===")

    sc_dir = args.dir
    if not sc_dir:
        installs = detect_all_sc_installations()
        if installs:
            sc_dir = installs[0]
            print(f"[DETECT] Using auto-detected Star Citizen path: {sc_dir}")
        else:
            print("[ERROR] No Star Citizen install detected. Please specify with --dir <path>.")
            sys.exit(1)

    if args.status:
        channels = scan_all_channels(sc_dir)
        stats = calculate_storage_stats(channels)
        print(f"\nTarget Directory: {sc_dir}")
        print(f"Physical Disk Used : {stats['physical_used_gb']} GB")
        print(f"Active Channels    : {stats['active_channels']} ({stats['symlink_count']} symlinked)")
        print(f"Estimated Space Saved: ~{stats['saved_gb']} GB SSD space")
        print("\nChannels:")
        for name, ch in channels.items():
            link_info = f"-> {ch['target_raw']}" if ch["is_link"] else "(Real Folder)"
            ver = ch["version_info"].get("branch", "N/A")
            print(f"  [{ch['link_type']:8}] {name:15} {link_info:20} (Branch: {ver})")

    if args.preset:
        procs = get_running_sc_processes()
        if procs:
            proc_names = ", ".join(sorted(set(p["name"] for p in procs)))
            print(f"\n[WARNING] Active Star Citizen / RSI Launcher process detected: {proc_names}")
            print("Modifying channel links while the game or launcher is open can cause file locks and corrupted installations.")
            if not args.force:
                try:
                    ans = input("Do you want to proceed anyway? [y/N]: ").strip().lower()
                    if ans != "y":
                        print("[ABORT] Operation cancelled by user.")
                        sys.exit(1)
                except (EOFError, KeyboardInterrupt):
                    print("\n[ABORT] Operation cancelled.")
                    sys.exit(1)
            else:
                print("[NOTICE] Continuing because --force was specified.")

    if args.preset == "reddit":
        print("\nApplying Reddit Method (Unified Base)...")
        logs = apply_reddit_preset(sc_dir)
        for line in logs:
            print(" ", line)
    elif args.preset == "independent":
        print("\nApplying Independent LIVE + Shared Testbed...")
        logs = apply_independent_live_preset(sc_dir)
        for line in logs:
            print(" ", line)
    elif args.preset == "direct":
        print("\nApplying Direct Link to LIVE...")
        logs = apply_direct_live_preset(sc_dir)
        for line in logs:
            print(" ", line)

    if args.backup_controls:
        backup_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "backups"))
        print(f"\nBacking up controls to {backup_dir}...")
        ok, msg, _ = backup_controls(sc_dir, backup_dir)
        print(f"[{'SUCCESS' if ok else 'ERROR'}] {msg}")

    if args.clean_shaders:
        print("\nCleaning shader caches...")
        count, freed, msg = clear_shader_caches(keep_latest=args.keep_latest_shaders)
        print(f"[SHADERS] {msg}")


def main():
    parser = argparse.ArgumentParser(description="Star Citizen Symlink Manager")
    parser.add_argument("--cli", action="store_true", help="Run in command-line mode without GUI")
    parser.add_argument("--dir", type=str, help="Path to StarCitizen root directory")
    parser.add_argument("--status", action="store_true", help="Print status of all channels and storage savings")
    parser.add_argument("--preset", choices=["reddit", "independent", "direct"], help="Apply a linking preset")
    parser.add_argument("--backup-controls", action="store_true", help="Take a 1-click backup of all keybinding/control files")
    parser.add_argument("--clean-shaders", action="store_true", help="Clean shader caches in LocalAppData")
    parser.add_argument("--keep-latest-shaders", action="store_true", help="Retain newest shader cache folder when cleaning")
    parser.add_argument("--force", action="store_true", help="Bypass process guard confirmation in CLI mode")

    args = parser.parse_args()

    # If any CLI flag is provided, run CLI mode
    if args.cli or args.status or args.preset or args.backup_controls or args.clean_shaders:
        run_cli(args)
    else:
        # Launch modern GUI
        from src.gui.app import main as gui_main
        gui_main()


if __name__ == "__main__":
    main()
