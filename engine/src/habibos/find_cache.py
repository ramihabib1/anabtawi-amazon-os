"""FIND-before-write cache — the load-bearing anti-fabrication seam (WRITE-02).

A real UPDATE/REMOVE in Phases 8-10 must target an entity ID that a *prior FIND actually
returned* — never an ID typed, remembered, or guessed. This module is that gate:

  - write(entity_type, ad_product, find_result): persist an agent-handed FIND result
    (e.g. `{"campaigns":[{campaignId, ...}], "nextToken": ...}`) to a dated local file
    `data/ads_<entity>_<adproduct>_find_<YYYY-MM-DD>.json`. Each item is pydantic
    validate-or-raised on its id field, so a renamed/missing id shape fails LOUD
    (drift surfaced, never silently cached — Pitfall 1 / T-06-08).
  - lookup(entity_type, ad_product, entity_id): read the NEWEST matching cache file
    (dated filenames + newest-wins so a stale snapshot can't shadow a fresh one —
    Pitfall 3 / T-06-09) and return the cached item dict on a HIT. On a MISS it returns
    a typed Refusal("stale/missing entity ID", "find_cache_miss"); the write builder
    stops on that Refusal, so a write can never execute on an unverified/stale ID
    (FIND-before-write, T-06-07).

THE SEAM (CLAUDE.md hard rule 1): the FIND network call is an MCP tool call made by the
agent, NOT by Python. This module imports no HTTP/socket library and never opens a
connection — it only reads and writes LOCAL files. It mirrors the `thresholds.read ->
None -> refuse` missing→refuse grammar exactly: a miss is a typed refusal, never a
default and never a fabricated ID.

The operator staleness window (how old a cache file may be before it is rejected) is a
documented Phase-8 dial (RESEARCH Assumption A2), NOT a silent hard-coded default here.
Phase 6 only enforces miss-refuses-at-build.
"""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, ValidationError

from .result import Refusal

# src/habibos/find_cache.py is two levels below the repo root; cache files live at
# <repo>/data/ (mirrors thresholds.CONFIG_PATH parents[2]). Tests monkeypatch this.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# A2 staleness window (Phase-8 documented dial, RESEARCH Assumption A2 / Pitfall 3): how old
# a FIND cache file's date tail may be before a WRITE-BEARING lookup rejects it. A reversible
# write wants a FRESH FIND — a days-old snapshot could shadow a since-changed entity (e.g. a
# bid that already moved), so a write-bearing lookup against a stale file is refused
# (stale_find_cache). This is a NAMED, commented dial — NOT a bare literal buried in lookup.
# Tightening/loosening it is a one-line edit here. 24h is the default reversible-write window;
# non-write-bearing reads (the Phase-6 contract) ignore it entirely (newest-wins is enough).
STALE_HOURS = 24

# entity_type -> (FIND result list key, per-item id field). Verified against the pinned
# FIND result shapes (06-RESEARCH lines 300-305): the campaigns/adGroups/targets/ads
# *Find* results each nest their rows under the plural key and carry the *Id field.
_ENTITY_MAP: dict[str, tuple[str, str]] = {
    "campaigns": ("campaigns", "campaignId"),
    "adGroups": ("adGroups", "adGroupId"),
    "targets": ("targets", "targetId"),
    "ads": ("ads", "adId"),
}


def _resolve(entity_type: str) -> tuple[str, str]:
    """Map entity_type to its (result key, id field), or fail loud on an unknown type."""
    try:
        return _ENTITY_MAP[entity_type]
    except KeyError as exc:
        known = ", ".join(sorted(_ENTITY_MAP))
        raise ValueError(
            f"Unknown FIND entity_type {entity_type!r} (known: {known})"
        ) from exc


def _prefix(entity_type: str, ad_product: str) -> str:
    """The dated-file prefix that scopes a cache to one entity type + ad product.

    ad_product (e.g. SPONSORED_PRODUCTS) is part of the key so an SP campaign FIND can
    never satisfy an SB/SD lookup. Lowercased + filesystem-safe.
    """
    safe_product = ad_product.lower().replace("/", "_")
    return f"ads_{entity_type}_{safe_product}_find_"


