"""Operator-threshold reader — missing means REFUSE, never a default (D-08 / TRUST-02).

Reads config/thresholds.toml on the (key, marketplace) grain with stdlib tomllib. A value
left empty ("") or absent (missing key OR missing marketplace) returns None so the caller
renders "no threshold set" and refuses the flag — it NEVER substitutes a default. This is
the project's core anti-fabrication guarantee for money-flagging logic.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

# src/habibos/thresholds.py is two levels below the repo root; the config lives at
# <repo>/config/thresholds.toml (RESEARCH §Pattern 4, line 309).
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "thresholds.toml"


def read(key: str, marketplace: str = "CA") -> float | None:
    """Return the threshold as a float, or None if unset.

    None means the caller MUST refuse the flag that depends on this value (D-08 /
    TRUST-02) — it is never a default. CA is the only active marketplace today, so it
    is the default argument.
    """
    with CONFIG_PATH.open("rb") as fh:
        data = tomllib.load(fh)
    raw = data.get("marketplace", {}).get(marketplace, {}).get(key, "")
    if raw == "" or raw is None:
        return None
    return float(raw)
