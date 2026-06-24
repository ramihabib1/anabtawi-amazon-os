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
    # The empty-refusal path (Phase-9 D-08) is now proven by an ABSENT key and an absent
    # marketplace, since days_of_cover_floor is no longer "" (it is live = 42 in Plan 09-01).
    # An absent key in the [marketplace.CA] block -> None.
    assert thresholds.read("a_key_that_does_not_exist", "CA") is None
    # An absent marketplace -> None (never a default).
    assert thresholds.read("acos_ceiling_pct", "ZZ") is None
    # Locks the seeded margin floor (seeded = 15 in Plan 02).
    assert thresholds.read("min_net_margin_pct", "CA") == 15.0


def test_phase9_dials_live() -> None:
    """The three Phase-9 dials read back as the exact live floats (D-01 / D-03 / D-05).

    - D-01: max_reversible_pct_change flipped "" -> 50 (the reversible magnitude cap is live;
      a reversible move steeper than -50% is refused, never clamped).
    - D-03: days_of_cover_floor flipped "" -> 42 (6-week maintain cover; a sub-cover SKU is
      refused from any spend-up — refuse-never-default).
    - D-05: conversion_benchmark ADDED = 12 to the machine mirror so the engine can read the
      conversion floor via thresholds.read (it previously lived only in state/targets.md).

    A silent revert of any dial back to "" / absent would flip the value to None and trip
    this test (the anti-tampering guarantee, T-09-01-01 / T-09-01-02).
    """
    cap = thresholds.read("max_reversible_pct_change", "CA")
    cover = thresholds.read("days_of_cover_floor", "CA")
    conversion = thresholds.read("conversion_benchmark", "CA")
    assert cap == 50.0
    assert cover == 42.0
    assert conversion == 12.0
    assert isinstance(cap, float)
    assert isinstance(cover, float)
    assert isinstance(conversion, float)


def test_default_marketplace_is_ca() -> None:
    # CA is the only active marketplace today; the default arg must resolve to it.
    assert thresholds.read("acos_ceiling_pct") == 30.0
