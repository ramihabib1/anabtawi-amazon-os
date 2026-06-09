"""DataDoe seam: a reusable tenacity poll primitive + a LOCAL artifact loader (D-02).

THE SEAM (CLAUDE.md "What NOT to Use", RESEARCH §Pattern 1): the DataDoe network calls
(exports_create / exports_get / exports_raw_download) are MCP tool calls made by the Hermes
*agent*, NOT by Python. A parallel Python HTTP client is FORBIDDEN. So this module imports
no HTTP library and never opens a network connection — it only:

  - poll_status: a reusable tenacity poll primitive (backoff + jitter, terminal on BOTH
    COMPLETED and FAILED so a FAILED export is never retried forever — RESEARCH Pitfall 4 /
    T-02-04). It is the substrate for a future Python-side poll (e.g. a Phase 3.5 custom
    MCP); it is NOT on this phase's critical path, because the agent polls via the MCP.
  - load_artifact: reads the already-downloaded LOCAL artifact (a path or bytes) the agent
    handed off — no fetch.
"""

from __future__ import annotations

from pathlib import Path

from tenacity import retry, retry_if_result, stop_after_attempt, wait_exponential_jitter

# A poll terminates on either terminal status — never spin forever on a FAILED export.
TERMINAL = {"COMPLETED", "FAILED"}


def _not_terminal(status: str) -> bool:
    return status not in TERMINAL


@retry(
    stop=stop_after_attempt(20),
    wait=wait_exponential_jitter(initial=1, max=15),
    retry=retry_if_result(_not_terminal),
)
def poll_status(get_status) -> str:
    """Call get_status() repeatedly until it returns COMPLETED or FAILED.

    Reusable poll primitive (RESEARCH tenacity sketch). get_status is a zero-arg callable
    returning the current export status string. Retries with exponential backoff + jitter,
    capped at 20 attempts, stopping on BOTH terminal statuses (T-02-04 / Pitfall 4). Not on
    this phase's critical path — the agent polls via the MCP today.
    """
    return get_status()


def load_artifact(path_or_bytes: str | Path | bytes) -> bytes:
    """Return the raw bytes of a LOCAL downloaded artifact — no HTTP fetch (the seam).

    Accepts raw bytes (returned as-is) or a local file path (read from disk). The agent
    downloads via the DataDoe MCP; Python only handles the artifact it was handed.
    """
    if isinstance(path_or_bytes, bytes):
        return path_or_bytes
    return Path(path_or_bytes).read_bytes()
