"""Backup and restore original identifier values."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_BACKUP_DIR = Path.home() / ".pc-privacy-spoofer" / "backups"


def backup_path(name: str = "latest") -> Path:
    return DEFAULT_BACKUP_DIR / f"{name}.json"


def save_backup(data: dict[str, Any], name: str = "latest") -> Path:
    path = backup_path(name)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "values": data,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def load_backup(name: str = "latest") -> dict[str, Any]:
    path = backup_path(name)
    if not path.exists():
        raise FileNotFoundError(f"No backup found at {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload.get("values", payload)


def merge_backup(existing: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    merged.update(updates)
    return merged
