"""Core spoof/restore operations shared by CLI and GUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from privacy_spoofer.admin import AdminRequiredError, ensure_admin
from privacy_spoofer.backup import load_backup, merge_backup, save_backup
from privacy_spoofer.ids import computer_name, mac, registry_ids
from privacy_spoofer.status import collect_status


@dataclass
class SpoofResult:
    results: list[dict[str, Any]]
    backup_path: str
    reboot_recommended: bool


@dataclass
class RestoreResult:
    results: list[dict[str, Any]]
    reboot_recommended: bool


def get_status() -> dict[str, Any]:
    return collect_status()


def list_adapters() -> list[mac.NetworkAdapter]:
    return mac.list_adapters()


def run_spoof(
    *,
    spoof_all: bool = False,
    spoof_mac: bool = False,
    spoof_registry: bool = False,
    spoof_computer_name: bool = False,
    adapter: str | None = None,
) -> SpoofResult:
    ensure_admin()
    backup: dict[str, Any] = {}
    results: list[dict[str, Any]] = []
    reboot_needed = False

    if spoof_all or spoof_mac:
        adapters = mac.list_adapters()
        physical = [a for a in adapters if a.description and "virtual" not in a.description.lower()]
        targets = physical if physical else adapters

        for net_adapter in targets:
            if adapter and net_adapter.key_name != adapter and net_adapter.description != adapter:
                continue
            result = mac.spoof_adapter(net_adapter.key_name, net_adapter.description)
            backup[f"mac:{net_adapter.key_name}"] = {
                "key_name": net_adapter.key_name,
                "description": net_adapter.description,
                "previous": result.get("previous"),
            }
            results.append(result)

    if spoof_all or spoof_registry:
        for target in registry_ids.TARGETS:
            current = registry_ids.read_all().get(target.name)
            if current is None:
                results.append({"name": target.name, "skipped": True})
                continue
            result = registry_ids.spoof_target(target)
            backup[f"registry:{target.name}"] = result.get("previous")
            results.append(result)

    if spoof_all or spoof_computer_name:
        result = computer_name.spoof_computer_name()
        backup["computer_name"] = result.get("previous")
        results.append(result)
        reboot_needed = True

    if not results:
        raise ValueError("Nothing selected. Choose at least one spoof target.")

    try:
        existing = load_backup()
        backup = merge_backup(existing, backup)
    except FileNotFoundError:
        pass

    path = save_backup(backup)
    return SpoofResult(results=results, backup_path=str(path), reboot_recommended=reboot_needed)


def run_restore(backup_name: str = "latest") -> RestoreResult:
    ensure_admin()
    try:
        backup = load_backup(backup_name)
    except FileNotFoundError:
        raise

    results: list[dict[str, Any]] = []

    for key, value in backup.items():
        if key.startswith("mac:"):
            entry = value if isinstance(value, dict) else {"key_name": key.split(":", 1)[1], "previous": value}
            key_name = entry["key_name"]
            description = entry.get("description") or ""
            if not description:
                for net_adapter in mac.list_adapters():
                    if net_adapter.key_name == key_name:
                        description = net_adapter.description
                        break
            results.append(mac.restore_adapter(key_name, description, entry.get("previous")))
        elif key.startswith("registry:"):
            name = key.split(":", 1)[1]
            target = registry_ids.target_by_name(name)
            if target:
                results.append(registry_ids.restore_target(target, value))
        elif key == "computer_name":
            results.append(computer_name.restore_computer_name(value))

    return RestoreResult(results=results, reboot_recommended="computer_name" in backup)
