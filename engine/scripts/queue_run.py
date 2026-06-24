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
    write_path: bool = False,
) -> GateRefusal | None:
    """Run the READ-ONLY gate chain for one spend-up candidate; return the FIRST refusal or None.

    Mirrors the spine's branch order: margin gate -> cover/conversion -> matured window ->
    internal competition. A present input that refuses short-circuits; this computes nothing —
    every decision is a pytest-covered module.

    INPUT-ABSENCE policy depends on WHICH path calls this (CR-01):
      - render path (write_path=False): a gate whose agent-supplied input is absent is SKIPPED,
        so a partial daily run still surfaces the gates it CAN evaluate (the table is advisory).
      - write path (write_path=True): the cover/conversion gate REFUSES (no_cover_data) when the
        live read is absent rather than skipping — a spend-up that fires a REAL account write
        must have cleared the EXEC-05 cover guardrail, never sailed past it on missing data
        (CLAUDE.md hard rule 4 — never assume cover; the guardrail must run on the path that
        actually writes). cover_gate.check already refuses no_cover_data on a None live read, so
        we hand it an empty live ({}) when the SKU is absent from the cover map.
    """
    sku = candidate["sku"]
    # UNIT MATCH (CR-02): gate.projected_tacos_pct adds delta_spend to a WINDOW ad_spend_sum
    # and divides by the WINDOW total_sales_sum, so the delta MUST be in the SAME window unit
    # as those sums (the candidate set's cited window — trailing 30d in the fixture), NOT the
    # weekly figure rank_queue ranks on. Feeding the raw weekly delta against a 30d window
    # under-projected TACOS ~4x and weakened the over-ceiling refusal in the permissive
    # direction. We scale weekly -> window here so ProposedAction.delta_spend is unambiguously
    # window CAD. The downstream cover/harvest gates read only is_spend_increasing (the SIGN),
    # which scaling by a positive window/7 preserves. window_days is the candidate's own cited
    # window length (default 30 = the fixture's documented trailing-30d window), never an
    # invented threshold.
    window_days = float(candidate.get("window_days", 30))
    delta_spend_window = float(candidate.get("delta_spend_weekly", 0.0)) * (window_days / 7.0)
    action = ProposedAction(
        sku=sku,
        action_type=candidate["action_type"],
        delta_spend=delta_spend_window,
        marketplace=marketplace,
        entity_type=candidate.get("entity_type"),
        entity_id=candidate.get("entity_id"),
        params=candidate.get("params", {}),
    )

    # 1. Margin gate (Phase 7) — projected TACOS vs the SKU's margin-derived ceiling. delta_spend
    #    is now window-scaled (CR-02) so the projection adds like-for-like window CAD.
    if gate_frame is not None and catalog_path is not None:
        verdict = gate.evaluate(gate_frame, action, catalog_path, marketplace)
        if isinstance(verdict, GateRefusal):
            return verdict

    # 2. Cover / conversion gate (Plan 02) — sub-cover or sub-conversion SKUs refuse. On the
    #    write path a missing live read is NOT skipped: pass an empty live ({}) so cover_gate
    #    refuses no_cover_data (the EXEC-05 guardrail must run before a real write, CR-01).
    live = cover_map.get(sku)
    if live is None and write_path:
        live = {}
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


def _candidate_from_args(args) -> dict:
    """Build the gate-chain candidate dict from the apply-mode CLI args (CR-01).

    Lets _apply_mode reuse the SAME read-only gate chain render mode runs. The operator's
    --delta-spend is ALREADY the window CAD delta the margin gate (and apply.apply) act on, so
    we carry it as delta_spend_weekly with window_days=7 — the weekly->window scale in
    _spend_up_refusal (* window_days/7) is then a no-op and the margin gate here sees the EXACT
    same delta apply.apply will, never a doubly-scaled figure. The `entity` keys the
    internal-competition gate's term lookup (mirrors the render candidate's `entity`).
    """
    return {
        "sku": args.sku,
        "action_type": args.action_type,
        "delta_spend_weekly": args.delta_spend,
        "window_days": 7,
        "entity": args.entity_id,
        "entity_type": args.entity_type,
        "entity_id": args.entity_id,
        "params": json.loads(args.params),
    }


