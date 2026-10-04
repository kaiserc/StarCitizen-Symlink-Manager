"""
Star Citizen Symlink Manager - Core Library
"""

from .detector import (
    detect_all_sc_installations,
    detect_rsi_launcher_exe,
    get_drive_info,
    is_valid_sc_dir,
)

from .symlink_ops import (
    is_admin,
    is_developer_mode_enabled,
    restart_as_admin,
    inspect_path,
    create_symbolic_link,
    create_junction,
    create_link_auto,
    safe_unlink,
    safe_rename,
)

from .channel_mgr import (
    STANDARD_CHANNELS,
    scan_all_channels,
    calculate_storage_stats,
    apply_reddit_preset,
    apply_independent_live_preset,
    apply_direct_live_preset,
)

from .keybind_mgr import (
    backup_controls,
    restore_controls,
    list_backups,
    discover_control_files,
)

from .shader_mgr import (
    inspect_shader_caches,
    clear_shader_caches,
    clean_user_cache_safe,
)

from .process_guard import (
    get_running_sc_processes,
)
