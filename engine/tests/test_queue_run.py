"""queue_run.py CLI contract tests (WRITE-04 / QUEUE-02 / EXEC-02, D-06/D-11).

Drive `queue_run.main([...])` with committed local fixtures and an `apply.apply` SPY (the
seam — no live write). What the contract pins:
  - render mode prints the dollar-ranked, class-tagged table; a spend-up tags needs-approval;
    the restock-gated GG-0DC1 (1 FBA unit) renders REFUSED cover_below_floor (EXEC-05).
  - render mode INVOKES apply.apply for the AUTO-class reversible row (autonomy != silence)
    and does NOT invoke it for a needs-approval spend-up row.
  - apply mode WITHOUT --approve refuses a needs-approval spend-up (apply.apply NOT called);
    WITH --approve it runs apply.apply and returns the applied result (D-06 batch gate).
  - the seller UUID never appears in stdout (hard rule 5).

No network. No seller UUID literal anywhere.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from habibos import apply as apply_mod
from habibos.result import AppliedResult, GateRefusal

# Make scripts/ importable so we can invoke the CLI's main() directly (mirror test_gate_action).
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import queue_run  # noqa: E402 — imported after the sys.path insert above

FIXTURES = REPO_ROOT / "tests" / "fixtures"
CANDIDATES = str(FIXTURES / "queue_candidates.json")
COVER = str(FIXTURES / "queue_cover_map.json")
# The committed premium window-sum export the margin gate reads (the --artifact for a spend-up).
# A spend-up reaching the write path with NO --artifact must REFUSE (no_margin), never apply
# (CR-04) — so a spend-up apply test MUST supply this real margin frame to clear the gate.
PROFIT = str(FIXTURES / "profit_by_sku_30d.csv")
# Any committed JSON works as a stand-in MCP fixture path — the apply.apply spy never reads it.
DRYRUN = str(FIXTURES / "actions_start_dryrun_biddown.json")
APPLYR = str(FIXTURES / "actions_get_completed.json")
STATUS = str(FIXTURES / "actions_get_completed.json")
FINDE = str(FIXTURES / "campaigns_find_echo.json")


def _applied_stub() -> AppliedResult:
    return AppliedResult(
        action_id="ACT-TEST-0001",
        status="COMPLETED",
        hash="deadbeef",
        applied_at="2026-06-24T00:00:00Z",
        marketplace="CA",
    )


def _spy(monkeypatch):
    """Replace apply.apply with a recording spy that returns a canned AppliedResult."""
    calls: list = []

    def fake_apply(action, **kwargs):
        calls.append(action)
        return _applied_stub()

    monkeypatch.setattr(apply_mod, "apply", fake_apply)
    return calls


def test_render_dollar_ranked_and_subcover_refusal(capsys) -> None:
    """Render prints the class-tagged table; GG-0DC1 renders REFUSED cover_below_floor.

    No MCP fixtures passed -> no auto-apply fires; the read-only gate chain still runs.
    """
    rc = queue_run.main(["render", "--candidates", CANDIDATES, "--cover", COVER])
    assert rc == 0
    out = capsys.readouterr().out
    # The class-tagged table carries the needs-approval class on a spend-up row.
    assert "needs-approval" in out
    assert "auto" in out  # the FX-M8MA bid_down reversible row
    # The restock-gated funded winner is refused sub-cover, not actionable.
    assert "GG-0DC1-SKHG" in out
    assert "cover_below_floor" in out


def test_render_auto_applies_reversible_not_spend_up(monkeypatch, capsys) -> None:
    """Render auto-applies the single AUTO reversible (FX-M8MA bid_down), never a spend-up."""
    calls = _spy(monkeypatch)
    rc = queue_run.main(
        [
            "render",
            "--candidates", CANDIDATES,
            "--cover", COVER,
            "--dryrun-resp", DRYRUN,
            "--apply-resp", APPLYR,
            "--status-resp", STATUS,
            "--find-echo", FINDE,
        ]
    )
    assert rc == 0
    # Exactly ONE apply.apply call — the lone auto-class reversible row (FX-M8MA bid_down).
    assert len(calls) == 1
    assert calls[0].sku == "FX-M8MA-MMSA"
    assert calls[0].action_type == "bid_down"
    out = capsys.readouterr().out
    assert "auto-applied" in out  # the reversible was actually applied, not just labelled


def test_auto_apply_injects_live_reversible_cap(monkeypatch, capsys) -> None:
    """The auto-apply action carries the live 50% reversible cap in its params (CR-05).

    apply._max_reversible_pct reads ONLY action.params["max_reversible_pct_change"] — it never
    reads thresholds.toml. The candidate fixtures inject no such param, so before CR-05 the cap
    reached magnitude.check as None (seeded permissive) and the documented "live at 50%" cap
    never fired. _auto_apply now reads thresholds.read and seeds it, so the cap actually enforces.
    """
    calls = _spy(monkeypatch)
    rc = queue_run.main(
        [
            "render",
            "--candidates", CANDIDATES,
            "--cover", COVER,
            "--dryrun-resp", DRYRUN,
            "--apply-resp", APPLYR,
            "--status-resp", STATUS,
            "--find-echo", FINDE,
        ]
    )
    assert rc == 0
    assert len(calls) == 1
    # The live cap (thresholds.toml max_reversible_pct_change = 50) is injected into the action
    # params so magnitude.check actually enforces it — never silently permissive.
    assert calls[0].params.get("max_reversible_pct_change") == 50.0


def test_apply_mode_without_approve_refuses(monkeypatch, capsys) -> None:
    """A needs-approval spend-up in apply mode WITHOUT --approve refuses; apply.apply not called."""
    calls = _spy(monkeypatch)
    rc = queue_run.main(
        [
            "apply",
            "--sku", "EU-Z87B-ZRBZ",
            "--action-type", "budget_up",
            "--delta-spend", "21.0",
            "--entity-type", "campaigns",
            "--entity-id", "CMP-1000000000003",
        ]
    )
    assert rc == 0
    assert calls == []  # the real write never fired
    out = capsys.readouterr().out
    payload = json.loads(out.strip().splitlines()[-1])
    assert payload["code"] == "approval_required"


def test_apply_mode_with_approve_applies(monkeypatch, capsys) -> None:
    """A spend-up in apply mode WITH --approve that clears the FULL gate chain runs apply.apply.

    The write path runs the SAME read-only chain render mode runs (CR-01): margin gate
    (--artifact) -> cover/conversion (--cover) -> matured-window -> internal-competition. So an
    applying spend-up must clear ALL of them, not just the margin gate. EU-Z87B-ZRBZ's window
    (CM ~36%, ceiling ~21%) clears a +21 CAD budget-up (projected TACOS ~7.7% < 21%), and its
    cover-map entry (cover 60 >= 42, conversion 25% >= 12%, days_of_data 30 matured) clears the
    cover/conversion + matured-window gates, so the write applies.
    """
    calls = _spy(monkeypatch)
    rc = queue_run.main(
        [
            "apply",
            "--approve",
            "--sku", "EU-Z87B-ZRBZ",
            "--action-type", "budget_up",
            "--delta-spend", "21.0",
            "--entity-type", "campaigns",
            "--entity-id", "CMP-1000000000003",
            "--artifact", PROFIT,
            "--cover", COVER,
            "--dryrun-resp", DRYRUN,
            "--apply-resp", APPLYR,
            "--status-resp", STATUS,
            "--find-echo", FINDE,
        ]
    )
    assert rc == 0
    assert len(calls) == 1
    assert calls[0].action_type == "budget_up"
    out = capsys.readouterr().out
    payload = json.loads(out.strip().splitlines()[-1])
    assert payload["action_id"] == "ACT-TEST-0001"
    assert payload["status"] == "COMPLETED"


def test_apply_mode_runs_cover_gate_before_write(monkeypatch, capsys) -> None:
    """The write path runs the cover/conversion gate, refusing GG-0DC1 (1 FBA unit) (CR-01).

    EXEC-05: GG-0DC1-SKHG at ~1 FBA unit (cover 2d, far below the 42-day floor) must be REFUSED
    cover_below_floor on the path that fires a real write — apply.apply alone never runs the
    cover gate, so before CR-01 this over-sell-into-stockout raise could fire. apply.apply must
    NOT be called (the write never starts).
    """
    calls = _spy(monkeypatch)
    rc = queue_run.main(
        [
            "apply",
            "--approve",
            "--sku", "GG-0DC1-SKHG",
            "--action-type", "bid_up",
            "--delta-spend", "7.0",
            "--entity-type", "targets",
            "--entity-id", "TGT-1000000000007",
            "--artifact", PROFIT,
            "--cover", COVER,
            "--dryrun-resp", DRYRUN,
            "--apply-resp", APPLYR,
            "--status-resp", STATUS,
            "--find-echo", FINDE,
        ]
    )
    assert rc == 0
    assert calls == []  # the real write never fired — the cover gate refused first
    out = capsys.readouterr().out
    payload = json.loads(out.strip().splitlines()[-1])
    assert payload["code"] == "cover_below_floor"


def test_apply_mode_spend_up_refuses_no_cover_data_on_write_path(monkeypatch, capsys) -> None:
    """A spend-up with NO --cover refuses no_cover_data on the write path, never sails past (CR-01).

    Unlike render mode (advisory; skips a gate whose input is absent), the write path requires
    the EXEC-05 cover guardrail to have run — a missing live read REFUSES, never silently skips.
    """
    calls = _spy(monkeypatch)
    rc = queue_run.main(
        [
            "apply",
            "--approve",
            "--sku", "EU-Z87B-ZRBZ",
            "--action-type", "budget_up",
            "--delta-spend", "21.0",
            "--entity-type", "campaigns",
            "--entity-id", "CMP-1000000000003",
            "--artifact", PROFIT,
            "--dryrun-resp", DRYRUN,
            "--apply-resp", APPLYR,
            "--status-resp", STATUS,
            "--find-echo", FINDE,
        ]
    )
    assert rc == 0
    assert calls == []  # no cover data -> refuse before the write fires
    out = capsys.readouterr().out
    payload = json.loads(out.strip().splitlines()[-1])
    assert payload["code"] == "no_cover_data"


def test_apply_mode_spend_up_without_artifact_refuses_no_margin(monkeypatch, capsys) -> None:
    """A spend-up reaching the write path with NO --artifact refuses no_margin, never crashes (CR-04).

    Without a margin frame, apply.apply -> gate.evaluate would dereference a None frame
    (AttributeError). The constitution requires a typed refusal for a missing money-gate input,
    so _apply_mode refuses BEFORE apply.apply is ever called.
    """
    calls = _spy(monkeypatch)
    rc = queue_run.main(
        [
            "apply",
            "--approve",
            "--sku", "EU-Z87B-ZRBZ",
            "--action-type", "budget_up",
            "--delta-spend", "21.0",
            "--entity-type", "campaigns",
            "--entity-id", "CMP-1000000000003",
            "--dryrun-resp", DRYRUN,
            "--apply-resp", APPLYR,
            "--status-resp", STATUS,
            "--find-echo", FINDE,
        ]
    )
    assert rc == 0
    assert calls == []  # the real write never fired
    out = capsys.readouterr().out
    payload = json.loads(out.strip().splitlines()[-1])
    assert payload["code"] == "no_margin"


def test_no_seller_uuid_in_stdout(capsys) -> None:
    """The seller UUID never appears in the rendered table / stdout (hard rule 5)."""
    queue_run.main(["render", "--candidates", CANDIDATES, "--cover", COVER])
    out = capsys.readouterr().out
    assert "sellerId" not in out
    seller = os.environ.get("AMAZON_CA_SELLER_ID")
    if seller:
        assert seller not in out


# ---- WR-01: is_act_now bypasses the matured-window gate -------------------------------------

_ACT_NOW_CANDIDATE = {
    "sku": "DEAD-SKU",
    "action_type": "bid_up",
    "delta_spend_weekly": 5.0,
    "entity": "TGT dead",
    "entity_id": "TGT-DEAD",
}


def test_immature_window_refuses_when_not_act_now() -> None:
    """An immature window (3d < 7d SP) refuses immature_window for a normal, NON-act-now signal."""
    cover_map = {
        "DEAD-SKU": {
            "days_of_cover": 90,
            "conversion_pct": 25.0,
            "days_of_data": 3,  # below the 7d SP maturity threshold
            "ad_product": "SPONSORED_PRODUCTS",
        }
    }
    refusal = queue_run._spend_up_refusal(
        _ACT_NOW_CANDIDATE,
        gate_frame=None,  # margin gate skipped (no frame) so we isolate the maturity branch
        catalog_path=None,
        cover_map=cover_map,
        term_acos_map={},
        marketplace="CA",
    )
    assert isinstance(refusal, GateRefusal)
    assert refusal.code == "immature_window"


def test_act_now_signal_bypasses_immature_window(monkeypatch) -> None:
    """WR-01: an act-now signal on the SAME immature window bypasses the maturity wait (no refusal).

    The harvest D-10 contract: an obviously-dead signal (here zero lifetime orders) must not wait
    for the window to mature. With is_act_now wired in, the matured-window gate is skipped and the
    chain returns None (no immature_window refusal) for the same 3d window.
    """
    cover_map = {
        "DEAD-SKU": {
            "days_of_cover": 90,
            "conversion_pct": 25.0,
            "days_of_data": 3,  # still immature, but...
            "ad_product": "SPONSORED_PRODUCTS",
            "lifetime_orders": 0,  # ...an act-now signal: bypass the maturity wait
        }
    }
    refusal = queue_run._spend_up_refusal(
        _ACT_NOW_CANDIDATE,
        gate_frame=None,
        catalog_path=None,
        cover_map=cover_map,
        term_acos_map={},
        marketplace="CA",
    )
    assert refusal is None  # act-now -> the maturity gate did not refuse
