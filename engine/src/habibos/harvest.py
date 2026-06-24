"""Two-class attribution + internal-competition + harvest-graduation predicates (QUEUE-04 /
EXEC-02, D-08/D-09/D-10) — CLAUDE.md hard rule 3 (hand-written, pytest-covered money logic).

Pure predicates over typed inputs — NO network, NO I/O. The agent reads the live windows /
campaign ACOS / order counts via MCP and hands them in as plain arguments (D-04); this module
only decides. Each predicate mirrors the `magnitude.check` shape: a clean pass returns None
(or a bool), a block returns a typed `GateRefusal` surfacing the breaching value verbatim —
never clamped, never a default (the GATE-04 / D-08 anti-fabrication discipline). No new
dataclass: every refusal reuses `result.GateRefusal`.

The #1 pitfall this guards (D-10): never act on an immature window. An efficiency verdict on
a window shorter than the ad product's maturity is refused; only an obviously-dead "act-now"
signal (inactive listing / zero lifetime orders / ENABLED on a discontinued SKU) bypasses the
maturity wait, because those signals do not depend on attribution maturing.
"""

from __future__ import annotations

from .result import GateRefusal, ProposedAction

# Matured-window thresholds in DAYS (D-09/D-10). A reviewable mapping keyed by the apply
# spine's ad_product label (apply.apply default "SPONSORED_PRODUCTS"). SP matures fastest;
# SB/SD carry longer attribution. An UNKNOWN ad product is treated as NOT matured (fail-safe).
MATURED_DAYS: dict[str, int] = {
    "SPONSORED_PRODUCTS": 7,
    "SPONSORED_BRANDS": 14,
    "SPONSORED_DISPLAY": 14,
}

# A search term graduates to a funded keyword only with proven conversion AND efficiency.
GRADUATION_MIN_ORDERS = 2

__all__ = [
    "MATURED_DAYS",
    "GRADUATION_MIN_ORDERS",
    "matured_threshold",
    "is_matured",
    "is_act_now",
    "judge_later_blocked",
    "consolidation_blocked",
    "graduates",
]


def matured_threshold(ad_product: str) -> int | None:
    """The required days of matured data for an ad product, or None if the product is unknown."""
    return MATURED_DAYS.get(ad_product)


def is_matured(ad_product: str, days_of_data: int) -> bool:
    """True when `days_of_data` meets the ad product's maturity threshold (D-09/D-10).

    An unknown ad product is NOT matured — fail-safe, never act on an unrecognized window.
    """
    threshold = matured_threshold(ad_product)
    if threshold is None:
        return False
    return days_of_data >= threshold


def is_act_now(signal: dict) -> bool:
    """True ONLY on an obviously-dead signal that does NOT depend on a matured window (D-10).

    The three act-now signals: an inactive listing, zero lifetime orders, or a campaign left
    ENABLED on a discontinued SKU. Everything else is judge-later (wait for the window).
    """
    return bool(
        signal.get("inactive_listing")
        or signal.get("lifetime_orders") == 0
        or signal.get("enabled_on_discontinued_sku")
    )


def judge_later_blocked(
    action: ProposedAction, ad_product: str, days_of_data: int
) -> None | GateRefusal:
    """Refuse an efficiency verdict on an immature window (the #1 pitfall, D-10).

    The caller invokes this for a judge-later action (one that is NOT act-now). When the
    window has not matured, refuse with `immature_window` surfacing the actual days; otherwise
    None. Mirrors `magnitude.check`'s pure (args) -> None | GateRefusal shape.
    """
    if is_matured(ad_product, days_of_data):
        return None
    threshold = matured_threshold(ad_product)
    return GateRefusal(
        f"efficiency verdict on an immature {ad_product} window "
        f"({days_of_data}d < {threshold}d matured) — judge later, never act now",
        code="immature_window",
        breached_value=float(days_of_data),
        ceiling=float(threshold) if threshold is not None else None,
    )


def consolidation_blocked(
    action: ProposedAction, term_campaign_acos: dict[str, float]
) -> None | GateRefusal:
    """Block a bid-up on a term live in >1 ENABLED campaign until consolidated (D-08, EXEC-02).

    `term_campaign_acos` maps each ENABLED campaignId running this term to its matured-window
    ACOS. Only a spend-increasing action (a bid-UP) can bid against yourself; a spend-down /
    pause never triggers this. When the term is live in more than one ENABLED campaign, refuse
    with `internal_competition`, naming the lowest-ACOS owning campaign (the keep) and the
    others to pause (reversible) first. A term in exactly one campaign has nothing to
    consolidate -> None.
    """
    if not action.is_spend_increasing:
        return None
    if len(term_campaign_acos) <= 1:
        return None
    owner = min(term_campaign_acos, key=lambda cid: term_campaign_acos[cid])
    others = sorted(cid for cid in term_campaign_acos if cid != owner)
    return GateRefusal(
        f"term live in {len(term_campaign_acos)} ENABLED campaigns — consolidate to the "
        f"lowest-ACOS owner {owner} (pause {', '.join(others)}) before raising the bid",
        code="internal_competition",
        breached_value=float(len(term_campaign_acos)),
    )


def graduates(orders: int, acos: float | None, ceiling: float | None) -> bool:
    """A search term graduates to a funded keyword (D-09).

    Requires proven conversion AND efficiency over a matured window: at least
    GRADUATION_MIN_ORDERS attributed orders AND a defined ACOS at or under the SKU's gate
    ceiling. A missing ACOS or ceiling never graduates (no defensible basis to fund).
    """
    return (
        orders >= GRADUATION_MIN_ORDERS
        and acos is not None
        and ceiling is not None
        and acos <= ceiling
    )
