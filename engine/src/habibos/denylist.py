"""Own-ASIN pre-dryRun refuse-gate — the self-cannibalization guard (EXEC-01 / D-06/D-07).

THE GUARANTEE (T-08-05): a reversible ad write whose TARGET is one of our OWN ASINs is a
HARD `GateRefusal(own_asin_denied)` BEFORE BUILD->DRYRUN — never a warn-and-confirm (D-07).
Advertising an Anabtawi product against our own listing cannibalizes organic sales and burns
spend, so the denylist refuses it at the gate, surfaced verbatim per CLAUDE.md hard rule 4.

THE OWNED SET (D-06 / D-06a): read from the DEDICATED `engine/config/owned_asins.toml` — NOT
from `sku_catalog.toml`'s COGS-gated rows. The operator decision (2026-06-22, RESEARCH Open
Q4) deliberately decoupled the two: the COGS catalog funds the margin gate (16 narrow rows),
while the denylist must cover the BROADER owned surface (every owned ASIN incl. the named
private-label exclusion B07TV972JT). Reading the COGS catalog for the owned set would WRONGLY
let an owned-but-non-COGS ASIN through — `test_owned_set_from_dedicated_source` pins that this
dedicated source is the authority.

WHICH WRITES CARRY A TARGET ASIN (Pattern 4 / A7): a pause (CAMPAIGNS_UPDATE) and a bid-down
(TARGETS_UPDATE) carry NO target ASIN — they mutate a campaign state / a target bid, not a
product target — so they pass the denylist CLEANLY (return None). Only a write that points an
ad AT an ASIN (a Sponsored-Display product target, a keyword/product target carrying an ASIN
in its `target_asin` / `expression`/`value`) can be denied. `extract_target_asins` returns []
for the no-target case, so `check` returns None.

THE SEAM (CLAUDE.md hard rule 1): pure typed refuse-gate. No HTTP/socket — `_load_owned`
reads the LOCAL toml. A missing owned_asins.toml RAISES (FileNotFoundError) — there is NO
silent fallback (cloned from gate._load_catalog's D-05 discipline): a denylist that silently
read an empty set would let EVERY owned ASIN through, the exact failure this gate prevents.
Records / the owned file carry only public ASINs — never the seller UUID (hard rule 5).
"""

from __future__ import annotations

import tomllib
from pathlib import Path

from .result import GateRefusal, ProposedAction

# The dedicated authoritative owned-ASIN source (D-06a). src/habibos/denylist.py is two
# levels below the repo root; config lives at <repo>/config/ (mirror gate/thresholds).
OWNED_ASINS_PATH = Path(__file__).resolve().parents[2] / "config" / "owned_asins.toml"

# Param keys a write may carry a TARGET ASIN under. `target_asin` is the normalized engine
# key (08-SCHEMA-PIN ledger params); `expression`/`value` mirror the live target payload
# field where a product-target ASIN lives. A pause/bid-down carries none of these.
_TARGET_ASIN_KEYS = ("target_asin", "value", "expression")


def _load_owned(owned_source: str | Path) -> set[str]:
    """Read the dedicated owned-ASIN set from owned_asins.toml with tomllib (D-06a).

    The owned set is the KEYS of the `[owned."<ASIN>"]` table (each row's metadata is
    informational). Clones gate._load_catalog's discipline: a missing file RAISES
    (FileNotFoundError) — NO silent fallback, because an empty owned set would let every
    owned ASIN through (the exact failure this gate prevents). Returns a set of ASIN strings.
    """
    with Path(owned_source).open("rb") as fh:
        data = tomllib.load(fh)
    return set(data.get("owned", {}).keys())


# Public alias — the contract calls `denylist.load_owned(...)` (test_owned_set_from_dedicated_source).
load_owned = _load_owned


def extract_target_asins(action: ProposedAction) -> list[str]:
    """Pull the TARGET ASIN(s) a write points an ad at, or [] when there is none (A7).

    Reads `action.params` for the pinned target fields (`target_asin` / `value` /
    `expression`). A pause (CAMPAIGNS_UPDATE, params={"state": "PAUSED"}) and a bid-down
    (TARGETS_UPDATE, params={"bid": ...}) carry NONE of these -> [] -> the denylist passes
    them cleanly. Only a product-target write carrying an ASIN returns a non-empty list.
    String ASIN values are upper-cased for a case-insensitive owned-set match.
    """
    params = action.params or {}
    asins: list[str] = []
    for key in _TARGET_ASIN_KEYS:
        raw = params.get(key)
        if raw is None:
            continue
        candidates = raw if isinstance(raw, (list, tuple)) else [raw]
        for candidate in candidates:
            if isinstance(candidate, str) and candidate.strip():
                asins.append(candidate.strip().upper())
    return asins


def check(
    action: ProposedAction, owned_source: str | Path = OWNED_ASINS_PATH
) -> None | GateRefusal:
    """Refuse a write that targets an owned ASIN; else None (EXEC-01 / D-06/D-07).

    Extracts the target ASIN(s) from the payload (`extract_target_asins`); if ANY is in the
    dedicated owned set -> a HARD `GateRefusal("payload targets an owned ASIN",
    code="own_asin_denied", source=<owned_asins.toml>)` BEFORE BUILD->DRYRUN — never a
    warn-and-confirm. A write with no target ASIN (pause/bid-down) returns None (passes
    cleanly). A missing owned_asins.toml RAISES (no silent fallback) — see `_load_owned`.
    """
    owned = _load_owned(owned_source)
    for asin in extract_target_asins(action):
        if asin in owned:
            return GateRefusal(
                "payload targets an owned ASIN — self-cannibalization refused",
                code="own_asin_denied",
                source=str(owned_source),
            )
    return None
