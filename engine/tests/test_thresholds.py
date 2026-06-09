"""D-07 / D-08 / TRUST-02 threshold-reader test (consumed by plan 02-01, used by 02-02 tacos.py).

Asserts the seeded CA ceilings read back as floats (acos=30.0, tacos=15.0) and that a
missing/empty/absent threshold returns None — NEVER a default. This is the core
anti-fabrication guarantee: the caller refuses the flag rather than guessing a ceiling
(D-08 / TRUST-02 / SOUL.md).

Asserts NOW (does not skip): runs against the seeded config/thresholds.toml committed in
this plan's Task 1 — no live connection needed.
"""

from __future__ import annotations

from habibos import thresholds


def test_reads_seeded_ceiling() -> None:
    # D-09 seeds acos_ceiling_pct=30 and tacos_ceiling_pct=15 (as numbers). The reader
    # returns them coerced to float so downstream compares stay in one numeric type.
    acos = thresholds.read("acos_ceiling_pct", "CA")
    tacos = thresholds.read("tacos_ceiling_pct", "CA")
    assert acos == 30.0
    assert tacos == 15.0
    assert isinstance(acos, float)
    assert isinstance(tacos, float)


def test_missing_threshold_returns_none() -> None:
    # Empty string ("") in the TOML -> None (caller renders "no threshold set"), D-08.
    assert thresholds.read("min_margin_pct", "CA") is None
    # An absent key in the [marketplace.CA] block -> None.
    assert thresholds.read("a_key_that_does_not_exist", "CA") is None
    # An absent marketplace -> None (never a default).
    assert thresholds.read("acos_ceiling_pct", "ZZ") is None


def test_default_marketplace_is_ca() -> None:
    # CA is the only active marketplace today; the default arg must resolve to it.
    assert thresholds.read("acos_ceiling_pct") == 30.0
