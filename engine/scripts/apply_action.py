#!/usr/bin/env python3
"""Thin CLI: a proposed reversible PPC write + the agent-handed MCP fixtures -> the typed
apply-spine result as JSON on stdout, with the one-time canary confirm (WRITE-03/06/07).

This is the callable apply seam the Phase 8 orchestrator invokes after the agent has made the
four MCP calls (actions_start dryRun:true, actions_start dryRun:false, actions_get poll,
*_FIND echo) and handed their JSON responses off as LOCAL files. It is the structural twin of
`gate_action.py` — a THIN wiring layer with NO business logic (the whole spine lives in
`habibos.apply`, the hand-written, pytest-covered core — CLAUDE.md hard rule 3):

    argv + fixture files -> apply.apply() (inside logging.logged_call) -> JSON on stdout

THE SEAM (CLAUDE.md hard rule 1): Python opens NO socket. The DataDoe `actions_start` /
`actions_get` / `*_FIND` calls are MCP tool calls the AGENT makes; this CLI only reads the
JSON the agent already downloaded to local files and threads them to the spine as zero-arg
callables. A parallel Python HTTP client is FORBIDDEN.

CANARY one-time confirm (D-08/D-09, RESEARCH Pattern 5): the phase's FIRST apply requires the
explicit `--confirm-canary`; the marker absent + the flag NOT passed -> a `canary_unconfirmed`
refusal in the JSON. The marker (`data/phase8_canary_confirmed`) is written only AFTER a
success; once present, subsequent reversible moves auto-apply WITHOUT the flag.

Security (V7/V8 / T-08-15): the structured log carries only the op name + marketplace. The
seller UUID is NEVER passed into `logged_call` fields, the decisions.md line, or the brain
note (the spine reads no secret); nothing here ever logs or prints a secret. A refusal
serializes verbatim as a refusal — it can NEVER be rewritten as a pass (`end_fields["status"]`
is set from `isinstance(result, (Refusal, GateRefusal))`, mirroring gate_action.py / T-07-11).
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from habibos import apply
from habibos import logging as habibos_logging
from habibos.result import AppliedResult, GateRefusal, ProposedAction, Refusal

# Repo root is one level above scripts/ (mirrors gate_action.py's repo-root-relative paths).
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OWNED = REPO_ROOT / "config" / "owned_asins.toml"
DEFAULT_CATALOG = REPO_ROOT / "config" / "sku_catalog.toml"


def _load(path: str) -> dict:
    """Read a local JSON fixture the agent already downloaded (no fetch — the seam)."""
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Apply a proposed reversible PPC write through the gated apply spine and "
        "emit the typed result (AppliedResult | Refusal | GateRefusal) as JSON.",
    )
    # The ProposedAction fields — the untrusted write proposal crossing into the spine.
    p.add_argument("--sku", required=True, help="The SKU the proposed PPC action targets.")
    p.add_argument(
        "--action-type",
        required=True,
        help="The reversible action type: pause | negative | bid_down.",
    )
    p.add_argument(
        "--delta-spend",
        type=float,
        default=0.0,
        help="CAD spend delta; the spine sets <=0 for reversible (spend-down -> gate auto-pass).",
    )
    p.add_argument("--marketplace", default="CA", help="Marketplace code (default CA).")
    p.add_argument(
        "--entity-type",
        required=True,
        help="The FIND entity class: campaigns | targets | adGroups | ads.",
    )
    p.add_argument(
        "--entity-id",
        required=True,
        help="The FIND-verified live entity id (campaignId/targetId/...) the write targets.",
    )
    p.add_argument(
        "--params",
        default="{}",
        help="JSON object of build/identity params (state / keyword+matchType / bid).",
    )
    # The agent-handed MCP fixture files (NO socket — the agent downloaded these).
    p.add_argument(
        "--dryrun-resp",
        required=True,
        help="Path to the actions_start(dryRun:true) response JSON the agent downloaded.",
    )
    p.add_argument(
        "--apply-resp",
        required=True,
        help="Path to the actions_start(dryRun:false) response JSON (the real write).",
    )
    p.add_argument(
        "--status-resp",
        required=True,
        help="Path to the latest actions_get response JSON (the poll loop reads this).",
    )
    p.add_argument(
        "--find-echo",
        required=True,
        help="Path to the *_FIND response JSON for the FIND-before-write + post-write echo.",
    )
    p.add_argument(
        "--owned",
        default=str(DEFAULT_OWNED),
        help="Path to the dedicated owned-ASIN denylist (default config/owned_asins.toml).",
    )
    p.add_argument(
        "--ad-product",
        default="SPONSORED_PRODUCTS",
        help="Ad product scoping the FIND cache (default SPONSORED_PRODUCTS).",
    )
    # The one-time canary confirm (D-08/D-09, RESEARCH Pattern 5).
    p.add_argument(
        "--confirm-canary",
        action="store_true",
        help="One-time confirm for the phase's FIRST apply; once the marker is written, "
        "subsequent reversible moves auto-apply without it (D-08/D-09).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    habibos_logging.configure()

    action = ProposedAction(
        sku=args.sku,
        action_type=args.action_type,
        delta_spend=args.delta_spend,
        marketplace=args.marketplace,
        entity_type=args.entity_type,
        entity_id=args.entity_id,
        params=json.loads(args.params),
    )

    with habibos_logging.logged_call(
        "apply_action", marketplace=args.marketplace
    ) as end_fields:
        result: AppliedResult | Refusal | GateRefusal = apply.apply(
            action,
            owned_source=args.owned,
            start_dryrun=lambda: _load(args.dryrun_resp),
            start_apply=lambda: _load(args.apply_resp),
            get_status=lambda: _load(args.status_resp),
            find_echo=lambda: _load(args.find_echo),
            confirm_canary=args.confirm_canary,
            ad_product=args.ad_product,
        )
        # A refusal can NEVER serialize as "applied" — derive the status from the result TYPE
        # (mirrors gate_action.py / T-07-11). NEVER pass the seller UUID into the log fields.
        end_fields["status"] = (
            "refused" if isinstance(result, (Refusal, GateRefusal)) else "applied"
        )

    json.dump(dataclasses.asdict(result), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
