"""Actions-lifecycle classifiers: dryRun PROCEED gate + actions_get poll verdict (WRITE-01/05).

This is the hand-written, pytest-covered money-adjacent core for the gated Amazon write
path. It NEVER opens a socket: the DataDoe `actions_start` / `actions_get` calls are MCP tool
calls made by the agent (the seam — see datadoe.py docstring). Python only classifies the
agent-handed JSON response into a typed verdict, mirroring tacos.py's anti-fabrication grammar:

  - classify_dryrun(resp) -> Proceed | Refusal — WRITE-01. PROCEED iff the dryRun is clean
    (status=="VALIDATED" && validation.valid is True && validation.issues==[]). Any other
    state STOPS with a Refusal(code="dryrun_invalid") carrying the issue message VERBATIM
    (never a substituted "ok"). No `dryRun:false` ever fires here — this is the gate BEFORE
    a real run.
  - classify_poll(resp) -> PollOutcome | Refusal — WRITE-05. Buckets the verbatim wire
    `status` against the PINNED datadoe.ACTION_* sets:
      COMPLETED                                   -> PollOutcome(state="done")
      PARTIALLY_COMPLETED / COMPLETED_WITH_ISSUES -> PollOutcome(state="done_with_issues", issues)
      PENDING / IN_PROGRESS / WAITING_…           -> PollOutcome(state="in_flight")
      ERROR / CANCELED / BLOCKED_*                -> Refusal(code="action_error", error.message verbatim)
      anything NOT in a modeled set              -> Refusal(code="unknown_status")
    An unmodeled status is NEVER assumed terminal and NEVER infinite-polled — it refuses.
    classify_poll classifies ONE agent-handed response; it does NOT drive the
    datadoe.poll_action_status loop (that in-flight→terminal LOOP is Phase 8's apply spine).
  - classify_poll_logged(resp) -> the same, wrapped in logging.logged_call so the op emits
    one .start + one .end and leaks no seller UUID (TRUST-03 / hard rule 5).

Schema drift (RESEARCH Pitfall 1): both classifiers pydantic-validate the response shape and
raise a ValueError on drift — a changed/untrusted response shape can never be silently misread
as PROCEED. Reconcile guard (RESEARCH lines 207-208): a DataDoe EXPORT status ("FAILED", which
is NOT in the action enum) is never a confirmation — it falls through to unknown_status; the
reconcile path is actions_get→terminal + FIND echo ONLY, never a DataDoe export status.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, ValidationError

from . import datadoe
from . import logging as habibos_logging
from .result import PollOutcome, Proceed, Refusal


# --- dryRun (actions_start dryRun:true) response shape — RESEARCH lines 308-326 -------
# RESEARCH Pitfall 2: `validation` is NESTED (validation.valid / validation.issues), NOT
# flat on the response. A flat read would mis-gate PROCEED.
class _ActionValidationIssue(BaseModel):
    model_config = ConfigDict(extra="ignore")

    path: list = []
    code: str = ""
    message: str = ""


class _ActionValidationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    valid: bool
    issues: list[_ActionValidationIssue] = []


class _ActionStartResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    type: str
    status: str
    validation: _ActionValidationResult


# --- actions_get (ActionStatusResponse) response shape — RESEARCH lines 329-355 -------
class _ActionExecutionError(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str = ""
    code: str = ""
    message: str = ""


class _ActionStatusResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    status: str
    error: Optional[_ActionExecutionError] = None


def classify_dryrun(resp: dict) -> Proceed | Refusal:
    """Classify an `actions_start dryRun:true` response into PROCEED or STOP (WRITE-01).

    PROCEED (a typed Proceed, never a bare True) iff status=="VALIDATED" AND
    validation.valid is True AND validation.issues==[]. Any other state -> a typed
    Refusal(code="dryrun_invalid") carrying the issue message(s) VERBATIM (never a
    substituted "ok"). Validates the (nested) shape and raises on drift — an untrusted
    response can never be silently mis-read as PROCEED.
    """
    try:
        parsed = _ActionStartResponse.model_validate(resp)
    except ValidationError as exc:  # noqa: BLE001 - surface drift, never coerce (Pitfall 1)
        raise ValueError(f"actions_start dryRun response schema mismatch (drift?): {exc}") from exc

    if parsed.status == "VALIDATED" and parsed.validation.valid and not parsed.validation.issues:
        return Proceed(action_type=parsed.type)

    # STOP — surface the issue messages verbatim (no substitution). If there are no issue
    # messages (e.g. status != VALIDATED with valid:true), state that plainly.
    messages = [i.message for i in parsed.validation.issues if i.message]
    reason = "; ".join(messages) if messages else (
        f"dryRun did not validate (status={parsed.status}, valid={parsed.validation.valid})."
    )
    return Refusal(reason, "dryrun_invalid")


def classify_poll(resp: dict) -> PollOutcome | Refusal:
    """Classify ONE `actions_get` response against the pinned ACTION_* sets (WRITE-05).

    Buckets the verbatim wire status: COMPLETED -> done; PARTIALLY_COMPLETED /
    COMPLETED_WITH_ISSUES -> done_with_issues (surfacing any error message verbatim);
    PENDING / IN_PROGRESS / WAITING_EXTERNAL_PROCESSING -> in_flight; ERROR / CANCELED /
    BLOCKED_* -> Refusal(code="action_error", error.message verbatim); a status in NONE of
    the modeled sets -> Refusal(code="unknown_status") — NEVER assumed terminal, NEVER
    infinite-polled. This classifies a SINGLE response; it does NOT drive the
    datadoe.poll_action_status loop (Phase 8's apply spine). Validates shape, raises on drift.
    """
    try:
        parsed = _ActionStatusResponse.model_validate(resp)
    except ValidationError as exc:  # noqa: BLE001 - surface drift, never coerce (Pitfall 1)
        raise ValueError(f"actions_get response schema mismatch (drift?): {exc}") from exc

    status = parsed.status
    error_message = parsed.error.message if parsed.error else ""

    if status in datadoe.ACTION_TERMINAL_SUCCESS:
        return PollOutcome(status=status, state="done", issues=[])
    if status in datadoe.ACTION_TERMINAL_PARTIAL:
        issues = [error_message] if error_message else []
        return PollOutcome(status=status, state="done_with_issues", issues=issues)
    if status in datadoe.ACTION_IN_FLIGHT:
        return PollOutcome(status=status, state="in_flight", issues=[])
    if status in datadoe.ACTION_TERMINAL_FAIL:
        reason = error_message or f"action failed with status {status} (no error message)."
        return Refusal(reason, "action_error")

    # Not in ANY modeled set — including a DataDoe EXPORT terminal ("FAILED") which is NOT an
    # action terminal. Refuse rather than assume terminal or poll forever (the reconcile guard:
    # an export status is never an action confirmation — RESEARCH lines 207-208).
    return Refusal(f"unknown action status: {status}", "unknown_status")


def classify_poll_logged(resp: dict) -> PollOutcome | Refusal:
    """classify_poll wrapped in logged_call — one .start + one .end, no seller UUID (TRUST-03).

    The single logged seam for an `actions_get` classify op. NEVER passes the seller UUID
    (or any secret) into the log fields. end_fields["status"] records the classified state
    ("done" / "done_with_issues" / "in_flight") or "refused".
    """
    habibos_logging.configure()
    with habibos_logging.logged_call("actions_get") as end_fields:
        result = classify_poll(resp)
        end_fields["status"] = "refused" if isinstance(result, Refusal) else result.state
    return result
