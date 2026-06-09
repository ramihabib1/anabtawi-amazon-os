"""TACOS-by-SKU money-logic tests (PROF-01, A1, D-03, D-04, D-05, D-07, D-08, D-10, D-11, A2).

Consumed by plan 02-02; re-pointed to the REAL captured export in plan 02-03.
Proves the hand-written money-logic core (`habibos.tacos.parse` / `classify`):
  - window acos/tacos/roi are COMPUTED from the source's window-summed components,
    applying the source's verbatim definitions (A1, operator-approved 2026-06-09 —
    DataDoe has no per-SKU window-ratio column and cannot aggregate a ratio server-side);
  - the percentage unit convention is pinned so the breach compare is not 100x off (A2);
  - a window tacos > acos row is flagged suspect (D-04);
  - rows render sorted by tacos descending, no-ratio rows last (D-05);
  - a catalog SKU absent from the export shows None ratios + "no data" (D-10), distinct
    from a PRESENT SKU with zero sales -> "no sales";
  - an empty/failed export returns a typed Refusal carrying the export id (D-11/TRUST-01);
  - a SKU above a set ceiling flags "breach"; an unset ceiling flags "no threshold set"
    while the number still renders (D-07/D-08).

FIXTURE: tests/fixtures/profit_by_sku_30d.csv is the REAL server-side `groupBy sku` +
`sum` export (CA, trailing 30d, captured 2026-06-09), sanitized to component sums only —
no seller UUID, no utility columns (groupBy collapsed them). test_env.py guards the UUID.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

from habibos.result import Answer, Refusal
from habibos.tacos import classify, parse

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "profit_by_sku_30d.csv"

# Real SKUs from the live fixture, chosen to exercise each edge.
FX = "FX-M8MA-MMSA"       # worst TACOS, negative ROI (ad money leaking)
P18 = "18-116Z-1R77"      # high TACOS, negative ROI
OK = "09-AJOP-CS83"       # low tacos/acos, healthy ROI
NOSALES = "9Z-KUHZ-FU2I"  # ad spend but ZERO sales -> "no sales", roi -100
ZEROAD = "EU-Z87B-ZRBZ"   # real sales, ~no ad sales -> acos "no sales", tiny tacos


def _frame() -> pl.DataFrame:
    return parse(FIXTURE, "COMPLETED")


def _pct(num: float, den: float) -> float | None:
    """Mirror of tacos._ratio for building expected values from the fixture sums."""
    return None if den == 0 else round(num / den * 100, 1)


def test_window_ratios_computed_from_components() -> None:
    """A1/PROF-01: SkuRow ratios == window ratios computed from the fixture's summed components."""
    frame = _frame()
    assert isinstance(frame, pl.DataFrame)
    src = {r["sku"]: r for r in frame.to_dicts()}
    answer = classify(frame, "exp-001", "2026-05-10", "2026-06-09", list(src.keys()))
    assert isinstance(answer, Answer)

    by = {row.seller_sku: row for row in answer.rows}
    for sku, r in src.items():
        assert by[sku].tacos == _pct(r["ad_spend_sum"], r["total_sales_sum"])
        assert by[sku].acos == _pct(r["ad_spend_sum"], r["ad_sales_sum"])
        assert by[sku].roi == _pct(r["profit_sum"], r["total_cost_sum"])

    # Spot-check the live numbers the operator signed off on (TRUST-04).
    assert by[FX].tacos == 69.2 and by[FX].acos == 74.0 and by[FX].roi == -27.1
    assert by[P18].tacos == 46.5

    # Provenance + verbatim definitions surfaced (D-06).
    assert "57a0cb319c" in answer.source
    assert answer.definitions["acos"] and answer.definitions["tacos"] and answer.definitions["roi"]


def test_ratio_units() -> None:
    """A2: ratios render as PERCENT (e.g. 69.2), not a 0.69 fraction."""
    frame = _frame()
    answer = classify(frame, "exp-001", "2026-05-10", "2026-06-09", [FX])
    by = {row.seller_sku: row for row in answer.rows}
    assert by[FX].tacos == 69.2
    assert by[FX].tacos > 1.0  # would be < 1 if it were a fraction


def test_present_zero_sales_is_no_sales_not_no_data() -> None:
    """A present SKU with zero sales -> None ratios + 'no sales' (distinct from absent 'no data')."""
    frame = _frame()
    answer = classify(frame, "exp-001", "2026-05-10", "2026-06-09", [NOSALES, ZEROAD])
    by = {row.seller_sku: row for row in answer.rows}
    # 9Z: ad spend, zero ad_sales AND zero total_sales -> tacos/acos None; roi computable (-100).
    assert by[NOSALES].tacos is None and by[NOSALES].acos is None
    assert by[NOSALES].roi == -100.0
    assert by[NOSALES].tacos_flag == "no sales"
    assert by[NOSALES].acos_flag == "no sales"
    # EU-Z87B: real sales but ~no ad sales -> acos None ("no sales"), tacos present and tiny.
    assert by[ZEROAD].acos is None and by[ZEROAD].acos_flag == "no sales"
    assert by[ZEROAD].tacos == 0.2


