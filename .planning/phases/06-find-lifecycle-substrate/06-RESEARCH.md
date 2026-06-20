# Phase 6: FIND + Lifecycle Substrate - Research

**Researched:** 2026-06-20
**Domain:** Async DataDoe Ads write loop substrate (dryRun harness, `*_FIND` ID caching, `actions_get` poll-to-terminal, reconcile-not-via-export) — zero account risk
**Confidence:** HIGH (live DataDoe OpenAPI spec pinned + existing engine source read + milestone research cited)

## Summary

Phase 6 builds the async-write *substrate* on operations that cannot change the account: a hand-written `lifecycle.py` that classifies `actions_start dryRun:true` and `actions_get` responses into proceed-vs-stop typed results; a FIND-before-write cache (`data/ads_*_find_*.json`) that refuses any write whose entity IDs aren't cached; a poll-to-terminal reconciliation that reuses `datadoe.poll_status`'s terminal-set discipline; and `logged_call` wrapping for the two new MCP ops. No `actions_start dryRun:false` ever fires in this phase. It mirrors M1's proven seam exactly: **the agent does MCP I/O; hand-written, pytest-covered Python owns the truth.**

The single highest-value research finding is that **the real `actions_get` status enum is larger and differently-named than the roadmap assumed.** The roadmap's Success Criterion 3 says terminal = `COMPLETED / FAILED / CANCELLED`. The live DataDoe OpenAPI spec (`https://api.datadoe.com/api/v1/docs/json`, pulled 2026-06-20) shows the real enum is `PENDING, IN_PROGRESS, WAITING_EXTERNAL_PROCESSING, COMPLETED, PARTIALLY_COMPLETED, COMPLETED_WITH_ISSUES, ERROR, BLOCKED_NO_TOKENS, BLOCKED_INVALID_INPUT, CANCELED` — there is **no `FAILED`** (it's `ERROR`), `CANCELED` is **one L**, and there are three additional terminal/blocked states the engine must classify (`PARTIALLY_COMPLETED`, `COMPLETED_WITH_ISSUES`, `BLOCKED_*`). Pinning this verbatim is Success Criterion 4 and prevents an infinite poll on a state the engine doesn't recognize.

**Primary recommendation:** Build `lifecycle.py` (typed dryRun + poll classifier mirroring `tacos.py`), `find_cache.py` (FIND write/read + build-time refusal mirroring `thresholds.py`'s missing→refuse pattern), pin the **verified** status enum into `datadoe.TERMINAL`, and wrap both new MCP ops in `logged_call`. Reuse `result.py`, `logging.py`, `datadoe.poll_status` unchanged. Add zero new PyPI dependencies. The dryRun *value* discipline (the brain note's "VALIDATED / valid / issues") maps to the spec's `ActionStartResponse.status == "VALIDATED"` + `validation.valid` + `validation.issues[]`.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| WRITE-01 | Validate any PPC write as a `dryRun` (returns VALIDATED + issues) before any real write | `lifecycle.classify_dryrun()` reads `ActionStartResponse.status=="VALIDATED"` + `validation.{valid,issues[]}` (pinned from live spec §Standard Stack). Unit-testable against a captured dryRun fixture — no live call needed to prove the classifier. |
| WRITE-02 | Pull live campaign/ad-group/target/ad IDs via `*_FIND` before any UPDATE/REMOVE (FIND-before-write) | `find_cache.py` writes `data/ads_*_find_*.json` from the `Action*FindResult` shape (verified: `{campaigns/targets/adGroups/ads:[...], nextToken}`), one ad-product per request (`adProductFilter.include` is `maxItems:1`, verified). Build-time refusal mirrors `thresholds.read()→None→refuse`. |
| WRITE-05 | Reconcile every applied write via `actions_get` (COMPLETED) + a `*_FIND` echo — never next-day DataDoe exports; failed/blocked refuses cleanly with returned error | `lifecycle.classify_poll()` + extended `datadoe.TERMINAL` (verified enum). Reconciliation = poll-to-terminal + FIND echo; engine has NO DataDoe-export read path in the reconcile loop by construction (the seam already forbids Python network I/O). `ERROR`/`BLOCKED_*` surface `ActionStartResponse.error` / `ActionExecutionErrorResult.message` verbatim. |

> WRITE-03/04/06/07 (real applies, logging, idempotency) are Phases 8–9 — out of scope here. This phase proves the loop with **no `dryRun:false`**.
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| `actions_start dryRun:true` MCP call | Agent (Hermes) / MCP transport | — | The seam: Python never opens a socket (`datadoe.py` docstring, CLAUDE.md hard rule 1). |
| `actions_get(actionId)` MCP call | Agent (Hermes) / MCP transport | — | Same seam. The agent polls; engine classifies the returned status. |
| `*_FIND` MCP call | Agent (Hermes) / MCP transport | — | Read-only, ungated; agent fires it, hands the JSON to Python to cache. |
| dryRun response classification (VALIDATED/valid/issues→proceed/stop) | Python engine (`lifecycle.py`) | — | Money/lifecycle truth is hand-written + tested (hard rule 3). |
| Poll status classification (terminal/in-flight/error) | Python engine (`lifecycle.py`) | `datadoe.poll_status` | Terminal-set discipline reused; engine decides retry-vs-terminal. |
| FIND-before-write enforcement (cache read + refuse) | Python engine (`find_cache.py`) | — | A write with uncached IDs is refused at BUILD, in code, not assumed. |
| FIND cache persistence (`data/ads_*_find_*.json`) | Python engine (write) | Filesystem (`data/`) | Mirrors the existing `data/*.csv` / `ads_sp_campaigns_live_*.json` cache pattern. |
| Call logging (`*.start`/`*.end` → `external-calls.jsonl`) | Python engine (`logging.logged_call`) | — | Reused unchanged; never logs the seller UUID. |
| Skill write-action reference (the 4 `actions_*` tools, FIND-before-write, dryRun) | Skill doc (`datadoe-query/SKILL.md`) | — | Operator/agent-facing playbook; renders + interprets, does not compute. |

