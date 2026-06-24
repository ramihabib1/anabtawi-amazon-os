"""Inventory + conversion spend-UP gate (EXEC-05 / D-03 / D-05) — CLAUDE.md hard rule 3.

THE GUARD: this gate refuses any budget/bid RAISE onto a SKU whose live stock cover is
below the 6-week floor (D-03: days_of_cover_floor = 42 days) or whose live conversion is
below the benchmark (D-05: conversion_benchmark = 12%). It is the EXEC-05 guardrail that
stops GG-0DC1 (1 FBA unit) from any scale-up, and a sub-12%-converting SKU from a raise.
Only a spend-UP is guarded; a spend-DOWN auto-passes (you can always wind a winner down,
mirror gate.evaluate's spend-direction-first branch — D-06).

THE ASYMMETRY (refuse-never-default, the OPPOSITE of magnitude.py's permissive seed): a
MISSING floor REFUSES here. Where `magnitude.check` treats a None cap as "no cap configured
-> pass at any magnitude" (a future-tightening dial), this gate treats a None floor as
`GateRefusal(no_threshold_set)` (the margin-gate grammar, gate.py:198-204). A spend-up onto
an UNGUARDED SKU is a money move with no guardrail, so a missing floor is a hard refusal, not
a default 42/12 (D-03/D-05; CLAUDE.md hard rule 4 — never invent a threshold).

THE READ HAPPENS IN THE AGENT, NOT HERE (D-04): the live days_of_cover and conversion_pct are
read by the AGENT via the DataDoe / AgentCentral MCP and PASSED IN, exactly as the operator
floors are passed in. This module opens NO socket, does NO fetch, reads NO inventory file — it
is a pure predicate over (action, the SKU's live cover + conversion, the two operator floors).
A stale/missing live number arrives as None and REFUSES (no_cover_data / no_conversion_data) —
the gate never assumes cover or conversion (hard rule 4). NEVER clamps: a breaching cover or
conversion is surfaced verbatim in `breached_value`, it is not rewritten to the floor
(mirror magnitude.py / gate.py:226 strict-breach-never-clamp).

Branch order (refuse, never clamp, never default — mirror gate.evaluate):

  1. spend-DECREASING (not is_spend_increasing) -> PASS (None), with NO floor read at all
     (a spend-down cannot over-scale stock/conversion — D-06; mirror gate.py:149-156).
  2. days_of_cover_floor is None -> GateRefusal(code="no_threshold_set") — refuse-never-default
     (D-03; mirror gate.py:198-204). NEVER a default 42.
  3. days_of_cover is None (live read failed / no data) -> GateRefusal(code="no_cover_data") —
     never assume cover (hard rule 4).
  4. STRICT days_of_cover < floor -> GateRefusal(code="cover_below_floor",
     breached_value=days_of_cover, ceiling=floor). Equal-to-floor PASSES (strict `<`, mirror
     gate.py:226 strict `>`); the breaching cover is surfaced verbatim, NEVER clamped to 42.
  5. conversion_benchmark is None -> GateRefusal(code="no_threshold_set") — refuse-never-default
     (D-05). NEVER a default 12.
  6. conversion_pct is None (live read failed / no data) -> GateRefusal(code="no_conversion_data")
     — never assume conversion (hard rule 4).
  7. STRICT conversion_pct < benchmark -> GateRefusal(code="conversion_below_floor",
     breached_value=conversion_pct, ceiling=benchmark). Equal PASSES, NEVER clamped to 12.
  8. both clear -> PASS (None). This gate computes no TACOS (the margin gate owns that math),
     so a clean pass is a bare None — the typed positive grammar of magnitude.check, whose
     contract this mirrors.

WHERE THE FLOORS COME FROM: the caller reads
`thresholds.read("days_of_cover_floor", mkt)` and `thresholds.read("conversion_benchmark", mkt)`
and passes them in (Plan 01 flipped them live: 42 / 12). This module is a pure predicate over
(action, cover, conversion, floors) so the contract test can drive every branch directly without
a config file or a network read.
"""

from __future__ import annotations

from .result import GateRefusal, ProposedAction

__all__ = ["check"]


def check(
    action: ProposedAction,
    days_of_cover: float | None,
    conversion_pct: float | None,
    days_of_cover_floor: float | None,
    conversion_benchmark: float | None,
) -> None | GateRefusal:
    """Refuse a spend-UP onto a sub-cover / sub-conversion SKU (never clamp, never default).

    `days_of_cover` / `conversion_pct` are the SKU's LIVE numbers the AGENT read via MCP
    (D-04) and handed in (either may be None when the live read failed). `days_of_cover_floor`
    / `conversion_benchmark` are the operator floors the caller read from
    `thresholds.read(...)` and handed in (either may be None when the key is unset). The gate
    opens no socket — it only decides. See the module docstring for the full branch order.

    Returns None on PASS; a typed GateRefusal on any breach / missing floor / missing live
    number. NEVER clamps a breaching value, NEVER substitutes a default floor.
    """
    # 1. Spend-direction FIRST — a spend-decrease auto-passes with NO floor read (D-06;
    #    a spend-down cannot over-scale stock or conversion — mirror gate.py:149-156).
    if not action.is_spend_increasing:
        return None

    # 2. Cover floor — None REFUSES, never a default 42 (refuse-never-default, D-03;
    #    the asymmetry vs magnitude's permissive seed — mirror gate.py:198-204).
    if days_of_cover_floor is None:
        return GateRefusal(
            "no threshold set — days_of_cover_floor unset",
            code="no_threshold_set",
        )

    # 3. Live cover missing -> refuse, never assume cover (hard rule 4).
    if days_of_cover is None:
        return GateRefusal(
            "no data — days_of_cover unavailable",
            code="no_cover_data",
        )

    # 4. STRICT cover breach (equal-to-floor passes); surface the breaching cover verbatim,
    #    NEVER clamp it to the floor (mirror gate.py:226 strict `>` / magnitude never-clamp).
    if days_of_cover < days_of_cover_floor:
        return GateRefusal(
            "stock cover below the 6-week floor",
            code="cover_below_floor",
            breached_value=days_of_cover,
            ceiling=days_of_cover_floor,
        )

    # 5. Conversion benchmark — None REFUSES, never a default 12 (refuse-never-default, D-05).
    if conversion_benchmark is None:
        return GateRefusal(
            "no threshold set — conversion_benchmark unset",
            code="no_threshold_set",
        )

    # 6. Live conversion missing -> refuse, never assume conversion (hard rule 4).
    if conversion_pct is None:
        return GateRefusal(
            "no data — conversion_pct unavailable",
            code="no_conversion_data",
        )

    # 7. STRICT conversion breach (equal passes); surface the breaching conversion verbatim,
    #    NEVER clamp it to the benchmark.
    if conversion_pct < conversion_benchmark:
        return GateRefusal(
            "conversion below the benchmark floor",
            code="conversion_below_floor",
            breached_value=conversion_pct,
            ceiling=conversion_benchmark,
        )

    # 8. Both clear -> PASS. This gate computes no TACOS (the margin gate owns that math),
    #    so a clean pass is a bare None — the typed positive grammar of magnitude.check.
    return None
