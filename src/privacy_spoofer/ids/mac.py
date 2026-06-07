"""Network adapter MAC address read/spoof/restore."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from typing import Any

import winreg

from privacy_spoofer.utils.random_id import random_mac

ADAPTER_CLASS = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e972-e325-11ce-bfc1-08002be10318}"

SKIP_DESCRIPTION_FRAGMENTS = (
    "wan miniport",
    "wi-fi direct",
    "kernel debug",
    "bluetooth device",
    "tap-",
    "virtualbox",
    "wireguard",
    "vpn",
    "ras async",
    "debug",
)


@dataclass
class NetworkAdapter:
    key_name: str
    description: str
    mac: str | None
    spoofed_mac: str | None
    connection_name: str | None


def _format_mac(raw: str) -> str:
    raw = re.sub(r"[^0-9A-Fa-f]", "", raw)
    if len(raw) != 12:
        return raw.upper()
    return ":".join(raw[i : i + 2] for i in range(0, 12, 2)).upper()


PS_TIMEOUT = 15


def _run_ps(script: str, timeout: int = PS_TIMEOUT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _live_macs_by_description() -> dict[str, str]:
    script = """
$adapters = Get-NetAdapter -ErrorAction SilentlyContinue |
  Select-Object InterfaceDescription, MacAddress
foreach ($a in $adapters) {
  if ($a.InterfaceDescription -and $a.MacAddress) {
    Write-Output ("{0}|{1}" -f $a.InterfaceDescription, ($a.MacAddress -replace '-', ':'))
  }
}
"""
    result = _run_ps(script)
    mapping: dict[str, str] = {}
    if result.returncode != 0:
        return mapping
    for line in result.stdout.splitlines():
        if "|" not in line:
            continue
        desc, addr = line.split("|", 1)
        mapping[desc.strip()] = addr.strip().upper()
    return mapping


def list_adapters() -> list[NetworkAdapter]:
    adapters: list[NetworkAdapter] = []
    live_macs = _live_macs_by_description()
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, ADAPTER_CLASS) as class_key:
        index = 0
        while True:
            try:
                sub_name = winreg.EnumKey(class_key, index)
                index += 1
            except OSError:
                break

            if not sub_name.isdigit():
                continue

            sub_path = f"{ADAPTER_CLASS}\\{sub_name}"
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, sub_path) as key:
                    desc = _read_reg_str(key, "DriverDesc")
                    if not desc:
                        continue
                    lowered = desc.lower()
                    if any(fragment in lowered for fragment in SKIP_DESCRIPTION_FRAGMENTS):
                        continue

                    current_mac = _read_reg_str(key, "NetworkAddress")
                    original = _read_reg_str(key, "OriginalNetworkAddress")
                    connection = _read_reg_str(key, "NetCfgInstanceId")
            except OSError:
                continue

            live_mac = live_macs.get(desc)
            adapters.append(
                NetworkAdapter(
                    key_name=sub_name,
                    description=desc,
                    mac=live_mac or (_format_mac(original) if original else None),
                    spoofed_mac=_format_mac(current_mac) if current_mac else None,
                    connection_name=connection,
                )
            )
    return adapters


def _read_reg_str(key: winreg.HKEYType, name: str) -> str | None:
    try:
        value, _ = winreg.QueryValueEx(key, name)
        return str(value) if value else None
    except OSError:
        return None


def _restart_adapter(description: str) -> tuple[bool, str]:
    safe = description.replace("'", "''")
    script = f"""
$ErrorActionPreference = 'Stop'
$adapter = Get-NetAdapter | Where-Object {{ $_.InterfaceDescription -eq '{safe}' }} | Select-Object -First 1
if (-not $adapter) {{ throw "Adapter not found: {safe}" }}
Disable-NetAdapter -Name $adapter.Name -Confirm:$false
Start-Sleep -Seconds 2
Enable-NetAdapter -Name $adapter.Name -Confirm:$false
Write-Output "restarted"
"""
    result = _run_ps(script)
    if result.returncode != 0:
        return False, (result.stderr or result.stdout or "Unknown error").strip()
    return True, "Adapter restarted"


def spoof_adapter(key_name: str, description: str, new_mac: str | None = None) -> dict[str, Any]:
    new_mac = (new_mac or random_mac()).replace(":", "").upper()
    sub_path = f"{ADAPTER_CLASS}\\{key_name}"

    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_READ | winreg.KEY_WRITE
    ) as key:
        previous = _read_reg_str(key, "NetworkAddress")
        winreg.SetValueEx(key, "NetworkAddress", 0, winreg.REG_SZ, new_mac)

    ok, message = _restart_adapter(description)
    return {
        "type": "mac",
        "key_name": key_name,
        "description": description,
        "previous": previous,
        "new": _format_mac(new_mac),
        "adapter_restarted": ok,
        "message": message,
    }


def restore_adapter(key_name: str, description: str, previous: str | None) -> dict[str, Any]:
    sub_path = f"{ADAPTER_CLASS}\\{key_name}"
    with winreg.OpenKey(
        winreg.HKEY_LOCAL_MACHINE, sub_path, 0, winreg.KEY_READ | winreg.KEY_WRITE
    ) as key:
        if previous:
            winreg.SetValueEx(key, "NetworkAddress", 0, winreg.REG_SZ, previous)
        else:
            try:
                winreg.DeleteValue(key, "NetworkAddress")
            except OSError:
                pass

    ok, message = _restart_adapter(description)
    return {
        "type": "mac",
        "key_name": key_name,
        "description": description,
        "restored": previous or "(hardware default)",
        "adapter_restarted": ok,
        "message": message,
    }
