"""Seeded-permissive bounded-% magnitude cap (SC-5 / D-01 / D-02) — CLAUDE.md hard rule 3.

THE MECHANISM (D-02 — build-the-refusal-path-THEN-seed-permissive): a reversible move whose
bounded-% magnitude exceeds a CONFIGURED cap is a `GateRefusal(over_cap)` — and it NEVER
clamps the magnitude to the limit (mirrors gate.py:226-233 / GATE-04's strict-breach-never-
clamp discipline). The refusal surfaces the BREACHING magnitude verbatim (hard rule 4); the
caller does not silently rewrite a 90% move to 50%.

THE SEED (D-01 / D-02 — the deliberate asymmetry vs the margin gate): the cap is SEEDED
PERMISSIVE. When `max_reversible_pct_change` is None (the live seed — the
`engine/config/thresholds.toml` key is absent/empty), a reversible move passes at ANY
magnitude (returns None). This is the OPPOSITE of the margin-gate floor, where a None
threshold REFUSES: here None means "no cap configured -> permissive", matching the operator's
D-01 decision that all reversible actions pass today (a reversible move can be undone, so the
magnitude cap is a future tightening dial, not a launch guard). T-08-08 is ACCEPTED on this
basis. The mechanism is BUILT + TESTED now so tightening later is a `thresholds.toml` edit,
not a code change.

WHERE THE CAP COMES FROM: the caller reads
`thresholds.read("max_reversible_pct_change", marketplace)` and passes it in. This module is
a pure predicate over (action, cap) so the contract test can drive both branches directly
without a config file. NO socket — pure typed gate.
"""

from __future__ import annotations

from .result import GateRefusal, ProposedAction


def _bounded_pct(action: ProposedAction) -> float | None:
    """The reversible move's bounded-% magnitude, read from action.params['pct_change'].

    The caller computes the before->after % change (e.g. a bid delta vs the prior bid) and
    hands it in `params["pct_change"]`. A missing/None pct_change -> None (no magnitude to
    check); the magnitude here is the absolute size of the move, so a -90% and a +90% move
    are both 90% against the cap.
    """
    raw = (action.params or {}).get("pct_change")
    if raw is None:
        return None
    return abs(float(raw))


def check(
    action: ProposedAction, max_reversible_pct_change: float | None = None
) -> None | GateRefusal:
    """Refuse an over-cap reversible move (never clamp); seeded permissive when the cap is None.

    - cap is None (the live seed, D-02): PERMISSIVE -> return None (pass at ANY magnitude).
      This is the deliberate asymmetry vs the margin gate (None there REFUSES) — documented
      in the module docstring.
    - cap IS set and the move's bounded-% (abs) exceeds it (STRICT `> cap`, equal passes —
      mirror GATE-04): `GateRefusal("reversible move exceeds the magnitude cap",
      code="over_cap", breached_value=<pct>, ceiling=<cap>)`. NEVER clamps to the cap.
    - cap is set but there is no pct to check (params lack pct_change): return None (nothing
      to breach).
    """
    if max_reversible_pct_change is None:
        return None  # seeded permissive (D-01/D-02) — no cap configured, pass at any magnitude

    pct = _bounded_pct(action)
    if pct is None:
        return None  # no magnitude to check -> nothing to breach

    if pct > max_reversible_pct_change:  # STRICT breach (equal passes), never clamp
        return GateRefusal(
            "reversible move exceeds the magnitude cap",
            code="over_cap",
            breached_value=pct,
            ceiling=max_reversible_pct_change,
        )
    return None
