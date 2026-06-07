"""Administrator privilege checks."""

from __future__ import annotations

import ctypes
import sys


class AdminRequiredError(RuntimeError):
    """Raised when an operation requires administrator privileges."""


ADMIN_MESSAGE = (
    "This operation requires Administrator privileges.\n"
    "Right-click the app or terminal and choose 'Run as administrator'."
)


def is_admin() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def ensure_admin() -> None:
    if not is_admin():
        raise AdminRequiredError(ADMIN_MESSAGE)


def require_admin() -> None:
    if not is_admin():
        print(f"Error: {ADMIN_MESSAGE}", file=sys.stderr)
        sys.exit(1)


def request_elevation() -> bool:
    """Re-launch the current process elevated. Returns True if elevation was requested."""
    if is_admin():
        return False

    executable = sys.executable
    script = sys.argv[0]
    params = " ".join(f'"{arg}"' if " " in arg else arg for arg in sys.argv[1:])

    if getattr(sys, "frozen", False):
        command = params or None
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", script, command, None, 1)
    elif script.lower().endswith(".py"):
        command = f'"{script}" {params}'.strip()
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, command, None, 1)
    else:
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", executable, params or None, None, 1)

    return ret > 32
