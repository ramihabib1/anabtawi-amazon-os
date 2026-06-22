"""CLI contract test for `scripts/gate_action.py` — locks the JSON verdict/refusal shape.

`gate_action.py` is the thin argv->gate.evaluate->JSON seam the Phase 8 apply spine calls.
It contains NO money logic (all of that is in `habibos.gate`, covered by test_gate.py); this
test pins the THREE JSON contract paths the spine depends on, invoking `main([...])` directly
and parsing the stdout JSON (capsys):

  1. PASS      — a spend-decreasing action -> JSON `auto_pass` is True (GateVerdict, D-06).
  2. over_ceiling refusal — a spend-up whose Δspend pushes projected over the SKU's ceiling
     -> JSON `code == "over_ceiling"` with non-null `breached_value` + `source` (GATE-04
     surfaced verbatim through the CLI — a refusal can NEVER serialize as a pass, T-07-11).
  3. sku_not_in_catalog refusal — a SKU absent from the catalog -> JSON
     `code == "sku_not_in_catalog"` (GATE-05).

FIXTURE: reuses the committed `tests/fixtures/profit_by_sku_30d.csv` window-sum export and
the small `tests/fixtures/sku_catalog_test.toml` catalog (HERO present with real cogs; a
funded SKU deliberately absent) — so the CLI exercises a live catalog read with no network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make scripts/ importable so we can invoke the CLI's main() directly.
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import gate_action  # noqa: E402 — imported after the sys.path insert above

FIXTURE = REPO_ROOT / "tests" / "fixtures" / "profit_by_sku_30d.csv"
TEST_CATALOG = REPO_ROOT / "tests" / "fixtures" / "sku_catalog_test.toml"

# Real SKUs chosen to exercise each CLI path (mirror test_gate.py).
HERO = "EU-Z87B-ZRBZ"          # present in fixture + TEST_CATALOG: sales 279.95, ad_spend 0.5
ABSENT = "NX-NOTIN-CAT0"       # absent from TEST_CATALOG -> sku_not_in_catalog (GATE-05)


def _run(capsys, **kwargs) -> dict:
    """Invoke gate_action.main with the given ProposedAction args; return the parsed JSON."""
    argv = [
        "--artifact", str(FIXTURE),
        "--export-id", "testxx",
        "--catalog", str(TEST_CATALOG),
        "--sku", kwargs["sku"],
        "--action-type", kwargs["action_type"],
        "--delta-spend", str(kwargs["delta_spend"]),
    ]
    rc = gate_action.main(argv)
    assert rc == 0
    out = capsys.readouterr().out
    return json.loads(out)


def test_cli_spend_down_emits_auto_pass(capsys) -> None:
    """PASS path: a spend-decreasing action -> JSON auto_pass True (GateVerdict, D-06)."""
    payload = _run(capsys, sku=HERO, action_type="pause", delta_spend=-5.0)
    assert payload["auto_pass"] is True
    # A spend-down auto-passes with NO projection — cannot breach a ceiling.
    assert payload["projected_tacos"] is None


def test_cli_over_ceiling_emits_refusal(capsys) -> None:
    """over_ceiling path: a spend-up over the ceiling -> code over_ceiling, never a pass."""
    payload = _run(capsys, sku=HERO, action_type="budget_up", delta_spend=1000.0)
    assert payload["code"] == "over_ceiling"
    # The breaching projected TACOS + its provenance are surfaced verbatim (GATE-04).
    assert payload["breached_value"] is not None
    assert payload["source"] is not None
    # A refusal NEVER serializes as a pass (T-07-11): no auto_pass key on a GateRefusal.
    assert "auto_pass" not in payload


def test_cli_absent_sku_emits_refusal(capsys) -> None:
    """sku_not_in_catalog path: a SKU absent from the catalog -> code sku_not_in_catalog."""
    payload = _run(capsys, sku=ABSENT, action_type="bid_up", delta_spend=1.0)
    assert payload["code"] == "sku_not_in_catalog"
