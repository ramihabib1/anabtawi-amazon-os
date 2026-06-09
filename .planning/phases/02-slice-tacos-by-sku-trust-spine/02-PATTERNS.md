# Phase 2: Slice — TACOS by SKU (+ trust spine) - Pattern Map

**Mapped:** 2026-06-09
**Files analyzed:** 12 (5 source modules, 1 script, 4 test files, 1 fixture, 1 SKILL.md)
**Analogs found:** 4 exact (test files) / 12

> **Greenfield caveat (read first):** Phase 2 creates the **first `src/` runtime package** in this repo. No Python source module (`datadoe.py`, `tacos.py`, `thresholds.py`, `logging.py`, `result.py`) has a same-role analog in the codebase — there are no existing controllers, services, or helpers to copy from. The only true analogs are:
> 1. **The four existing `tests/` files** — these establish a strong, consistent pytest convention the new test files MUST replicate (docstring header citing requirement IDs, `from __future__ import annotations`, `REPO_ROOT = Path(__file__).resolve().parent.parent`, skip-clean-until-built fixtures, `# noqa: BLE001` on broad excepts).
> 2. **`tests/conftest.py`** — the established fixture + `.env`-loading + path convention.
> 3. **`config/thresholds.toml`** — the exact file the threshold reader parses (`[marketplace.CA]` grain, `""`-means-refuse).
> 4. **`scripts/backup.sh`** — the only existing `scripts/` artifact; sets the `scripts/` location convention (executable, repo-root-relative paths) for `scripts/answer_tacos.py`.
>
> For the **source modules**, the closest "pattern" is the **RESEARCH.md Code Examples** (Patterns 1–4), which are project-doctrine sketches, not real codebase analogs. Where a source file has no codebase analog, this map says so honestly and points to (a) the nearest convention to honor and (b) the RESEARCH sketch to start from. The planner should treat RESEARCH §"Architecture Patterns"/§"Code Examples" as the authoritative starting code for source modules, and the `tests/` files as the authoritative starting code for test modules.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/habibos/__init__.py` | package-init | n/a | _(none — first src package)_ | no-analog |
| `src/habibos/result.py` | model (typed results) | transform | _(none)_ — RESEARCH Pattern 2 sketch | no-analog (doctrine sketch) |
| `src/habibos/logging.py` | utility (structlog wrapper) | event-driven (log emit) | _(none)_ — RESEARCH Pattern 3 sketch | no-analog (doctrine sketch) |
| `src/habibos/thresholds.py` | config reader | file-I/O (read TOML) | `config/thresholds.toml` (data contract) + `tests/conftest.py` (path convention) | data-contract match |
| `src/habibos/datadoe.py` | service (export wrapper / poll primitive) | request-response (poll) + file-I/O (load artifact) | _(none)_ — RESEARCH Pattern 1 + tenacity sketch | no-analog (doctrine sketch) |
| `src/habibos/tacos.py` | service (parse + classify; money-logic core) | transform (CRUD-read → classify) | _(none)_ — RESEARCH Code Examples sketch | no-analog (doctrine sketch) |
| `scripts/answer_tacos.py` | CLI entrypoint | request-response (argv → JSON stdout) | `scripts/backup.sh` (location/convention only) | weak (location only) |
| `tests/test_tacos.py` | test | transform | `tests/test_config_seed.py` + `tests/test_schema.py` | exact (convention) |
| `tests/test_thresholds.py` | test | file-I/O | `tests/test_config_seed.py` | exact (convention) |
| `tests/test_logging.py` | test | event-driven | `tests/test_env.py` (asserts-now style) | exact (convention) |
| `tests/fixtures/profit_by_sku_30d.csv` | test fixture | n/a (data) | _(none — first fixture)_ | no-analog |
| `~/.hermes/skills/tacos-by-sku/SKILL.md` | skill (agent surface) | n/a | `.hermes-context/SOUL.md` (markdown deliverable convention only) | weak |

## Pattern Assignments

### `src/habibos/thresholds.py` (config reader, file-I/O)

**Analog:** `config/thresholds.toml` (the data contract) + `tests/conftest.py` (repo-root path convention).

**No source-code analog exists.** Start from RESEARCH §Pattern 4 (lines 301–320 of `02-RESEARCH.md`). Two concrete conventions from the real codebase the planner MUST honor:

**1. Repo-root path resolution — copy the established convention from `tests/conftest.py` (line 24):**
```python
REPO_ROOT = Path(__file__).resolve().parent.parent
```
For a module at `src/habibos/thresholds.py`, repo root is **two** parents up from the package dir, i.e. `Path(__file__).resolve().parents[2]` (matches the RESEARCH sketch line 309: `parents[2] / "config" / "thresholds.toml"`). Verify the parent count against the final file depth — `tests/conftest.py` uses `.parent.parent` because it sits one level down; `src/habibos/*.py` sits two levels down.

**2. The exact TOML contract to parse — from `config/thresholds.toml`:**
```toml
[marketplace.CA]            # amazon.ca (CAD) — your only active marketplace today
min_margin_pct = ""
acos_ceiling_pct = ""       # ← D-09 seeds this to 30
tacos_ceiling_pct = ""      # ← D-09 seeds this to 15
days_of_cover_floor = ""
zero_conversion_spend_trigger = ""
```
The reader keys on `data["marketplace"][marketplace][key]`. **Empty string `""` or absent → return `None` (caller refuses); NEVER a default** (D-08 / TRUST-02). The file header itself states this rule verbatim: *"A value left empty ("" or absent) means REFUSE the answer that needs it — it is NOT a default."*

**Core pattern (from RESEARCH Pattern 4, adapt — note grain is `[marketplace.CA]`, key like `acos_ceiling_pct`):**
```python
import tomllib
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "thresholds.toml"

def read(key: str, marketplace: str = "CA") -> float | None:
    with CONFIG_PATH.open("rb") as fh:
        data = tomllib.load(fh)
    raw = data.get("marketplace", {}).get(marketplace, {}).get(key, "")
    if raw == "" or raw is None:
        return None          # caller renders "no threshold set" (D-08)
    return float(raw)
```
> Use stdlib `tomllib` (3.12 available) — do NOT add a TOML dependency (RESEARCH §Don't Hand-Roll).

---

### `src/habibos/result.py` (model — typed Answer/Refusal, transform)

**Analog:** None in codebase. Start from RESEARCH §Pattern 2 (lines 226–259 of `02-RESEARCH.md`).

**Convention to honor (from every existing source/test file):** module starts with `from __future__ import annotations` (used in all 5 existing test files — see `tests/conftest.py:15`, `test_env.py:9`, `test_schema.py:13`, `test_config_seed.py:11`, `test_context.py:12`). This lets the `float | None` / `str | None` unions in the dataclasses parse cleanly.

**Core pattern (frozen dataclasses, discriminated result — copy from RESEARCH lines 231–258):**
```python
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Refusal:
    reason: str            # surfaced verbatim to operator
    code: str              # "empty_export" | "failed_export" | "missing_threshold"
    export_id: str | None = None

@dataclass(frozen=True)
class SkuRow:
    seller_sku: str
    acos: float | None     # None == "no data (not in premium export)" (D-10)
    tacos: float | None
    roi: float | None
    acos_flag: str         # "ok" | "breach" | "no threshold set" (D-08)
    tacos_flag: str
    suspect: bool = False  # TACOS>ACOS inversion (D-04)

@dataclass(frozen=True)
class Answer:
    rows: list[SkuRow]
    export_id: str         # provenance (D-06) — non-optional on success
    window_from: str
    window_to: str
    source: str = "DataDoe premium Profit by SKU & Date (57a0cb319c)"
    definitions: dict[str, str] = field(default_factory=lambda: {...})
```
> **Trust-spine rule:** refusal is a *typed return*, never `None`/`0`/a swallowed exception (RESEARCH Anti-Patterns, lines 322–328). This is the project's core anti-fabrication guarantee.

---

### `src/habibos/logging.py` (utility — structlog wrapper, event-driven)

**Analog:** None in codebase (the existing `structlog==26.1.0` dep in `pyproject.toml` is unused so far). Start from RESEARCH §Pattern 3 (lines 266–298).

**Conventions to honor:**
- Repo-root-relative log path, mirroring `tests/conftest.py:24` style: `Path(__file__).resolve().parents[2] / "logs" / "external-calls.jsonl"`.
- Broad-except handling matches the established repo idiom — `tests/conftest.py:60` uses `except Exception as exc:  # noqa: BLE001`. Replicate that exact `# noqa: BLE001` comment on the broad except in `logged_call` (ruff is the configured linter; this is how the repo silences the warning).

**Core pattern (one-event-in / one-event-out context manager — copy from RESEARCH lines 273–297):**
```python
import time, structlog
from contextlib import contextmanager
from pathlib import Path

LOG_PATH = Path(__file__).resolve().parents[2] / "logs" / "external-calls.jsonl"

def configure() -> None:
    LOG_PATH.parent.mkdir(exist_ok=True)
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.WriteLoggerFactory(file=LOG_PATH.open("a")),
    )

@contextmanager
def logged_call(op: str, **start_fields):
    log = structlog.get_logger()
    t0 = time.perf_counter()
    log.info(f"{op}.start", **start_fields)              # one event IN
    status = "ok"; end_fields: dict = {}
    try:
        yield end_fields                                  # caller fills row_count, byte_size, status
    except Exception as exc:                              # noqa: BLE001
        status = "error"; end_fields["error"] = repr(exc); raise
    finally:
        log.info(f"{op}.end", status=end_fields.pop("status", status),
                 duration_ms=round((time.perf_counter() - t0) * 1000, 1), **end_fields)
```
> **Log fields (D-12):** source id, filters, row count, byte size, duration_ms, status. **Security (RESEARCH §Security V7/V8):** never log the seller UUID or any secret. Add `logs/` to `.gitignore` (currently NOT present — see Shared Patterns → .gitignore).

---

### `src/habibos/datadoe.py` (service — export wrapper + poll primitive, request-response + file-I/O)

**Analog:** None. Start from RESEARCH §Pattern 1 (lines 215–220) + the tenacity sketch (lines 444–459).

**Seam constraint (load-bearing):** the DataDoe network calls (`exports_create`/`exports_get`/`exports_raw_download`) are **MCP tool calls made by the Hermes agent**, NOT by Python. Python receives only the downloaded artifact (path/bytes) + export id. A parallel Python HTTP client is FORBIDDEN (CLAUDE.md "What NOT to Use"). So `datadoe.py` provides:
- `load_artifact(path | bytes)` — read the local artifact only.
- a **reusable tenacity poll primitive** (`poll_status`) that is the substrate for a future Python-side poll (Phase 3.5 custom MCP), documented but NOT on this phase's critical path.

**Core pattern (tenacity poll, terminal on COMPLETED/FAILED — copy from RESEARCH lines 446–458):**
```python
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_result

TERMINAL = {"COMPLETED", "FAILED"}

def _not_terminal(status: str) -> bool:
    return status not in TERMINAL

@retry(stop=stop_after_attempt(20),
       wait=wait_exponential_jitter(initial=1, max=15),
       retry=retry_if_result(_not_terminal))
def poll_status(get_status) -> str:
    return get_status()
```
> tenacity stops on BOTH `COMPLETED` and `FAILED` (terminal) — never retries a `FAILED` export forever (RESEARCH Pitfall 4). Add `tenacity==9.1.4` to `pyproject.toml` (`uv add`).

---

### `src/habibos/tacos.py` (service — parse + classify, the money-logic core)

**Analog:** None — this is the hand-written, pytest-covered classification core (CLAUDE.md hard rule 4). Start from RESEARCH §Code Examples (lines 393–441).

**The ONLY arithmetic Python is allowed to do** (RESEARCH Anti-Patterns + D-03): (a) trailing-30-day window math, (b) the `TACOS ≤ ACOS` sanity guard, (c) the threshold-breach comparison, (d) no-data/refusal classification. **Ratios (acos/tacos/roi) are READ as columns, NEVER recomputed.**

**Core pattern (copy from RESEARCH lines 401–440):**
```python
import polars as pl
from .result import Answer, Refusal, SkuRow
from . import thresholds

def classify(frame, export_id, window_from, window_to, catalog_skus, marketplace="CA"):
    if frame.height == 0:
        return Refusal("Export returned no rows — no data.", "empty_export", export_id)  # D-11
    acos_ceiling = thresholds.read("acos_ceiling_pct", marketplace)   # None → refuse flag (D-08)
    tacos_ceiling = thresholds.read("tacos_ceiling_pct", marketplace)
    present = {r["seller_sku"]: r for r in frame.to_dicts()}
    rows = []
    for sku in catalog_skus:
        r = present.get(sku)
        if r is None:                                    # D-10: show SKU, "no data"
            rows.append(SkuRow(sku, None, None, None, "no data", "no data")); continue
        acos, tacos, roi = r["acos"], r["tacos"], r["roi"]
        suspect = tacos is not None and acos is not None and tacos > acos   # D-04
        rows.append(SkuRow(sku, acos, tacos, roi,
                           _flag(acos, acos_ceiling), _flag(tacos, tacos_ceiling), suspect))
    rows.sort(key=lambda x: (x.tacos is None, -(x.tacos or 0)))   # D-05: TACOS desc, no-data last
    return Answer(rows=rows, export_id=export_id, window_from=window_from, window_to=window_to)

def _flag(value, ceiling):
    if ceiling is None: return "no threshold set"   # D-08 / TRUST-02 — never a default
    if value is None:   return "no data"
    return "breach" if value > ceiling else "ok"
```
> **Validation (RESEARCH Pitfall 1):** pydantic-validate the parsed columns before they touch the answer; on schema mismatch raise → Refusal, don't coerce. **Units (Pitfall 2 / A2):** confirm percent-vs-fraction convention at first real pull; `acos_ceiling_pct=30` must compare in the same units as the `acos` column. Add `polars==1.41.2` (`uv add`).

---

### `scripts/answer_tacos.py` (CLI entrypoint, request-response)

**Analog:** `scripts/backup.sh` — **location/convention only**, not code (it is bash). It establishes that `scripts/` holds executable, repo-root-relative operator entrypoints. The new file is Python.

**Pattern (from RESEARCH lines 199–200, 485):** thin CLI — `--artifact <path> --export-id <id> --marketplace CA`, calls `tacos.classify(...)` inside `logging.logged_call(...)`, prints the typed result as JSON on stdout for the agent to render. No business logic here; it only wires args → `habibos.*` → stdout.

---

### `tests/test_tacos.py`, `tests/test_thresholds.py`, `tests/test_logging.py` (tests)

**Analog (EXACT convention match):** `tests/test_config_seed.py`, `tests/test_schema.py`, `tests/test_env.py`. Copy this established structure exactly:

**1. Docstring header citing requirement IDs + which plan consumes it** (from `test_config_seed.py:1-9`):
```python
"""DATA-04 config-seed test (consumed by plan 01-04).

Asserts ... <what + why> ...

Until plan 01-04 ... this SKIPS cleanly (...).
"""
```
New tests cite their req IDs: `test_tacos.py` → PROF-01, D-04, D-05, D-10, D-11, A2; `test_thresholds.py` → D-07/D-08/TRUST-02; `test_logging.py` → TRUST-03/D-12 (see RESEARCH §Phase Requirements → Test Map, lines 566–577).

**2. Module preamble (every existing test uses this — `test_config_seed.py:11-13`):**
```python
from __future__ import annotations
import pytest
```

**3. Skip-clean-until-built vs assert-now distinction:**
- **Skip-clean** when a dependency (live DB, live export) isn't available — pattern from `test_config_seed.py:34-42` (`pytest.skip("... — plan 01-04")`). Use for the **live** fixture (`tests/fixtures/profit_by_sku_30d.csv`) before the real pull: skip if the real fixture is absent, OR (RESEARCH §Wave 0, lines 585-592) start against a synthetic CSV scaffold and re-point to the real capture.
- **Assert-now** (no skip) when the artifact already exists — pattern from `test_env.py:30-65`. Once the fixture CSV is committed, `test_tacos.py` asserts immediately (it does not need a live connection — money-logic runs against the file).

**4. Repo-root path resolution** (`test_env.py:21`, `conftest.py:24`):
```python
REPO_ROOT = Path(__file__).resolve().parent.parent
```
Use `REPO_ROOT / "tests" / "fixtures" / "profit_by_sku_30d.csv"` for the fixture and `REPO_ROOT / "config" / "thresholds.toml"` in `test_thresholds.py`.

**5. Broad-except idiom** (`conftest.py:60`): `except Exception as exc:  # noqa: BLE001` when catching connect/parse failures to skip cleanly.

**6. `.env` already auto-loaded** by `conftest.py:27` (`load_dotenv(REPO_ROOT / ".env")`) — new tests inherit `AMAZON_CA_SELLER_ID` without re-loading. Do NOT inline the seller UUID anywhere (enforced by `test_env.py` scanning `src/`, `db/`, `tests/`).

---

### `tests/fixtures/profit_by_sku_30d.csv` (test fixture)

**Analog:** None — first fixture in the repo. **DoD constraint (CLAUDE.md):** must be a **real** captured premium export, not mocked. RESEARCH §Wave 0 (lines 585, 592) prescribes: build against a small synthetic CSV mirroring the documented premium columns to get red→green, then **re-point to the real captured export** the moment the live pull succeeds. The real capture is gated on the DataDoe MCP connection (see No-Analog table / Shared Patterns → live-connection blocker). Columns to mirror: `seller_sku, acos, tacos, roi, ad_spend, ad_sales, total_sales, profit, total_cost, currency` (RESEARCH line 152).

---

### `~/.hermes/skills/tacos-by-sku/SKILL.md` (skill — agent surface)

**Analog:** `.hermes-context/SOUL.md` — markdown-deliverable convention only (it is the existing version-controlled markdown the agent reads). No existing SKILL.md analog. Start from RESEARCH §Code Examples SKILL.md skeleton (lines 462–493).

**agentskills.io frontmatter (RESEARCH lines 463–472, CITED spec):** required `name` (≤64), `description` (≤1024, what-it-does + when-to-use with keywords); optional `metadata.version`, `compatibility` (≤500). Body < 500 lines / ~5000 tokens. Lives at `~/.hermes/skills/tacos-by-sku/`; validate with `skills-ref validate ./tacos-by-sku` before `hermes skills install`. The body instructs the agent through the seam: call DataDoe MCP (`exports_create` → poll `exports_get` → `exports_raw_download`) → run `scripts/answer_tacos.py` → render in recommendation voice (SOUL.md). On a `Refusal`, surface the reason verbatim, never substitute a number.

## Shared Patterns

### Repo-root path resolution
**Source:** `tests/conftest.py:24`, `tests/test_env.py:21`, `tests/test_context.py:19`
**Apply to:** every new source module and test that reads a repo file.
```python
REPO_ROOT = Path(__file__).resolve().parent.parent          # tests/ (one level down)
# source modules in src/habibos/ are two levels down:
CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "thresholds.toml"
```

### Module preamble
**Source:** all five existing test files (`conftest.py:15`, `test_env.py:9`, etc.)
**Apply to:** every new `.py` file (source + test).
```python
from __future__ import annotations
```
Required so the `float | None` / `str | None` unions in `result.py` and the type hints elsewhere stay valid on the 3.12 floor without runtime cost.

### Broad-except + ruff noqa idiom
**Source:** `tests/conftest.py:60`
**Apply to:** `logging.py` (`logged_call`), and any test catching connect/parse failures to skip.
```python
except Exception as exc:  # noqa: BLE001
```

### Secret hygiene (seller UUID)
**Source:** `tests/test_env.py` (the guard) + `.env`/`.gitignore`
**Apply to:** every source + test + the SKILL.md. The seller UUID must NEVER be inlined — it lives only in the gitignored `.env`, auto-loaded by `conftest.py:27`. `test_env.py` actively scans `src/`, `db/`, `tests/` for the literal and fails the build if found. The SKILL.md must reference it as `$AMAZON_CA_SELLER_ID`, not the literal.

### Typed-result / never-fabricate (the trust spine)
**Source:** RESEARCH §Pattern 2 (no codebase analog — this phase establishes it)
**Apply to:** `result.py`, `tacos.py`, `thresholds.py`, `scripts/answer_tacos.py`.
Every no-data / empty / failed / missing-threshold edge returns a typed `Refusal` or a `None`-sentinel `SkuRow` — never `0`, never blank, never a swallowed exception. This is the project's core anti-fabrication guarantee (D-08/D-10/D-11, SOUL.md).

### Test docstring convention (req-ID + consuming-plan + skip-policy)
**Source:** `tests/test_config_seed.py:1-9`, `test_schema.py:1-11`, `test_context.py:1-10`
**Apply to:** all three new test files. Header names the requirement IDs it proves, the plan that turns it green, and whether it skips-clean or asserts-now.

### pyproject / pytest config
**Source:** `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `addopts="-ra"`)
**Apply to:** Phase-2 setup. Two additions required (RESEARCH §Wave 0, lines 589–590):
1. `uv add polars==1.41.2 tenacity==9.1.4` (both currently ABSENT from `dependencies`).
2. Add `pythonpath = ["src"]` to `[tool.pytest.ini_options]` so tests can `import habibos.*` (no `src/` package is importable today — this is net-new).

### .gitignore — add `logs/`
**Source:** current `.gitignore` (does NOT yet ignore `logs/`)
**Apply to:** Phase-2 setup. The `logged_call` wrapper writes `logs/external-calls.jsonl` at runtime; it is runtime output, not a tracked artifact (RESEARCH line 299, §Security V8). Add `logs/` to `.gitignore`.

## No Analog Found

Files with no role-equivalent in the codebase (planner should use the cited RESEARCH section as the starting code, not a real analog):

| File | Role | Data Flow | Reason / Starting Point |
|------|------|-----------|-------------------------|
| `src/habibos/__init__.py` | package-init | n/a | First `src/` package ever. Empty or version export. |
| `src/habibos/result.py` | model | transform | No dataclass/model layer exists. → RESEARCH Pattern 2 (lines 226-259). |
| `src/habibos/logging.py` | utility | event-driven | `structlog` dep present but unused. → RESEARCH Pattern 3 (lines 266-298). |
| `src/habibos/datadoe.py` | service | request-response | No service/wrapper layer exists; agent-MCP seam is new. → RESEARCH Pattern 1 + tenacity sketch (lines 215-220, 444-459). |
| `src/habibos/tacos.py` | service (money-logic) | transform | First money-logic module. → RESEARCH Code Examples (lines 393-441). |
| `tests/fixtures/profit_by_sku_30d.csv` | fixture | data | First fixture. Real capture gated on DataDoe MCP connection (Seller Central + Amazon Ads not yet connected — blocking the live pull, not the code build). Synthetic scaffold first, re-point to real. |
| `~/.hermes/skills/tacos-by-sku/SKILL.md` | skill | n/a | First Hermes skill. → RESEARCH SKILL.md skeleton (lines 462-493) + agentskills.io spec. |

> **Live-connection blocker (carried from Phase 1):** The DataDoe MCP is not wired into Hermes and Seller Central + Amazon Ads are not connected for amazon.ca (confirmed by this session's Agent Central MCP notice: *"Seller Central is not connected... Amazon Ads is not connected"*). All **code + fixture-backed tests** can be built green without it; only the **live acceptance pull (DATA-05) and TRUST-04 spot-check** are gated. Planner: mark the real-fixture capture and live pull as `checkpoint:human-verify`.

## Metadata

**Analog search scope:** `tests/` (5 files, all read), `config/thresholds.toml`, `scripts/`, `pyproject.toml`, `.gitignore`, repo root (no `src/` exists).
**Files scanned:** 8 source-of-truth files read in full (conftest.py, test_config_seed.py, test_env.py, test_schema.py, test_context.py, thresholds.toml, pyproject.toml, .gitignore) + directory listings confirming no `src/`/`tests/fixtures/`.
**Pattern extraction date:** 2026-06-09
**Key finding:** Source modules are greenfield (no analogs) — the load-bearing real-codebase conventions are concentrated in the `tests/` files (pytest structure, path resolution, `from __future__ import annotations`, skip-vs-assert policy, `# noqa: BLE001`) and the `config/thresholds.toml` data contract. RESEARCH §Patterns 1–4 + §Code Examples are the authoritative starting code for the five new source modules.
