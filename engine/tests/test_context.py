"""CTX-01/02 persona + business-context test (consumed by plan 01-03).

Asserts the version-controlled source of truth (.hermes-context/SOUL.md and
business-context.md) exists, is non-stub, and has been deployed to the live
~/.hermes runtime. Plan 01-03 authors these and deploys them; until then this
SKIPS cleanly (files absent).

"Non-stub" = the deployed SOUL.md is not the Hermes template placeholder and
carries real operator/business content of meaningful length.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))

# Markers that indicate an un-personalized template stub (RESEARCH §Standard
# Stack — live SOUL.md is currently a template stub).
STUB_MARKERS = (
    "template",
    "placeholder",
    "TODO",
    "<your",
    "fill in",
)

# A real persona/context file should be more than a trivial stub.
MIN_NON_STUB_CHARS = 200


def _is_non_stub(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    if len(text.strip()) < MIN_NON_STUB_CHARS:
        return False
    lowered = text.lower()
    return not any(marker.lower() in lowered for marker in STUB_MARKERS)


def test_soul_and_context_deployed() -> None:
    # 1) Source of truth in git.
    src_soul = REPO_ROOT / ".hermes-context" / "SOUL.md"
    src_ctx = REPO_ROOT / ".hermes-context" / "business-context.md"
    if not src_soul.exists() or not src_ctx.exists():
        pytest.skip(
            ".hermes-context/{SOUL.md,business-context.md} not yet authored — plan 01-03"
        )

    assert _is_non_stub(src_soul), "SOUL.md is still a stub/placeholder (CTX-01)"
    assert _is_non_stub(src_ctx), "business-context.md is still a stub/placeholder (CTX-02)"

    # 2) Deployed into the live ~/.hermes runtime.
    deployed_soul = HERMES_HOME / "SOUL.md"
    if not deployed_soul.exists():
        pytest.skip(f"SOUL.md not yet deployed to {HERMES_HOME} — plan 01-03")

    assert _is_non_stub(deployed_soul), (
        f"Deployed {deployed_soul} is still the template stub (CTX-01)"
    )
