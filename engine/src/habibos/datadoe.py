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


# --- actions_* lifecycle status enum (Phase 6, WRITE-05) -----------------------------
# The DataDoe `actions_get` (ActionStatusResponse) status enum, PINNED VERBATIM from the
# live spec. This is the one genuinely-new fact in Phase 6 and is load-bearing: a wrong
# enum causes an infinite poll (an in-flight status never reaches a terminal set) or a
# silently-assumed terminal (RESEARCH Pitfall 1 / T-06-02). There is NO `FAILED` (it is
# `ERROR`) and `CANCELED` is spelled with ONE L — never the roadmap's COMPLETED/FAILED/
# CANCELLED. Kept SEPARATE from the export `TERMINAL` above (different lifecycle).
# verified against api.datadoe.com/api/v1/docs/json 2026-06-20
ACTION_IN_FLIGHT = {"PENDING", "IN_PROGRESS", "WAITING_EXTERNAL_PROCESSING"}
ACTION_TERMINAL_SUCCESS = {"COMPLETED"}
ACTION_TERMINAL_PARTIAL = {"PARTIALLY_COMPLETED", "COMPLETED_WITH_ISSUES"}
ACTION_TERMINAL_FAIL = {"ERROR", "CANCELED", "BLOCKED_NO_TOKENS", "BLOCKED_INVALID_INPUT"}
ACTION_TERMINAL = ACTION_TERMINAL_SUCCESS | ACTION_TERMINAL_PARTIAL | ACTION_TERMINAL_FAIL


def _action_not_terminal(status: str) -> bool:
    return status not in ACTION_TERMINAL


@retry(
    stop=stop_after_attempt(20),
    wait=wait_exponential_jitter(initial=1, max=15),
    retry=retry_if_result(_action_not_terminal),
)
def poll_action_status(get_status) -> str:
    """Poll an action's status until it reaches an ACTION_TERMINAL state.

    The in-flight→terminal poll PRIMITIVE for the actions lifecycle (mirror of poll_status,
    same tenacity config — capped 20 attempts, exponential backoff + jitter, terminal on the
    pinned ACTION_TERMINAL set so an in-flight status is never spun on forever). get_status is
    a zero-arg callable returning the current action status string.

    Phase 6 only proves single-response classification (lifecycle.classify_poll, Plan 02);
    the full in-flight→terminal poll LOOP is driven end-to-end by Phase 8's apply spine.
    Building the primitive here is intentional substrate, not dead wiring.
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