## Project Constraints (from CLAUDE.md)

These are binding and have the same authority as locked decisions. Research recommends nothing that contradicts them.

1. **Data layer is READ-ONLY for analysis; the only write surface is the gated `actions_start` path.** Python never opens a socket — the agent does all MCP I/O (`datadoe.py` "the seam"; STACK.md forbids `httpx`/`requests`/SDK/`boto3`).
2. **No autonomous writes to Amazon.** This phase fires **zero** `dryRun:false`. Even dryRun real-payload validation against a disabled-or-enabled action type is the agent's job at execution, not research.
3. **Money/lifecycle logic is hand-written, reviewed, and pytest-covered.** `lifecycle.py` + `find_cache.py` are hand-written; `cd engine && uv run pytest` must stay green (currently 16 passed / 5 skipped, verified 2026-06-20).
4. **Never invent a number or a threshold.** A FIND cache miss → typed refusal ("stale/missing entity ID"), never a fabricated ID. A poll status the engine doesn't recognize → surface it, never assume terminal.
5. **Secrets live in `.env`** — `$AMAZON_CA_SELLER_ID` (the seller UUID, prefix `5692b95f`) is never inlined in code, skills, committed files, or logs. `logged_call` start/end fields must never carry it (verified by `test_logging.py::test_no_secret_in_log`).
6. **Every external call is logged.** Each `actions_start`/`actions_get` is wrapped by `logged_call` → `external-calls.jsonl` with `<op>.start`/`<op>.end` (Success Criterion 5).

## Standard Stack

**No new PyPI dependency is required** (confirmed against `engine/pyproject.toml` + `engine/uv.lock`, 2026-06-20). The work is code-shaped: new engine modules reusing already-pinned libraries.

### Core (all already pinned — verified in `engine/uv.lock`)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `pydantic` | 2.13.4 [VERIFIED: engine/pyproject.toml] | Validate the dryRun/poll/FIND response shapes; typed lifecycle models | Same `BaseModel`+frozen-dataclass pattern as `result.py`/`tacos.py`. Validate-or-raise on schema drift (mirrors `tacos._PremiumRow`). |
| `tenacity` | 9.1.4 [VERIFIED: engine/pyproject.toml] | Poll `actions_get` to a terminal status (backoff+jitter, capped) | `datadoe.poll_status` already implements terminal-on-set with `wait_exponential_jitter`; extend `TERMINAL`. |
| `structlog` | 26.1.0 [VERIFIED: engine/pyproject.toml] | One-event-in/one-out logging of each MCP op | `logging.logged_call` already gives the `*.start`/`*.end` JSON-line contract. |
| stdlib `json` / `tomllib` / `argparse` / `pathlib` | 3.12 | FIND-cache read/write, CLI wiring, file naming | Mirror `answer_tacos.py` exactly. No library. |
| `pytest` (dev) | ≥9.0.3 [VERIFIED: engine/pyproject.toml] | The lifecycle + find-cache contract tests | Money/lifecycle-logic contract stays green (hard rule 3). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing `datadoe.poll_status` | A new poll loop in `lifecycle.py` | Rejected — duplicates the terminal-on-set + capped-retry logic already tested. Extend `TERMINAL`, reuse the primitive. |
| `pydantic` validation of FIND/dryRun JSON | Hand-rolled `dict.get` parsing | `pydantic` (already used in `tacos.py`) fails loud on drift; hand-rolling silently tolerates missing fields → fabrication risk. Use `pydantic`. |
| Any HTTP client / Amazon Ads SDK | — | **Forbidden** (CLAUDE.md hard rule 1, STACK.md anti-scope). The MCP is the transport. |

**Installation:** None. `cd engine && uv sync` already provides everything. Verified: `uv run pytest` green 2026-06-20.

## Package Legitimacy Audit

> This phase installs **no external packages.** All four runtime libraries are already pinned in `engine/uv.lock` and were vetted in Milestone 1.

| Package | Registry | Status | slopcheck | Disposition |
|---------|----------|--------|-----------|-------------|
| pydantic | PyPI | pinned 2.13.4, M1-vetted | n/a (no install) | Already present |
| tenacity | PyPI | pinned 9.1.4, M1-vetted | n/a (no install) | Already present |
| structlog | PyPI | pinned 26.1.0, M1-vetted | n/a (no install) | Already present |
| polars | PyPI | pinned 1.41.2, M1-vetted | n/a (no install) | Already present (not needed by P6 directly) |

**Packages removed due to slopcheck [SLOP] verdict:** none.
**Packages flagged as suspicious [SUS]:** none.
*No install step exists in this phase, so the legitimacy gate is a no-op. If a planner adds a dependency, it must be re-audited.*

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────── PHASE 6 SCOPE (no dryRun:false) ───────────────────┐
                         │                                                                       │
 OPERATOR asks ──▶ AGENT (Hermes) ── MCP ──▶ DataDoe actions API                                 │
 "validate this           │  actions_start(dryRun:true)   ─────────▶  ActionStartResponse        │
  pause"                  │  actions_get(actionId)        ─────────▶  ActionStatusResponse       │
                          │  *_FIND (one adProduct)       ─────────▶  Action*FindResult          │
                          │       │  (agent owns transport; Python NEVER opens a socket)         │
                          ▼       ▼                                                               │
                   ┌───────────────────────────────────────────────────────────────┐            │
                   │  PYTHON ENGINE (truth layer — hand-written, pytest-covered)     │            │
                   │                                                                 │            │
                   │  find_cache.write(find_result) ─▶ data/ads_<entity>_find_<dt>.json          │
                   │  find_cache.lookup(entity_id)  ─▶ HIT → ok | MISS → Refusal("stale/missing")│
                   │                                          ▲                       │          │
                   │                                          └── FIND-before-write (build-time) │
                   │                                                                 │            │
                   │  lifecycle.classify_dryrun(ActionStartResponse)                 │            │
                   │     status==VALIDATED & validation.valid & issues==[] ─▶ PROCEED│            │
                   │     valid==false OR issues!=[]                         ─▶ STOP(issues verbatim)
                   │                                                                 │            │
                   │  lifecycle.classify_poll(ActionStatusResponse.status)          │            │
                   │     terminal-success (COMPLETED)            ─▶ DONE             │            │
                   │     terminal-partial (PARTIALLY_COMPLETED / COMPLETED_WITH_ISSUES) ─▶ DONE+surface
                   │     terminal-fail (ERROR / CANCELED / BLOCKED_*) ─▶ STOP(error verbatim)    │
                   │     in-flight (PENDING / IN_PROGRESS / WAITING_EXTERNAL_PROCESSING) ─▶ keep polling
                   │        └── via datadoe.poll_status (capped, terminal-on-set, no infinite spin)
                   │                                                                 │            │
                   │  every actions_start/actions_get wrapped by logging.logged_call │            │
                   │     ─▶ engine/logs/external-calls.jsonl  (.start/.end, no UUID)  │            │
                   └───────────────────────────────────────────────────────────────┘            │
                                                                                                 │
   RECONCILE = actions_get→terminal  +  *_FIND echo   ◀── NOT a next-day DataDoe export (≤24h lag)│
                         │                                                                       │
                         └───────────────────────────────────────────────────────────────────────┘
