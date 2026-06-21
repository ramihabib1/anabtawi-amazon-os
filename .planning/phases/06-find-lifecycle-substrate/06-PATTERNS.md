# Phase 6: FIND + Lifecycle Substrate - Pattern Map

**Mapped:** 2026-06-20
**Files analyzed:** 10 (4 new modules + 2 optional CLIs + 2 new tests + 1 modified module + fixtures)
**Analogs found:** 10 / 10 (every new file has an exact M1 analog — this phase is ~90% wiring proven patterns)

> Source-of-truth note for the planner: every new module mirrors an EXISTING file in `engine/src/habibos/`. All import paths below are package-relative (`from . import ...`) inside `src/habibos/`, and absolute (`from habibos. ...`) inside `tests/` and `scripts/`. The package is `habibos` (NOT `habib_os` — that's only the egg-info dir). `pythonpath=["src"]` is set in `engine/pyproject.toml`, so new `.py` files under `src/habibos/` are picked up with no reinstall.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `engine/src/habibos/lifecycle.py` | service (classifier core) | transform (response → typed verdict) | `engine/src/habibos/tacos.py` | exact (typed parse+classify, pydantic validate-or-raise, Refusal on edge) |
| `engine/src/habibos/find_cache.py` | service (cache read/write + refuse) | file-I/O + CRUD (write `data/*.json`, lookup) | `engine/src/habibos/thresholds.py` (missing→None→refuse) + `engine/src/habibos/datadoe.py` `load_artifact` (local file I/O) | exact (missing→refuse) + role-match (file I/O) |
| `engine/src/habibos/datadoe.py` (MODIFY) | config/constants + poll primitive | event-driven (poll to terminal) | itself — additive `ACTION_*` sets alongside existing `TERMINAL` | exact (same file) |
| `engine/src/habibos/result.py` (MODIFY, additive) | model (frozen dataclasses) | — | itself — reuse `Refusal`; add `Proceed`/`PollOutcome` | exact (same file) |
| `engine/scripts/classify_dryrun.py` (NEW, optional) | route (thin CLI seam) | request-response (argv→JSON) | `engine/scripts/answer_tacos.py` | exact |
| `engine/scripts/classify_poll.py` (NEW, optional) | route (thin CLI seam) | request-response (argv→JSON) | `engine/scripts/answer_tacos.py` | exact |
| `engine/tests/test_lifecycle.py` | test | unit (fixture-driven) | `engine/tests/test_tacos.py` (fixture load) + `engine/tests/test_logging.py` (log assert) | exact |
| `engine/tests/test_find_cache.py` | test | unit (tmp_path I/O) | `engine/tests/test_logging.py` (tmp_path/monkeypatch) + `engine/tests/test_tacos.py` | exact |
| `engine/tests/fixtures/*.json` (dryrun/poll/find) | test fixture | file-I/O | `engine/tests/fixtures/profit_by_sku_30d.csv` + seed from `data/ads_sp_campaigns_live_2026-06-20.json` | role-match |
| `data/ads_campaigns_find_2026-06-20.json` | stored data (cache) | file-I/O | `data/ads_sp_campaigns_live_2026-06-20.json` (already FIND-shaped, 91 SP campaigns) | exact shape |

---

## Pattern Assignments

### `engine/src/habibos/lifecycle.py` (service, transform)

**Analog:** `engine/src/habibos/tacos.py` — the only hand-written, pytest-covered classifier core. Mirror its `parse()` + `classify()` grammar: pydantic validate-or-raise on the response shape, then a pure function returning a typed `Answer`/`Proceed` or `Refusal` — never a bare bool, never a swallowed error.

**Module docstring + imports pattern** (`tacos.py:33-58`) — package-relative imports, `from __future__ import annotations`, pydantic `BaseModel`/`ConfigDict`/`ValidationError`, pull `Refusal` from `.result`:
```python
from __future__ import annotations
from pathlib import Path
import json
from pydantic import BaseModel, ConfigDict, ValidationError
from . import datadoe                       # ACTION_TERMINAL_* sets (see modify below)
from .result import Refusal                 # reuse for STOP/fail; add Proceed/PollOutcome
```

**Pydantic validate-or-raise on drift** — copy `tacos._PremiumRow` + the `parse()` try/except verbatim in shape (`tacos.py:61-104`). For Phase 6 model the nested dryRun shape (RESEARCH Pitfall 2: `validation` is nested, not flat):
```python
# tacos.py:61-78 — the model-to-mirror
class _PremiumRow(BaseModel):
    model_config = ConfigDict(extra="ignore")   # tolerate utility cols; required col still raises
    sku: str
    ...

# tacos.py:98-102 — the validate-or-raise idiom (copy this control flow)
try:
    for row in frame.to_dicts():
        _PremiumRow.model_validate(row)
except ValidationError as exc:               # noqa: BLE001 — surface drift, never coerce
    raise ValueError(f"... schema mismatch (drift?): {exc}") from exc
```
For lifecycle, model `ActionStartResponse{status, validation:{valid, issues:[{path,code,message}]}}` and `ActionStatusResponse{status, type, details}` as nested `BaseModel`s. PROCEED iff `status=="VALIDATED" and validation.valid and validation.issues==[]` (RESEARCH §"actions_start dryRun:true response", line 327).

**Typed-edge → Refusal pattern** (`tacos.py:88-89, 145-146`) — the FAILED/empty edges return a `Refusal` with a `code`, never a number:
```python
if status == "FAILED":
    return Refusal("Export failed — no data.", "failed_export")
...
if frame.height == 0:
    return Refusal("Export returned no rows — no data.", "empty_export", export_id)
```
`classify_dryrun`: `valid==false`/non-empty issues → `Refusal(<issues verbatim>, "dryrun_invalid")`. `classify_poll`: terminal-fail → `Refusal(<ActionExecutionErrorResult.message verbatim>, "action_error")`; unmodeled status → `Refusal("unknown action status: <s>", "unknown_status")` (RESEARCH Pitfall 1 — NEVER assume terminal nor infinite-poll).

**Flag/branch helper pattern** (`tacos.py:118-124` `_present_flag`) — small pure helper, strict comparisons, explicit "no threshold"-style branch. Mirror for `classify_poll`'s status→bucket mapping against the `datadoe.ACTION_*` sets.

---

### `engine/src/habibos/datadoe.py` (MODIFY — additive constants + reused poll primitive)

**Analog:** the file itself (`engine/src/habibos/datadoe.py:23-43`). **Do NOT widen the existing export `TERMINAL`** — add NEW named action sets so the export and action lifecycles stay separate, verified, and named (RESEARCH Pitfall 1).

**Existing, REUSED unchanged** — `poll_status` drives the loop; lifecycle only classifies ONE response (RESEARCH §Pattern 3, "Reuse, don't add"):
```python
# datadoe.py:23-43 — EXISTING (read this; reuse as-is for the poll loop)
TERMINAL = {"COMPLETED", "FAILED"}                  # export statuses — do NOT touch
def _not_terminal(status: str) -> bool:
    return status not in TERMINAL
@retry(stop=stop_after_attempt(20), wait=wait_exponential_jitter(initial=1, max=15),
       retry=retry_if_result(_not_terminal))
def poll_status(get_status) -> str:                 # zero-arg callable → terminal status string
    return get_status()
```
Note: `poll_status` is hard-wired to the export `_not_terminal`. To drive an ACTION poll, EITHER add a parallel `poll_action_status` with an `_action_not_terminal` predicate over `ACTION_TERMINAL`, OR (cleaner per RESEARCH) keep one primitive and pass the predicate. Planner's call — but keep the export `TERMINAL` untouched.

**ADD (verified enum, pin verbatim with the source comment)** — RESEARCH §"Extending the poll terminal set", lines 359-365:
```python
# engine/src/habibos/datadoe.py — ADD below the existing TERMINAL block.
# verified against api.datadoe.com/api/v1/docs/json 2026-06-20 (RESEARCH Pitfall 1 / SC-4)
ACTION_IN_FLIGHT       = {"PENDING", "IN_PROGRESS", "WAITING_EXTERNAL_PROCESSING"}
ACTION_TERMINAL_SUCCESS = {"COMPLETED"}
ACTION_TERMINAL_PARTIAL = {"PARTIALLY_COMPLETED", "COMPLETED_WITH_ISSUES"}
ACTION_TERMINAL_FAIL    = {"ERROR", "CANCELED", "BLOCKED_NO_TOKENS", "BLOCKED_INVALID_INPUT"}
ACTION_TERMINAL = ACTION_TERMINAL_SUCCESS | ACTION_TERMINAL_PARTIAL | ACTION_TERMINAL_FAIL
```
NO `FAILED` (it's `ERROR`); `CANCELED` is one L. A status in NONE of these sets → lifecycle refuses (`test_unknown_status_refuses`). `test_action_terminal_enum_pinned` asserts the set verbatim (SC-4).

---

### `engine/src/habibos/find_cache.py` (service, file-I/O + missing→refuse)

**Analog A — missing→refuse:** `engine/src/habibos/thresholds.py:19-31`. The lookup returns the cached entity OR `None`/`Refusal` on miss — NEVER a fabricated ID (RESEARCH §Pattern 2, lines 181-190):
```python
# thresholds.py:19-31 — the missing→refuse shape to mirror
def read(key: str, marketplace: str = "CA") -> float | None:
    with CONFIG_PATH.open("rb") as fh:
        data = tomllib.load(fh)
    raw = data.get("marketplace", {}).get(marketplace, {}).get(key, "")
    if raw == "" or raw is None:
        return None          # None ⇒ caller MUST refuse — never a default
    return float(raw)
```
`find_cache.lookup(entity_id, entity_type)` → cached entity dict on HIT, or `Refusal("stale/missing entity ID", "find_cache_miss")` on MISS. A write builder calls this at BUILD time and stops on the refusal (FIND-before-write, WRITE-02).

**Analog B — repo-root-relative path constant:** `thresholds.py:16` / `logging.py:26` — resolve paths from `__file__`, never CWD:
```python
# thresholds.py:16 — src/habibos/x.py is parents[2] from the repo root
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "thresholds.toml"
# find_cache: DATA_DIR = Path(__file__).resolve().parents[2] / "data"
# write → data/ads_<entity>_find_<YYYY-MM-DD>.json ; lookup prefers the NEWEST file (Pitfall 3)
```

**Analog C — local file I/O, no network (the seam):** `engine/src/habibos/datadoe.py:46-54` `load_artifact` — reads a LOCAL file the agent handed off; imports no HTTP library:
```python
# datadoe.py:46-54 — local-only I/O; Python NEVER opens a socket (CLAUDE.md hard rule 1)
def load_artifact(path_or_bytes: str | Path | bytes) -> bytes:
    if isinstance(path_or_bytes, bytes):
        return path_or_bytes
    return Path(path_or_bytes).read_bytes()
```
`find_cache.write(find_result, entity_type)` parses the agent-handed FIND JSON (`{campaigns:[...], nextToken}`), pydantic-validates the item shape (reuse the `tacos._PremiumRow` validate-or-raise idiom), and `json.dump`s it to `data/ads_<entity>_find_<date>.json`. Cache items match `data/ads_sp_campaigns_live_2026-06-20.json` item keys verbatim (verified): `campaignId, name, adProduct, state, budgets, optimizations, status, ...`. One ad-product per file (`adProductFilter.include` is `maxItems:1`).

---

### `engine/src/habibos/result.py` (MODIFY — additive)

**Analog:** the file itself. **Reuse `Refusal` unchanged** for every stop/fail path (`result.py:26-32`):
```python
# result.py:26-32 — reuse as-is; its (reason, code, export_id?) fits dryRun-invalid + action-error
@dataclass(frozen=True)
class Refusal:
    reason: str          # surfaced verbatim to the operator
    code: str            # add codes: "dryrun_invalid" | "action_error" | "find_cache_miss" | "unknown_status"
    export_id: str | None = None
```
**ADD (additive, frozen dataclass — mirror `SkuRow`/`Answer` at `result.py:35-66`)** a small success/in-flight type so the proceed path is also typed (no bare bool — RESEARCH Open Question 2):
```python
# Mirror the frozen-dataclass shape of result.SkuRow (result.py:35-50)
@dataclass(frozen=True)
class Proceed:           # dryRun PROCEED verdict
    action_type: str
@dataclass(frozen=True)
class PollOutcome:       # poll classification: terminal-success/partial/in-flight + surfaced issues
    status: str
    state: str           # "done" | "done_with_issues" | "in_flight"
    issues: list[str] = field(default_factory=list)
```
Keep `from __future__ import annotations` + `from dataclasses import dataclass, field` (already imported, `result.py:10-12`).

---

### `engine/scripts/classify_dryrun.py` & `classify_poll.py` (route, request-response — optional)

**Analog:** `engine/scripts/answer_tacos.py` (read entirely). THIN wiring only — no business logic; all classification lives in `lifecycle.py` (the load-bearing deliverable). Mirror exactly:

**Module-docstring "this is the seam, no logic here" framing** (`answer_tacos.py:1-22`).

**Imports + repo-root constant** (`answer_tacos.py:24-38`):
```python
from habibos import logging as habibos_logging
from habibos.result import Refusal           # + Proceed / PollOutcome
from habibos import lifecycle
REPO_ROOT = Path(__file__).resolve().parent.parent     # scripts/ is one level below repo root
```

**argparse builder** (`answer_tacos.py:52-67`) — `--artifact` (the agent-handed response JSON), `--status`, pass-through args; computes nothing.

**`logged_call` wrapping of the op + JSON-on-stdout serialize** (`answer_tacos.py:70-128`) — wrap the classify call in `habibos_logging.logged_call(<op>, ...)`, fill `end_fields` (`status`, counts), `dataclasses.asdict` the typed result, `json.dump(..., sys.stdout)`. Set `end_fields["status"] = "refused"` on a `Refusal` (`answer_tacos.py:107-124`). NEVER pass the seller UUID into `logged_call` start fields.

---

### `engine/tests/test_lifecycle.py` (test, unit)

**Analog A — fixture load + per-case asserts:** `engine/tests/test_tacos.py:22-49` (repo-root + fixture path constant, `_frame()` helper, real-data spot checks):
```python
# test_tacos.py:31-43 — the fixture-load idiom to mirror
REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "dryrun_validated.json"   # per-case fixture
def _load(name: str) -> dict:
    return json.loads((REPO_ROOT / "tests" / "fixtures" / name).read_text())
```
Cases (from RESEARCH Test Map, lines 433-441): `test_dryrun_validated_proceeds`, `test_dryrun_invalid_stops` (issues surfaced verbatim), `test_poll_terminal_classification`, `test_poll_error_surfaces_message`, `test_unknown_status_refuses`, `test_action_terminal_enum_pinned` (assert `datadoe.ACTION_TERMINAL` == verified set verbatim, SC-4). Assert `isinstance(result, Refusal)` / `Proceed` and `.code`, mirroring `test_tacos.py:177-183`.

**Analog B — logged-op assertion (`test_ops_logged_no_secret`):** `engine/tests/test_logging.py` (read entirely). Mirror the `log_file` fixture (`test_logging.py:34-43`): monkeypatch `hlog.LOG_PATH` → `tmp_path`, `hlog.configure()`, `structlog.reset_defaults()` on teardown. Assert one `.start` + one `.end` (`test_logging.py:45-62`) and the UUID-absence guard (`test_logging.py:85-94`):
```python
# test_logging.py:25-32, 85-94 — the secret-hygiene idiom to copy for the new ops
SELLER_UUID_PREFIX = "5692" + "b95f"        # assembled, never written literally
...
raw = log_file.read_text(encoding="utf-8")
assert SELLER_UUID_PREFIX not in raw, "seller UUID prefix leaked into the log (V7/V8)"
```

---

### `engine/tests/test_find_cache.py` (test, unit — tmp_path I/O)

**Analog:** `engine/tests/test_logging.py:34-43` (the `tmp_path` + `monkeypatch.setattr` fixture idiom) + `test_tacos.py` (typed-result asserts).
```python
# Mirror test_logging.py:34-43 — point find_cache.DATA_DIR at tmp_path, no real data/ writes
@pytest.fixture
def cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(find_cache, "DATA_DIR", tmp_path)
    return tmp_path
```
Cases (RESEARCH lines 439-440): `test_find_write_and_lookup` (write a FIND result → `data/ads_*_find_*.json`, a cached ID looks up HIT), `test_uncached_id_refuses` (non-cached ID → `Refusal("stale/missing entity ID", "find_cache_miss")` — assert `isinstance(r, Refusal)` and `r.code`, mirroring `test_tacos.py:177-179`). Seed the FIND input from the `campaigns_find.json` fixture.

---

### Fixtures (`engine/tests/fixtures/*.json`) + cache seed (`data/ads_campaigns_find_2026-06-20.json`)

**Analog:** `engine/tests/fixtures/profit_by_sku_30d.csv` (real, sanitized capture; documented in the test docstring `test_tacos.py:17-20`).

- `campaigns_find.json` — **seed directly** from `data/ads_sp_campaigns_live_2026-06-20.json` (VERIFIED `{"campaigns": [91 items]}`, item keys `campaignId, name, adProduct, state, budgets, optimizations, status, marketplaces, ...`). Shape == `ActionAdsCampaignsFindResult` (RESEARCH lines 300-305, 387).
- `dryrun_validated.json` / `dryrun_invalid.json` — `ActionStartResponse` shape (RESEARCH lines 307-327): `{actionId:null, status:"VALIDATED", dryRun:true, validation:{valid, issues:[{path,code,message}]}, error:null}`. Re-capture a real Ads dryRun for these (the brain note has a LISTINGS one to model the nesting).
- `actions_get_completed.json` / `actions_get_error.json` — `ActionStatusResponse` (RESEARCH lines 329-355): completed `{status:"COMPLETED", type, details}`; error carries `ActionExecutionErrorResult{status:"ERROR", code, message}` for `test_poll_error_surfaces_message`.

**Secret hygiene for every fixture/cache file:** sanitize out `sellerOrVendorId` (the `5692b95f…` UUID). NOTE — at HEAD `.json` is **NOT** in `test_env.py`'s `SCAN_SUFFIXES` (`test_env.py:27` = `{".py",".sql",".md",".toml",".yaml",".yml",".sh",".txt"}`), so a raw UUID-bearing JSON fixture would pass `test_env.py` **silently**. 06-01 Task 1b ADDS `.json` to `SCAN_SUFFIXES` so the standing scan covers committed JSON under tracked dirs (`src`,`db`,`tests`) going forward; until then the explicit `grep -rl 5692b95f tests/fixtures/ data/...` in 06-01 Task 2 is the sole guard. The `data/ads_sp_campaigns_live_2026-06-20.json` cache seed lives under `data/`, which is **outside** `TRACKED_SOURCE_DIRS` and is therefore never reached by the standing scan even after Task 1b — it is guarded solely by that explicit grep. Strip the UUID when copying it into `tests/fixtures/`.

---

## Shared Patterns

### Typed-result anti-fabrication (the project's core guarantee)
**Source:** `engine/src/habibos/result.py:1-66` (`Refusal`/`Answer`/`SkuRow`) + `engine/src/habibos/tacos.py:88-89,118-124,145-146`
**Apply to:** `lifecycle.py`, `find_cache.py`, both CLIs, both tests.
Every no-data / invalid / unknown-status / cache-miss edge returns a frozen-dataclass `Refusal` (reason + code) or a typed `Proceed`/`PollOutcome` — NEVER a bare bool, a fabricated ID, a `0`, or a swallowed exception. PROCEED/terminal requires ALL positive conditions explicitly; a status in no set → refuse, never a default (RESEARCH Pitfall 1, hard rule 4).

### Pydantic validate-or-raise on schema drift
**Source:** `engine/src/habibos/tacos.py:61-78` (`_PremiumRow`) + `:98-102` (try/except `ValidationError` → `raise ValueError`)
**Apply to:** `lifecycle.py` (dryRun/poll response models), `find_cache.py` (FIND item model).
`model_config = ConfigDict(extra="ignore")` tolerates utility fields; a missing/renamed REQUIRED field still raises. Never `resp.get("status")` dict-walking — a renamed field would silently flip the proceed/stop verdict (RESEARCH Pitfall 5, V5).

### `logged_call` one-in-one-out, no secret
**Source:** `engine/src/habibos/logging.py:42-67` (the wrapper) + `engine/tests/test_logging.py:34-94` (the test idiom)
**Apply to:** both CLIs (`classify_dryrun.py`, `classify_poll.py`) and the `test_ops_logged_no_secret` case.
Wrap each `actions_start`/`actions_get` op: `with habibos_logging.logged_call("<op>", ...) as end: ...; end["status"]=...`. The `.end` emits even on exception and the exception re-raises (`logging.py:57-67`). NEVER pass `sellerOrVendorId` into start/end fields (`test_no_secret_in_log`, hard rule 5).

### Reuse `datadoe.poll_status` (do NOT rebuild the loop)
**Source:** `engine/src/habibos/datadoe.py:23-43`
**Apply to:** the poll-to-terminal reconcile path.
`lifecycle.classify_poll` decides terminal-vs-in-flight for ONE response; `poll_status` (capped 20 attempts, jittered, terminal-on-set) drives the loop. Do not hand-roll a `while`+`sleep` (re-introduces the infinite-spin bug). The ONLY change is the NEW `ACTION_*` constants (RESEARCH §Pattern 3, Don't-Hand-Roll).

### Repo-root-relative paths + thin-CLI seam
**Source:** `engine/src/habibos/thresholds.py:16`, `engine/src/habibos/logging.py:26` (`Path(__file__).resolve().parents[2]`) and `engine/scripts/answer_tacos.py` (CLI = argv → core → JSON, no logic)
**Apply to:** `find_cache.py` (`DATA_DIR`), both CLIs. Python never opens a socket — the agent does all MCP I/O; the CLI consumes the agent-handed response JSON file (`datadoe.py` "the seam", hard rule 1).

---

## No Analog Found

None. Every Phase 6 file has an exact or strong M1 analog. The single genuinely-new fact is non-code: the **verified `actions_get` status enum** (`ACTION_TERMINAL_*`), which must be pinned from the live DataDoe spec, not training data or the roadmap (RESEARCH Pitfall 1 / SC-4).

## Metadata

**Analog search scope:** `engine/src/habibos/`, `engine/scripts/`, `engine/tests/`, `engine/config/`, `data/`
**Files scanned (read in full):** `tacos.py`, `result.py`, `thresholds.py`, `datadoe.py`, `logging.py`, `answer_tacos.py`, `test_tacos.py`, `test_logging.py`, `conftest.py`, `test_env.py` (head), `data/ads_sp_campaigns_live_2026-06-20.json` (shape), `engine/pyproject.toml` (pytest config)
**Pattern extraction date:** 2026-06-20
