"""Random identifier generators."""

from __future__ import annotations

import random
import uuid


def random_mac() -> str:
    """Generate a locally-administered, unicast MAC address (no separators)."""
    first = random.randint(0, 255)
    first = (first & 0xFE) | 0x02  # locally administered, unicast
    rest = [random.randint(0, 255) for _ in range(5)]
    octets = [first, *rest]
    return "".join(f"{b:02X}" for b in octets)


def random_guid() -> str:
    return str(uuid.uuid4())


def random_product_id() -> str:
    """Windows-style product ID: XXXXX-XXXXX-XXXXX-XXXXX-XXXXX."""
    parts = ["".join(str(random.randint(0, 9)) for _ in range(5)) for _ in range(5)]
    return "-".join(parts)


def random_computer_name(prefix: str = "DESKTOP") -> str:
    suffix = "".join(random.choice("0123456789ABCDEF") for _ in range(7))
    return f"{prefix}-{suffix}"
