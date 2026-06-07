"""Registry-based Windows identifiers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import winreg

from privacy_spoofer.utils.random_id import random_guid, random_product_id

HKLM = winreg.HKEY_LOCAL_MACHINE


@dataclass(frozen=True)
class RegistryTarget:
    name: str
    path: str
    value_name: str
    generator: Callable[[], str]
    reboot_required: bool = False
    notes: str = ""


TARGETS: list[RegistryTarget] = [
    RegistryTarget(
        name="machine_guid",
        path=r"SOFTWARE\Microsoft\Cryptography",
        value_name="MachineGuid",
        generator=random_guid,
        notes="Used by apps and Windows for device fingerprinting.",
    ),
    RegistryTarget(
        name="hw_profile_guid",
        path=r"SYSTEM\CurrentControlSet\Control\IDConfigDB\Hardware Profiles\0001",
        value_name="HwProfileGuid",
        generator=lambda: "{" + random_guid().upper() + "}",
        notes="Hardware profile identifier.",
    ),
    RegistryTarget(
        name="product_id",
        path=r"SOFTWARE\Microsoft\Windows NT\CurrentVersion",
        value_name="ProductId",
        generator=random_product_id,
        notes="Windows installation product ID.",
    ),
    RegistryTarget(
        name="sus_client_id",
        path=r"SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate",
        value_name="SusClientId",
        generator=random_guid,
        notes="Windows Update client identifier (if present).",
    ),
]


def _read_value(path: str, value_name: str) -> str | None:
    try:
        with winreg.OpenKey(HKLM, path, 0, winreg.KEY_READ) as key:
            value, reg_type = winreg.QueryValueEx(key, value_name)
            if reg_type != winreg.REG_SZ:
                return None
            return str(value)
    except OSError:
        return None


def read_all() -> dict[str, str | None]:
    return {target.name: _read_value(target.path, target.value_name) for target in TARGETS}


def spoof_target(target: RegistryTarget, new_value: str | None = None) -> dict[str, Any]:
    previous = _read_value(target.path, target.value_name)
    if previous is None:
        return {
            "type": "registry",
            "name": target.name,
            "skipped": True,
            "reason": "Value not present on this system",
        }

    value = new_value or target.generator()
    with winreg.OpenKey(HKLM, target.path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, target.value_name, 0, winreg.REG_SZ, value)

    return {
        "type": "registry",
        "name": target.name,
        "path": target.path,
        "value_name": target.value_name,
        "previous": previous,
        "new": value,
        "reboot_required": target.reboot_required,
    }


def restore_target(target: RegistryTarget, previous: str | None) -> dict[str, Any]:
    if previous is None:
        return {"type": "registry", "name": target.name, "skipped": True, "reason": "No backup value"}

    with winreg.OpenKey(HKLM, target.path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
        winreg.SetValueEx(key, target.value_name, 0, winreg.REG_SZ, previous)

    return {
        "type": "registry",
        "name": target.name,
        "restored": previous,
    }


def target_by_name(name: str) -> RegistryTarget | None:
    for target in TARGETS:
        if target.name == name:
            return target
    return None
