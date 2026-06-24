"""Dollar-ranked queue money-core: expected-weekly-$ estimator + dollars-first sort (D-07).

This is hand-written, pytest-covered money-touching logic (CLAUDE.md hard rules 3 + 4) —
the genuinely new money math of Phase 9. Its anti-fabrication contract mirrors tacos.py:

  - The estimator computes a candidate's EXPECTED weekly $ impact from the candidate's OWN
    window-summed components, NEVER a chat estimate. The formula is reviewed code (below),
    and test_rank_queue rebuilds the expected value from the same components (the test_tacos
    `_pct`-mirror pattern, T-09-03-01 mitigation) so a fabricated $ cannot pass review.
  - A candidate with no defensible $ estimate — a zero/missing denominator that makes the
    underlying window ACOS undefined — gets `expected_weekly_usd = None`, NEVER 0 and NEVER
    a guess (T-09-03-02). This clones the tacos._ratio None-on-undefined grammar EXACTLY.
  - None-estimate rows sort LAST (the D-07 key), never silently dropped (hard rule 4).
  - Every emitted QueueRow cites its provenance — the DataDoe source id + window behind the
    numbers (T-09-03-03, hard rule 5). No seller UUID enters a row (source-id + dates only).

This module is PURE: it opens NO socket and performs NO fetch (D-04). The agent does all
MCP I/O and feeds the candidate components (+ the source/window provenance they carry) in
via the committed candidate set; the engine only reads that local artifact and ranks.

Estimate model (documented in tests/fixtures/queue_candidates.json):
    expected incremental weekly sales $ = delta_spend_weekly / window_acos_fraction,
    where window_acos_fraction = ad_spend_sum / ad_sales_sum over the cited window.
A zero ad_sales_sum (or ad_spend_sum, i.e. a zero acos_fraction) -> undefined ACOS ->
expected_weekly_usd is None. A reversible spend-DOWN candidate has delta_spend_weekly <= 0,
so its expected weekly $ is negative (a saving) and it ranks below the spend-up winners but
above the undefined-estimate rows.
"""

from __future__ import annotations

import json
from pathlib import Path

from .result import QueueRow

__all__ = ["estimate_weekly_usd", "rank"]


def estimate_weekly_usd(candidate: dict) -> float | None:
    """Expected weekly $ impact of a candidate, or None when undefined.

    Clones the tacos._ratio None-on-undefined shape: any zero/missing denominator (here a
    zero/missing ad_sales_sum, or a zero window_acos_fraction from a zero ad_spend_sum)
    returns None ("undefined") — NEVER 0 and NEVER a substituted value (T-09-03-02).

    The defensible formula (reviewed code, tied to the candidate's own fields so the test
    can rebuild it): incremental weekly sales $ = delta_spend_weekly / window_acos_fraction,
    where window_acos_fraction = ad_spend_sum / ad_sales_sum over the cited window. Spending
    $X more at a window ACOS fraction f returns X / f in incremental sales; a spend-down
    (delta_spend_weekly < 0) yields a negative figure (a saving). The result rounds to cents.
    """
    delta_spend_weekly = candidate.get("delta_spend_weekly")
    ad_spend_sum = candidate.get("ad_spend_sum")
    ad_sales_sum = candidate.get("ad_sales_sum")

    # Missing component -> undefined (never coerce a missing input to 0).
    if delta_spend_weekly is None or ad_spend_sum is None or ad_sales_sum is None:
        return None
    # Zero/missing denominator -> undefined ACOS -> None (the _ratio grammar).
    if ad_sales_sum == 0:
        return None
    acos_fraction = ad_spend_sum / ad_sales_sum
    if acos_fraction == 0:
        return None
    return round(delta_spend_weekly / acos_fraction, 2)


def rank(candidates_path: str | Path) -> list[QueueRow]:
    """Read the committed candidate set and emit dollar-ranked, provenance-cited QueueRows.

    The agent feeds the candidate components into a local JSON artifact (no socket here, D-04);
    `rank` reads that artifact, estimates each candidate's expected weekly $ impact from its
    OWN components, and sorts dollars-first with no-estimate rows LAST.

    Mirrors tacos.classify's present-loop + the D-07 sort key. The candidate set carries the
    DataDoe source + window in each candidate's `provenance` field (and at the file's top-level
    `source`/`window`), so every QueueRow cites provenance (hard rule 5) without the engine ever
    naming the source itself. `cls` is left at the QueueRow default ("auto") — Plan 04's queue.py
    sets the real reversibility class; this module computes none, renders nothing, opens no socket.
    """
    raw = json.loads(Path(candidates_path).read_text())
    candidates = raw["candidates"]

    # Fallback provenance from the file's own header (source id + window) — used only if a
    # candidate omits its per-row provenance, so every row still cites source + window.
    top_source = raw.get("source", "")
    top_window = raw.get("window", "")
    fallback_provenance = f"{top_source} | window {top_window}".strip(" |")

    rows: list[QueueRow] = []
    for c in candidates:
        provenance = c.get("provenance") or fallback_provenance
        rows.append(
            QueueRow(
                sku=c["sku"],
                entity=c.get("entity", ""),
                action_type=c.get("action_type", ""),
                current=c.get("current"),
                proposed=c.get("proposed"),
                expected_weekly_usd=estimate_weekly_usd(c),
                provenance=provenance,
            )
        )

    # D-07: highest expected-$/wk first, None-estimate rows LAST (never treated as 0).
    rows.sort(key=lambda x: (x.expected_weekly_usd is None, -(x.expected_weekly_usd or 0)))
    return rows
