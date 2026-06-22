"""EXEC-01 own-ASIN denylist contract tests (Wave 0, RED).

These are the EXECUTABLE CONTRACT that Plan 02 (`habibos.denylist`) implements against.
Until `habibos.denylist` exists they FAIL RED on the missing import — the intended Wave-0
state (08-VALIDATION.md 08-02·T2), NOT a failure to fix.

What the contract pins (D-06/D-06a/D-07):
  - test_own_asin_refused: a payload whose target value is an OWNED ASIN -> a hard
    GateRefusal(code="own_asin_denied") BEFORE BUILD→DRYRUN. The denylist never warns-and-
    confirms; it refuses (D-07), surfaced verbatim. This is the EXEC-01 self-cannibalization
    guard (advertising an owned product on our own page).
  - test_pause_passes_denylist: a pause (no target ASIN in the payload) passes the denylist
    cleanly (returns None) — pauses/bid-downs carry no target ASIN to deny (Pattern 4 / A7).
  - test_owned_set_from_dedicated_source: the owned set is read from the DEDICATED
    owned_asins source (D-06a), NOT from sku_catalog's COGS rows. B07TV972JT is in the
    dedicated owned set but ABSENT from sku_catalog_test.toml — so a denylist that mistakenly
    read the COGS catalog would WRONGLY pass it. The test proves the dedicated source wins.

No network (the denylist is a pure typed refuse-gate). No seller UUID literal anywhere here.
"""

from __future__ import annotations

from pathlib import Path

# RED on import: habibos.denylist does not exist until Plan 02. The intended Wave-0 baseline.
from habibos import denylist
from habibos.result import GateRefusal, ProposedAction

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"
# The DEDICATED owned-ASIN source (D-06a) — carries B07TV972JT, which is deliberately ABSENT
# from the COGS catalog below, so the dedicated-source test can prove which file is read.
OWNED = FIXTURES / "owned_asins_test.toml"
COGS_CATALOG = FIXTURES / "sku_catalog_test.toml"  # the Phase-7 margin catalog (NO B07TV972JT)

OWNED_ASIN = "B07TV972JT"  # the named private-label exclusion; in OWNED, not in COGS_CATALOG


def test_own_asin_refused() -> None:
    """EXEC-01/D-06: a target whose ASIN is in the owned set -> GateRefusal(own_asin_denied)."""
    # A Sponsored-Display product-target write pointing an ad at our OWN ASIN.
    action = ProposedAction(
        sku="X",
        action_type="negative",
        delta_spend=0,
        entity_type="targets",
        entity_id="TGT-3000000000001",
        params={"target_asin": OWNED_ASIN},
    )
    refusal = denylist.check(action, owned_source=OWNED)
    assert isinstance(refusal, GateRefusal)
    assert refusal.code == "own_asin_denied"


def test_pause_passes_denylist() -> None:
    """EXEC-01/Pattern 4: a pause (no target ASIN) passes the denylist cleanly (None)."""
    action = ProposedAction(
        sku="X",
        action_type="pause",
        delta_spend=0,
        entity_type="campaigns",
        entity_id="CMP-1000000000003",
        params={"state": "PAUSED"},
    )
    result = denylist.check(action, owned_source=OWNED)
    assert result is None  # nothing to deny — a pause carries no target ASIN


def test_owned_set_from_dedicated_source() -> None:
    """D-06a: the owned set is read from the dedicated owned_asins source, NOT sku_catalog COGS rows.

    B07TV972JT is in OWNED but ABSENT from COGS_CATALOG. A denylist that (wrongly) sourced
    the owned set from the COGS catalog would NOT refuse it. The refusal proves the dedicated
    source is the authority.
    """
    owned = denylist.load_owned(OWNED)
    assert OWNED_ASIN in owned
    # The dedicated source is decoupled from the COGS catalog — the COGS catalog does NOT
    # carry the named exclusion, so reading it would silently let the owned ASIN through.
    import tomllib

    cogs_skus = tomllib.load(COGS_CATALOG.open("rb")).get("sku", {})
    cogs_asins = {row.get("asin") for row in cogs_skus.values()}
    assert OWNED_ASIN not in cogs_asins
