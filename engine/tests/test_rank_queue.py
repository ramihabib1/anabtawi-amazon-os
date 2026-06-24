"""Dollar-ranked queue estimator contract tests (D-07) — Wave 1, RED.

These are the EXECUTABLE CONTRACT that Plan 09-03 (`habibos.rank_queue`) implements
against. Until `habibos.rank_queue` and `QueueRow` exist they FAIL RED on the missing
imports — the intended Phase-9 Wave-1 baseline (the plan's verify step expects this),
NOT a defect.

Mirrors test_tacos.py: a small committed fixture (queue_candidates.json) drives real
numbers, and the EXPECTED weekly-$ impact is rebuilt here from the fixture's OWN
components (the test_tacos `_pct`-mirror pattern, T-09-01-03 mitigation) — so a
fabricated estimate cannot pass review unnoticed.

What the contract pins:
  - rows sort by expected weekly $ impact DESCENDING with None-estimate rows LAST — the
    D-07 sort key `(x.expected_weekly_usd is None, -(x.expected_weekly_usd or 0))`;
  - a candidate with an undefined / zero-denominator estimate gets
    `expected_weekly_usd is None` (NOT 0, NOT a guess — the `_ratio` None-on-undefined
    idiom: zero ad_sales_sum -> undefined ACOS -> undefined incremental sales);
  - every row carries a non-empty `provenance` string citing source + window.

Mirror signature (final shape decided in Plan 03):
    rank_queue.rank(candidates_path) -> list[QueueRow]   # sorted, dollars-first, None last

No network. No seller UUID literal anywhere here.
"""

from __future__ import annotations

from pathlib import Path

# RED on import: habibos.rank_queue and QueueRow do not exist until Plan 09-03. Wave-1 baseline.
from habibos import rank_queue
from habibos.result import QueueRow

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "queue_candidates.json"

# The undefined-estimate edge row: zero ad_sales_sum -> undefined ACOS -> expected None.
UNDEFINED_SKU = "C5-TXQU-Y67R"


def _expected_weekly_usd(delta_spend_weekly: float, ad_spend_sum: float, ad_sales_sum: float):
    """Rebuild the expected weekly-$ impact from a candidate's OWN components (mirror tacos._pct).

    The estimator's model (documented in the fixture): incremental weekly sales $ =
    delta_spend_weekly / window_acos_fraction, where window_acos_fraction =
    ad_spend_sum / ad_sales_sum. A zero ad_sales_sum -> undefined ACOS -> None (never 0).
    """
    if ad_sales_sum == 0:
        return None
    acos_fraction = ad_spend_sum / ad_sales_sum
    if acos_fraction == 0:
        return None
    return round(delta_spend_weekly / acos_fraction, 2)


def test_rows_sorted_dollars_desc_none_last() -> None:
    """D-07: rows sort by expected weekly $ DESCENDING, None-estimate rows LAST."""
    rows = rank_queue.rank(FIXTURE)
    assert all(isinstance(r, QueueRow) for r in rows)
    seq = [r.expected_weekly_usd for r in rows]
    present = [v for v in seq if v is not None]
    # Present estimates are in descending order.
    assert present == sorted(present, reverse=True)
    # Every None-estimate row sits after the last present-estimate row.
    first_none = next((i for i, v in enumerate(seq) if v is None), len(seq))
    assert all(v is None for v in seq[first_none:])


def test_undefined_estimate_is_none_not_zero() -> None:
    """An undefined (zero-denominator) estimate is None, NEVER 0 or a guess."""
    rows = rank_queue.rank(FIXTURE)
    by = {r.sku: r for r in rows}
    assert by[UNDEFINED_SKU].expected_weekly_usd is None
    # And it sorts last (a None is not silently treated as 0 in the ordering).
    assert rows[-1].expected_weekly_usd is None


def test_estimates_match_fixture_components() -> None:
    """T-09-01-03: each row's estimate equals the value rebuilt from the fixture's own components."""
    import json

    raw = json.loads(FIXTURE.read_text())
    candidates = {c["sku"]: c for c in raw["candidates"]}
    rows = rank_queue.rank(FIXTURE)
    for r in rows:
        c = candidates[r.sku]
        expected = _expected_weekly_usd(
            c["delta_spend_weekly"], c["ad_spend_sum"], c["ad_sales_sum"]
        )
        assert r.expected_weekly_usd == expected


def test_every_row_carries_provenance() -> None:
    """Every QueueRow carries a non-empty provenance string citing source + window."""
    rows = rank_queue.rank(FIXTURE)
    assert rows  # the fixture is non-empty
    for r in rows:
        assert isinstance(r.provenance, str)
        assert r.provenance.strip()
        # Cites the premium source id and a window range.
        assert "57a0cb319c" in r.provenance
        assert ".." in r.provenance


# The 1%-window-ACOS artifact: EU-Z87B-ZRBZ has ad_spend_sum=0.5 (tiny), so a $21/wk raise
# extrapolates to ~$2100/wk on the historical AVERAGE ACOS — a model artifact, not a forecast.
ARTIFACT_SKU = "EU-Z87B-ZRBZ"


def test_materiality_bar_unset_is_seeded_permissive() -> None:
    """WR-02: an unset materiality bar (None) computes every estimate as before (permissive)."""
    default_rows = {r.sku: r for r in rank_queue.rank(FIXTURE)}
    explicit_none = {r.sku: r for r in rank_queue.rank(FIXTURE, None)}
    # The tiny-denominator artifact still produces its (large) estimate when no bar is set.
    assert default_rows[ARTIFACT_SKU].expected_weekly_usd is not None
    assert (
        explicit_none[ARTIFACT_SKU].expected_weekly_usd
        == default_rows[ARTIFACT_SKU].expected_weekly_usd
    )


def test_materiality_bar_nullifies_sub_materiality_estimate() -> None:
    """WR-02: a set bar makes a sub-materiality candidate's estimate None (sorts LAST, never #1).

    EU-Z87B-ZRBZ's ad_spend_sum is 0.5; a $5 materiality bar puts it below the threshold, so its
    estimate is None (undefined — the None-on-undefined grammar) and it no longer dominates the
    ranking on a 1% window-ACOS artifact. Estimates above the bar are unaffected.
    """
    rows = {r.sku: r for r in rank_queue.rank(FIXTURE, materiality_min_ad_spend=5.0)}
    assert rows[ARTIFACT_SKU].expected_weekly_usd is None
    # A materially-spending candidate above the bar keeps its estimate.
    assert rows["FX-M8MA-MMSA"].expected_weekly_usd is not None