def _auto_apply(candidate: dict, args, marketplace: str):
    """Apply one standing-approved reversible through the Phase-8 spine UNCHANGED.

    The reversible's delta_spend is <=0 (the margin gate auto-passes), but the magnitude cap —
    now LIVE at 50 — refuses an over-cap reversible. Returns the typed spine result. The agent
    supplies the reversible's dryRun/apply/poll/FIND responses as local files (the seam).
    """
    # READ + INJECT THE LIVE CAP (CR-05): apply._max_reversible_pct reads ONLY
    # action.params["max_reversible_pct_change"]; it never reads thresholds.toml. The candidate
    # fixtures inject no such param, so the cap reached magnitude.check as None -> seeded
    # permissive -> the documented "live at 50%" reversible cap NEVER fired (a -90% bid_down
    # would auto-apply unbounded). Read the live cap from config and seed it into params so the
    # auto-apply path actually enforces it. setdefault: an explicit agent-injected per-action cap
    # still wins; absent one, the live config cap (50) applies. A None cap (key unset/empty)
    # stays permissive — the magnitude gate's documented seeded-permissive asymmetry (D-01/D-02).
    cap = thresholds.read("max_reversible_pct_change", marketplace)
    params = dict(candidate.get("params", {}))
    if cap is not None:
        params.setdefault("max_reversible_pct_change", cap)
    action = ProposedAction(
        sku=candidate["sku"],
        action_type=candidate["action_type"],
        delta_spend=float(candidate.get("delta_spend_weekly", 0.0)),
        marketplace=marketplace,
        entity_type=candidate.get("entity_type"),
        entity_id=candidate.get("entity_id"),
        params=params,
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
    # WR-05: key by a PER-ROW identity (sku, entity), not by sku alone. A SKU running several
    # campaigns yields multiple candidates with the same sku but DIFFERENT entities; a sku-only
    # dict kept only the LAST, so every ranked row for that sku resolved to the same (wrong)
    # candidate — gating the wrong entity_id / params. rank_queue's QueueRow carries the same
    # `entity`, so (sku, entity) maps each ranked row to its OWN candidate.
    candidates = {(c["sku"], c.get("entity", "")): c for c in payload.get("candidates", [])}

    # Optional agent-supplied read inputs (skip a gate cleanly when its input is absent).
    cover_map = _load(args.cover) if args.cover else {}
    term_acos_map = _load(args.term_acos) if args.term_acos else {}
    gate_frame = None
    if args.artifact:
        parsed = gate.parse(Path(args.artifact), args.status)
        gate_frame = None if isinstance(parsed, Refusal) else parsed

    rows = queue.tag(rank_queue.rank(args.candidates))

    # WR-04: annotations are keyed by the row's RANK (its 1-based position in the rendered
    # table), not by sku [action] alone. The table (queue.render) enumerates rows from rank 1 in
    # the SAME order, so a duplicate SKU or any future reordering between the two emissions can
    # no longer mismatch a refusal annotation to the wrong row — the rank index is the shared
    # row identity. The refusal is what tells the operator a raise is NOT actionable, so it must
    # not drift from the row it refers to.
    annotations: list[str] = []
    rendered: list[QueueRow] = []
    can_auto_apply = bool(args.dryrun_resp and args.apply_resp and args.status_resp and args.find_echo)

    for rank, row in enumerate(rows, start=1):
        candidate = candidates.get((row.sku, row.entity), {})
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
                # WR-03: wrap the queue-level auto-apply in logged_call (op + marketplace only;
                # NEVER the seller UUID) so EVERY queue-initiated real write has a consistent
                # audit record — mirroring _apply_mode. apply._logged_start_apply logs the inner
                # start, but the queue-level decision to auto-fire was previously unlogged.
                with habibos_logging.logged_call(
                    "queue_run", marketplace=args.marketplace
                ) as end_fields:
                    result = _auto_apply(candidate, args, args.marketplace)
                    # A refusal can NEVER serialize as applied — derive status from result TYPE.
                    end_fields["status"] = (
                        "refused"
                        if isinstance(result, (Refusal, GateRefusal))
                        else "applied"
                    )
                note = f"auto-applied -> {_status_of(result)}"
            else:
                note = "auto (standing-approved; apply inputs not supplied this run)"
        rendered.append(row)
        # Prefix with the rank so the annotation ties to its table row by POSITION (WR-04),
        # never by SKU string alone (which would mismatch a duplicate-SKU row).
        annotations.append(f"  #{rank} {row.sku} [{row.action_type}]: {note}")

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

    # A spend-up that reaches the write path with NO margin frame must REFUSE, never crash
    # (CR-04). apply.apply -> _evaluate_margin -> gate.evaluate(None, ...) would dereference a
    # None frame (AttributeError 'NoneType' has no attribute 'to_dicts'). The constitution
    # requires a missing money-gate input to surface a TYPED refusal, never an uncaught
    # traceback and never a silent proceed (hard rule 4). Refuse early with the gate's grammar.
    if action.is_spend_increasing and gate_frame is None:
        refusal = GateRefusal(
            "no margin — no premium export (--artifact) supplied for the spend-up margin gate",
            code="no_margin",
        )
        json.dump(dataclasses.asdict(refusal), sys.stdout)
        sys.stdout.write("\n")
        return 0

    # FULL GATE CHAIN ON THE WRITE PATH (CR-01): apply.apply runs ONLY the margin gate, the
    # denylist, and the magnitude cap — it never runs the cover/conversion, matured-window, or
    # internal-competition gates. So the chain that decides a spend-up is ACTIONABLE (render
    # mode) and the chain that EXECUTES it (here) were different chains, and the EXEC-05 cover
    # guardrail (stop GG-0DC1 at 1 FBA unit) never ran on the path that actually fires a write.
    # Run the SAME read-only chain render mode runs, refusing on the FIRST GateRefusal, BEFORE
    # apply.apply. write_path=True makes the cover gate refuse no_cover_data on a missing live
    # read rather than skip — a real write must clear the guardrail, never sail past it.
    if action.is_spend_increasing:
        cover_map = _load(args.cover) if args.cover else {}
        term_acos_map = _load(args.term_acos) if args.term_acos else {}
        refusal = _spend_up_refusal(
            _candidate_from_args(args),
            gate_frame=gate_frame,
            catalog_path=args.catalog,
            cover_map=cover_map,
            term_acos_map=term_acos_map,
            marketplace=args.marketplace,
            write_path=True,
        )
        if refusal is not None:
            json.dump(dataclasses.asdict(refusal), sys.stdout)
            sys.stdout.write("\n")
            return 0

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
