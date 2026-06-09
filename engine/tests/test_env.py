"""CONN-02 guard: the amazon.ca seller UUID lives in .env, never in source.

Asserts NOW (does not skip): the env var must be present, and the literal UUID
must not appear anywhere under tracked source directories. This enforces
CLAUDE.md hard rule 5 (secrets in .env only) and threat T-01-01 (information
disclosure of the seller identity).
"""

from __future__ import annotations

import os
from pathlib import Path

# The distinctive prefix of the amazon.ca seller UUID (CLAUDE.md / docs/04).
# It must NEVER appear inlined in tracked source — only in the gitignored .env
# (T-01-01). We assemble the prefix at runtime rather than writing the literal
# string here, so that `grep -rn '<uuid>' src/ db/ tests/` stays clean even in
# this guard file (Task 2 acceptance criterion).
SELLER_UUID_PREFIX = "5692" + "b95f"

REPO_ROOT = Path(__file__).resolve().parent.parent

# Directories that hold tracked source. The UUID must not appear in any of them.
TRACKED_SOURCE_DIRS = ("src", "db", "tests")

# File suffixes worth scanning (source + SQL + skill/markdown deliverables).
SCAN_SUFFIXES = {".py", ".sql", ".md", ".toml", ".yaml", ".yml", ".sh", ".txt"}


def test_seller_id_in_env_not_code() -> None:
    # 1) AMAZON_CA_SELLER_ID must be loaded into the environment (from .env via
    #    conftest's load_dotenv). If it is missing, the cache step (Task 2) has
    #    not been completed.
    seller_id = os.environ.get("AMAZON_CA_SELLER_ID")
    assert seller_id, (
        "AMAZON_CA_SELLER_ID is not set in the environment — it must be cached "
        "in the gitignored .env (plan 01-01 Task 2)."
    )
    assert seller_id.startswith(SELLER_UUID_PREFIX), (
        "AMAZON_CA_SELLER_ID does not match the expected amazon.ca seller UUID."
    )

    # 2) The literal UUID must NOT appear in any tracked source directory.
    offenders: list[str] = []
    for rel_dir in TRACKED_SOURCE_DIRS:
        base = REPO_ROOT / rel_dir
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
                continue
            # Don't flag this guard file's own constant.
            if path.resolve() == Path(__file__).resolve():
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
            except OSError:
                continue
            if SELLER_UUID_PREFIX in text:
                offenders.append(str(path.relative_to(REPO_ROOT)))

    assert not offenders, (
        "Seller UUID found inlined in tracked source (must live only in .env): "
        + ", ".join(offenders)
    )
