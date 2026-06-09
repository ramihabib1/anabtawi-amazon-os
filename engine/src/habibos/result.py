"""Typed trust-spine results — the project's core anti-fabrication guarantee (D-02).

Every no-data / empty / failed / missing-threshold edge returns one of these typed
results, NEVER a bare None, a fabricated 0, a blank, or a swallowed exception
(RESEARCH §Pattern 2, Anti-Patterns; SOUL.md). A missing SKU is a SkuRow with
None ratios ("no data"), an empty/failed export is a Refusal, and a successful answer
is an Answer that always cites its provenance (export_id, source, verbatim definitions).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Verbatim from docs/datadoe-source-map.md §3a — definitions are surfaced, NEVER
# recomputed in Python (D-03). The ratios are READ as the premium source's own columns.
DEFINITIONS: dict[str, str] = {
    "acos": "ad_spend / 14-day ad sales, %",
    "tacos": "ad_spend / total_sales, %",
    "roi": "profit / total_cost, %",
}

# Provenance string for the premium Profit-by-SKU & Date source (D-06).
PREMIUM_SOURCE = "DataDoe premium Profit by SKU & Date (57a0cb319c)"


@dataclass(frozen=True)
class Refusal:
    """A typed refusal surfaced verbatim to the operator — never a substituted number."""

    reason: str  # human-readable, surfaced verbatim to the operator
    code: str  # "empty_export" | "failed_export" | "missing_threshold"
    export_id: str | None = None


@dataclass(frozen=True)
class SkuRow:
    """One per-SKU row.

    None acos/tacos/roi means "no data (not in premium export)" (D-10) — distinct from
    0 (which would mean "no spend"). The flag columns carry "ok" | "breach" |
    "no threshold set" | "no data"; suspect marks a TACOS>ACOS inversion (D-04).
    """

    seller_sku: str
    acos: float | None
    tacos: float | None
    roi: float | None
    acos_flag: str
    tacos_flag: str
    suspect: bool = False


@dataclass(frozen=True)
class Answer:
    """A successful, provenance-cited answer (D-06).

    export_id is non-optional: a successful Answer always names the export it was
    computed from. definitions defaults to the verbatim source-map definitions.
    """

    rows: list[SkuRow]
    export_id: str
    window_from: str
    window_to: str
    source: str = PREMIUM_SOURCE
    definitions: dict[str, str] = field(default_factory=lambda: dict(DEFINITIONS))
