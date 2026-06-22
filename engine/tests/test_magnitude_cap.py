"""SC-5 / D-02 magnitude-cap contract tests (Wave 0, RED).

These are the EXECUTABLE CONTRACT that Plan 02 (`habibos.magnitude`) implements against.
Until `habibos.magnitude` exists they FAIL RED on the missing import — the intended Wave-0
state (08-VALIDATION.md 08-02·T3), NOT a failure to fix.

What the contract pins (D-02 — build-the-refusal-path-then-seed-permissive):
  - test_magnitude_cap_refuses_when_set: when a bounded-% cap IS configured and a reversible
    move exceeds it -> GateRefusal(code="over_cap"). The cap REFUSES, it NEVER clamps the
    magnitude to the limit (mirrors GATE-04's never-clamp discipline). The mechanism exists
    and is tested.
  - test_magnitude_cap_seeded_permissive: when the cap is ABSENT / None (the live seed, D-02)
    -> the reversible move passes at ANY magnitude (returns None). Live behavior matches D-01
    (permissive for all reversible actions); tightening later is a config dial, not code.

No network. No seller UUID literal anywhere here.
"""

from __future__ import annotations

# RED on import: habibos.magnitude does not exist until Plan 02. The intended Wave-0 baseline.
from habibos import magnitude
from habibos.result import GateRefusal, ProposedAction


def _bid_down(pct: float) -> ProposedAction:
    """A reversible bid-down whose params carry the before/after for a bounded-% check."""
    return ProposedAction(
        sku="X",
        action_type="bid_down",
        delta_spend=0,
        entity_type="targets",
        entity_id="TGT-2000000000007",
        params={"pct_change": pct},
    )


def test_magnitude_cap_refuses_when_set() -> None:
    """SC-5/D-02: cap configured + over-cap reversible -> GateRefusal(over_cap), never clamps."""
    # A cap of 50% configured; a 90% bid-down exceeds it.
    refusal = magnitude.check(_bid_down(90.0), max_reversible_pct_change=50.0)
    assert isinstance(refusal, GateRefusal)
    assert refusal.code == "over_cap"
    # NEVER clamps: the refusal surfaces the breaching magnitude, it does not rewrite it to 50.
    assert refusal.breached_value == 90.0


def test_magnitude_cap_seeded_permissive() -> None:
    """SC-5/D-02: cap absent/None (the live seed) -> reversible passes at any magnitude (None)."""
    # The seeded-permissive default: no cap set -> a 95% bid-down passes cleanly.
    result = magnitude.check(_bid_down(95.0), max_reversible_pct_change=None)
    assert result is None