```

### Recommended file additions
```
engine/src/habibos/
├── lifecycle.py          # NEW — classify dryRun + poll responses (mirrors tacos.py typed result)
├── find_cache.py         # NEW — FIND write/read + build-time refusal (mirrors thresholds.py missing→refuse)
├── datadoe.py            # MODIFIED — extend TERMINAL with the verified status enum
└── result.py             # MODIFIED (additive) — add lifecycle result types OR reuse Refusal as-is

engine/scripts/
├── classify_dryrun.py    # NEW (optional) — thin CLI: dryRun JSON → proceed/stop JSON (mirrors answer_tacos.py)
└── classify_poll.py      # NEW (optional) — thin CLI: actions_get JSON → terminal/in-flight/error JSON

engine/tests/
├── test_lifecycle.py     # NEW — dryRun + poll classification + status-enum coverage
├── test_find_cache.py    # NEW — cache write/read + miss-refuses-at-build
└── fixtures/
    ├── dryrun_validated.json        # captured VALIDATED/valid:true/issues:[]
    ├── dryrun_invalid.json          # valid:false + issues[]
    ├── actions_get_completed.json   # terminal COMPLETED
    ├── actions_get_error.json       # ERROR + ActionExecutionErrorResult.message
    └── campaigns_find.json          # {campaigns:[...], nextToken} (reuse data/ads_sp_campaigns_live_2026-06-20.json shape)

data/
└── ads_campaigns_find_2026-06-20.json   # cached FIND (the read that makes any UPDATE/REMOVE executable)

.claude/skills/datadoe-query/SKILL.md    # MODIFIED — add write-action reference section
```

### Pattern 1: Typed lifecycle classifier (mirror `tacos.py`)
**What:** A pure function that takes the parsed MCP response and returns a typed proceed/stop result — never a bare bool, never a swallowed error.
**When to use:** dryRun response classification (WRITE-01) and poll classification (WRITE-05).
**Example (the shape to mirror — `tacos._present_flag` / `parse`):**
```python
# Source: engine/src/habibos/tacos.py:80-124 (the verified existing pattern)
def parse(artifact, status):
    if status == "FAILED":
        return Refusal("Export failed — no data.", "failed_export")  # typed, never a number
    ...
    try:
        for row in frame.to_dicts():
            _PremiumRow.model_validate(row)            # pydantic — fail loud on drift
    except ValidationError as exc:
        raise ValueError(f"Premium export schema mismatch (drift?): {exc}") from exc
    return frame
```
`lifecycle.classify_dryrun(resp)` follows the same grammar: a clean `VALIDATED/valid:true/issues:[]` returns a `Proceed`-type result; any `valid:false` or non-empty `issues` returns a `Refusal` carrying the issues verbatim (no substitution).

### Pattern 2: Missing → refuse (mirror `thresholds.read` for the FIND cache)
**What:** A cache lookup that returns a typed refusal on miss, never a fabricated value.
**When to use:** FIND-before-write enforcement (WRITE-02).
**Example (the shape to mirror):**
```python
# Source: engine/src/habibos/thresholds.py:19-31 (verified existing pattern)
def read(key, marketplace="CA"):
    ...
    raw = data.get("marketplace", {}).get(marketplace, {}).get(key, "")
    if raw == "" or raw is None:
        return None     # None means caller MUST refuse — never a default
    return float(raw)
```
`find_cache.lookup(entity_id, entity_type)` → returns the cached entity dict, or a `Refusal("stale/missing entity ID", "find_cache_miss")` when the ID isn't in any `data/ads_<entity>_find_*.json`. A write builder calls this at BUILD time and stops on the refusal.

### Pattern 3: Reuse `datadoe.poll_status` terminal-on-set (do NOT rebuild)
**What:** The capped, jittered poll that stops on a terminal status set.
**Reuse, don't add:** `lifecycle.classify_poll` decides terminal-vs-in-flight for ONE response; `datadoe.poll_status` drives the loop. Extend only the `TERMINAL` set.
```python
# Source: engine/src/habibos/datadoe.py:23-43 (verified existing)
TERMINAL = {"COMPLETED", "FAILED"}        # ◀── M1 export statuses; INSUFFICIENT for actions
def _not_terminal(status): return status not in TERMINAL
@retry(stop=stop_after_attempt(20), wait=wait_exponential_jitter(initial=1, max=15),
       retry=retry_if_result(_not_terminal))
