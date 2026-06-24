"""Inventory + conversion spend-up gate contract tests (D-03 / D-05) — Wave 1, RED.

These are the EXECUTABLE CONTRACT that Plan 09-02 (`habibos.cover_gate`) implements
against. Until `habibos.cover_gate` exists they FAIL RED on the missing import — the
intended Phase-9 Wave-1 baseline (the plan's verify step expects this), NOT a defect.

The cover gate is a pure predicate over (action, the SKU's live cover + conversion, the
two operator floors) — mirroring `magnitude.check(action, cap)`'s socket-free shape and
`gate.py`'s refuse-never-default / strict-breach / spend-direction-first grammar. The
FINAL signature is decided in Plan 02; this contract pins the BEHAVIOR each branch must
exhibit. Mirror used here:

    cover_gate.check(
        action,                 # ProposedAction; only spend-UP (delta_spend > 0) is guarded
        days_of_cover,          # the SKU's live (on-hand + inbound) / velocity, or None
        conversion_pct,         # the SKU's live conversion %, or None
        days_of_cover_floor,    # thresholds.read("days_of_cover_floor", mkt) -> 42.0 or None
        conversion_benchmark,   # thresholds.read("conversion_benchmark", mkt) -> 12.0 or None
    ) -> None | GateRefusal

What the contract pins (refuse, NEVER clamp, NEVER default — D-03/D-05):
  (1) spend-UP, cover < 42 -> GateRefusal(code="cover_below_floor") whose breached_value is
      the ACTUAL cover number, NEVER clamped to 42 (mirror magnitude.py's never-clamp).
  (2) cover EXACTLY == 42 -> PASS (None / GateVerdict): strict `<` breach, equal passes
      (mirror gate.py:226).
  (3) spend-UP, conversion < 12 -> GateRefusal(code="conversion_below_floor") surfacing the
      actual conversion %.
  (4) a MISSING floor (thresholds.read -> None) -> GateRefusal(code="no_threshold_set"),
      never a default (refuse-never-default, D-03 — the asymmetry vs the magnitude cap).
  (5) a spend-DOWN (delta_spend <= 0) -> PASS without reading any floor (the cover gate only
      guards spend-UP, mirror gate.evaluate's spend-direction-first branch).
  + the named edge: GG-0DC1 at 1 FBA unit (cover far below 42) -> cover_below_floor refusal.

No network. No seller UUID literal anywhere here.
"""

from __future__ import annotations

# RED on import: habibos.cover_gate does not exist until Plan 09-02. The intended Wave-1 baseline.
from habibos import cover_gate
from habibos.result import GateRefusal, ProposedAction

# The two live Phase-9 floors (Plan 09-01 flipped them live in thresholds.toml).
COVER_FLOOR = 42.0
CONVERSION_FLOOR = 12.0


def _spend_up(sku: str = "GG-0DC1-SKHG", action_type: str = "budget_up") -> ProposedAction:
    """A spend-INCREASING action (delta_spend > 0) — the only direction the cover gate guards."""
    return ProposedAction(sku=sku, action_type=action_type, delta_spend=25.0)


def _spend_down(sku: str = "FX-M8MA-MMSA") -> ProposedAction:
    """A reversible spend-DECREASING action (delta_spend <= 0) — the cover gate must not guard it."""
    return ProposedAction(sku=sku, action_type="bid_down", delta_spend=-18.0)


def test_cover_below_floor_refuses_never_clamps() -> None:
    """(1) spend-UP with cover < 42 -> cover_below_floor; breached_value is the ACTUAL cover, not 42."""
    refusal = cover_gate.check(
        _spend_up(),
        days_of_cover=30.0,
        conversion_pct=20.0,
        days_of_cover_floor=COVER_FLOOR,
        conversion_benchmark=CONVERSION_FLOOR,
    )
    assert isinstance(refusal, GateRefusal)
    assert refusal.code == "cover_below_floor"
    # NEVER clamps: the refusal surfaces the breaching cover verbatim, it does not rewrite it to 42.
    assert refusal.breached_value == 30.0
    assert refusal.breached_value != COVER_FLOOR


def test_cover_exactly_at_floor_passes() -> None:
    """(2) cover EXACTLY == 42 -> PASS (None): strict `<` breach, equal passes (mirror gate.py:226)."""
    result = cover_gate.check(
        _spend_up(),
        days_of_cover=42.0,
        conversion_pct=20.0,
        days_of_cover_floor=COVER_FLOOR,
        conversion_benchmark=CONVERSION_FLOOR,
    )
    assert result is None


def test_conversion_below_floor_refuses() -> None:
    """(3) spend-UP converting below 12% -> conversion_below_floor, surfacing the actual conversion %."""
    refusal = cover_gate.check(
        _spend_up(),
        days_of_cover=90.0,
        conversion_pct=8.0,
        days_of_cover_floor=COVER_FLOOR,
        conversion_benchmark=CONVERSION_FLOOR,
    )
    assert isinstance(refusal, GateRefusal)
    assert refusal.code == "conversion_below_floor"
    # Surfaces the actual conversion %, never clamped to the 12 benchmark.
    assert refusal.breached_value == 8.0


def test_missing_floor_refuses_never_defaults() -> None:
    """(4) a MISSING floor (None) -> no_threshold_set, never a default (refuse-never-default, D-03)."""
    refusal = cover_gate.check(
        _spend_up(),
        days_of_cover=10.0,
        conversion_pct=20.0,
        days_of_cover_floor=None,  # thresholds.read returned None -> refuse, never assume 42
        conversion_benchmark=CONVERSION_FLOOR,
    )
    assert isinstance(refusal, GateRefusal)
    assert refusal.code == "no_threshold_set"


def test_spend_down_passes_without_reading_floor() -> None:
    """(5) a spend-DOWN (delta_spend <= 0) -> PASS; the cover gate only guards spend-UP (D-06 shape)."""
    # Even with floors omitted entirely (None) and a catastrophic cover, a spend-DOWN passes:
    # the spend-direction branch is checked FIRST, before any floor read (mirror gate.evaluate).
    result = cover_gate.check(
        _spend_down(),
        days_of_cover=1.0,
        conversion_pct=0.0,
        days_of_cover_floor=None,
        conversion_benchmark=None,
    )
    assert result is None


def test_gg0dc1_one_unit_cover_below_floor() -> None:
    """Named edge: GG-0DC1 at 1 FBA unit (cover far below 42) -> cover_below_floor refusal."""
    # 1 unit over the window's velocity is a tiny cover (well under the 42-day floor).
    one_unit_cover = 2.0
    refusal = cover_gate.check(
        _spend_up(sku="GG-0DC1-SKHG", action_type="bid_up"),
        days_of_cover=one_unit_cover,
        conversion_pct=25.0,
        days_of_cover_floor=COVER_FLOOR,
        conversion_benchmark=CONVERSION_FLOOR,
    )
    assert isinstance(refusal, GateRefusal)
    assert refusal.code == "cover_below_floor"
    assert refusal.breached_value == one_unit_cover
