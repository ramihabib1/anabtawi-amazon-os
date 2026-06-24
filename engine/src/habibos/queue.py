"""Daily-queue class-tagger + dollar-ranked table renderer (QUEUE-01/02/03, D-01/D-02/D-07).

This module owns TWO things and NO money math:

  1. The reversibility CLASS TAG (D-01 / D-02). The class is derived from action_type +
     blast radius exactly the way `ProposedAction.is_spend_increasing` derives a flag from
     data (result.py:92-94) — it is a pure lookup over two reviewable frozensets, never a
     judgement call. A spend-UP (bid_up / budget_up / harvest) and a wider-blast negative
     (phrase / broad) tag `needs-approval` (explicit approval — the spend or the suppression
     blast radius is too wide for standing approval). A pause / EXACT-match negative /
     bid_down tags `auto` (a reversible move carries standing approval — autonomy != silence,
     shown already-actioned). An UNKNOWN action_type fails safe toward the human gate
     (`needs-approval`) — an unmodeled action is NEVER auto-applied.

  2. The dollar-ranked TABLE RENDER (D-07). The renderer formats already-ranked, already-
     tagged QueueRows and computes NOTHING — no ratio, no rank, no class (the ranking is
     rank_queue.py's, the money is the gate's, the class is `classify`/`classify_row`'s).
     This mirrors the no-business-logic-in-render rule (answer_tacos._serialize): a render
     bug cannot fabricate a dollar figure or a class. A None expected estimate renders as an
     em-dash, never 0 — it is "no defensible estimate", and rank_queue already sorts it last.

Opens no network connection — a pure utility over QueueRow + stdlib only.
"""

from __future__ import annotations

import dataclasses

from .result import QueueRow

NEEDS_APPROVAL = "needs-approval"
AUTO = "auto"

# The two reviewable class maps (D-01 / D-02). Kept as frozensets so the mapping is
# auditable in one place and the contract test can assert each membership directly.
# A spend increase or a wide-blast (phrase/broad) negative needs explicit approval.
NEEDS_APPROVAL_ACTIONS = frozenset(
    {"bid_up", "budget_up", "harvest", "negative_phrase", "negative_broad"}
)
# A reversible move carries standing approval. "negative_exact" is the EXACT-match negative;
# a bare "negative" with no match_type is treated as exact (the reversible default).
AUTO_ACTIONS = frozenset({"pause", "bid_down", "negative_exact", "negative"})

# The D-07 render columns, in dollar-ranked, one-screen order.
COLUMNS = (
    "rank",
    "SKU",
    "entity",
    "action",
    "current -> proposed",
    "expected $/wk",
    "provenance",
    "class",
)

__all__ = [
    "classify",
    "classify_row",
    "tag",
    "render_row",
    "render",
    "NEEDS_APPROVAL_ACTIONS",
    "AUTO_ACTIONS",
]


def _canonical(action_type: str, match_type: str | None = None) -> str:
    """Fold the `negative` + match_type form into the canonical action_type.

    The standalone tagger is called both ways: `classify("negative", match_type="phrase")`
    (the entity-level call) and `classify("negative_phrase")` (the QueueRow.action_type, which
    already encodes the match). Normalizing here keeps the membership maps the single source.
    """
    if action_type == "negative" and match_type:
        return f"negative_{match_type}"
    return action_type


def classify(action_type: str, match_type: str | None = None) -> str:
    """Return the reversibility class ("needs-approval" | "auto") for an action.

    Driven off frozenset membership (the data-derived-flag style). An UNKNOWN action_type
    returns needs-approval — fail safe toward the human gate, never auto-apply an unmodeled
    action (T-09-04-01).
    """
    canon = _canonical(action_type, match_type)
    if canon in NEEDS_APPROVAL_ACTIONS:
        return NEEDS_APPROVAL
    if canon in AUTO_ACTIONS:
        return AUTO
    return NEEDS_APPROVAL


def classify_row(row: QueueRow) -> str:
    """Class for a ranked QueueRow — its action_type already encodes the negative match."""
    return classify(row.action_type)


def tag(rows: list[QueueRow]) -> list[QueueRow]:
    """Return new QueueRows with `cls` set from classify_row, order PRESERVED.

    QueueRow is frozen, so we rebuild via dataclasses.replace. The incoming order is the
    dollar-ranked order rank_queue produced — the tagger never re-sorts (D-07).
    """
    return [dataclasses.replace(row, cls=classify_row(row)) for row in rows]


def render_row(
    rank: int,
    sku: str,
    entity: str,
    action: str,
    current: float | None,
    proposed: float | None,
    expected_weekly_usd: float | None,
    provenance: str,
    match_type: str | None = None,
) -> dict:
    """The per-row render schema (D-07) — a typed dict carrying every surfaced key.

    `class` is derived here via classify (the renderer formats; the class map decides) so a
    single row can be emitted without first building a QueueRow.

    DELIBERATE FUTURE-USE PUBLIC API (IN-01): this builder is tested but NOT yet on any
    production path — `render` (below) builds its table cells directly from QueueRow fields, it
    does NOT call render_row. It is exported and contract-pinned so a future per-row / JSON
    surface can reuse the exact schema; a reader should not assume it runs in the current table.
    """
    return {
        "rank": rank,
        "sku": sku,
        "entity": entity,
        "action": action,
        "current": current,
        "proposed": proposed,
        "expected_weekly_usd": expected_weekly_usd,
        "provenance": provenance,
        "class": classify(action, match_type),
    }


def _fmt_money(value: float | None) -> str:
    """Format a CAD figure; None -> em-dash ("no defensible estimate", never 0)."""
    if value is None:
        return "—"
    return f"{value:.2f}"


def _fmt_transition(current: float | None, proposed: float | None) -> str:
    return f"{_fmt_money(current)} -> {_fmt_money(proposed)}"


def render(rows: list[QueueRow]) -> str:
    """Format already-ranked, already-tagged rows as ONE dollar-ranked, class-tagged table.

    Reads QueueRow fields only — computes no ratio, no rank, no class. A None expected
    estimate renders as an em-dash (never 0); rank_queue already sorted those rows last.
    The class shown is `row.cls` (set by `tag`). Markdown pipe table — dollars-first, one
    screen (CLAUDE.md rank-by-dollars).
    """
    header = "| " + " | ".join(COLUMNS) + " |"
    divider = "| " + " | ".join("---" for _ in COLUMNS) + " |"
    lines = [header, divider]
    for rank, row in enumerate(rows, start=1):
        cells = (
            str(rank),
            row.sku,
            row.entity,
            row.action_type,
            _fmt_transition(row.current, row.proposed),
            _fmt_money(row.expected_weekly_usd),
            row.provenance,
            row.cls,
        )
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)