def poll_status(get_status): return get_status()
```
**Change for Phase 6:** the action terminal set is NOT the export set. Either widen `TERMINAL` (risk: a FAILED *export* status `FAILED` doesn't exist for actions) or — cleaner — add an `ACTION_TERMINAL` constant so the export and action lifecycles keep separate, named, verified sets (recommended; see Pitfall 1).

### Anti-Patterns to Avoid
- **Assuming `FAILED`/`CANCELLED` are the terminal states.** They are not — the real enum uses `ERROR` and `CANCELED` (one L). Hard-coding the roadmap's assumed names causes an **infinite poll** on a real `ERROR`. (See Pitfall 1.)
- **Treating the org-disabled rejection as a body status.** It is an **HTTP 412** ("Action execution is disabled for this organization") at `dryRun:false` start — not an `actions_get` status. Phase 6 never hits it (no real run), but the substrate must classify the agent-relayed 412 as a typed refusal, not a retry. (See Pitfall 4.)
- **Reading a next-day DataDoe export to confirm a write.** DataDoe reporting lags ≤24h; reconciliation is `actions_get`→terminal + `*_FIND` echo only. The engine has no export-read in the reconcile path by construction.
- **Caching multiple ad-products in one FIND file.** `adProductFilter.include` is `maxItems:1` (verified). One ad-product per request → one cache file per (entity, adProduct, date).
- **Logging the seller UUID into `external-calls.jsonl`.** Never pass `sellerOrVendorId` into `logged_call` start/end fields.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Polling `actions_get` to terminal | A new while-loop with sleep | `datadoe.poll_status` (extend the terminal set) | Already capped, jittered, terminal-on-set, tested. Re-rolling re-introduces the infinite-spin bug `poll_status` was written to prevent. |
| Validating MCP response shape | `resp.get("status")` dict-walking | `pydantic` model (like `tacos._PremiumRow`) | Fails loud on schema drift; dict-walking silently tolerates a renamed field → wrong proceed/stop verdict. |
| Call logging | A `print`/custom logger | `logging.logged_call` | One-in-one-out contract, error-on-exception-still-emits, UUID-hygiene already tested. |
| Typed proceed/stop/refuse results | Returning `(bool, str)` tuples | Frozen dataclasses in `result.py` style | No bare None / swallowed error; the project's anti-fabrication guarantee. |
| The status enum | Memorized constant from the roadmap | The **verified** enum pinned from `actions_details_schema_get` / the live spec | The roadmap's `COMPLETED/FAILED/CANCELLED` is wrong; only the live schema is authoritative (Success Criterion 4). |

**Key insight:** Every primitive this phase needs already exists in the M1 engine. Phase 6 is ~90% *wiring proven patterns to a new response shape* and ~10% new code (the two classifiers + the cache). The one genuinely new fact is the **verified status enum**, which must come from the live schema, not training data or the roadmap.

## Runtime State Inventory

> This is a greenfield substrate phase (new modules, new cache files) — not a rename/refactor. The only "runtime state" is the new FIND cache and the existing log file. Included for completeness.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | New: `data/ads_*_find_*.json` cache files (created by this phase). Existing reusable: `data/ads_sp_campaigns_live_2026-06-20.json` is already a `CAMPAIGNS_FIND`-shaped capture (`{campaigns:[91 items], ...}`, verified). | Engine writes new cache; existing file can seed the `campaigns_find.json` fixture. |
| Live service config | DataDoe org-enable state (Settings → Actions, OFF by default). **Not touched in Phase 6** (no real run). | None this phase — but the substrate must classify the 412 disabled-action rejection for Phase 8. |
| OS-registered state | None — desktop app, no cron/launchd/Task Scheduler registration for this phase. | None — verified (no scheduled task touches the engine). |
| Secrets/env vars | `$AMAZON_CA_SELLER_ID` in `engine/.env` (gitignored). Used as `sellerOrVendorId` in every `actions_*` request — supplied by the AGENT, never read by Python, never logged. | None — code rename-free; `test_logging.py` guards UUID leakage. |
| Build artifacts | `engine/src/habib_os.egg-info/` exists (editable install). New modules under `src/habibos/` are picked up automatically (`pythonpath=["src"]` in pyproject). | None — no reinstall needed for new `.py` files in the existing package. |

**Verified:** `cd engine && uv run pytest` is green (16 passed, 5 skipped) as of 2026-06-20 — the substrate is being added to a passing suite.

## Common Pitfalls

### Pitfall 1: Wrong terminal status enum → infinite poll (HIGHEST severity for this phase)
**What goes wrong:** The roadmap (Success Criterion 3) says terminal = `COMPLETED / FAILED / CANCELLED`. The **live DataDoe spec** says the real `actions_get` status enum is `PENDING, IN_PROGRESS, WAITING_EXTERNAL_PROCESSING, COMPLETED, PARTIALLY_COMPLETED, COMPLETED_WITH_ISSUES, ERROR, BLOCKED_NO_TOKENS, BLOCKED_INVALID_INPUT, CANCELED`. There is **no `FAILED`** (it's `ERROR`) and **no `CANCELLED`** (it's `CANCELED`, one L). If `TERMINAL` contains the roadmap's assumed names, a real `ERROR` or `CANCELED` is treated as "not terminal" and `poll_status` spins until it exhausts its 20-attempt cap — the exact infinite-spin failure `poll_status` was built to avoid.
**Why it happens:** Training data and the roadmap predate the live schema pull; the names are plausible-but-wrong.
**How to avoid:** Pin the enum verbatim from `actions_details_schema_get` (or the live spec) into a named `ACTION_TERMINAL` set. Classify: success-terminal `{COMPLETED}`; partial-terminal `{PARTIALLY_COMPLETED, COMPLETED_WITH_ISSUES}` (done, but surface the issues); fail-terminal `{ERROR, CANCELED, BLOCKED_NO_TOKENS, BLOCKED_INVALID_INPUT}`; in-flight `{PENDING, IN_PROGRESS, WAITING_EXTERNAL_PROCESSING}`. A status NOT in any set → typed refusal ("unknown action status"), never assumed terminal *or* infinitely polled. This is Success Criterion 4.
**Warning signs:** A poll that runs to its retry cap on a real run; a test that uses `FAILED` and passes (it shouldn't exist).

### Pitfall 2: dryRun response field confusion (VALIDATED is a status, valid/issues live under `validation`)
**What goes wrong:** The brain note shorthand "returns `status: VALIDATED, valid: true/false, issues: []`" reads as three sibling fields. In the real `ActionStartResponse`, `status == "VALIDATED"` is the top-level status, but `valid` and `issues[]` live **nested under `validation`** (`ActionValidationResult{valid:bool, issues:ActionValidationIssue[]}`), and each issue is `{path:string[], code:string, message:string}`. Classifying off a flat `resp["valid"]` misses the real path.
**How to avoid:** Model it as `ActionStartResponse.status` + `ActionStartResponse.validation.valid` + `ActionStartResponse.validation.issues[].{path,code,message}`. Capture a real dryRun fixture (the brain note already did one for `AMAZON_LISTINGS_UPDATE` 2026-06-20 — re-capture an *Ads* dryRun for the fixture). PROCEED only when `status==VALIDATED AND validation.valid==true AND validation.issues==[]`.
**Warning signs:** `KeyError: 'valid'` at top level; a "valid" dryRun that actually had issues.

### Pitfall 3: FIND cache staleness silently passing an old ID
**What goes wrong:** A cached `data/ads_*_find_*.json` from days ago may name a campaign that's since been paused/archived/renamed. A naive lookup returns the stale ID and a later UPDATE targets a wrong/dead entity.
**Why it happens:** The cache is a file, not a live read; nothing forces freshness.
**How to avoid:** (a) FIND is read-only and ungated — re-run it cheaply before a write batch; (b) stamp each cache file with its capture date in the filename (`ads_campaigns_find_2026-06-20.json`) and have `find_cache.lookup` prefer the newest and optionally refuse a lookup older than a configurable staleness window (operator dial, not invented). For Phase 6 (no real write) a miss-refuses-at-build test is sufficient; the staleness window is finalized in Phase 8. Document the choice; don't hard-code a default silently (hard rule 4).
**Warning signs:** A lookup HIT for an entity the latest FIND no longer lists.

### Pitfall 4: Org-disabled rejection is HTTP 412, not a poll status
**What goes wrong:** When `dryRun:false` runs against an action type not enabled in DataDoe Settings → Actions, the API returns **HTTP 412** ("Action execution is disabled for this organization. Ask an organization owner to enable it…") — verified in the live spec's POST `/api/v1/actions` 412 response. This is NOT an `actions_get` status; an engine that only classifies poll statuses won't see it.
**Why it happens:** The roadmap's "4th gate" is an HTTP-level precondition, surfaced by the MCP as an error, not as an action lifecycle state.
**How to avoid:** Phase 6 fires no real run, so it won't hit 412 directly — but the substrate must be able to classify an agent-relayed disabled-action error as a **typed refusal with the unblock message verbatim**, not a retry. Same for **HTTP 402** (no AI tokens) and **HTTP 429** (rate limit — max **2 req/s per org**, `Retry-After` header). Treat 429 as the only retryable HTTP error; 412/402 are refusals.
**Warning signs:** A "disabled" error being retried; rate-limit errors not backing off.

### Pitfall 5: Schema drift between the pinned enum and a later DataDoe change
**What goes wrong:** DataDoe is in private beta (the spec's 501 response says "Actions are available in private beta only"). The status enum or response shape may change.
**How to avoid:** Validate every response with `pydantic` (fail loud, like `tacos._PremiumRow`); a new/renamed status raises rather than silently mis-classifying. Keep the pinned enum in ONE named constant with a source comment (`# verified against api.datadoe.com/api/v1/docs/json 2026-06-20`) so a re-verification is a one-line diff. Re-pin via `actions_details_schema_get` if a real run ever returns an unmodeled status.
**Warning signs:** A `pydantic` ValidationError on a poll; an unfamiliar status string.

