"""WRITE-02 FIND-cache contract tests (Wave 0, RED).

These are the EXECUTABLE CONTRACT that Plan 03 (`habibos.find_cache`) implements against.
Until `habibos.find_cache` exists they FAIL RED on the missing import — the intended Wave 0
state (06-VALIDATION.md), not a failure to fix.

What the contract pins:
  - find_cache.write(a FIND result) persists `data/ads_*_find_*.json`, and a cached entity ID
    looks up HIT (WRITE-02);
  - a non-cached ID -> Refusal("stale/missing entity ID", "find_cache_miss") at lookup, so a
    real run can never target an unverified/stale ID (FIND-before-write enforced).

DATA_DIR is monkeypatched to tmp_path (mirror of test_logging.py:34-43) so no real data/
writes happen. No seller UUID literal appears anywhere here.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from habibos import find_cache
from habibos.result import Refusal

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"


@pytest.fixture
def cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point find_cache.DATA_DIR at tmp_path — no real data/ writes (PATTERNS:214-217)."""
    monkeypatch.setattr(find_cache, "DATA_DIR", tmp_path)
    return tmp_path


def _campaigns_find() -> dict:
    return json.loads((FIXTURES / "campaigns_find.json").read_text(encoding="utf-8"))


def test_find_write_and_lookup(cache_dir: Path) -> None:
    """WRITE-02: a FIND result writes data/ads_*_find_*.json; a cached ID looks up HIT."""
    result = _campaigns_find()
    cached_id = result["campaigns"][0]["campaignId"]

    path = find_cache.write("campaigns", "SPONSORED_PRODUCTS", result)
    assert Path(path).exists()
    name = Path(path).name
    assert name.startswith("ads_") and "_find_" in name and name.endswith(".json")

    hit = find_cache.lookup("campaigns", "SPONSORED_PRODUCTS", cached_id)
    assert not isinstance(hit, Refusal)
    assert hit["campaignId"] == cached_id


def test_uncached_id_refuses(cache_dir: Path) -> None:
    """WRITE-02: a non-cached ID -> Refusal('stale/missing entity ID', 'find_cache_miss')."""
    find_cache.write("campaigns", "SPONSORED_PRODUCTS", _campaigns_find())

    miss = find_cache.lookup("campaigns", "SPONSORED_PRODUCTS", "CMP-NOT-IN-CACHE")
    assert isinstance(miss, Refusal)
    assert miss.code == "find_cache_miss"
    assert "stale" in miss.reason or "missing" in miss.reason


def test_stale_cache_refused(cache_dir: Path) -> None:
    """A2 (Phase-8 staleness window, Wave-0 RED): a cache file older than the staleness window
    is REJECTED for a WRITE-BEARING lookup -> Refusal(code="stale_find_cache").

    Plan 02 adds the staleness dial (RESEARCH Pitfall 3 / Assumption A2): a reversible write
    wants a FRESH FIND, so a days-old `ads_*_find_<old>.json` must NOT satisfy a write-bearing
    lookup (it could shadow a since-changed entity). This test pins that contract. It FAILS
    RED today because `lookup` has no `write_bearing` parameter yet — the intended Wave-0 state
    (the dial is implemented in Plan 02, not here). It writes a cache file with an OLD date tail
    by hand (find_cache.write always stamps today), then asserts a write-bearing lookup refuses.
    """
    result = _campaigns_find()
    cached_id = result["campaigns"][0]["campaignId"]

    # Hand-write a cache file dated well outside any sane 24h window (the date is the filename
    # tail find_cache.lookup sorts on). find_cache.write would stamp today, so we forge the name.
    stale_name = "ads_campaigns_sponsored_products_find_2020-01-01.json"
    (cache_dir / stale_name).write_text(json.dumps(result), encoding="utf-8")

    stale = find_cache.lookup(
        "campaigns", "SPONSORED_PRODUCTS", cached_id, write_bearing=True
    )
    assert isinstance(stale, Refusal)
    assert stale.code == "stale_find_cache"
