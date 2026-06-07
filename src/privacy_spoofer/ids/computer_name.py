"""Computer name spoofing."""

from __future__ import annotations

import subprocess
from typing import Any

import winreg

from privacy_spoofer.utils.random_id import random_computer_name

HKLM = winreg.HKEY_LOCAL_MACHINE

NAME_KEYS = [
    (r"SYSTEM\CurrentControlSet\Control\ComputerName\ComputerName", "ComputerName"),
    (r"SYSTEM\CurrentControlSet\Control\ComputerName\ActiveComputerName", "ComputerName"),
    (r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "Hostname"),
    (r"SYSTEM\CurrentControlSet\Services\Tcpip\Parameters", "NV Hostname"),
]


def get_computer_name() -> str | None:
    try:
        with winreg.OpenKey(HKLM, NAME_KEYS[0][0], 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, NAME_KEYS[0][1])
            return str(value)
    except OSError:
        return None


def spoof_computer_name(new_name: str | None = None) -> dict[str, Any]:
    previous = get_computer_name()
    name = new_name or random_computer_name()

    for path, value_name in NAME_KEYS:
        try:
            with winreg.OpenKey(HKLM, path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, name)
        except OSError:
            pass

    # Also set via WMI for consistency
    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Rename-Computer -NewName '{name}' -Force",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    return {
        "type": "computer_name",
        "previous": previous,
        "new": name,
        "reboot_required": True,
    }


def restore_computer_name(previous: str | None) -> dict[str, Any]:
    if not previous:
        return {"type": "computer_name", "skipped": True, "reason": "No backup value"}

    for path, value_name in NAME_KEYS:
        try:
            with winreg.OpenKey(HKLM, path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, previous)
        except OSError:
            pass

    subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Rename-Computer -NewName '{previous}' -Force",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    return {
        "type": "computer_name",
        "restored": previous,
        "reboot_required": True,
    }
