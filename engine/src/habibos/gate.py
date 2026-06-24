"""Margin-tiered safety-gate money core (GATE-01..05 + D-03/D-04) — CLAUDE.md hard rule 3.

This is the hand-written, pytest-covered money core — the structural twin of `tacos.py`.
Per CLAUDE.md hard rule 3, money-touching logic is hand-written, reviewed and tested, NEVER
auto-generated and NEVER computed in prose. Per hard rule 4 it never invents a number or a
threshold: a missing SKU, a 0/null COGS, a zero-sales window, an unset floor, or an
over-ceiling spend-up each return a typed `GateRefusal` (never a default, never a clamp).

The anti-fabrication grammar is cloned from `tacos.py`:

  - GATE-01 / D-03 (pre-ad contribution margin): a SKU's window contribution margin is
    computed from the premium source's window-summed components with `ad_spend_sum` ADDED
    BACK, because `profit_sum` is POST-ad (Path A back-out). CM% =
    (profit_sum + ad_spend_sum) / total_sales_sum * 100. A zero/missing denominator yields
    None ("no sales / undefined") — NEVER 0 or a guess (this mirrors `tacos._ratio`).
  - D-01 (per-SKU ceiling): ceiling = CM% - floor, where the floor is the operator's single
    `min_net_margin_pct` (NOT a per-tier table — D-01a). An unset floor (`thresholds.read`
    -> None) is a `no_threshold_set` refusal on EVERY spend-up, never a default.
  - D-06 (worst-case projection): a spend-up's projected TACOS holds window sales flat and
    adds the caller-supplied `delta_spend` to ad spend — the worst case. A spend-DECREASE
    cannot breach a TACOS ceiling, so it auto-passes with no projection and no config read.
  - GATE-04 (strict breach, never clamp): the breach test is the strict `projected > ceiling`
    (equal passes — mirror `tacos._present_flag`). An over-ceiling spend-up returns a
    `GateRefusal` naming the breaching `projected` value + its `source`; the breaching value
    is NEVER rewritten / clamped to the ceiling.
  - GATE-05 / D-05 (explicit catalog): the canonical SKU set is read from the machine-readable
    `sku_catalog.toml` (tomllib). A SKU absent there is a `sku_not_in_catalog` refusal — there
    is NO silent export-rows fallback.

The window-sum reader is REUSED from `tacos.py` (`parse`, `PREMIUM_SOURCE_ID`) — the gate
does not re-roll a CSV reader; `profit_sum`, `ad_spend_sum`, `total_sales_sum` are all in
that pydantic-validated, fail-loud-on-drift column set.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

import polars as pl

from . import thresholds
from .result import PREMIUM_SOURCE, GateRefusal, GateVerdict, ProposedAction
from .tacos import PREMIUM_SOURCE_ID, parse  # noqa: F401 — REUSE the validated reader / provenance

__all__ = [
    "PREMIUM_SOURCE_ID",
    "parse",
    "contribution_margin_pct",
    "ceiling_tacos_pct",
    "projected_tacos_pct",
    "evaluate",
]


def contribution_margin_pct(
    profit_sum: float | None,
    ad_spend_sum: float | None,
    total_sales_sum: float | None,
) -> float | None:
    """Pre-ad contribution margin as a percent, or None when undefined (GATE-01 / D-03).

    `ad_spend_sum` is ADDED BACK because `profit_sum` is POST-ad (Path A back-out): the
    pre-ad contribution is (profit_sum + ad_spend_sum). Clones `tacos._ratio`'s
    None-on-zero-denominator grammar exactly — a zero or missing `total_sales_sum`
    (divide-by-zero, Pitfall 4) returns None ("no sales / undefined"), NEVER 0 or a guess.
    A missing profit/ad-spend component is likewise undefined -> None, never coerced.
    """
    if total_sales_sum is None or total_sales_sum == 0:
        return None  # divide-by-zero / no sales -> undefined, never 0 (Pitfall 4)
    if profit_sum is None or ad_spend_sum is None:
        return None  # missing component -> undefined, never coerced
    return round((profit_sum + ad_spend_sum) / total_sales_sum * 100, 1)  # ad_spend ADDED BACK (D-03)


def ceiling_tacos_pct(cm_pct: float, floor: float) -> float:
    """Per-SKU TACOS ceiling = CM% - floor (D-01).

    The caller refuses earlier if either input is None (no_margin / no_threshold_set), so
    this pure function takes two floats. There is no per-tier ceiling table (D-01a): one
    operator floor minus the SKU's own live contribution margin.
    """
    return round(cm_pct - floor, 1)


def projected_tacos_pct(
    ad_spend_sum: float | None,
    delta_spend: float,
    total_sales_sum: float | None,
) -> float | None:
    """Worst-case projected TACOS for a spend-up, or None on zero/missing sales (D-06).

    Holds window sales flat (the worst case) and adds the caller-supplied `delta_spend` to
    ad spend: (ad_spend_sum + delta_spend) / total_sales_sum * 100. Clones the
    None-on-zero-denominator grammar — a zero/missing `total_sales_sum` returns None, never 0.

    UNIT CONTRACT (CR-02): `delta_spend` MUST be expressed in the SAME window as `ad_spend_sum`
    and `total_sales_sum` (window CAD, NOT a weekly figure). Feeding a weekly delta against a
    30-day window under-projects TACOS ~4x. The caller (queue_run._spend_up_refusal) scales any
    weekly delta to the window before constructing the ProposedAction.
    """
    if total_sales_sum is None or total_sales_sum == 0:
        return None
    if ad_spend_sum is None:
        return None
    return round((ad_spend_sum + delta_spend) / total_sales_sum * 100, 1)


def _load_catalog(catalog_path: str | Path) -> dict:
    """Read the machine-readable per-SKU catalog (the [sku] table) with tomllib (D-05).

    The catalog source is EXPLICIT — a missing file raises (FileNotFoundError), never a
    silent fallback. Returns the `[sku."<SKU>"] -> {asin, tier, cogs}` mapping; an absent
    SKU is the caller's `sku_not_in_catalog` refusal, not a default.
    """
    with Path(catalog_path).open("rb") as fh:
        data = tomllib.load(fh)
    return data.get("sku", {})


def evaluate(
    frame: pl.DataFrame,
    action: ProposedAction,
    catalog_path: str | Path,
    marketplace: str | None = None,
) -> GateVerdict | GateRefusal:
    """Evaluate a ProposedAction against its SKU's margin-derived TACOS ceiling.

    Branch order (refuse, never clamp, never default on every missing/over-ceiling input):

      1. spend-DECREASING (not is_spend_increasing) -> GateVerdict(auto_pass=True), NO config
         or catalog read (a spend-down cannot breach a TACOS ceiling — D-06, Pitfall 5).
      2. zero-sales window (the SKU's row in the frame has total_sales_sum == 0) -> CM%
         undefined -> GateRefusal(code="no_margin", D-04). Checked from the window sums
         before catalog membership so an export-present zero-sales SKU refuses for the RIGHT
         reason (no margin), not "not in catalog".
      3. SKU absent from the catalog -> GateRefusal(code="sku_not_in_catalog", D-05). No
         silent export-rows fallback.
      4. catalog cogs <= 0 / null / missing -> GateRefusal(code="no_margin", D-03/D-04):
         an unreliable landed COGS cannot anchor a margin.
      5. SKU absent from the export frame (no window sums) -> GateRefusal(code="no_margin"):
         no components -> CM% undefined.
      6. floor = thresholds.read("min_net_margin_pct", marketplace); None ->
         GateRefusal(code="no_threshold_set", D-07) on every spend-up — never a default.
      7. cm = contribution_margin_pct(...) (None -> no_margin); ceiling = cm - floor;
         projected = projected_tacos_pct(...); STRICT projected > ceiling ->
         GateRefusal(code="over_ceiling", breached_value=projected, ceiling=ceiling,
         source=PREMIUM_SOURCE) naming the breaching number — NEVER a clamped GateVerdict.
         Otherwise GateVerdict(projected_tacos=projected, ceiling=ceiling,
         contribution_margin=cm).
    """
    mkt = marketplace if marketplace is not None else action.marketplace

    # 1. Spend-direction FIRST — a spend-decrease auto-passes with no read (Pitfall 5, D-06).
    if not action.is_spend_increasing:
        return GateVerdict(
            projected_tacos=None,
            ceiling=None,
            contribution_margin=None,
            auto_pass=True,
        )

    # Pull this SKU's window-summed components from the validated frame (if present).
    present = {r["sku"]: r for r in frame.to_dicts()}
    row = present.get(action.sku)

    # 2. A present SKU with a zero-sales window -> CM% undefined -> no_margin (D-04), checked
    #    before catalog membership so an export-present zero-sales SKU refuses for the right
    #    reason rather than "not in catalog".
    if row is not None and (row["total_sales_sum"] is None or row["total_sales_sum"] == 0):
        return GateRefusal(
            "no margin — zero-sales window, contribution margin undefined",
            code="no_margin",
            source=PREMIUM_SOURCE,
        )

    # 3. Catalog membership — explicit, no silent fallback (D-05).
    catalog = _load_catalog(catalog_path)
    entry = catalog.get(action.sku)
    if entry is None:
        return GateRefusal(
            "SKU not in catalog table",
            code="sku_not_in_catalog",
        )

    # 4. Unreliable / zero / missing catalog COGS -> no margin (D-03/D-04).
    cogs = entry.get("cogs")
    if cogs is None or cogs <= 0:
        return GateRefusal(
            "no margin — unreliable / zero catalog COGS",
            code="no_margin",
            source=PREMIUM_SOURCE,
        )

    # 5. SKU absent from the export frame -> no window components -> CM% undefined (no_margin).
    if row is None:
        return GateRefusal(
            "no margin — SKU absent from the premium export window",
            code="no_margin",
            source=PREMIUM_SOURCE,
        )

    # 6. Floor read — None -> no_threshold_set on every spend-up, never a default (D-07).
    floor = thresholds.read("min_net_margin_pct", mkt)
    if floor is None:
        return GateRefusal(
            "no threshold set — min_net_margin_pct unset",
            code="no_threshold_set",
        )

    # 7. Compute CM% -> ceiling -> projected; strict breach refuses (never clamps).
    cm = contribution_margin_pct(
        row["profit_sum"], row["ad_spend_sum"], row["total_sales_sum"]
    )
    if cm is None:
        return GateRefusal(
            "no margin — contribution margin undefined",
            code="no_margin",
            source=PREMIUM_SOURCE,
        )
    ceiling = ceiling_tacos_pct(cm, floor)
    projected = projected_tacos_pct(
        row["ad_spend_sum"], action.delta_spend, row["total_sales_sum"]
    )
    if projected is None:
        return GateRefusal(
            "no margin — projected TACOS undefined",
            code="no_margin",
            source=PREMIUM_SOURCE,
        )
    if projected > ceiling:  # STRICT: equal passes (mirror tacos._present_flag)
        return GateRefusal(
            "projected TACOS breaches the SKU's margin-derived ceiling",
            code="over_ceiling",
            breached_value=projected,
            ceiling=ceiling,
            source=PREMIUM_SOURCE,
        )
    return GateVerdict(
        projected_tacos=projected,
        ceiling=ceiling,
        contribution_margin=cm,
    )
