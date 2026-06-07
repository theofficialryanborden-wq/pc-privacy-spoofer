"""Collect current identifier status."""

from __future__ import annotations

import subprocess
from typing import Any

from privacy_spoofer.ids import computer_name, mac, registry_ids


def get_volume_serials() -> list[dict[str, str]]:
    result = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Volume -ErrorAction SilentlyContinue | Select DriveLetter, FileSystemLabel, UniqueId",
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    serials: list[dict[str, str]] = []
    if result.returncode != 0:
        return serials

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if len(lines) <= 2:
        return serials

    for line in lines[2:]:
        parts = line.split(None, 2)
        if len(parts) >= 3:
            serials.append(
                {
                    "drive": parts[0],
                    "label": parts[1],
                    "unique_id": parts[2],
                }
            )
    return serials


def collect_status() -> dict[str, Any]:
    adapters = mac.list_adapters()
    registry = registry_ids.read_all()
    return {
        "computer_name": computer_name.get_computer_name(),
        "registry": registry,
        "network_adapters": [
            {
                "description": a.description,
                "mac": a.mac,
                "spoofed_mac": a.spoofed_mac,
                "key": a.key_name,
            }
            for a in adapters
        ],
        "volumes": get_volume_serials(),
    }