## Code Examples

Verified shapes from the **live DataDoe OpenAPI spec** (`https://api.datadoe.com/api/v1/docs/json`, "DataDoe REST API 0.0.1", pulled 2026-06-20). The MCP tools (`actions_start`/`actions_get`/`actions_list`/`actions_details_schema_get`) are thin wrappers over these REST endpoints — same request/response schemas.

### `actions_start` request (the `ActionRequest` shape)
```jsonc
// Source: ActionRequest schema — POST /api/v1/actions
{
  "type": "AMAZON_ADS_CAMPAIGNS_FIND",   // enum (see full list in State of the Art)
  "sellerOrVendorId": "<uuid>",          // supplied by the AGENT from .env, never by Python
  "dryRun": true,                         // default false; Phase 6 only ever uses true
  "details": { /* oneOf per type — see FIND + UPDATE below */ }
}
```

### `*_FIND` request — one ad-product per request (verified `maxItems:1`)
```jsonc
// Source: ActionRequestAdsCampaignFindDetails + ActionRequestAdsCampaignQuery + ActionRequestAdsAdProductFilter
{
  "type": "AMAZON_ADS_CAMPAIGNS_FIND",
  "sellerOrVendorId": "<uuid>",
  "details": {
    "campaignQuery": {
      "adProductFilter": { "include": ["SPONSORED_PRODUCTS"] },  // maxItems:1 → ONE ad-product per request
      "stateFilter": { /* ENABLED/PAUSED filter */ },
      "maxResults": 100,                                          // 1..100
      "nextToken": "..."                                          // paginate
    }
  }
}
```
FIND variants and their result keys (verified):
- `AMAZON_ADS_CAMPAIGNS_FIND` → `details.campaignQuery` → result `{campaigns:[...], nextToken}`
- `AMAZON_ADS_AD_GROUPS_FIND` → `details.adGroupQuery` → result `{adGroups:[...], nextToken}`
- `AMAZON_ADS_TARGETS_FIND`   → `details.targetQuery`  → result `{targets:[...], nextToken, totalResults}`
- `AMAZON_ADS_ADS_FIND`       → `details.adQuery`      → result `{ads:[...], nextToken}`

