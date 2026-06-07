"""Command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from privacy_spoofer import __version__
from privacy_spoofer.admin import AdminRequiredError, require_admin
from privacy_spoofer import operations


def _print_json(data: Any) -> None:
    print(json.dumps(data, indent=2))


def cmd_status(_: argparse.Namespace) -> int:
    _print_json(operations.get_status())
    return 0


def cmd_spoof(args: argparse.Namespace) -> int:
    try:
        result = operations.run_spoof(
            spoof_all=args.all,
            spoof_mac=args.mac,
            spoof_registry=args.registry,
            spoof_computer_name=args.computer_name,
            adapter=args.adapter,
        )
    except AdminRequiredError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Backup saved to: {result.backup_path}\n")
    _print_json({"results": result.results, "reboot_recommended": result.reboot_recommended})
    if result.reboot_recommended:
        print("\nNote: Computer name changes require a reboot to fully apply.")
    return 0


def cmd_restore(args: argparse.Namespace) -> int:
    try:
        require_admin()
        result = operations.run_restore(args.backup)
    except AdminRequiredError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    _print_json({"results": result.results, "reboot_recommended": result.reboot_recommended})
    return 0


def cmd_list_adapters(_: argparse.Namespace) -> int:
    adapters = operations.list_adapters()
    for adapter in adapters:
        print(f"[{adapter.key_name}] {adapter.description}")
        print(f"  Current MAC: {adapter.mac or 'unknown'}")
        if adapter.spoofed_mac:
            print(f"  Registry override: {adapter.spoofed_mac}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="privacy-spoofer",
        description="Spoof common Windows identifiers for privacy (with backup/restore).",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show current identifiers").set_defaults(func=cmd_status)
    sub.add_parser("list-adapters", help="List network adapters").set_defaults(func=cmd_list_adapters)

    spoof = sub.add_parser("spoof", help="Spoof identifiers (requires admin)")
    spoof.add_argument("--all", action="store_true", help="Spoof MAC, registry IDs, and computer name")
    spoof.add_argument("--mac", action="store_true", help="Spoof network adapter MAC addresses")
    spoof.add_argument("--registry", action="store_true", help="Spoof registry-based IDs")
    spoof.add_argument("--computer-name", action="store_true", help="Spoof computer name")
    spoof.add_argument("--adapter", help="Only spoof adapter with this registry key or description")
    spoof.set_defaults(func=cmd_spoof)

    restore = sub.add_parser("restore", help="Restore identifiers from backup (requires admin)")
    restore.add_argument("--backup", default="latest", help="Backup name (default: latest)")
    restore.set_defaults(func=cmd_restore)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)
