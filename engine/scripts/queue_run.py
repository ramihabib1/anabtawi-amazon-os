#!/usr/bin/env python3
"""Thin CLI: the daily dollar-ranked PPC queue — rank -> gate -> render, auto-applying the
standing-approved reversibles and applying an explicitly-approved spend-up through the
Phase-8 spine. NO business logic (the ranking is rank_queue's, the money/gates are the
pytest-covered modules', the spine is apply.apply's). Structural twin of apply_action.py /
gate_action.py.

THE SEAM (CLAUDE.md hard rule 1): Python opens NO network connection. The live
velocity / days-of-cover / conversion reads and the dryRun / apply / poll / FIND responses
are MCP tool calls the AGENT makes; this CLI only reads the JSON the agent already downloaded
to LOCAL files and threads them to the spine as zero-arg callables. A parallel Python HTTP
client is FORBIDDEN.

TWO MODES (D-06 batch approval):
  render (default): rank -> tag -> render the dollar-ranked, class-tagged table. For every
    spend-UP row, run the READ-ONLY gate chain (margin gate -> cover/conversion gate ->
    matured-window -> internal-competition) and annotate any GateRefusal on the row so a
    refused raise is NOT actionable. Each AUTO-class row (a standing-approved reversible) is
    actually auto-applied via apply.apply (autonomy != silence — a real spine call, not a
    label); a needs-approval row is NEVER auto-applied here (it waits for apply mode +
    --approve).
  apply: given the explicit --approve batch gate, build a spend-up ProposedAction and run it
    through apply.apply UNCHANGED (the margin gate inside refuses an over-ceiling raise, never
    clamps — D-11). Without --approve a needs-approval row is refused, never applied.

Security (hard rule 5): the seller UUID is NEVER passed into a log field, the rendered table,
or stdout. A refusal can never serialize as applied (end_fields["status"] is derived from the
result TYPE, mirroring apply_action.py / gate_action.py).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from habibos import apply, cover_gate, gate, harvest, queue, rank_queue, thresholds
from habibos import logging as habibos_logging
from habibos.result import (
    AppliedResult,
    GateRefusal,
    GateVerdict,
    ProposedAction,
    QueueRow,
    Refusal,
)

# Repo root is one level above scripts/ (mirrors apply_action.py / gate_action.py).
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OWNED = REPO_ROOT / "config" / "owned_asins.toml"
DEFAULT_CATALOG = REPO_ROOT / "config" / "sku_catalog.toml"

# The spend-up action types (positive delta_spend) — everything else is a reversible.
SPEND_UP_ACTIONS = frozenset({"bid_up", "budget_up", "harvest"})


def _load(path: str) -> dict:
    """Read a local JSON fixture the agent already downloaded (no network — the seam)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _spend_up_refusal(
    candidate: dict,
    *,
    gate_frame,
    catalog_path: str | Path | None,
    cover_map: dict,
    term_acos_map: dict,
    marketplace: str,
) -> GateRefusal | None:
    """Run the READ-ONLY gate chain for one spend-up candidate; return the FIRST refusal or None.

    Mirrors the spine's branch order: margin gate -> cover/conversion -> matured window ->
    internal competition. Each gate is skipped only when its agent-supplied input is absent
    (so a partial daily run still surfaces the gates it CAN evaluate); a present input that
    refuses short-circuits. This computes nothing — every decision is a pytest-covered module.
    """
    sku = candidate["sku"]
    action = ProposedAction(
        sku=sku,
        action_type=candidate["action_type"],
        delta_spend=float(candidate.get("delta_spend_weekly", 0.0)),
        marketplace=marketplace,
        entity_type=candidate.get("entity_type"),
        entity_id=candidate.get("entity_id"),
        params=candidate.get("params", {}),
    )

    # 1. Margin gate (Phase 7) — projected TACOS vs the SKU's margin-derived ceiling.
    if gate_frame is not None and catalog_path is not None:
        verdict = gate.evaluate(gate_frame, action, catalog_path, marketplace)
        if isinstance(verdict, GateRefusal):
            return verdict

    # 2. Cover / conversion gate (Plan 02) — sub-cover or sub-conversion SKUs refuse.
    live = cover_map.get(sku)
    if live is not None:
        refusal = cover_gate.check(
            action,
            live.get("days_of_cover"),
            live.get("conversion_pct"),
            thresholds.read("days_of_cover_floor", marketplace),
            thresholds.read("conversion_benchmark", marketplace),
        )
        if isinstance(refusal, GateRefusal):
            return refusal

    # 3. Matured-window gate (Plan 05) — an efficiency verdict on an immature window refuses.
    #    A present-but-null days_of_data (a failed/partial agent read) is "no data": skip this
    #    gate rather than crash on int(None). Mirror cover_gate's None-is-no-data discipline —
    #    the engine never turns a missing live read into an uncaught TypeError (hard rule 4).
    days_of_data = live.get("days_of_data") if live is not None else None
    if days_of_data is not None:
        ad_product = live.get("ad_product", "SPONSORED_PRODUCTS")
        refusal = harvest.judge_later_blocked(action, ad_product, int(days_of_data))
        if isinstance(refusal, GateRefusal):
            return refusal

    # 4. Internal-competition gate (Plan 05) — a contested term blocks a bid-up.
    term_key = candidate.get("entity")
    contested = term_acos_map.get(term_key)
    if contested:
        refusal = harvest.consolidation_blocked(action, contested)
        if isinstance(refusal, GateRefusal):
            return refusal

    return None