def write(entity_type: str, ad_product: str, find_result: dict) -> Path:
    """Persist an agent-handed FIND result to a dated local cache file; return its path.

    Pulls the row list from under the result key (e.g. find_result["campaigns"]) and
    pydantic validate-or-raises each item on its REQUIRED id field — a renamed/missing
    id shape raises ValueError (drift surfaced, never silently cached). Writes the full
    result to DATA_DIR/ads_<entity>_<adproduct>_find_<today>.json. NO socket: local I/O
    only (the seam).
    """
    result_key, id_field = _resolve(entity_type)

    items = find_result.get(result_key)
    if items is None:
        raise ValueError(
            f"FIND result schema mismatch (drift?): missing {result_key!r} key"
        )

    class _FindItem(BaseModel):
        # Tolerate the many utility/optional FIND columns; the id field stays REQUIRED so
        # a renamed/absent id raises rather than being silently cached.
        model_config = ConfigDict(extra="ignore")

    _FindItem.__annotations__ = {id_field: str}

    try:
        for item in items:
            _FindItem.model_validate(item)
    except ValidationError as exc:  # surface drift, never coerce (Pitfall 1 / T-06-08)
        raise ValueError(f"FIND result schema mismatch (drift?): {exc}") from exc

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"{_prefix(entity_type, ad_product)}{date.today().isoformat()}.json"
    path.write_text(json.dumps(find_result, indent=2), encoding="utf-8")
    return path


def _file_date(cache_file: Path, prefix: str) -> date | None:
    """Parse the YYYY-MM-DD date tail from a dated cache filename, or None if unparseable.

    The filename is `<prefix><YYYY-MM-DD>.json` (see write()); the date tail is what the
    newest-wins sort and the A2 staleness window read. A malformed tail returns None so the
    caller can treat it conservatively (a write-bearing lookup rejects an undatable file).
    """
    stem = cache_file.name
    if not stem.startswith(prefix) or not stem.endswith(".json"):
        return None
    tail = stem[len(prefix) : -len(".json")]
    try:
        return datetime.strptime(tail, "%Y-%m-%d").date()
    except ValueError:
        return None


def lookup(
    entity_type: str,
    ad_product: str,
    entity_id: str,
    write_bearing: bool = False,
) -> dict | Refusal:
    """Return the cached entity dict on a HIT, else a typed Refusal.

    Reads the NEWEST ads_<entity>_<adproduct>_find_*.json in DATA_DIR (dated filenames
    sorted descending — newest wins, so a stale file can't shadow a fresh capture,
    Pitfall 3) and scans its rows for one whose id field == entity_id. A MISS (no cache
    file, or no matching id) returns Refusal("stale/missing entity ID", "find_cache_miss")
    — NEVER a default, NEVER a fabricated ID. This is the FIND-before-write gate (T-06-07).

    A2 staleness window (Phase-8, write-bearing only): when `write_bearing=True`, the NEWEST
    cache file's date tail must be within STALE_HOURS of today — a reversible write wants a
    FRESH FIND, so a days-old snapshot could shadow a since-changed entity. An over-window
    newest file returns Refusal("stale FIND cache — re-FIND required", "stale_find_cache")
    BEFORE the id scan (a fresh re-FIND is required, not a hit on a stale id). Non-write-
    bearing reads (the Phase-6 contract) skip the window entirely — newest-wins is enough.
    """
    result_key, id_field = _resolve(entity_type)
    miss = Refusal("stale/missing entity ID", "find_cache_miss")

    if not DATA_DIR.exists():
        return miss

    prefix = _prefix(entity_type, ad_product)
    # Newest-wins: the date is the filename tail, so a reverse lexical sort is a date sort.
    cache_files = sorted(DATA_DIR.glob(f"{prefix}*.json"), reverse=True)
    if not cache_files:
        return miss

    # A2 staleness window — a write-bearing lookup rejects an over-window NEWEST cache file
    # (the freshest available is still too old) so a reversible write never targets a stale
    # entity. Day-granular: filename dates are YYYY-MM-DD, so the window is read in whole days.
    if write_bearing:
        newest_date = _file_date(cache_files[0], prefix)
        stale_days = STALE_HOURS / 24
        if newest_date is None or (date.today() - newest_date).days > stale_days:
            return Refusal("stale FIND cache — re-FIND required", "stale_find_cache")

    for cache_file in cache_files:
        result = json.loads(cache_file.read_text(encoding="utf-8"))
        for item in result.get(result_key, []):
            if item.get(id_field) == entity_id:
                return item

    return miss
