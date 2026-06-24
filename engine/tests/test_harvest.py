"""harvest.py predicate contracts (QUEUE-04 / EXEC-02, D-08/D-09/D-10).

Two-branch refuse/pass tests (the test_magnitude_cap analog) for the two-class attribution,
internal-keyword-competition, and harvest-graduation predicates. Pure inputs — no network,
no seller UUID.
"""

from __future__ import annotations

from habibos import harvest
from habibos.result import GateRefusal, ProposedAction


def _bid_up(delta: float = 1.0) -> ProposedAction:
    """A spend-increasing bid-up (the only action that can bid against itself)."""
    return ProposedAction(
        sku="X",
        action_type="bid_up",
        delta_spend=delta,
        entity_type="targets",
        entity_id="TGT-1",
        params={"pct_change": 20.0},
    )


def _bid_down() -> ProposedAction:
    return ProposedAction(sku="X", action_type="bid_down", delta_spend=0.0)


# ---- is_matured (D-09/D-10) ----------------------------------------------------------------


def test_is_matured_sp_threshold() -> None:
    """SP matures at 7d: 6d is immature, 7d is matured."""
    assert harvest.is_matured("SPONSORED_PRODUCTS", 6) is False
    assert harvest.is_matured("SPONSORED_PRODUCTS", 7) is True


def test_is_matured_sb_threshold() -> None:
    """SB/SD mature at 14d: 13d is immature, 14d is matured."""
    assert harvest.is_matured("SPONSORED_BRANDS", 13) is False
    assert harvest.is_matured("SPONSORED_BRANDS", 14) is True


def test_is_matured_unknown_product_is_never_matured() -> None:
    """An unrecognized ad product is fail-safe NOT matured at any window length."""
    assert harvest.is_matured("MYSTERY", 999) is False


# ---- is_act_now (D-10) ---------------------------------------------------------------------


def test_is_act_now_on_dead_signals() -> None:
    """Each obviously-dead signal is act-now (bypasses the maturity wait)."""
    assert harvest.is_act_now({"inactive_listing": True}) is True
    assert harvest.is_act_now({"lifetime_orders": 0}) is True
    assert harvest.is_act_now({"enabled_on_discontinued_sku": True}) is True


def test_is_act_now_false_on_healthy_signal() -> None:
    """A healthy, selling campaign is judge-later, not act-now."""
    assert (
        harvest.is_act_now(
            {
                "inactive_listing": False,
                "lifetime_orders": 42,
                "enabled_on_discontinued_sku": False,
            }
        )
        is False
    )


# ---- judge_later_blocked (D-10, the #1 pitfall) --------------------------------------------


def test_judge_later_blocked_on_immature_window() -> None:
    """An efficiency verdict at 5d SP is refused immature_window, surfacing the actual days."""
    refusal = harvest.judge_later_blocked(_bid_up(), "SPONSORED_PRODUCTS", 5)
    assert isinstance(refusal, GateRefusal)
    assert refusal.code == "immature_window"
    assert refusal.breached_value == 5.0  # the actual days, never clamped to the threshold
    assert refusal.ceiling == 7.0


def test_judge_later_passes_on_matured_window() -> None:
    """A matured (7d SP) window lets the efficiency verdict proceed (None)."""
    assert harvest.judge_later_blocked(_bid_up(), "SPONSORED_PRODUCTS", 7) is None


# ---- consolidation_blocked (D-08, no bidding against yourself) -----------------------------


def test_consolidation_blocked_term_in_two_campaigns() -> None:
    """A bid-up on a term live in 2 ENABLED campaigns is blocked until consolidated."""
    refusal = harvest.consolidation_blocked(
        _bid_up(), {"CAMP-A": 35.0, "CAMP-B": 18.0}
    )
    assert isinstance(refusal, GateRefusal)
    assert refusal.code == "internal_competition"
    # The lowest-ACOS campaign (CAMP-B) is named as the owner to keep.
    assert "CAMP-B" in refusal.reason


def test_consolidation_passes_term_in_one_campaign() -> None:
    """A term live in exactly one campaign has nothing to consolidate -> None."""
    assert harvest.consolidation_blocked(_bid_up(), {"CAMP-A": 22.0}) is None


def test_consolidation_ignores_non_bid_up() -> None:
    """A reversible (non spend-increasing) action never triggers consolidation."""
    assert (
        harvest.consolidation_blocked(_bid_down(), {"CAMP-A": 35.0, "CAMP-B": 18.0})
        is None
    )


# ---- graduates (D-09) ----------------------------------------------------------------------


def test_graduates_requires_orders_and_efficiency() -> None:
    """Graduate only with >=2 orders AND a defined ACOS at/under the ceiling."""
    assert harvest.graduates(2, acos=20.0, ceiling=25.0) is True
    assert harvest.graduates(1, acos=20.0, ceiling=25.0) is False  # too few orders
    assert harvest.graduates(2, acos=30.0, ceiling=25.0) is False  # over the ceiling
    assert harvest.graduates(2, acos=None, ceiling=25.0) is False  # no defensible ACOS
    assert harvest.graduates(2, acos=20.0, ceiling=None) is False  # no ceiling
