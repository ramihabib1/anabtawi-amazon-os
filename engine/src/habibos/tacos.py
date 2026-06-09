"""TACOS-by-SKU money-logic core: parse + classify (CLAUDE.md hard rule 4).

This is the ONLY hand-written, pytest-covered money-touching module in the phase.
Its anti-fabrication contract:

  - The premium "Profit by SKU & Date" source (57a0cb319c) computes acos/tacos/roi
    at DAILY grain. There is NO per-SKU trailing-WINDOW ratio column, and DataDoe's
    server-side aggregations (sum/avg/...) cannot correctly produce one (averaging a
    daily ratio is wrong). Per the operator-approved A1 decision (2026-06-09), the
    window ratio is computed HERE, by this reviewed core, from the source's own
    window-summed components — applying the source's verbatim definitions
    (result.DEFINITIONS) to the sums. This is window aggregation, NOT re-deriving the
    metric: the definitions are unchanged; only the components are summed over the
    window (a server-side `groupBy sku` + `sum`). We never invent a definition and
    never substitute a number.
  - Window ratios: tacos = Σad_spend / Σtotal_sales, acos = Σad_spend / Σad_sales,
    roi = Σprofit / Σtotal_cost — each ×100 (percent, A2). A zero denominator yields
    None ("no sales"), never 0 or a guess.
  - The arithmetic beyond the ratio is two comparisons: the TACOS<=ACOS sanity guard
    (D-04) and the threshold-breach compare (D-07).
  - A catalog SKU absent from the export -> a SkuRow with None ratios + "no data"
    (D-10), distinct from a present SKU with zero sales ("no sales").
  - An empty or FAILED export -> a typed Refusal carrying the export id (D-11 /
    TRUST-01), never a substituted number.
  - A missing ceiling (thresholds.read -> None) -> "no threshold set" for that flag
    while the numeric value still renders (D-08).

Schema drift (RESEARCH Pitfall 1): parse() pydantic-validates the REQUIRED columns
and raises on a mismatch (the caller surfaces a Refusal). extra="ignore" tolerates
DataDoe's utility columns; a missing/renamed REQUIRED column still fails loud.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl
from pydantic import BaseModel, ConfigDict, ValidationError

from . import thresholds
from .result import PREMIUM_SOURCE, Answer, Refusal, SkuRow

# The premium Profit-by-SKU & Date source (docs/datadoe-source-map.md §3a, 57a0cb319c).
PREMIUM_SOURCE_ID = "57a0cb319c"

# The window-summed component columns the money logic reads. These are produced by a
# server-side `groupBy sku` + `sum` export (aliased *_sum to avoid DataDoe's
# ALIAS_COLLISION with the source column names). The ratio is computed from these
# sums per the A1 decision — see the module docstring.
EXPECTED_COLUMNS = (
    "sku",
    "ad_spend_sum",
    "ad_sales_sum",
    "total_sales_sum",
    "profit_sum",
    "total_cost_sum",
    "currency",
)


class _PremiumRow(BaseModel):
    """Pydantic validation of one window-aggregated export row — fail loud on drift.

    extra="ignore" tolerates DataDoe's prepended utility columns and the extra
    `units_sum`, while a missing/renamed REQUIRED column (e.g. `sku`) still raises
    (RESEARCH Pitfall 1) rather than being silently coerced into the money logic.
    """

    model_config = ConfigDict(extra="ignore")

    sku: str
    ad_spend_sum: float | None
    ad_sales_sum: float | None
    total_sales_sum: float | None
    profit_sum: float | None
    total_cost_sum: float | None
    currency: str


def parse(artifact: str | Path | bytes, status: str) -> pl.DataFrame | Refusal:
    """Read a downloaded window-aggregated export artifact into a validated frame, or Refuse.

    status == "FAILED" -> Refusal("failed_export") (D-11): a failed export is never a
    substituted number. Otherwise read the local artifact (path or bytes) into a polars
    DataFrame and pydantic-validate the REQUIRED columns; a column mismatch raises a
    ValueError (the caller surfaces a Refusal) — required columns are never coerced.
    """
    if status == "FAILED":
        return Refusal("Export failed — no data.", "failed_export")

    if isinstance(artifact, bytes):
        frame = pl.read_csv(artifact)
    else:
        frame = pl.read_csv(Path(artifact))

    # Validate the required column set (and per-row types). On drift this raises
    # ValidationError; the caller (CLI) maps it to a Refusal — never coerce.
    try:
        for row in frame.to_dicts():
            _PremiumRow.model_validate(row)
    except ValidationError as exc:  # noqa: BLE001 - surface drift, never coerce (Pitfall 1)
        raise ValueError(f"Premium export schema mismatch (drift?): {exc}") from exc

    return frame


def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    """Window ratio as a percent, or None when the denominator is zero/missing.

    None means "no sales / undefined" — NEVER 0 or a guess. Applies the source's own
    definition (DEFINITIONS) to window-summed components (A1, operator-approved).
    """
    if numerator is None or denominator is None or denominator == 0:
        return None
    return round(numerator / denominator * 100, 1)


def _present_flag(value: float | None, ceiling: float | None) -> str:
    """Flag for a SKU PRESENT in the export — never invents a threshold (D-08/TRUST-02)."""
    if ceiling is None:
        return "no threshold set"  # missing ceiling -> refuse the flag, never a default
    if value is None:
        return "no sales"  # present but zero-denominator -> distinct from absent "no data"
    return "breach" if value > ceiling else "ok"  # strict: value == ceiling is "ok"


def classify(
    frame: pl.DataFrame,
    export_id: str,
    window_from: str,
    window_to: str,
    catalog_skus: list[str],
    marketplace: str = "CA",
) -> Answer | Refusal:
    """Turn a validated window-aggregated frame + catalog into the typed TACOS-by-SKU answer.

    Empty frame -> Refusal("empty_export") carrying export_id (D-11). For each catalog
    SKU: absent from the frame -> None ratios + "no data" (D-10); present -> COMPUTE the
    window acos/tacos/roi from the summed components (A1, operator-approved), set suspect
    on a TACOS>ACOS inversion (D-04), and flag acos/tacos against the operator ceilings
    (D-07/D-08). A present SKU with zero sales -> None ratios + "no sales" (distinct from
    absent "no data"). Rows sort by TACOS descending with no-ratio rows last (D-05). The
    returned Answer always cites the export id (provenance, D-06 / TRUST-01).
    """
    if frame.height == 0:
        return Refusal("Export returned no rows — no data.", "empty_export", export_id)

    acos_ceiling = thresholds.read("acos_ceiling_pct", marketplace)  # None means refuse flag (D08)
    tacos_ceiling = thresholds.read("tacos_ceiling_pct", marketplace)

    present = {r["sku"]: r for r in frame.to_dicts()}
    rows: list[SkuRow] = []
    for sku in catalog_skus:
        r = present.get(sku)
        if r is None:  # D-10: catalog SKU absent from export -> "no data", never 0/blank
            rows.append(SkuRow(sku, None, None, None, "no data", "no data"))
            continue
        # Window ratios computed from the source's summed components (A1, D-03 amended).
        acos = _ratio(r["ad_spend_sum"], r["ad_sales_sum"])
        tacos = _ratio(r["ad_spend_sum"], r["total_sales_sum"])
        roi = _ratio(r["profit_sum"], r["total_cost_sum"])
        suspect = tacos is not None and acos is not None and tacos > acos  # D-04 sanity guard
        rows.append(
            SkuRow(
                seller_sku=sku,
                acos=acos,
                tacos=tacos,
                roi=roi,
                acos_flag=_present_flag(acos, acos_ceiling),
                tacos_flag=_present_flag(tacos, tacos_ceiling),
                suspect=suspect,
            )
        )

    rows.sort(key=lambda x: (x.tacos is None, -(x.tacos or 0)))  # D-05: TACOS desc, no-ratio last
    return Answer(
        rows=rows,
        export_id=export_id,
        window_from=window_from,
        window_to=window_to,
        source=PREMIUM_SOURCE,
    )
