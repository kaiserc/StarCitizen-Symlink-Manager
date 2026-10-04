"""
test_core.py - Comprehensive automated tests for Star Citizen Symlink Manager core.
"""

import os
import sys
import tempfile
import unittest

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.core.detector import (
    detect_all_sc_installations,
    detect_rsi_launcher_exe,
    get_drive_info,
    is_valid_sc_dir,
)
from src.core.symlink_ops import (
    inspect_path,
    create_link_auto,
    safe_unlink,
    safe_rename,
    is_admin,
)
from src.core.channel_mgr import (
    scan_all_channels,
    calculate_storage_stats,
    parse_build_manifest,
)
from src.core.keybind_mgr import (
    discover_control_files,
    backup_controls,
    list_backups,
)
from src.core.shader_mgr import (
    inspect_shader_caches,
)
from src.core.process_guard import (
    get_running_sc_processes,
)


class TestCore(unittest.TestCase):
    def test_detector(self):
        installs = detect_all_sc_installations()
        print("\n[TEST] Detected installations:", installs)
        self.assertIsInstance(installs, list)
        
        if not installs:
            self.skipTest("No SC install found on this machine. Skipping detector validation.")

        first = installs[0]
        self.assertTrue(is_valid_sc_dir(first))

        drive_info = get_drive_info(first)
        print("[TEST] Drive info:", drive_info)
        self.assertTrue(drive_info["supports_symlinks"])

        launcher = detect_rsi_launcher_exe()
        print("[TEST] RSI Launcher executable:", launcher)

    def test_links_in_temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "BaseGame")
            os.makedirs(target, exist_ok=True)
            with open(os.path.join(target, "test_asset.txt"), "w") as f:
                f.write("StarCitizenData")

            link_path = os.path.join(tmpdir, "PTU_Link")

            # Create link (auto falls back to junction if not admin)
            ok, ltype, msg = create_link_auto(target, link_path)
            print(f"\n[TEST] Link creation result: ok={ok}, type={ltype}, msg={msg}")
            self.assertTrue(ok)
            self.assertIn(ltype, ["symlink", "junction"])

            # Verify inspection
            info = inspect_path(link_path)
            self.assertTrue(info["exists"])
            self.assertTrue(info["is_link"])
            self.assertTrue(info["target_exists"])

            # Verify files are accessible through link
            linked_asset = os.path.join(link_path, "test_asset.txt")
            self.assertTrue(os.path.isfile(linked_asset))

            # Test safe unlink: should remove link, but NEVER target files!
            ok_unlink, msg_unlink = safe_unlink(link_path)
            self.assertTrue(ok_unlink)
            self.assertFalse(os.path.exists(link_path))
            self.assertTrue(os.path.exists(target), "Target folder must still exist!")
            self.assertTrue(os.path.isfile(os.path.join(target, "test_asset.txt")), "Target file must be unharmed!")

    def test_scan_user_sc_install(self):
        installs = detect_all_sc_installations()
        if not installs:
            self.skipTest("No SC install found")

        sc_dir = installs[0]
        channels = scan_all_channels(sc_dir)
        print(f"\n[TEST] Scanned channels in {sc_dir}:")
        for name, ch in channels.items():
            print(f"  - {name:15}: type={ch['link_type']}, target={ch['target_raw']}, size={ch['size_gb']} GB")

        stats = calculate_storage_stats(channels)
        print("[TEST] Storage statistics:", stats)
        self.assertGreaterEqual(stats["saved_gb"], 0)

    def test_keybinding_discovery_and_backup(self):
        installs = detect_all_sc_installations()
        if not installs:
            self.skipTest("No SC install found")

        sc_dir = installs[0]
        # Check if Game or LIVE has control files
        for ch in ["Game", "LIVE"]:
            p = os.path.join(sc_dir, ch)
            if os.path.exists(p):
                found = discover_control_files(p)
                print(f"[TEST] Controls found in {ch}:", len(found["mappings"]), "mappings,", len(found["characters"]), "characters")

        # Test backup to tempdir
        with tempfile.TemporaryDirectory() as tmp_backup_dir:
            ok, msg, manifest = backup_controls(sc_dir, tmp_backup_dir)
            print("[TEST] Backup result:", ok, msg)
            if ok:
                backups = list_backups(tmp_backup_dir)
                self.assertEqual(len(backups), 1)
                print("[TEST] Listed backup:", backups[0]["filename"], backups[0]["size_kb"], "KB")

    def test_shaders_and_processes(self):
        caches = inspect_shader_caches()
        print("\n[TEST] Found shader caches:", len(caches))
        for c in caches[:3]:
            print(f"  - {c['name']}: {c['size_mb']} MB (version: {c['version_tag']})")

        procs = get_running_sc_processes()
        print("[TEST] Running SC processes:", procs)


if __name__ == "__main__":
    unittest.main()