The `campaigns:[...]` items match `data/ads_sp_campaigns_live_2026-06-20.json` exactly (verified: keys `campaignId, name, adProduct, state, budgets, optimizations, …`). Use that file as the `campaigns_find.json` fixture.

### `actions_start dryRun:true` response (the `ActionStartResponse` shape)
```jsonc
// Source: ActionStartResponse + ActionValidationResult + ActionValidationIssue
{
  "actionId": null,                       // null on dryRun (no action created)
  "status": "VALIDATED",                  // ◀── WRITE-01 success marker
  "dryRun": true,
  "request": { /* echoes ActionRequest */ },
  "validation": {
    "valid": true,                        // ◀── proceed gate
    "issues": [                           // ◀── non-empty → STOP, surface verbatim
      // { "path": ["details","campaigns",0,"budgets"], "code": "...", "message": "..." }
    ]
  },
  "result": null,
  "error": null,
  "cause": null,
  "queuedAt": null
}
```
**Classify PROCEED iff** `status=="VALIDATED" && validation.valid==true && validation.issues==[]`.

### `actions_get` response (the `ActionStatusResponse` shape) — VERIFIED status enum
```jsonc
// Source: ActionStatusResponse — GET /api/v1/actions/{actionId}
{
  "actionId": "<uuid>",
  "type": "AMAZON_ADS_CAMPAIGNS_UPDATE",
  "sellerOrVendorId": "<uuid>",
  "status": "COMPLETED",   // enum ▼ — PIN THIS verbatim into ACTION_TERMINAL
  // PENDING | IN_PROGRESS | WAITING_EXTERNAL_PROCESSING        → in-flight (keep polling)
  // COMPLETED                                                  → terminal success
  // PARTIALLY_COMPLETED | COMPLETED_WITH_ISSUES                → terminal, surface issues
  // ERROR | CANCELED | BLOCKED_NO_TOKENS | BLOCKED_INVALID_INPUT → terminal failure (surface verbatim)
  "details": { /* echoes the action details */ }
}
```
Note: there is **no `FAILED`** and **no `CANCELLED`** — the roadmap's assumed names are wrong.

### Terminal failure payload (the `ActionExecutionErrorResult` shape)
```jsonc
// Source: ActionExecutionErrorResult (also ActionStartResponse.error)
{
  "status": "ERROR",
  "code": "AMAZON_ADS_INSUFFICIENT_PERMISSIONS" | "EXECUTION_FAILED",
  "message": "User-friendly explanation of why the action failed and what to do next."
}
```
WRITE-05: a failed/blocked action surfaces this `message` cleanly (verbatim, never a substituted "ok").

### Extending the poll terminal set (the engine change)
```python
# engine/src/habibos/datadoe.py — ADD (keep the export TERMINAL separate)
# verified against api.datadoe.com/api/v1/docs/json 2026-06-20
ACTION_IN_FLIGHT = {"PENDING", "IN_PROGRESS", "WAITING_EXTERNAL_PROCESSING"}
ACTION_TERMINAL_SUCCESS = {"COMPLETED"}
ACTION_TERMINAL_PARTIAL = {"PARTIALLY_COMPLETED", "COMPLETED_WITH_ISSUES"}
ACTION_TERMINAL_FAIL = {"ERROR", "CANCELED", "BLOCKED_NO_TOKENS", "BLOCKED_INVALID_INPUT"}
ACTION_TERMINAL = ACTION_TERMINAL_SUCCESS | ACTION_TERMINAL_PARTIAL | ACTION_TERMINAL_FAIL
```

## State of the Art

| Old Approach (roadmap/brain-note assumption) | Current Approach (verified live 2026-06-20) | Impact |
|--------------|------------------|--------|
| Terminal = `COMPLETED / FAILED / CANCELLED` | Real enum: `…COMPLETED, PARTIALLY_COMPLETED, COMPLETED_WITH_ISSUES, ERROR, …, CANCELED` (no `FAILED`; `CANCELED` one-L) | Pin the real enum or risk infinite poll. Three extra states to classify. |
| dryRun returns flat `status/valid/issues` | `status=="VALIDATED"` top-level; `valid`+`issues[]` nested under `validation`; each issue `{path,code,message}` | Classifier reads `validation.*`, not flat fields. |
| Org-disabled = a rejected real run (status) | HTTP **412** at start; also 402 (no tokens), 429 (rate limit, 2 req/s) | Classify HTTP-level refusals; only 429 is retryable. |
| FIND "one adProduct per request" (prose) | `adProductFilter.include` is `minItems:1, maxItems:1` enum of `{AMAZON_DSP, SPONSORED_BRANDS, SPONSORED_DISPLAY, SPONSORED_PRODUCTS, SPONSORED_TELEVISION}` | One cache file per (entity, adProduct). For Anabtawi today only `SPONSORED_PRODUCTS` exists (91 campaigns, verified). |