def _auto_apply(candidate: dict, args, marketplace: str):
    """Apply one standing-approved reversible through the Phase-8 spine UNCHANGED.

    The reversible's delta_spend is <=0 (the margin gate auto-passes), but the magnitude cap —
    now LIVE at 50 — refuses an over-cap reversible. Returns the typed spine result. The agent
    supplies the reversible's dryRun/apply/poll/FIND responses as local files (the seam).
    """
    action = ProposedAction(
        sku=candidate["sku"],
        action_type=candidate["action_type"],
        delta_spend=float(candidate.get("delta_spend_weekly", 0.0)),
        marketplace=marketplace,
        entity_type=candidate.get("entity_type"),
        entity_id=candidate.get("entity_id"),
        params=candidate.get("params", {}),
    )
    return apply.apply(
        action,
        owned_source=args.owned,
        start_dryrun=lambda: _load(args.dryrun_resp),
        start_apply=lambda: _load(args.apply_resp),
        get_status=lambda: _load(args.status_resp),
        find_echo=lambda: _load(args.find_echo),
        confirm_canary=args.confirm_canary,
        catalog_path=args.catalog,
        ad_product=args.ad_product,
    )


def _status_of(result) -> str:
    """One-word actioned status derived from the spine result TYPE (never from a flag)."""
    if isinstance(result, AppliedResult):
        return f"applied:{result.status}"
    if isinstance(result, (Refusal, GateRefusal)):
        return f"refused:{result.code}"
    return "unknown"


def _render_mode(args) -> int:
    """Rank -> tag -> render the daily table; annotate spend-up refusals; auto-apply reversibles."""
    payload = _load(args.candidates)
    candidates = {c["sku"]: c for c in payload.get("candidates", [])}

    # Optional agent-supplied read inputs (skip a gate cleanly when its input is absent).
    cover_map = _load(args.cover) if args.cover else {}
    term_acos_map = _load(args.term_acos) if args.term_acos else {}
    gate_frame = None
    if args.artifact:
        parsed = gate.parse(Path(args.artifact), args.status)
        gate_frame = None if isinstance(parsed, Refusal) else parsed

    rows = queue.tag(rank_queue.rank(args.candidates))

    annotations: list[str] = []
    rendered: list[QueueRow] = []
    can_auto_apply = bool(args.dryrun_resp and args.apply_resp and args.status_resp and args.find_echo)

    for row in rows:
        candidate = candidates.get(row.sku, {})
        note = ""
        if row.cls == queue.NEEDS_APPROVAL:
            if row.action_type in SPEND_UP_ACTIONS:
                refusal = _spend_up_refusal(
                    candidate,
                    gate_frame=gate_frame,
                    catalog_path=args.catalog,
                    cover_map=cover_map,
                    term_acos_map=term_acos_map,
                    marketplace=args.marketplace,
                )
                if refusal is not None:
                    note = f"REFUSED:{refusal.code} — {refusal.reason}"
                else:
                    note = "needs-approval (gate-passed; awaits --approve)"
            else:
                note = "needs-approval (phrase/broad negative — awaits --approve)"
            # A needs-approval row is NEVER auto-applied in render mode.
        else:  # AUTO — a standing-approved reversible: actually apply it (autonomy != silence).
            if can_auto_apply:
                result = _auto_apply(candidate, args, args.marketplace)
                note = f"auto-applied -> {_status_of(result)}"
            else:
                note = "auto (standing-approved; apply inputs not supplied this run)"
        rendered.append(row)
        annotations.append(f"  {row.sku} [{row.action_type}]: {note}")

    sys.stdout.write(queue.render(rendered))
    sys.stdout.write("\n\nGate / apply annotations:\n")
    sys.stdout.write("\n".join(annotations))
    sys.stdout.write("\n")
    return 0


