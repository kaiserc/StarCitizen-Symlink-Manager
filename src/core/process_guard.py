"""
process_guard.py - Detects running Star Citizen or RSI Launcher processes
to prevent file lock conflicts during link operations.
"""

import subprocess
from typing import List, Dict, Any

SC_PROCESS_NAMES = {
    "starcitizen.exe": "Star Citizen Game Client",
    "rsi launcher.exe": "RSI Launcher",
    "easyanticheat_eos.exe": "Easy Anti-Cheat",
    "crashhandler64.exe": "Star Citizen Crash Handler",
}


def get_running_sc_processes() -> List[Dict[str, Any]]:
    """
    Checks if any Star Citizen or RSI Launcher processes are currently active.
    Returns list of dicts with process name, PID, and user-friendly description.
    """
    running = []
    try:
        # Run tasklist with CSV format without headers
        cmd = ["tasklist", "/FO", "CSV", "/NH"]
        res = subprocess.run(cmd, capture_output=True, text=True, errors="ignore")
        if res.returncode == 0:
            for line in res.stdout.splitlines():
                parts = [p.strip().strip('"') for p in line.split('","')]
                if len(parts) >= 2:
                    image_name = parts[0].lower()
                    pid = parts[1]
                    if image_name in SC_PROCESS_NAMES:
                        running.append({
                            "name": parts[0],
                            "description": SC_PROCESS_NAMES[image_name],
                            "pid": pid,
                        })
    except Exception:
        pass

    return running