def test_missing_sku_no_data() -> None:
    """D-10: a catalog SKU absent from the export -> None ratios + 'no data', never 0/blank."""
    frame = _frame()
    answer = classify(frame, "exp-001", "2026-05-10", "2026-06-09", [FX, "SKU-NOT-IN-EXPORT"])
    by = {row.seller_sku: row for row in answer.rows}
    missing = by["SKU-NOT-IN-EXPORT"]
    assert missing.acos is None and missing.tacos is None and missing.roi is None
    assert missing.acos_flag == "no data" and missing.tacos_flag == "no data"


def test_sorted_tacos_desc() -> None:
    """D-05: rows ordered by tacos descending, with no-ratio (None tacos) rows last."""
    frame = _frame()
    src = {r["sku"]: r for r in frame.to_dicts()}
    answer = classify(frame, "exp-001", "2026-05-10", "2026-06-09", [*src.keys(), "SKU-NOT-IN-EXPORT"])
    seq = [row.tacos for row in answer.rows]
    present = [t for t in seq if t is not None]
    assert present == sorted(present, reverse=True)
    first_none = next(i for i, t in enumerate(seq) if t is None)
    assert all(t is None for t in seq[first_none:])


def test_flag_breach_and_refused() -> None:
    """D-07/D-08: above ceiling -> 'breach', below -> 'ok'; unset ceiling -> 'no threshold set'."""
    frame = _frame()
    answer = classify(frame, "exp-001", "2026-05-10", "2026-06-09", [FX, OK])
    by = {row.seller_sku: row for row in answer.rows}
    # Ceilings seeded acos=30 / tacos=15.
    assert by[FX].acos_flag == "breach"   # acos 74.0 > 30
    assert by[FX].tacos_flag == "breach"  # tacos 69.2 > 15
    assert by[OK].acos_flag == "ok"       # acos 5.5 <= 30
    assert by[OK].tacos_flag == "ok"      # tacos 5.5 <= 15

    # Unset ceiling (read returns None) -> flag refuses, number still renders.
    answer_xx = classify(frame, "exp-001", "2026-05-10", "2026-06-09", [FX], marketplace="XX")
    assert isinstance(answer_xx, Answer)
    by_xx = {row.seller_sku: row for row in answer_xx.rows}
    assert by_xx[FX].acos_flag == "no threshold set"
    assert by_xx[FX].acos == 74.0  # number still renders


def test_sanity_guard_flags_inversion() -> None:
    """D-04: a row with window tacos > acos is suspect; a normal row is not.

    Real CA data has acos >= tacos for every SKU (ad_sales <= total_sales), so the
    inversion is exercised with a synthetic component frame.
    """
    frame = pl.DataFrame(
        {
            "sku": ["INV", "NORMAL"],
            "ad_spend_sum": [10.0, 10.0],
            "ad_sales_sum": [100.0, 50.0],
            "total_sales_sum": [50.0, 200.0],
            "profit_sum": [5.0, 30.0],
            "total_cost_sum": [20.0, 100.0],
            "currency": ["CAD", "CAD"],
        }
    )
    answer = classify(frame, "exp-x", "2026-05-10", "2026-06-09", ["INV", "NORMAL"])
    by = {row.seller_sku: row for row in answer.rows}
    assert by["INV"].tacos == 20.0 and by["INV"].acos == 10.0  # 10/50 vs 10/100
    assert by["INV"].suspect is True
    assert by["NORMAL"].suspect is False


def test_empty_export_refuses() -> None:
    """D-11/TRUST-01: empty frame -> Refusal(empty_export) w/ export_id; FAILED status -> Refusal(failed_export)."""
    empty = pl.DataFrame(
        schema={
            "sku": pl.String,
            "ad_spend_sum": pl.Float64,
            "ad_sales_sum": pl.Float64,
            "total_sales_sum": pl.Float64,
            "profit_sum": pl.Float64,
            "total_cost_sum": pl.Float64,
            "currency": pl.String,
        }
    )
    refusal = classify(empty, "exp-empty", "2026-05-10", "2026-06-09", [FX])
    assert isinstance(refusal, Refusal)
    assert refusal.code == "empty_export"
    assert refusal.export_id == "exp-empty"

    failed = parse(FIXTURE, "FAILED")
    assert isinstance(failed, Refusal)
    assert failed.code == "failed_export"


def test_provenance_on_answer() -> None:
    """TRUST-01/D-06: every successful Answer carries the passed export_id."""
    frame = _frame()
    answer = classify(frame, "exp-prov-123", "2026-05-10", "2026-06-09", [FX])
    assert isinstance(answer, Answer)
    assert answer.export_id == "exp-prov-123"
