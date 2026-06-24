"""Class-tagging renderer contract tests (D-01 / D-02) — Wave 1, RED.

These are the EXECUTABLE CONTRACT that Plan 09-03/09-04 (`habibos.queue`) implements
against. Until `habibos.queue` exists they FAIL RED on the missing import — the intended
Phase-9 Wave-1 baseline (the plan's verify step expects this), NOT a defect.

What the contract pins (the standing-approval autonomy split, D-01 / D-02):
  - a spend-UP row (bid_up / budget_up / harvest) tags `needs-approval` (explicit approval
    for spend increases — D-01);
  - a phrase- or broad-match negative tags `needs-approval` (a phrase/broad negative can
    over-suppress, so it is NOT auto — the RED queue contract D-02);
  - a pause / exact-match negative / bid_down tags `auto` (reversible moves carry standing
    approval — D-01/D-02).
  - the render row schema carries the keys:
    rank, sku, entity, action, current, proposed, expected_weekly_usd, provenance, class.

Mirror signatures (final shape decided in Plan 03/04):
    queue.classify(action_type, match_type=None) -> "needs-approval" | "auto"
    queue.render_row(rank, queue_row) -> dict   # the per-row render schema

No network. No seller UUID literal anywhere here.
"""

from __future__ import annotations

# RED on import: habibos.queue does not exist until Plan 09-03/09-04. The intended Wave-1 baseline.
from habibos import queue

NEEDS_APPROVAL = "needs-approval"
AUTO = "auto"


def test_spend_up_tags_needs_approval() -> None:
    """D-01: every spend-UP action (bid_up / budget_up / harvest) needs explicit approval."""
    assert queue.classify("bid_up") == NEEDS_APPROVAL
    assert queue.classify("budget_up") == NEEDS_APPROVAL
    assert queue.classify("harvest") == NEEDS_APPROVAL


def test_phrase_and_broad_negatives_tag_needs_approval() -> None:
    """D-02: a phrase- or broad-match negative can over-suppress -> needs-approval (NOT auto)."""
    assert queue.classify("negative", match_type="phrase") == NEEDS_APPROVAL
    assert queue.classify("negative", match_type="broad") == NEEDS_APPROVAL


def test_reversibles_tag_auto() -> None:
    """D-01/D-02: reversible moves carry standing approval -> auto.

    A pause, an EXACT-match negative, and a bid_down are all reversible.
    """
    assert queue.classify("pause") == AUTO
    assert queue.classify("negative", match_type="exact") == AUTO
    assert queue.classify("bid_down") == AUTO


def test_render_row_schema() -> None:
    """The per-row render schema carries every key the queue surface renders."""
    row = queue.render_row(
        rank=1,
        sku="EU-Z87B-ZRBZ",
        entity="SP-EU-Z87B campaign",
        action="budget_up",
        current=5.0,
        proposed=8.0,
        expected_weekly_usd=42.0,
        provenance="DataDoe premium Profit by SKU & Date (57a0cb319c) | window 2026-05-12..2026-06-10",
    )
    expected_keys = {
        "rank",
        "sku",
        "entity",
        "action",
        "current",
        "proposed",
        "expected_weekly_usd",
        "provenance",
        "class",
    }
    assert expected_keys <= set(row.keys())
    # A spend-up renders the needs-approval class.
    assert row["class"] == NEEDS_APPROVAL
    assert row["rank"] == 1
    assert row["sku"] == "EU-Z87B-ZRBZ"
