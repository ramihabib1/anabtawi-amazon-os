"""Margin-tiered safety-gate money-logic tests (GATE-01..05 + D-03/D-04).

The Nyquist RED baseline for Plan 03's `habibos.gate`. These tests are the CONTRACT
the gate is written test-first against — they MUST FAIL RED here (gate.py absent) and
turn GREEN only when Plan 03 implements `habibos.gate`.

What the gate guarantees (mirrors the tacos.py anti-fabrication grammar):
  - GATE-01: pre-ad contribution margin computed from the source's window-summed
    components, with ad_spend ADDED BACK (profit is POST-ad; D-03). CM% =
    (profit_sum + ad_spend_sum) / total_sales_sum * 100.
  - D-03: the back-out is asserted against the committed fixture arithmetic
    (EU-Z87B-ZRBZ -> 36.0%), so a fabricated margin can never pass review unnoticed.
  - GATE-02: per-SKU ceiling = CM% - floor; an unset floor (`""` / absent marketplace)
    -> GateRefusal(code="no_threshold_set") on every spend-up, never a default.
  - GATE-03: spend-direction branch — a spend-increasing action with projected <= ceiling
    PASSES (GateVerdict); a spend-decreasing action auto-passes (GateVerdict(auto_pass=True))
    with no projection (D-06).
  - GATE-04: an over-ceiling spend-up -> GateRefusal(code="over_ceiling") whose
    breached_value is the projected TACOS and whose source is set — NEVER a value clamped
    to the ceiling.
  - GATE-05: a SKU absent from the catalog -> GateRefusal(code="sku_not_in_catalog").
  - D-04: a SKU with 0/null catalog COGS OR total_sales_sum == 0 -> CM% undefined ->
    GateRefusal(code="no_margin"), never a guessed/substituted margin.

Strict-breach semantics (mirror tacos._present_flag): a projected EXACTLY equal to the
ceiling must PASS; only projected > ceiling refuses.

FIXTURE: reuses the same committed `tests/fixtures/profit_by_sku_30d.csv` window-sum
export that test_tacos.py asserts against. The small catalog fixture
`tests/fixtures/sku_catalog_test.toml` is created in Plan 02 — referenced here by its
constant path so these tests fail RED on the absent gate module, not on a typo.
"""

from __future__ import annotations

from pathlib import Path

import polars as pl

# RED on import: habibos.gate does not exist until Plan 03. This is the intended
# Wave 1 baseline (the seven tests below collect but error/fail on the missing module).
from habibos import gate
from habibos.result import GateRefusal, GateVerdict, ProposedAction
from habibos.tacos import parse

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "profit_by_sku_30d.csv"
# Small dedicated catalog fixture (created in Plan 02): carries a HERO SKU with real cogs,
# a SKU with cogs = 0 (no_margin edge), and deliberately OMITS a SKU the tests fund
# (sku_not_in_catalog edge) — so the catalog refusals are exercised independent of the
# live engine/config/sku_catalog.toml.
TEST_CATALOG = REPO_ROOT / "tests" / "fixtures" / "sku_catalog_test.toml"

# Real SKUs from the live fixture, chosen to exercise each gate edge (mirror test_tacos.py).
HERO = "EU-Z87B-ZRBZ"      # ad_spend 0.5, sales 279.95, profit 100.27 -> CM% 36.0, ceiling 21.0
NOSALES = "9Z-KUHZ-FU2I"   # total_sales_sum 0 -> CM% None -> no_margin refusal (D-04)
ZEROCOGS = "ASW-H50"       # total_sales_sum 0 -> CM% None -> no_margin refusal (D-04)
ABSENT = "SKU-NOT-IN-CATALOG"  # not in TEST_CATALOG -> sku_not_in_catalog refusal (GATE-05)


def _frame() -> pl.DataFrame:
    return parse(FIXTURE, "COMPLETED")


def _row(sku: str) -> dict:
    """The fixture's window-summed component row for a SKU (build expected values from it)."""
    frame = _frame()
    return {r["sku"]: r for r in frame.to_dicts()}[sku]


# --- GATE-01: contribution margin from window sums (pre-ad back-out) ---------------------


def test_contribution_margin_pre_ad() -> None:
    """GATE-01: CM% is computed from the window-summed components with ad_spend added back.

    The gate's contribution_margin_pct mirrors tacos._ratio (round(... * 100, 1), None on
    zero/missing denominator) but adds ad_spend_sum back because profit_sum is POST-ad (D-03).
    """
    r = _row(HERO)
    cm = gate.contribution_margin_pct(r["profit_sum"], r["ad_spend_sum"], r["total_sales_sum"])
    # (100.27 + 0.5) / 279.95 * 100 == 36.0 — NOT profit/sales (which would be ~35.8).
    expected = round((r["profit_sum"] + r["ad_spend_sum"]) / r["total_sales_sum"] * 100, 1)
    assert cm == expected == 36.0

    # Zero/missing denominator -> None (undefined), never 0 or a guess (mirror _ratio).
    assert gate.contribution_margin_pct(10.0, 1.0, 0) is None
    assert gate.contribution_margin_pct(None, 1.0, 100.0) is None
    assert gate.contribution_margin_pct(10.0, None, 100.0) is None


