#!/usr/bin/env python3
"""Thin CLI: an agent-handed `actions_start dryRun:true` response -> the typed PROCEED/STOP JSON.

This is the seam the Hermes write-path skill calls AFTER the agent makes the
`actions_start dryRun:true` MCP call and hands the response JSON to disk. It is THIN wiring —
NO classification logic lives here (all of it is in habibos.lifecycle, the hand-written core):

    argv -> load JSON -> lifecycle.classify_dryrun() (inside logging.logged_call) -> JSON on stdout

The CLI computes nothing and gates nothing on its own — it threads the agent-handed response
through the reviewed classifier and serializes the typed verdict. No `dryRun:false` ever fires
here: this is the gate BEFORE a real run. On a Refusal the JSON carries reason + code so the
agent surfaces it verbatim and NEVER substitutes a number. Never logs or prints the seller UUID.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from habibos import lifecycle
from habibos import logging as habibos_logging
from habibos.result import Proceed, Refusal

# Repo root is one level above scripts/ (mirrors answer_tacos.py repo-root-relative paths).
REPO_ROOT = Path(__file__).resolve().parent.parent


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Classify an agent-handed actions_start dryRun response into the typed PROCEED/STOP JSON."
    )
    p.add_argument(
        "--artifact",
        required=True,
        help="Path to the agent-handed actions_start dryRun:true response JSON.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    habibos_logging.configure()

    resp = json.loads(Path(args.artifact).read_text(encoding="utf-8"))

    with habibos_logging.logged_call("actions_start") as end_fields:
        result: Proceed | Refusal = lifecycle.classify_dryrun(resp)
        end_fields["status"] = "refused" if isinstance(result, Refusal) else "validated"

    json.dump(dataclasses.asdict(result), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