**Full action `type` enum (verified):** `AMAZON_LISTINGS_UPDATE, AMAZON_ORDERS_CANCEL, AMAZON_ORDERS_CONFIRM_SHIPMENT, AMAZON_ADS_{CAMPAIGNS,AD_GROUPS,TARGETS,ADS,AD_ASSOCIATIONS}_{ADD,REMOVE,UPDATE}, AMAZON_ADS_{CAMPAIGNS,AD_GROUPS,TARGETS,ADS,AD_ASSOCIATIONS}_FIND`. Note the `AMAZON_ADS_` prefix (the brain note's shorthand drops it; the engine must use the full string).

**Deprecated/outdated:** the brain note's `actions_*` shorthand and the roadmap's status names are *descriptions*, not the wire format — defer to the pinned schema.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The MCP tool `actions_get` response is identical to the REST `GET /api/v1/actions/{actionId}` `ActionStatusResponse` (the MCP is a thin wrapper). | Code Examples | If the MCP reshapes the field names, the classifier mis-reads. **Mitigation:** Success Criterion 4 requires the executor to confirm via `actions_details_schema_get`/a live `actions_get` and re-pin — this research gives the verified REST shape as the high-confidence starting point. |
| A2 | A FIND-cache staleness window value is an operator dial, not invented here. | Pitfall 3 | If a default is hard-coded, it violates hard rule 4. **Mitigation:** Phase 6 only needs the miss-refuses test; the window is finalized in Phase 8 with operator input. |
| A3 | `data/ads_sp_campaigns_live_2026-06-20.json` is a genuine `CAMPAIGNS_FIND` capture (its `{campaigns:[…]}` shape matches `ActionAdsCampaignsFindResult`). | Architecture / fixtures | If it was produced by a different tool with a divergent shape, the fixture is misleading. **Mitigation:** shape verified field-by-field against the spec; low risk. |

## Open Questions

1. **MCP-vs-REST field parity for `actions_get`.**
   - What we know: the REST `ActionStatusResponse` is fully pinned (above).
   - What's unclear: whether the DataDoe MCP `actions_get` tool returns that object verbatim or wraps/renames it.
   - Recommendation: executor calls `actions_details_schema_get` (read-only, safe) and one live `actions_get` against any historical action to confirm before finalizing the `pydantic` model. Success Criterion 4 mandates this.

2. **Where lifecycle result types live.**
   - What we know: `result.py` has `Refusal/Answer/SkuRow`.
   - What's unclear: whether to reuse `Refusal` for stop/fail (its `code` field fits) or add `Proceed`/`PollResult` types.
   - Recommendation: reuse `Refusal` for the stop path (consistency); add a small `Proceed`/`PollOutcome` frozen dataclass for the success/in-flight path. Planner's call; either honors the typed-result contract.

3. **Whether thin CLIs (`classify_dryrun.py`/`classify_poll.py`) are needed in Phase 6.**
   - What we know: M1 always exposed money logic via a thin CLI the skill calls.
   - What's unclear: whether the agent classifies inline or via CLI for the substrate.
   - Recommendation: build the CLIs for consistency with `answer_tacos.py` (the skill renders JSON, never re-derives) — but the *classifier functions* are the load-bearing deliverable; the CLI is thin wiring.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `uv` + Python 3.12 + engine deps | All engine code/tests | ✓ | engine venv (pytest green 2026-06-20) | — |
| DataDoe MCP `actions_*` tools (ToolSearch-loadable) | Live `actions_details_schema_get`/`actions_list` confirmation (Success Criterion 4) | ✓ (orchestrator/executor; **not** the research agent) | private beta | This research pins the REST schema as the high-confidence substitute; executor confirms live. |
| `data/ads_sp_campaigns_live_2026-06-20.json` | `campaigns_find.json` fixture seed | ✓ | 91 SP campaigns | re-run `CAMPAIGNS_FIND` if stale |
| DataDoe org-enable (Settings → Actions) | Real `dryRun:false` runs | ✗ (OFF by default) | — | **Not needed in Phase 6** — no real run fires. |

**Missing dependencies with no fallback:** none for Phase 6 (the only ✗, org-enable, is out of scope — this phase is no-op by design).
**Missing dependencies with fallback:** live MCP confirmation of `actions_get` shape — fallback is the pinned REST schema, confirmed at execution per Success Criterion 4.

## Validation Architecture

> `workflow.nyquist_validation` is enabled (config.json verified). This section feeds VALIDATION.md.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.0.3 (verified `engine/pyproject.toml`) |
| Config file | `engine/pyproject.toml` `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `pythonpath=["src"]`) |
| Quick run command | `cd engine && uv run pytest tests/test_lifecycle.py -x` |
| Full suite command | `cd engine && uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| WRITE-01 | A clean dryRun (`status==VALIDATED`, `validation.valid`, no issues) classifies PROCEED | unit (fixture) | `pytest tests/test_lifecycle.py::test_dryrun_validated_proceeds -x` | ❌ Wave 0 |
| WRITE-01 | A `valid:false`/non-empty-issues dryRun classifies STOP and surfaces issues verbatim | unit (fixture) | `pytest tests/test_lifecycle.py::test_dryrun_invalid_stops -x` | ❌ Wave 0 |
| WRITE-05 | `COMPLETED` → terminal success; `PENDING/IN_PROGRESS/WAITING_EXTERNAL_PROCESSING` → in-flight | unit (fixture) | `pytest tests/test_lifecycle.py::test_poll_terminal_classification -x` | ❌ Wave 0 |
| WRITE-05 | `ERROR/CANCELED/BLOCKED_*` → terminal failure, surfaces `ActionExecutionErrorResult.message` | unit (fixture) | `pytest tests/test_lifecycle.py::test_poll_error_surfaces_message -x` | ❌ Wave 0 |
| WRITE-05 | An unmodeled status → typed refusal, NOT assumed terminal nor infinite-polled | unit | `pytest tests/test_lifecycle.py::test_unknown_status_refuses -x` | ❌ Wave 0 |
| WRITE-05 | `ACTION_TERMINAL` set matches the verified enum verbatim (Success Criterion 4) | unit | `pytest tests/test_lifecycle.py::test_action_terminal_enum_pinned -x` | ❌ Wave 0 |
| WRITE-02 | A FIND result writes `data/ads_*_find_*.json`; a cached ID looks up HIT | unit (tmp_path) | `pytest tests/test_find_cache.py::test_find_write_and_lookup -x` | ❌ Wave 0 |
| WRITE-02 | A non-cached ID → `Refusal("stale/missing entity ID")` at build (FIND-before-write enforced) | unit | `pytest tests/test_find_cache.py::test_uncached_id_refuses -x` | ❌ Wave 0 |
| WRITE-01/05 | Each `actions_start`/`actions_get` op wraps `logged_call` → one `.start`+`.end`, no UUID | unit (tmp log) | `pytest tests/test_lifecycle.py::test_ops_logged_no_secret -x` | ❌ Wave 0 (extends existing `test_logging.py` pattern) |
| SC-4 (live) | `actions_get`/`actions_details_schema_get` MCP shape confirmed against live | manual (read-only MCP) | executor runs `actions_details_schema_get` + one `actions_get`; **agent**, not pytest | n/a — live confirm |

### Sampling Rate
- **Per task commit:** `cd engine && uv run pytest tests/test_lifecycle.py tests/test_find_cache.py -x` (< 5s)
- **Per wave merge:** `cd engine && uv run pytest` (full suite, currently 16+new passed / 5 skipped)
- **Phase gate:** Full suite green + the one live read-only MCP confirmation (Success Criterion 4) before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_lifecycle.py` — covers WRITE-01, WRITE-05 (dryRun + poll classification, enum pinning, logging)
- [ ] `tests/test_find_cache.py` — covers WRITE-02 (cache write/read + miss-refuses-at-build)
- [ ] `tests/fixtures/dryrun_validated.json`, `dryrun_invalid.json` — captured dryRun responses (re-capture a real Ads dryRun; the brain note has a LISTINGS one to model the shape)
- [ ] `tests/fixtures/actions_get_completed.json`, `actions_get_error.json` — captured poll responses (one terminal-success, one `ERROR`)
- [ ] `tests/fixtures/campaigns_find.json` — seed from `data/ads_sp_campaigns_live_2026-06-20.json` (shape already verified)
- [ ] No framework install needed — pytest is present and green.

## Security Domain

> `security_enforcement` not explicitly false → enabled. This is a substrate with no new auth/session surface; the relevant controls are secret hygiene and input validation of untrusted MCP responses.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No new auth — DataDoe API key + seller UUID handled by the MCP/agent, never by Python. |
| V3 Session Management | no | No sessions. |
| V4 Access Control | partial | The org-enable gate (DataDoe Settings → Actions) + human approval are the access controls; Phase 6 fires no real run. |
| V5 Input Validation | **yes** | `pydantic`-validate every MCP response (dryRun/poll/FIND) before classifying — fail loud on drift (mirror `tacos._PremiumRow`). An unmodeled status → refusal, never silent pass. |
| V6 Cryptography | no | No crypto; idempotency hashing (`hashlib`) arrives in Phase 8, not here. |
| V7/V8 Secrets/Logging | **yes** | `$AMAZON_CA_SELLER_ID` never inlined, never passed into `logged_call` fields, never written to `external-calls.jsonl` (guarded by `test_logging.py::test_no_secret_in_log` — extend the assertion to the new ops). |

### Known Threat Patterns for this substrate
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Seller UUID leaks into the call log | Information Disclosure | Never pass `sellerOrVendorId` into `logged_call`; assert-absent test on the new ops (extend `test_no_secret_in_log`). |
| Malformed/changed MCP response mis-classified as PROCEED | Tampering / Elevation | `pydantic` validation + explicit unmodeled-status refusal; PROCEED requires all three positive conditions, never a default. |
| Stale FIND ID causes a write to a wrong entity (in a later phase) | Tampering | FIND-before-write build-time refusal + dated cache files + (Phase 8) staleness window. |
| Silent infinite poll consumes the rate budget (2 req/s) | Denial of Service (self-inflicted) | Capped `poll_status` (20 attempts) + correct terminal set; 429 backoff via `Retry-After`. |

## Sources

### Primary (HIGH confidence)
- **DataDoe live OpenAPI spec** — `https://api.datadoe.com/api/v1/docs/json` ("DataDoe REST API 0.0.1", pulled 2026-06-20). Pinned: `ActionRequest` (type enum, dryRun, details oneOf), `ActionStartResponse` (status enum incl. VALIDATED), `ActionStatusResponse` (the real `actions_get` status enum), `ActionValidationResult`/`ActionValidationIssue`, `ActionExecutionErrorResult`, the `Action*FindResult` shapes, `ActionRequestAdsAdProductFilter` (maxItems:1), `ActionRequestAdsTargetItem` (bid/negative/state), POST `/api/v1/actions` response codes (200/202/402/412/429/501).
- `engine/src/habibos/{tacos,result,thresholds,datadoe,logging}.py` — the verified M1 patterns to mirror (read 2026-06-20).
- `engine/scripts/answer_tacos.py`, `engine/tests/{test_tacos,test_logging,conftest}.py` — thin-CLI-over-MCP seam + test layout (read 2026-06-20).
- `data/ads_sp_campaigns_live_2026-06-20.json` — a real `CAMPAIGNS_FIND`-shaped capture (91 SP campaigns; shape verified against the spec).
- `cd engine && uv run pytest` — green (16 passed, 5 skipped), verified 2026-06-20.

### Secondary (MEDIUM confidence)
- `brain/raw/2026-06-20_datadoe-write-path-gating.md` — the 4-gate chain, dryRun discipline, org-enable block (the prose the live spec now confirms/corrects).
- `.planning/research/{ARCHITECTURE,STACK,FEATURES,PITFALLS,SUMMARY}.md` — milestone v2.0 research (cited, not re-derived).
- [GitHub Deltologic/datadoe-mcp](https://github.com/Deltologic/datadoe-mcp/tree/main) · [DataDoe Actions docs](https://www.datadoe.com/hub/docs/datadoe-features/actions) — corroborating tool list (the four `actions_*` tools) and dryRun semantics.

### Tertiary (LOW confidence)
- None relied upon — every load-bearing claim is pinned to the live spec or read source.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — zero new deps; all four libraries pinned in `uv.lock` and M1-vetted.
- Architecture / lifecycle shapes: HIGH — pinned verbatim from the live DataDoe OpenAPI spec, cross-checked against the captured FIND file and the M1 engine patterns.
- Status enum (the key finding): HIGH — verified against the live spec; flagged the roadmap's assumed names as wrong.
- MCP-vs-REST parity: MEDIUM — research pins the REST shape; executor confirms the MCP wrapper live per Success Criterion 4.
- Pitfalls: HIGH (account/spec-specific) — sourced from the live spec + our own audit.

**Research date:** 2026-06-20
**Valid until:** 2026-07-04 (14 days — DataDoe Actions is in private beta; re-pin the status enum if a live run returns an unmodeled status).