def test_profit_is_post_ad_addback() -> None:
    """D-03: the back-out matches the committed fixture arithmetic — proves profit is POST-ad.

    A fabricated/forgotten back-out would fail this assertion (anti-repudiation, T-07-02).
    """
    hero = _row(HERO)
    # The back-out value (correct, pre-ad).
    cm_addback = gate.contribution_margin_pct(
        hero["profit_sum"], hero["ad_spend_sum"], hero["total_sales_sum"]
    )
    assert cm_addback == 36.0
    # The naive post-ad value (WRONG) — locks that the gate is NOT computing profit/sales.
    naive_post_ad = round(hero["profit_sum"] / hero["total_sales_sum"] * 100, 1)
    assert cm_addback != naive_post_ad

    # A present SKU with zero total_sales -> CM% undefined (None), not 0 (Pitfall 4).
    z = _row(NOSALES)
    assert gate.contribution_margin_pct(z["profit_sum"], z["ad_spend_sum"], z["total_sales_sum"]) is None


# --- GATE-02: ceiling = CM% - floor; unset floor refuses every spend-up ------------------


def test_ceiling_and_unset_floor_refuses() -> None:
    """GATE-02: ceiling = CM% - floor; with the floor UNSET every spend-up refuses (SC-2).

    The unset-floor path is exercised via a marketplace with no min_net_margin_pct
    (e.g. "XX") — the same None-ceiling trick test_tacos.py uses around marketplace="XX" —
    so this is independent of the live seeded floor (15) Plan 02 adds.
    """
    # ceiling = CM% - floor (D-01): 36.0 - 15 = 21.0.
    assert gate.ceiling_tacos_pct(36.0, 15.0) == 21.0

    # Floor unset for marketplace "XX" -> GateRefusal(no_threshold_set) on a spend-up.
    spend_up = ProposedAction(sku=HERO, action_type="bid_up", delta_spend=5.0, marketplace="XX")
    result = gate.evaluate(_frame(), spend_up, TEST_CATALOG)
    assert isinstance(result, GateRefusal)
    assert result.code == "no_threshold_set"


# --- GATE-03: spend-direction branch ----------------------------------------------------


def test_spend_direction_branch() -> None:
    """GATE-03: spend-increasing within ceiling passes; spend-decreasing auto-passes (D-06)."""
    # A tiny spend-up on the HERO: projected = (0.5 + 1.0) / 279.95 * 100 = 0.5 <= 21.0 -> PASS.
    spend_up = ProposedAction(sku=HERO, action_type="bid_up", delta_spend=1.0)
    passed = gate.evaluate(_frame(), spend_up, TEST_CATALOG)
    assert isinstance(passed, GateVerdict)
    assert passed.auto_pass is False
    assert passed.projected_tacos is not None
    assert passed.projected_tacos <= passed.ceiling

    # A spend-decreasing action auto-passes with NO projection (D-06) — cannot breach.
    spend_down = ProposedAction(sku=HERO, action_type="pause", delta_spend=-2.0)
    auto = gate.evaluate(_frame(), spend_down, TEST_CATALOG)
    assert isinstance(auto, GateVerdict)
    assert auto.auto_pass is True
    assert auto.projected_tacos is None


# --- GATE-04: breach refuses, never clamps ----------------------------------------------


def test_breach_refuses_never_clamps() -> None:
    """GATE-04: an over-ceiling spend-up -> GateRefusal naming breached_value + source.

    The breaching value is NEVER clamped to the ceiling; the result is a GateRefusal,
    NOT a GateVerdict whose projected_tacos == ceiling (T-07-01).
    """
    # A huge spend delta pushes projected TACOS well over the 21.0 ceiling for the HERO.
    breach = ProposedAction(sku=HERO, action_type="budget_up", delta_spend=1000.0)
    result = gate.evaluate(_frame(), breach, TEST_CATALOG)
    assert isinstance(result, GateRefusal)
    assert not isinstance(result, GateVerdict)
    assert result.code == "over_ceiling"
    # breached_value is the PROJECTED TACOS that breached, never the clamped ceiling.
    r = _row(HERO)
    projected = round((r["ad_spend_sum"] + 1000.0) / r["total_sales_sum"] * 100, 1)
    assert result.breached_value == projected
    assert result.breached_value > result.ceiling  # it really breached
    assert result.source is not None  # provenance named (PREMIUM_SOURCE)


# --- GATE-05: SKU not in catalog refuses -------------------------------------------------


def test_sku_not_in_catalog_refuses() -> None:
    """GATE-05: a ProposedAction for a SKU absent from the catalog -> sku_not_in_catalog."""
    action = ProposedAction(sku=ABSENT, action_type="bid_up", delta_spend=1.0)
    result = gate.evaluate(_frame(), action, TEST_CATALOG)
    assert isinstance(result, GateRefusal)
    assert result.code == "sku_not_in_catalog"


# --- D-04: unreliable / zero COGS refuses ------------------------------------------------


def test_unreliable_cogs_refuses() -> None:
    """D-04: a SKU with 0/null catalog cogs OR total_sales_sum == 0 -> no_margin refusal.

    9Z-KUHZ-FU2I and ASW-H50 both have total_sales_sum == 0 in the fixture, so CM% is
    undefined -> the gate refuses with code="no_margin", never a substituted margin.
    """
    for sku in (NOSALES, ZEROCOGS):
        action = ProposedAction(sku=sku, action_type="bid_up", delta_spend=1.0)
        result = gate.evaluate(_frame(), action, TEST_CATALOG)
        assert isinstance(result, GateRefusal)
        assert result.code == "no_margin"
