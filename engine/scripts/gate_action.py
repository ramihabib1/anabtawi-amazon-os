#!/usr/bin/env python3
"""Thin CLI: a proposed PPC write + a downloaded premium-export artifact -> the typed
margin-gate verdict as JSON on stdout.

This is the callable gate seam the Phase 8 BUILD->DRYRUN apply spine invokes after the
agent downloads the premium Profit-by-SKU export via the DataDoe MCP. It is the structural
twin of `answer_tacos.py` — a THIN wiring layer with NO business logic (all money math is in
`habibos.gate`, the hand-written, pytest-covered core — CLAUDE.md hard rule 3):

    argv -> gate.parse() + gate.evaluate() (inside logging.logged_call) -> JSON on stdout

The CLI computes NO ratios, NO ceilings, NO projections and makes NO clamp/pass decisions —
it threads the proposed action + window-sum frame to `gate.evaluate` unmodified and
`dataclasses.asdict`s whatever typed result comes back (GateVerdict or GateRefusal). A
refusal serializes verbatim as a refusal — it can NEVER be rewritten as a pass (the
`end_fields["status"]` is set from `isinstance(result, GateRefusal)`, T-07-11).

Catalog source — EXPLICIT, never a silent fallback (D-05 / GATE-05): the CLI points the
gate at a committed machine-readable catalog file. A SKU absent there surfaces as a
`sku_not_in_catalog` refusal in the JSON; a missing catalog FILE is surfaced cleanly, never
a silent default.

Security (V7/V8 / T-07-12): the structured log carries only the op name + source_id +
marketplace. The seller UUID is NEVER passed into `logged_call` fields (the gate reads no
secret); nothing here ever logs or prints a secret.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from habibos import gate
from habibos import logging as habibos_logging
from habibos.result import GateRefusal, GateVerdict, ProposedAction, Refusal

# Repo root is one level above scripts/ (mirrors answer_tacos.py's repo-root-relative paths).
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = REPO_ROOT / "config" / "sku_catalog.toml"


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Evaluate a proposed PPC write against its SKU's margin-derived TACOS "
        "ceiling and emit the typed gate verdict as JSON.",
    )
    # Export provenance (mirrors answer_tacos.py).
    p.add_argument("--artifact", required=True, help="Path to the downloaded export artifact (CSV).")
    p.add_argument("--export-id", required=True, help="DataDoe export id (provenance).")
    p.add_argument("--marketplace", default="CA", help="Marketplace code (default CA — the only active marketplace).")
    p.add_argument("--status", default="COMPLETED", help="Export job status (COMPLETED|FAILED); FAILED -> Refusal.")
    p.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG),
        help="Path to the committed machine-readable catalog (default config/sku_catalog.toml).",
    )
    # The ProposedAction fields — the untrusted write proposal crossing into the gate.
    p.add_argument("--sku", required=True, help="The SKU the proposed PPC action targets.")
    p.add_argument("--action-type", required=True, help="e.g. bid_up | budget_up | pause | negative.")
    p.add_argument(
        "--delta-spend",
        required=True,
        type=float,
        help="Caller-computed CAD spend delta; >0 spend-increasing (gated), <=0 spend-decreasing (auto-pass).",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    habibos_logging.configure()

    catalog_path = Path(args.catalog)
    artifact_path = Path(args.artifact)
    action = ProposedAction(
        sku=args.sku,
        action_type=args.action_type,
        delta_spend=args.delta_spend,
        marketplace=args.marketplace,
    )

    with habibos_logging.logged_call(
        "gate_action",
        source_id=gate.PREMIUM_SOURCE_ID,
        marketplace=args.marketplace,
    ) as end_fields:
        # Parse the export to the validated window-sum frame; a FAILED/empty export is a
        # typed Refusal surfaced as JSON (the gate owns the read; the CLI computes nothing).
        parsed = gate.parse(artifact_path, args.status)
        if isinstance(parsed, Refusal):
            result: GateVerdict | GateRefusal | Refusal = parsed
            end_fields["status"] = "refused"
        else:
            result = gate.evaluate(parsed, action, catalog_path, args.marketplace)
            end_fields["status"] = "refused" if isinstance(result, GateRefusal) else "pass"

    json.dump(dataclasses.asdict(result), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