def _apply_mode(args) -> int:
    """Apply ONE explicitly-approved spend-up through the spine; refuse without --approve."""
    action = ProposedAction(
        sku=args.sku,
        action_type=args.action_type,
        delta_spend=args.delta_spend,
        marketplace=args.marketplace,
        entity_type=args.entity_type,
        entity_id=args.entity_id,
        params=json.loads(args.params),
    )

    # The batch-approval gate (D-06 / WRITE-04): a spend-up (needs-approval) row requires the
    # one deliberate explicit --approve. Absent -> refuse, never apply (apply.apply NOT called).
    needs_approval = queue.classify(args.action_type) == queue.NEEDS_APPROVAL
    if needs_approval and not args.approve:
        refusal = Refusal(
            "needs-approval spend-up requires the explicit --approve batch confirm (D-06)",
            "approval_required",
        )
        json.dump(dataclasses.asdict(refusal), sys.stdout)
        sys.stdout.write("\n")
        return 0

    gate_frame = None
    if args.artifact:
        parsed = gate.parse(Path(args.artifact), args.status)
        gate_frame = None if isinstance(parsed, Refusal) else parsed

    with habibos_logging.logged_call("queue_run", marketplace=args.marketplace) as end_fields:
        result = apply.apply(
            action,
            owned_source=args.owned,
            start_dryrun=lambda: _load(args.dryrun_resp),
            start_apply=lambda: _load(args.apply_resp),
            get_status=lambda: _load(args.status_resp),
            find_echo=lambda: _load(args.find_echo),
            confirm_canary=args.confirm_canary,
            catalog_path=args.catalog,
            gate_frame=gate_frame,
            ad_product=args.ad_product,
        )
        # A refusal can NEVER serialize as applied — derive status from the result TYPE.
        end_fields["status"] = (
            "refused" if isinstance(result, (Refusal, GateRefusal)) else "applied"
        )

    json.dump(dataclasses.asdict(result), sys.stdout)
    sys.stdout.write("\n")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Daily dollar-ranked PPC queue: render the class-tagged table (auto-applying "
        "standing-approved reversibles) or apply an explicitly-approved spend-up through the spine.",
    )
    p.add_argument("mode", choices=["render", "apply"], help="render (default daily table) | apply (one approved spend-up).")
    p.add_argument("--marketplace", default="CA", help="Marketplace code (default CA).")
    p.add_argument("--catalog", default=str(DEFAULT_CATALOG), help="Committed machine-readable catalog.")
    p.add_argument("--owned", default=str(DEFAULT_OWNED), help="Owned-ASIN denylist.")
    p.add_argument("--ad-product", default="SPONSORED_PRODUCTS", help="Ad product scoping the FIND cache.")
    # render-mode read inputs (all optional — a missing input skips its gate cleanly).
    p.add_argument("--candidates", help="Path to the agent-downloaded candidate set JSON (render mode).")
    p.add_argument("--cover", help="Path to the per-SKU live cover+conversion map JSON (render mode).")
    p.add_argument("--term-acos", help="Path to the per-term campaign-ACOS map JSON (render mode).")
    p.add_argument("--artifact", help="Path to the downloaded premium export CSV for the margin gate.")
    p.add_argument("--status", default="COMPLETED", help="Export job status (COMPLETED|FAILED).")
    # apply-mode ProposedAction fields.
    p.add_argument("--sku", help="The SKU the proposed spend-up targets (apply mode).")
    p.add_argument("--action-type", help="bid_up | budget_up | harvest (apply mode).")
    p.add_argument("--delta-spend", type=float, default=0.0, help="CAD spend delta; >0 spend-up (apply mode).")
    p.add_argument("--entity-type", help="FIND entity class: campaigns | targets | adGroups | ads.")
    p.add_argument("--entity-id", help="FIND-verified live entity id the write targets.")
    p.add_argument("--params", default="{}", help="JSON build/identity params (state / keyword+matchType / bid).")
    # agent-downloaded MCP fixture files (the seam — no network).
    p.add_argument("--dryrun-resp", help="actions_start(dryRun:true) response JSON.")
    p.add_argument("--apply-resp", help="actions_start(dryRun:false) response JSON (the real write).")
    p.add_argument("--status-resp", help="actions_get response JSON (the poll loop).")
    p.add_argument("--find-echo", help="*_FIND response JSON for the FIND-before-write + echo.")
    # the explicit batch-approval gate (D-06) + the one-time canary confirm.
    p.add_argument("--approve", action="store_true", help="The explicit batch confirm a spend-up requires (D-06).")
    p.add_argument("--confirm-canary", action="store_true", help="One-time confirm for the phase's first apply.")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    habibos_logging.configure()
    if args.mode == "render":
        return _render_mode(args)
    return _apply_mode(args)


if __name__ == "__main__":
    raise SystemExit(main())
