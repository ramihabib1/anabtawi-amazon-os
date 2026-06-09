#!/usr/bin/env python3
"""Thin CLI: a downloaded premium-export artifact -> the typed TACOS-by-SKU JSON answer.

This is the seam the Hermes "tacos-by-sku" skill (Plan 02-03) calls AFTER the agent
downloads the export via the DataDoe MCP. It is a THIN wiring layer — NO business logic
lives here (all of it is in habibos.tacos, the hand-written money-logic core):

    argv -> parse() + classify() (inside logging.logged_call) -> JSON on stdout

Pass-through (D-01): the export is parsed in memory, NOT persisted or cached. Re-asking
re-pulls. The CLI computes NO dates and NO ratios; it threads --window-from/--window-to
to classify unmodified and lets the SOURCE own the ratios (D-03).

Catalog source — EXPLICIT, never a silent export-rows fallback (D-10 / T-02-16): the CLI
loads an explicit committed catalog file so a catalog SKU absent from the export surfaces
as "no data", and it STATES the coverage basis in the JSON (coverage_basis). An
export-derived catalog is a labelled last resort, never presented as if D-10 were satisfied.

Recommendation voice (SOUL.md): the CLI returns DATA only — it never claims an Amazon
action. On a Refusal the JSON carries reason + code + coverage_basis so the agent surfaces
it verbatim and NEVER substitutes a number. Never logs or prints the seller UUID.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from habibos import logging as habibos_logging
from habibos.result import Answer, Refusal
from habibos.tacos import PREMIUM_SOURCE_ID, classify, parse

# Repo root is one level above scripts/ (mirrors scripts/backup.sh repo-root-relative paths).
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG = REPO_ROOT / "tests" / "fixtures" / "ca_catalog_skus.txt"


def _load_catalog(path: Path) -> list[str]:
    """Read one seller_sku per line; ignore blanks and '#' comments. Order preserved."""
    skus: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        skus.append(stripped)
    return skus


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Turn a downloaded DataDoe premium Profit-by-SKU export into the typed TACOS-by-SKU JSON answer."
    )
    p.add_argument("--artifact", required=True, help="Path to the downloaded export artifact (CSV).")
    p.add_argument("--export-id", required=True, help="DataDoe export id (provenance, threaded to the answer).")
    p.add_argument("--marketplace", default="CA", help="Marketplace code (default CA — the only active marketplace).")
    p.add_argument("--status", default="COMPLETED", help="Export job status (COMPLETED|FAILED); FAILED -> Refusal.")
    p.add_argument("--window-from", default="", help="Window start (the agent passes the resolved trailing-30d window).")
    p.add_argument("--window-to", default="", help="Window end. The CLI passes both through unmodified — it computes no dates.")
    p.add_argument(
        "--catalog",
        default=str(DEFAULT_CATALOG),
        help="Path to a committed catalog SKU list (default tests/fixtures/ca_catalog_skus.txt).",
    )
    return p


def _serialize(result: Answer | Refusal, coverage_basis: str) -> dict:
    """dataclasses.asdict the typed result and attach the explicit coverage basis."""
    payload = dataclasses.asdict(result)
    payload["coverage_basis"] = coverage_basis  # D-10: always state the catalog source
    return payload


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    habibos_logging.configure()

    catalog_path = Path(args.catalog)
    artifact_path = Path(args.artifact)

    # Catalog source — EXPLICIT, never a silent export-rows fallback (D-10 / T-02-16).
    if catalog_path.exists():
        catalog_skus = _load_catalog(catalog_path)
        coverage_basis = f"committed catalog ({catalog_path.name}, {len(catalog_skus)} SKUs)"
    else:
        # Last resort ONLY: derive the present set from the export's own rows, and label it
        # honestly so the operator is never misled into thinking a SKU is absent.
        catalog_skus = []
        coverage_basis = (
            "catalog source = export rows; not-in-export detection for catalog SKUs "
            "lands with sku_master in Phase 3.5"
        )

    with habibos_logging.logged_call(
        "tacos_export",
        source_id=PREMIUM_SOURCE_ID,
        marketplace=args.marketplace,
        window_from=args.window_from,
        window_to=args.window_to,
    ) as end_fields:
        parsed = parse(artifact_path, args.status)
        if isinstance(parsed, Refusal):
            result: Answer | Refusal = parsed
            end_fields["row_count"] = 0
            end_fields["byte_size"] = artifact_path.stat().st_size if artifact_path.exists() else 0
            end_fields["status"] = "refused"
        else:
            frame = parsed
            # If no committed catalog was available, the present set IS the export's SKUs.
            skus = catalog_skus or frame.get_column("sku").to_list()
            result = classify(
                frame,
                args.export_id,
                args.window_from,
                args.window_to,
                skus,
                marketplace=args.marketplace,
            )
            end_fields["row_count"] = frame.height
            end_fields["byte_size"] = artifact_path.stat().st_size if artifact_path.exists() else 0
            end_fields["status"] = "refused" if isinstance(result, Refusal) else "ok"

    json.dump(_serialize(result, coverage_basis), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
