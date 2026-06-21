#!/usr/bin/env python3
"""Thin CLI: an agent-handed `actions_get` response -> the typed terminal/in-flight/error JSON.

This is the seam the Hermes write-path skill calls AFTER the agent makes an `actions_get` MCP
call and hands the response JSON to disk. It is THIN wiring — NO classification logic lives
here (all of it is in habibos.lifecycle, the hand-written core):

    argv -> load JSON -> lifecycle.classify_poll() (inside logging.logged_call) -> JSON on stdout

The CLI classifies ONE agent-handed response; it does NOT drive the in-flight->terminal poll
loop (that is Phase 8's apply spine). On a terminal-failure or unmodeled status the typed
result is a Refusal carrying reason + code so the agent surfaces it verbatim and NEVER reads a
failed action as "done". Never logs or prints the seller UUID.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from habibos import lifecycle
from habibos import logging as habibos_logging
from habibos.result import PollOutcome, Refusal

# Repo root is one level above scripts/ (mirrors answer_tacos.py repo-root-relative paths).
REPO_ROOT = Path(__file__).resolve().parent.parent


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Classify an agent-handed actions_get response into the typed terminal/in-flight/error JSON."
    )
    p.add_argument(
        "--artifact",
        required=True,
        help="Path to the agent-handed actions_get response JSON.",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    habibos_logging.configure()

    resp = json.loads(Path(args.artifact).read_text(encoding="utf-8"))

    with habibos_logging.logged_call("actions_get") as end_fields:
        result: PollOutcome | Refusal = lifecycle.classify_poll(resp)
        end_fields["status"] = "refused" if isinstance(result, Refusal) else result.state

    json.dump(dataclasses.asdict(result), sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
