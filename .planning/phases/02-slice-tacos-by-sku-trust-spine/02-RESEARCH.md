# Phase 2: Slice — TACOS by SKU (+ trust spine) - Research

**Researched:** 2026-06-09
**Domain:** Live DataDoe export → in-memory parse → provenance-cited per-SKU ACOS/TACOS/ROI answer in a Hermes desktop skill, plus the reusable anti-fabrication trust spine (export wrapper + structlog + refusal types)
**Confidence:** HIGH (stack, architecture, SKILL.md spec verified) / MEDIUM (live DataDoe export-response shape — schema known, runtime wire format pending first real pull)

## Summary

Phase 2 is the first runtime-code phase. It creates the first Python source package and the first Hermes skill, and it builds the substrate every later slice reuses: a DataDoe export wrapper (create → poll → download, retry/backoff, terminal on COMPLETED/FAILED), a structlog "one event in, one event out" logging wrapper, and an anti-fabrication trust spine (typed refusal results, provenance threading, no-data sentinels). The single acceptance answer it delivers is "what's my TACOS by SKU" — all ~30 CA SKUs, sorted by TACOS descending, over a trailing-30-day window, each row citing the DataDoe premium Profit-by-SKU source (`57a0cb319c`, confirmed ENABLED) and the export id it was computed from.

The defining constraint is **D-01 pure pass-through**: no persistence, no caching of export artifacts. `metric_snapshots`, `cogs`, and `decision_ledger` are Phase 3.5 — they are NOT built here, and ROADMAP success-criteria 2 ("persisted into `metric_snapshots`", "reconciles against `cogs`") is explicitly deferred by the Supabase-deferral note. The second defining constraint is **D-03 no hand-rolling of ratios**: ACOS, TACOS, ROI, and profit are read *directly* as columns from the premium source and surfaced with their verbatim definitions — Python never recomputes them. The only hand-written, pytest-covered "money logic" in this phase is (a) the trailing-30-day window math, (b) the `TACOS ≤ ACOS` sanity guard (D-04), (c) the threshold-flag comparison against `config/thresholds.toml` (D-07/D-08), and (d) the no-data / refusal classification (D-10/D-11).

**Primary recommendation:** Build a small `src/habibos/` package with four modules — `datadoe.py` (export wrapper, tenacity-wrapped poll), `logging.py` (structlog config + a `logged_call` wrapper writing JSON to `logs/external-calls.jsonl`), `thresholds.py` (tomllib reader, `(key, marketplace)` grain, missing→refusal), and `tacos.py` (parse premium export with polars, apply sanity guard + no-data sentinels + flagging, return a typed `Answer | Refusal`). Add `polars==1.41.2` and `tenacity==9.1.4` to `pyproject.toml` (currently absent). Author one Hermes skill `tacos-by-sku` whose SKILL.md instructs the agent to call the DataDoe MCP, hand the downloaded artifact path to `scripts/answer_tacos.py`, and render the returned rows in recommendation voice. Test against a real captured export fixture committed under `tests/fixtures/`.

## <user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Slice scope (live-only)**
- **D-01:** Pure pass-through — each question pulls a fresh DataDoe export, parsed in memory, with **no local persistence or caching** of export artifacts. Re-asking re-pulls. Confirms the ROADMAP Supabase-deferral note: persistence is Phase 3.5's job, not a half-built cache here.
- **D-02:** The reusable substrate built in this slice = (a) a DataDoe export wrapper handling create → poll → download with retry/backoff (terminal on COMPLETED/FAILED), (b) structlog-wrapped logging on every external call, and (c) the anti-fabrication trust spine (provenance, refusal). Built once here, reused by Phases 3–5.

**Margin / ratio source**
- **D-03:** ACOS, TACOS, ROI, and profit are read **directly** from the premium `amazon_profit_by_sku_and_date` source (`57a0cb319c`, confirmed ENABLED) — never hand-rolled in skill prose. Definitions surfaced **verbatim** from the source map: `acos` = ad_spend ÷ 14-day ad-sales; `tacos` = ad_spend ÷ total_sales; `roi` = profit ÷ total_cost.
- **D-04:** Sanity guard — for the same SKU, `TACOS ≤ ACOS` must hold (total_sales ≥ ad_sales). A row violating it is flagged as suspect / refused for that row, not displayed as correct.

**Answer shape**
- **D-05:** Default view = **all ~30 CA SKUs, sorted by TACOS descending** (worst first), over a **trailing-30-day** window. Operator can request a different window on any ask.
- **D-06:** Each row shows ACOS, TACOS, ROI, each labelled with its definition and its source (DataDoe premium Profit-by-SKU). The answer cites provenance = the DataDoe export id it was computed from.

**Thresholds & flagging**
- **D-07:** The answer **reports the numbers AND flags** SKUs breaching `acos_ceiling_pct` / `tacos_ceiling_pct` read from `config/thresholds.toml` (`(key, marketplace)` grain, CA).
- **D-08:** Missing ceiling → the flag column **refuses** for that ratio ("no threshold set"), never guesses. The numeric report still renders fully — the numbers themselves do not depend on any threshold; only the flag does.
- **D-09:** Operator delegated PPC ceiling-setting to the advisor. **Recommended starting seeds** to write into `config/thresholds.toml`: `acos_ceiling_pct = 30`, `tacos_ceiling_pct = 15`. These are **operator-adopted recommendations, not runtime-invented values** — to be tuned after the first real answer.

**Trust-spine edges**
- **D-10:** A SKU missing from the premium export → **show the SKU** with ACOS/TACOS/ROI = "no data (not in premium export)" — never 0 or blank. Distinguishes "not covered" from "no spend." (No `cogs` fallback until 3.5.)
- **D-11:** A whole export that is empty or failed → **refuse** ("no data") rather than substitute any number (locked TRUST-01).
- **D-12:** Every DataDoe call is wrapped and logged via structlog to a **local structured log file** (decision_ledger deferred to 3.5): log source id, filters, row count, byte size, duration, status — one event in, one event out.

### Claude's Discretion
- Exact Python package/module layout and the Hermes `SKILL.md` structure.
- Export parsing approach (polars vs stdlib) and trailing-window date math.
- Local log file path and format; typographic rendering of "no data" and flag cells.

### Deferred Ideas (OUT OF SCOPE)
- `metric_snapshots` persistence, `cogs` FX-reconciliation, `decision_ledger`, and the `config`-table migration (from `thresholds.toml`) → **Phase 3.5** (Supabase truth store).
- Per-SKU **break-even** ACOS ceiling (needs reconciled per-SKU margin) → revisit at 3.5.
- Wasted-spend ranking and deeper threshold-based flagging → **Phase 3**.
</user_constraints>

## <phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DATA-05 | "A DataDoe export is persisted into `metric_snapshots` end-to-end against live data" | **Persistence portion DEFERRED to Phase 3.5** per ROADMAP Supabase-deferral note. In Phase 2, DATA-05 is satisfied *live-only*: an end-to-end real export pull (create→poll→download→parse) against live DataDoe, validated against the ~30-SKU CA catalog. The `metric_snapshots` write does not happen here. See Architecture Patterns (export wrapper) + Validation Architecture. |
| PROF-01 ★ | "what's my TACOS by SKU" → correct ACOS/TACOS/ROI, prefer premium Profit-by-SKU, each ratio labelled with definition + source | Read columns directly from `57a0cb319c` (D-03). Verbatim definitions from `docs/datadoe-source-map.md`. See Standard Stack + Code Examples (parse + render). |
| PROF-02 | "Per-SKU true margin reconciles DataDoe Profit against `cogs` with FX… falls back cleanly" | **`cogs` reconciliation DEFERRED to Phase 3.5** (no `cogs` table exists yet). In Phase 2 the premium source is the sole authority; the "fallback when premium misses a SKU" reduces to the D-10 no-data sentinel (show SKU, "no data (not in premium export)"). The `datadoe_profit` vs `cogs_fallback` provenance stamp is a 3.5 concern. |
| TRUST-01 | Every numeric answer cites provenance (export id); failed/empty export → refuse, never substitute | Provenance threading: export id from MCP call → through parser → into every rendered row (D-06). Typed `Refusal` on empty/failed (D-11). See Trust Spine pattern. |
| TRUST-02 | Thresholds read from config — never invented; missing → refusal, not default | `config/thresholds.toml` reader, `(key, marketplace)` grain, missing key → per-ratio flag refusal (D-08). Config table is `thresholds.toml` until 3.5. See Code Examples (threshold reader). |
| TRUST-03 | Every external call wrapped and logged | structlog `logged_call` wrapper, one event in / one event out, JSON to a local log file (D-12). See Trust Spine pattern + Don't Hand-Roll. |
| TRUST-04 | The acceptance answer is spot-checked manually against Seller Central and signed off | Manual checkpoint — not automatable. Planner adds a `checkpoint:human-verify` task: operator compares the answer's per-SKU TACOS to Seller Central / Campaign Manager for the window. See Validation Architecture. |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Ask "what's my TACOS by SKU" + render answer | Hermes agent / skill (`SKILL.md`) | — | The skill is the conversational surface; it orchestrates and renders in recommendation voice (SOUL.md). |
| Call DataDoe (create/poll/download) | Hermes agent → DataDoe **MCP** | Python wrapper (poll/retry logic) | Per CLAUDE.md & docs/04: the *agent* calls the MCP tools; **Python handles the downloaded artifact only**. A parallel HTTP client is explicitly forbidden ("What NOT to Use"). |
| Parse export + apply sanity guard + flagging | Python helper (`tacos.py`) | — | Money-touching classification (TACOS≤ACOS guard, threshold flags, no-data sentinels) is hand-written + pytest-covered Python, never skill prose (CLAUDE.md hard rule 4). |
| ACOS/TACOS/ROI values | DataDoe premium source (`57a0cb319c`) | — | D-03: read directly as columns; never recomputed in Python or prose. |
| Threshold lookup | `config/thresholds.toml` (local file) | — | Interim home for the future Supabase `config` table; `(key, marketplace)` grain. |
| Structured logging of external calls | Python `logging.py` (structlog) → local JSONL file | — | D-12: decision_ledger deferred; local file is the interim audit spine. |
| Provenance / refusal decisions | Python helper (typed result objects) | — | Trust spine: refusal must be a *typed return*, not a swallowed exception, so the skill cannot silently fabricate. |
| Persistence (`metric_snapshots`) | **Supabase (Phase 3.5)** | — | Explicitly deferred. NOT in this phase. |

## Standard Stack

### Core (already pinned in `pyproject.toml` — from CLAUDE.md, verified installed)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | 3.12.13 | Runtime for all helpers | Project floor ≥3.12; unlocks stdlib `tomllib`. `[VERIFIED: python3 --version]` |
| pydantic | 2.13.4 | Validate premium-export rows before they touch the answer | Catches DataDoe schema drift early (RESEARCH Pitfall — schema drift). `[VERIFIED: uv pip list]` |
| structlog | 26.1.0 | Structured JSON logging — "one event in, one event out" | TRUST-03 / D-12. `[VERIFIED: uv pip list]` |
| python-dotenv | 1.2.2 | Load `.env` (`AMAZON_CA_SELLER_ID`) | Secrets in env (CLAUDE.md rule 5); already used by `tests/conftest.py`. `[VERIFIED: pyproject.toml]` |

### Supporting (MUST be added this phase — currently absent from `pyproject.toml`)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **tenacity** | 9.1.4 | Retry/backoff around the `exports_get` poll loop; terminal on COMPLETED/FAILED | D-02. `requires-python >=3.10` (compatible with 3.12). `[VERIFIED: pypi.org/pypi/tenacity/json — released 2026-02-07]` |
| **polars** | 1.41.2 | Parse + sort + per-row classify the downloaded CSV/JSON export | D-05 (sort by TACOS desc), light and fast for ~30 rows. `requires-python >=3.10`. `[VERIFIED: pypi.org/pypi/polars/json]` |

> **Provenance note:** `tenacity` and `polars` are named in the project's own CLAUDE.md "Recommended Stack" (authoritative project decision) AND version-verified against PyPI this session. They are tagged `[VERIFIED]` on that basis. slopcheck was unavailable this session (see Package Legitimacy Audit) — the planner should still gate the install behind the normal review, but both are long-established, high-trust packages named in the project's locked stack.

### Already installed but transitive (do NOT rely on directly without pinning)
| Library | Version | Note |
|---------|---------|------|
| httpx | 0.28.1 | Pulled in transitively by `supabase`. **Not needed this phase** — the agent calls the DataDoe MCP; Python does not fetch signed URLs directly unless the MCP returns a URL (`exports_raw_url_get`) the agent hands off. Prefer `exports_raw_download` (bytes/path) to avoid a Python HTTP path entirely (D-01 pass-through). |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| polars | stdlib `csv` + dicts | For ~30 rows stdlib is genuinely viable and zero-dependency (D-01 is pure pass-through, no heavy compute). **Recommendation: use polars** — it is the project-blessed parser (CLAUDE.md), gives clean `sort`/`filter`/null-handling for the no-data sentinel logic, and is reused by Phase 3's 2500-row PPC work. Establishing it now avoids a parser swap later. |
| tenacity | hand-rolled `while` poll loop | Hand-rolled is acceptable for a one-shot poll, but tenacity standardizes backoff+jitter+max-attempts and is the project-blessed choice. Use tenacity, configured to **stop on terminal COMPLETED/FAILED** (not retry those) and retry only transient/PENDING/PROCESSING states. |
| `exports_raw_download` (bytes/path) | `exports_raw_url_get` (signed URL) | `raw_url_get` forces a Python HTTP fetch (httpx) and a second network hop. Prefer `raw_download` so Python only ever touches a local artifact. Fall back to `raw_url_get` only if `raw_download` is unavailable for the artifact size. |

**Installation:**
```bash
uv add polars==1.41.2 tenacity==9.1.4
```

**Version verification (this session):**
- `polars` 1.41.2 — `[VERIFIED: pypi.org/pypi/polars/json]`, requires-python ≥3.10
- `tenacity` 9.1.4 — `[VERIFIED: pypi.org/pypi/tenacity/json — 2026-02-07]`, requires-python ≥3.10

## Package Legitimacy Audit

> slopcheck could not be installed in this environment (`pip install slopcheck` failed — no network/registry access for the sandboxed pip). Per protocol graceful-degradation, packages are tagged on the strength of being **named in the project's own locked CLAUDE.md stack** + PyPI version verification, but the planner should keep the normal install review.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| polars | PyPI | ~5 yrs (well-established) | very high (millions/mo) | github.com/pola-rs/polars | unavailable | Approved — named in CLAUDE.md locked stack; PyPI-verified 1.41.2 |
| tenacity | PyPI | ~9 yrs | very high | github.com/jd/tenacity | unavailable | Approved — named in CLAUDE.md locked stack; PyPI-verified 9.1.4 (2026-02-07) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

*slopcheck was unavailable at research time. Both packages are named in the project's authoritative CLAUDE.md "Recommended Stack" and version-verified against PyPI. They are not hallucination candidates (both are multi-year, high-download, repo-backed). The planner may proceed with `uv add` but should run `uv lock` and review the resolved lockfile diff before committing.*

## Architecture Patterns

### System Architecture Diagram

```
Operator (Hermes desktop workspace)
        │  "what's my TACOS by SKU"
        ▼
┌──────────────────────────────────────────────┐
│ Hermes agent + SOUL.md persona                │
│ activates skill: tacos-by-sku                 │
└──────────────┬───────────────────────────────┘
               │ SKILL.md instructs:
               │ 1. call DataDoe MCP
               ▼
┌──────────────────────────────────────────────┐   read-only
│ DataDoe MCP (agent-invoked)                   │──────────────► Amazon
│  exports_create(sourceId=57a0cb319c,          │   (no write path)
│    columns=[seller_sku, acos, tacos, roi,     │
│    ad_spend, ad_sales, total_sales, profit,   │
│    total_cost, currency], from=T-30, to=T,    │
│    filters: marketplace=CA, limit≤2500)       │
│  → exports_get(id) poll → COMPLETED/FAILED    │
│  → exports_raw_download → artifact (path/bytes)│
└──────────────┬───────────────────────────────┘
               │ 2. agent hands artifact path + export_id
               ▼
┌──────────────────────────────────────────────┐
│ scripts/answer_tacos.py  (Python helper)      │
│   ├─ logging.logged_call wraps the whole op   │──► logs/external-calls.jsonl
│   │   (source id, filters, rows, bytes, ms,   │     (one event in / one out)
│   │    status)                                │
│   ├─ tacos.parse(artifact) → polars frame     │
│   │     • pydantic-validate columns           │
│   │     • EMPTY/FAILED → Refusal (D-11)       │
│   ├─ tacos.classify(frame, thresholds)        │
│   │     • TACOS≤ACOS sanity guard (D-04)      │
│   │     • missing SKU → "no data" sentinel    │
│   │       (D-10)                              │
│   │     • flag vs acos/tacos ceiling (D-07)   │
│   │     • missing ceiling → flag refusal (D-08)│
│   └─ thresholds.read(key, "CA")               │◄── config/thresholds.toml
│         missing → refusal (D-08/TRUST-02)     │
│   returns: Answer(rows, export_id) | Refusal  │
└──────────────┬───────────────────────────────┘
               │ 3. typed result (JSON on stdout)
               ▼
┌──────────────────────────────────────────────┐
│ Hermes agent renders in recommendation voice  │
│  • all ~30 CA SKUs, TACOS desc (D-05)         │
│  • each ratio labelled w/ definition + source │
│  • cites export id (D-06)                     │
│  • flags breaches; "no threshold set" if none │
└───────────────────────────────────────────────┘
```

### Recommended Project Structure
```
src/
└── habibos/
    ├── __init__.py
    ├── logging.py        # structlog config + logged_call wrapper (TRUST-03, reused by all phases)
    ├── result.py         # Answer / Refusal typed results (trust spine, reused by all phases)
    ├── thresholds.py     # tomllib reader, (key, marketplace) grain, missing→Refusal (TRUST-02)
    ├── datadoe.py        # export wrapper: artifact loader + tenacity poll helper (D-02, reused)
    └── tacos.py          # parse premium export, sanity guard, no-data sentinels, flagging (PROF-01)
scripts/
    └── answer_tacos.py   # thin CLI: reads artifact path + export_id args, prints JSON result
tests/
    ├── fixtures/
    │   └── profit_by_sku_30d.csv   # REAL captured export (committed, sanitized if needed)
    ├── test_tacos.py     # money-logic unit tests against the real fixture
    ├── test_thresholds.py
    └── test_logging.py
~/.hermes/skills/
    └── tacos-by-sku/
        ├── SKILL.md
        └── (references the repo's scripts/answer_tacos.py)
```

> **Why a `src/habibos/` package, not flat modules:** the modules `logging.py`, `result.py`, `thresholds.py`, `datadoe.py` are the explicit reusable substrate (D-02) consumed by Phases 3–5. A namespaced package makes the reuse import-clean (`from habibos.datadoe import ...`) and survives the Phase 3.5 addition of a `persistence.py`/`snapshots.py` without restructuring. Add `[tool.setuptools]`/`[build-system]` or rely on `uv`'s editable src layout; confirm `src/` is importable in tests (add `pythonpath = ["src"]` to `[tool.pytest.ini_options]` or a `[tool.uv]` workspace config).

### Pattern 1: Agent-calls-MCP, Python-handles-artifact (the seam)
**What:** The DataDoe network calls (`exports_create` / `exports_get` / `exports_raw_download`) are MCP tool calls made by the *Hermes agent*, not by Python. Python receives only the downloaded artifact (a file path or raw bytes) plus the export id, and produces the typed answer.
**When to use:** Every DataDoe-backed answer in this project. Mandated by CLAUDE.md ("Let the agent call the MCP; Python handles the downloaded artifact") and "What NOT to Use" (a hand-rolled DataDoe REST client is forbidden).
**Example:** SKILL.md body instructs the agent to: (1) call the MCP with the exact `exports_create` args, (2) poll `exports_get` until terminal, (3) call `exports_raw_download`, (4) run `scripts/answer_tacos.py --artifact <path> --export-id <id> --marketplace CA`. The Python `tenacity` poll helper in `datadoe.py` is available for any future Python-side polling (e.g. a custom MCP in 3.5) but is NOT on the critical path when the agent does the polling — document it as the reusable poll primitive, and have the skill body carry the poll instruction for the agent.

> **Open clarification (low risk):** Whether the *agent* polls (via repeated MCP `exports_get` calls guided by SKILL.md prose) or whether a single Python entrypoint does create→poll→download is a SKILL.md authoring choice. Recommendation: **agent orchestrates the MCP calls** (keeps Python free of MCP/network surface, honoring the seam), and `datadoe.py` ships the tenacity poll *primitive* for reuse + a `load_artifact(path|bytes)` function. The planner should pick one and state it; both satisfy D-02.

### Pattern 2: Typed Refusal, not swallowed exception (the trust spine)
**What:** The helper returns a discriminated result — `Answer(rows, export_id, window)` or `Refusal(reason, code)` — never `None`, never a fabricated zero, never a silently-caught exception that lets the agent improvise a number.
**When to use:** Every no-data / empty / failed / missing-threshold edge (D-08, D-10, D-11).
**Example:**
```python
# src/habibos/result.py
from __future__ import annotations
from dataclasses import dataclass, field

@dataclass(frozen=True)
class Refusal:
    reason: str            # human-readable, surfaced verbatim to operator
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
    export_id: str         # provenance (D-06) — non-optional on a successful Answer
    window_from: str
    window_to: str
    source: str = "DataDoe premium Profit by SKU & Date (57a0cb319c)"
    definitions: dict[str, str] = field(default_factory=lambda: {
        "acos": "ad_spend ÷ 14-day ad sales, %",
        "tacos": "ad_spend ÷ total_sales, %",
        "roi": "profit ÷ total_cost, %",
    })
```

### Pattern 3: "One event in, one event out" logged_call wrapper (TRUST-03 / D-12)
**What:** A context manager / decorator that emits a structured `*.start` event (source id, filters, window) and a `*.end` event (row count, byte size, duration_ms, status) for every external/DataDoe operation, to a local JSONL file.
**When to use:** Wrap the whole DataDoe answer operation. Reused by every later slice.
**Example:**
```python
# src/habibos/logging.py
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
    log.info(f"{op}.start", **start_fields)            # one event IN
    status = "ok"
    end_fields: dict = {}
    try:
        yield end_fields                               # caller fills row_count, byte_size, status
    except Exception as exc:                            # noqa: BLE001
        status = "error"; end_fields["error"] = repr(exc); raise
    finally:
        log.info(f"{op}.end", status=end_fields.pop("status", status),
                 duration_ms=round((time.perf_counter() - t0) * 1000, 1), **end_fields)  # one event OUT
```
> **Log file path/format (D-12 discretion):** `logs/external-calls.jsonl` (newline-delimited JSON, one object per event) at repo root. Add `logs/` to `.gitignore` (it is runtime output, not a tracked artifact). This is the interim `decision_ledger` until Phase 3.5.

### Pattern 4: tomllib threshold reader, missing → Refusal (TRUST-02 / D-08)
**What:** Read `config/thresholds.toml` with stdlib `tomllib` (3.11+), key on `(key, marketplace)`, treat empty-string or absent values as "not set" → return a `Refusal`/`None`, never a default.
**Example:**
```python
# src/habibos/thresholds.py
import tomllib
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "thresholds.toml"

def read(key: str, marketplace: str = "CA") -> float | None:
    """Return the threshold, or None if unset (caller refuses — NEVER a default)."""
    with CONFIG_PATH.open("rb") as fh:
        data = tomllib.load(fh)
    raw = data.get("marketplace", {}).get(marketplace, {}).get(key, "")
    if raw == "" or raw is None:
        return None            # caller renders "no threshold set" (D-08)
    return float(raw)
```
> Note the toml grain is `[marketplace.CA]` with keys like `acos_ceiling_pct` / `tacos_ceiling_pct` (matches the seeded file). The values are currently `""` (empty) — D-09 seeds `acos_ceiling_pct = 30`, `tacos_ceiling_pct = 15` as **numbers, not strings** (the reader handles both, but seed them as numeric).

### Anti-Patterns to Avoid
- **Recomputing ACOS/TACOS/ROI in Python.** Forbidden by D-03 and CLAUDE.md "What NOT to Use" (hand-rolled ratios when the premium column exists → definition drift). Read the columns; surface the verbatim definitions. The *only* arithmetic Python does is the `TACOS ≤ ACOS` comparison guard and the threshold-breach comparison — neither recomputes a ratio.
- **Returning `0` or blank for a missing SKU.** Violates D-10. Use the `None`→"no data (not in premium export)" sentinel; this distinguishes "not covered" from "no spend."
- **Defaulting a missing threshold.** Violates D-08/TRUST-02/SOUL.md. Refuse the *flag* for that ratio while still rendering the number.
- **Persisting/caching the export artifact.** Violates D-01 pass-through. No `metric_snapshots`, no on-disk cache, no memoization across asks. The downloaded artifact is read once, in memory, and discarded.
- **A Python HTTP client to DataDoe.** Forbidden ("What NOT to Use"). Agent calls the MCP.
- **Summing attributed sales across SP/SB/SD.** Mixed attribution windows (SP 7d, SB/SD 14d). The premium source already provides per-SKU `acos`/`tacos`/`ad_sales` with its own attribution; state the source, don't re-aggregate across programs.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| ACOS/TACOS/ROI math | A margin calculator in Python | The premium source's `acos`/`tacos`/`roi` columns (D-03) | Definition drift; the source's definitions are authoritative + surfaced verbatim. |
| DataDoe network access | A REST/HTTP client | The DataDoe MCP (agent-invoked) | CLAUDE.md forbids a parallel client; unmaintained surface that drifts from the MCP contract. |
| Poll-loop retry/backoff | A `while True: sleep()` loop | `tenacity` (backoff + jitter + max attempts, terminal on COMPLETED/FAILED) | Project-blessed; self-documenting; reused by all slices. |
| Structured logging | `print()` / ad-hoc dict logging | `structlog` JSON to `logs/external-calls.jsonl` | TRUST-03; one event in/out; the interim audit spine. |
| TOML parsing | A regex/INI parser | stdlib `tomllib` (3.11+) | Native, zero-dependency, correct. |
| Export-row validation | Manual `if col in row` checks | `pydantic` model over the expected premium columns | Catches DataDoe schema drift before it touches the answer. |
| CSV parse + sort + null-handling | Hand-rolled dict munging | `polars` | Project-blessed; clean null semantics for the no-data sentinel; reused for the 2500-row Phase 3 work. |

**Key insight:** This phase's value is *correctness and provenance*, not computation. Almost nothing should be hand-built except the four pieces of hand-written, pytest-covered classification logic (window math, sanity guard, flagging, no-data/refusal). Everything else is the premium source's own columns + blessed libraries.

## Runtime State Inventory

> Phase 2 is **greenfield runtime code** (first Python package, first skill) under a strict **D-01 no-persistence** constraint. There is no rename/refactor/migration of existing stored state. The relevant "state" questions:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | **None — D-01 forbids persistence.** No `metric_snapshots`/`cogs`/`decision_ledger` writes this phase (Supabase deferred to 3.5). The only file written at runtime is the append-only `logs/external-calls.jsonl` (not a datastore). | None for migration; add `logs/` to `.gitignore`. |
| Live service config | DataDoe MCP must be **wired into the Hermes CLI/desktop runtime** (`hermes mcp add`/`install`) — per Phase-1 SUMMARY, `~/.hermes/config.yaml` `servers:` is still empty (`hermes mcp list` → "No MCP servers configured"). The skill cannot call DataDoe from the desktop app until this is done. | **Operator/checkpoint:** wire DataDoe MCP into Hermes, `hermes mcp test datadoe`. See Environment Availability. |
| OS-registered state | None — no cron/launchd/scheduler (M1 is on-demand/conversational; no clock-cron assumed). | None. |
| Secrets/env vars | `AMAZON_CA_SELLER_ID` already cached in gitignored `.env` (5692b95f-…). No new secrets this phase. `SUPABASE_DB_URL*` remain empty (deferred). | None — reuse existing `.env` via `python-dotenv` (already loaded in `tests/conftest.py`). |
| Build artifacts / installed packages | Adding `polars` + `tenacity` updates `uv.lock`. The new `src/habibos/` package needs to be importable (pytest pythonpath / editable install). | `uv add`, `uv lock`, ensure `src/` on pythonpath for tests. |

**Connection blocker (carried from Phase 1, must be resolved before the live acceptance test):** Per the Phase-1 SUMMARY and the live Agent-Central MCP server instructions in this very session ("Seller Central is not connected… Amazon Ads is not connected for this marketplace"), the DataDoe-backed live `exports_*` round-trip may be blocked until the Seller Central + Amazon Ads connections are completed at the DataDoe/agentcentral dashboard. The *code* (parser, trust spine, tests against a fixture) can be built without the live connection; the **live acceptance pull (DATA-05) and TRUST-04 spot-check require the connection live**. The planner must treat the live pull as a `checkpoint:human-verify` gated on connection availability.

## Common Pitfalls

### Pitfall 1: DataDoe premium-export schema drift / column-name mismatch
**What goes wrong:** The export's actual column names/casing differ from the documented set, and Python silently reads `None`/wrong column → wrong or "no data" answer for every SKU.
**Why it happens:** The source-map columns (`docs/datadoe-source-map.md`) were enumerated via `exports_sources_get`, but the *export row* wire format (CSV header names, JSON key casing, percentage as `0.30` vs `30.0`) is only confirmed at the first real pull.
**How to avoid:** Validate the parsed frame against a `pydantic` model of the expected columns; on mismatch, raise (→ Refusal), don't coerce. Capture a real export as a committed fixture and pin the parser to its exact headers. **Confirm the percentage convention** (is `acos` `0.30` or `30.0`?) on the first pull and document it — the threshold compare (`acos_ceiling_pct = 30`) must use the same units.
**Warning signs:** Every SKU shows "no data"; ratios off by 100×; `TACOS ≤ ACOS` guard fires on every row.

### Pitfall 2: TACOS/ACOS unit mismatch in the sanity guard and flag compare
**What goes wrong:** `acos`/`tacos` come back as fractions (0.30) while the ceiling is a percent (30) → the breach flag fires/never-fires incorrectly, and the `TACOS ≤ ACOS` guard is fine (both same units) but the *flag* compare is 100× off.
**Why it happens:** Mixed conventions between the source columns and `thresholds.toml`.
**How to avoid:** Normalize once at parse time to a single documented unit (recommend **percent**, matching `*_ceiling_pct`), assert the convention in a test against the real fixture.
**Warning signs:** Nothing flagged when obvious breaches exist, or everything flagged.

### Pitfall 3: Window math — "trailing-30-day" off-by-one and timezone basis
**What goes wrong:** The `from`/`to` window is computed in the wrong timezone or inclusive/exclusive of today, pulling 29 or 31 days, or crossing the marketplace-local date boundary wrong.
**Why it happens:** The premium source's `date` is **marketplace-local (CA)** per the source map. Computing the window in UTC or system-local can shift the boundary.
**How to avoid:** Compute `to = today (CA-local)`, `from = to - 30 days`, document inclusive/exclusive explicitly, and unit-test the window function. Let the *agent* pass the window to `exports_create`; Python's window helper is for default + override.
**Warning signs:** Row counts/totals that don't reconcile to Seller Central for the window (caught at TRUST-04).

### Pitfall 4: Empty vs failed vs partial export conflated
**What goes wrong:** A `COMPLETED` export with zero rows is treated as "no SKUs have spend" (a number) instead of "no data" (refusal), OR a `FAILED` export is retried forever.
**Why it happens:** Not distinguishing the three terminal cases.
**How to avoid:** tenacity stops on both COMPLETED and FAILED (terminal); the parser then branches: FAILED → `Refusal("failed_export")`; COMPLETED+0 rows → `Refusal("empty_export")` (D-11); COMPLETED+rows → Answer. A SKU *present in the catalog but absent from the rows* is the D-10 per-SKU "no data" sentinel — distinct from a whole-export refusal.
**Warning signs:** An answer that says "all SKUs $0 TACOS"; a poll loop that never terminates on FAILED.

### Pitfall 5: 30-SKU coverage assumption / 2500-row cap (low risk this phase)
**What goes wrong:** Assuming all ~30 CA SKUs appear in the premium export.
**Why it happens:** Premium coverage is schema-confirmed but per-SKU completeness is validated only at the first pull (DATA-05).
**How to avoid:** ~30 SKUs is far under the 2500-row cap, so the cap is **not** a concern here (it's Phase 3's problem). But do reconcile the export's SKU list against the known catalog and render any catalog SKU absent from the export with the D-10 sentinel. **Confirm at first pull** that the export ≠ exactly 2500 rows (would indicate truncation — not expected for 30 SKUs × 30 days unless un-aggregated; aggregate by SKU or accept the daily grain and roll up).
**Warning signs:** Fewer rows than expected; exactly 2500 rows.

## Code Examples

### Parse premium export + classify (the money-logic core)
```python
# src/habibos/tacos.py  — pattern sketch; ratios are READ, never recomputed (D-03)
import polars as pl
from .result import Answer, Refusal, SkuRow
from . import thresholds

PREMIUM_SOURCE = "DataDoe premium Profit by SKU & Date (57a0cb319c)"

def classify(frame: pl.DataFrame, export_id: str, window_from: str, window_to: str,
             catalog_skus: list[str], marketplace: str = "CA") -> Answer | Refusal:
    if frame.height == 0:
        return Refusal("Export returned no rows — no data.", "empty_export", export_id)

    acos_ceiling = thresholds.read("acos_ceiling_pct", marketplace)   # None → refuse flag (D-08)
    tacos_ceiling = thresholds.read("tacos_ceiling_pct", marketplace)

    # Roll daily grain → per-SKU for the window if the source is per-date.
    # (Sum ad_spend/ad_sales/total_sales/profit/total_cost per seller_sku, then the
    #  ratios are still READ per the source's own definition at the rolled grain —
    #  if the source only exposes per-row ratios, prefer pulling an aggregated export
    #  via exports_create groupBy=seller_sku so the SOURCE computes the window ratio.
    #  DECISION FOR PLANNER: prefer server-side groupBy so ratios stay source-computed.)

    present = {r["seller_sku"]: r for r in frame.to_dicts()}
    rows: list[SkuRow] = []
    for sku in catalog_skus:
        r = present.get(sku)
        if r is None:                                    # D-10: show SKU, "no data"
            rows.append(SkuRow(sku, None, None, None, "no data", "no data"))
            continue
        acos, tacos, roi = r["acos"], r["tacos"], r["roi"]
        suspect = tacos is not None and acos is not None and tacos > acos   # D-04
        rows.append(SkuRow(
            seller_sku=sku, acos=acos, tacos=tacos, roi=roi,
            acos_flag=_flag(acos, acos_ceiling),
            tacos_flag=_flag(tacos, tacos_ceiling),
            suspect=suspect,
        ))
    rows.sort(key=lambda x: (x.tacos is None, -(x.tacos or 0)))   # D-05: TACOS desc, no-data last
    return Answer(rows=rows, export_id=export_id, window_from=window_from, window_to=window_to,
                  source=PREMIUM_SOURCE)

def _flag(value: float | None, ceiling: float | None) -> str:
    if ceiling is None:
        return "no threshold set"        # D-08 / TRUST-02 — never a default
    if value is None:
        return "no data"
    return "breach" if value > ceiling else "ok"
```

### tenacity poll primitive (reusable; used if Python ever polls)
```python
# src/habibos/datadoe.py
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_result

TERMINAL = {"COMPLETED", "FAILED"}

def _not_terminal(status: str) -> bool:
    return status not in TERMINAL

@retry(stop=stop_after_attempt(20),
       wait=wait_exponential_jitter(initial=1, max=15),
       retry=retry_if_result(_not_terminal))
def poll_status(get_status) -> str:
    """get_status() -> current export status string; retries until COMPLETED/FAILED."""
    return get_status()
```

### Hermes SKILL.md (skeleton)
```markdown
---
name: tacos-by-sku
description: Answers "what's my TACOS by SKU" (and ACOS/ROI per SKU) for amazon.ca
  from the DataDoe premium Profit-by-SKU source, trailing 30 days, sorted worst-first,
  with provenance and threshold flags. Use when the operator asks about TACOS, ACOS,
  ad cost of sales, or per-SKU advertising efficiency.
metadata:
  version: "1.0"
compatibility: Requires the DataDoe MCP wired into Hermes, Python 3.12+, and uv.
---

# TACOS by SKU

When the operator asks for TACOS / ACOS / ROI by SKU:

1. Call the DataDoe MCP:
   - `exports_create` sourceId=`57a0cb319c`, columns: seller_sku, acos, tacos, roi,
     ad_spend, ad_sales, total_sales, profit, total_cost, currency;
     filters: marketplace CA (A2EUQ1WTGCTBG2), seller = $AMAZON_CA_SELLER_ID;
     from = today−30d, to = today (marketplace-local); groupBy seller_sku; limit 2500.
   - Poll `exports_get(id)` until COMPLETED or FAILED.
   - On COMPLETED, `exports_raw_download` → save the artifact path.
2. Run `scripts/answer_tacos.py --artifact <path> --export-id <id> --marketplace CA`.
3. Render the returned JSON in recommendation voice (SOUL.md): numbers-first, terse,
   all ~30 CA SKUs sorted by TACOS descending. For each ratio show its definition and
   source. Cite the export id. Flag breaches; show "no threshold set" where the flag
   refused; show "no data (not in premium export)" for SKUs the export missed.
4. If the script returns a Refusal (empty/failed export, missing threshold), surface
   the reason verbatim. NEVER invent or substitute a number.
```
> Skill lives at `~/.hermes/skills/tacos-by-sku/`. Validate with `skills-ref validate ./tacos-by-sku` before `hermes skills install`. Body is well under the 500-line / 5000-token recommendation; push the column list / definitions into a `references/` file if it grows. `[CITED: agentskills.io/specification]`

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Architecture doc (`docs/01-architecture.md`) Hetzner server + Agent Central + cron | Hermes Mac desktop app, DataDoe-only, on-demand (no cron) | 2026-06-08 revision header | Ignore the Hetzner/Agent-Central/cron framing in 01-architecture.md; CLAUDE.md + docs/04 win. No scheduling in M1. |
| Thresholds in Supabase `config` table | Thresholds in `config/thresholds.toml` (local), `(key, marketplace)` grain | 2026-06-08 Supabase deferral | Phase 2 reads the TOML; migrates to `config` table in 3.5. The "missing → refuse" rule is unchanged. |
| Margin via `cogs` reconciliation | Margin/ratios direct from premium Profit-by-SKU (ENABLED) | 2026-06-08 (premium confirmed enabled) | `cogs` is fallback/reconciliation (Phase 3.5), not primary. Phase 2 reads premium columns directly. |
| `configparser`/INI | stdlib `tomllib` | Python 3.11 | Native TOML; no third-party parser. |

**Deprecated/outdated:**
- `docs/01-architecture.md` Layers 0/3 (Hetzner host, cron scheduler, Agent Central as a source) — superseded by the doc's own 2026-06-08 revision note and CLAUDE.md. Use it only for the read-only/gated-write *philosophy*, not the infra.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | The premium export delivers `acos`/`tacos`/`roi` as **per-row ratios** that can be rolled to a window via a `groupBy seller_sku` server-side aggregation (so the SOURCE still computes the window ratio, not Python) | Code Examples / Pattern 1 | If the source can't groupBy ratios server-side, a window-level ratio would require Python arithmetic — which collides with D-03. **Resolve at first live pull**: prefer pulling an already-windowed/aggregated export, or accept the per-date grain and have the agent request the source's own windowed columns. Planner must lock this. |
| A2 | Export ratio columns are returned as **percent (e.g. 30.0)**, matching `*_ceiling_pct` | Pitfall 1/2 | Off-by-100× flags. Confirm units at first pull; normalize at parse. |
| A3 | `exports_raw_download` returns a local artifact (path/bytes) Python can read without an HTTP fetch | Standard Stack / Pattern 1 | If only `exports_raw_url_get` (signed URL) is available, a Python httpx fetch is needed — acceptable but adds a network path. Confirm which the MCP exposes. |
| A4 | DataDoe MCP will be wired into Hermes and the Seller-Central/Ads connections completed before the live acceptance test | Environment Availability | Blocks the live DATA-05 pull + TRUST-04 spot-check (not the code/tests). Carried-over Phase-1 checkpoint. |
| A5 | The percentage/units and exact CSV header casing are stable enough to pin a committed fixture | Pitfall 1 | Schema drift would break the parser; pydantic validation + a re-captured fixture mitigates. |
| A6 | `src/` layout will be importable in tests via pytest pythonpath / uv editable | Project Structure | If not configured, tests can't import `habibos.*`. Trivial to fix (`pythonpath = ["src"]`). |

## Open Questions (RESOLVED at first live pull — see Plan 02-03 Task 3)

1. **Server-side ratio aggregation vs Python roll-up (A1 — highest priority).** RESOLVED: confirmed at first live pull per Plan 02-03 Task 3 checkpoint (see 02-03-SUMMARY.md).
   - What we know: source grain is per marketplace × connection × child_asin × sku × **date**; ratios are source-computed columns.
   - What's unclear: whether a 30-day window's per-SKU ratio comes from a `groupBy seller_sku` aggregated export (source computes it) or must be derived. D-03 forbids Python deriving it.
   - Recommendation: **Pull an aggregated export** (`exports_create` with `groupBy seller_sku` + appropriate aggregations / a windowed source variant) so the ratio stays source-computed. The planner should make the `exports_create` arg shape a concrete task and confirm at first pull. If the source only exposes per-date ratios and no server-side windowed ratio, escalate to the operator (it changes whether Phase 2 can honor D-03 without recomputation).

2. **`raw_download` vs `raw_url_get` (A3).** RESOLVED: confirmed at first live pull per Plan 02-03 Task 3 checkpoint (see 02-03-SUMMARY.md).
   - Recommendation: prefer `raw_download`; document the fallback.

3. **Percentage convention (A2).** Confirm at first pull; pin in a test. RESOLVED: confirmed at first live pull per Plan 02-03 Task 3 checkpoint (see 02-03-SUMMARY.md).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | all helpers | ✓ | 3.12.13 | — |
| uv | env/dep mgmt | ✓ | 0.11.19 | — |
| pytest | tests | ✓ | 9.0.3 | — |
| ruff | lint | ✓ | 0.15.16 | — |
| pydantic / structlog / python-dotenv | trust spine | ✓ | 2.13.4 / 26.1.0 / 1.2.2 | — |
| polars | export parse | ✗ (not installed) | — (target 1.41.2) | stdlib `csv` (viable for ~30 rows) |
| tenacity | poll backoff | ✗ (not installed) | — (target 9.1.4) | hand-rolled poll (discouraged) |
| **DataDoe MCP wired into Hermes** | live export pull (DATA-05), acceptance answer | ✗ | — | **none — blocking for the live pull**; code+fixture tests proceed without it |
| **Seller Central + Amazon Ads connection (DataDoe)** | live data returns rows | ✗ (per Phase-1 SUMMARY + this session's MCP notice) | — | **none — blocking for live data**; build against captured fixture meanwhile |
| skills-ref | SKILL.md validation | ? (not verified) | — | manual frontmatter review |

**Missing dependencies with no fallback (blocking the LIVE acceptance test, not the code build):**
- DataDoe MCP not wired into the Hermes CLI/desktop runtime (`servers:` empty).
- Seller Central + Amazon Ads not connected for amazon.ca → live `exports_*` returns no Amazon data.

**Missing dependencies with fallback:**
- `polars`, `tenacity` → `uv add` (one command); stdlib fallbacks exist but the blessed libs are recommended.
- The entire parser + trust spine + unit tests can be built and turned green **against a committed real-export fixture** without the live connection. Only the final live pull + TRUST-04 spot-check are gated on the connection.

## Validation Architecture

> Nyquist validation enabled (`workflow.nyquist_validation: true`). Each success criterion must be provable; money-logic against a **real** export fixture (CLAUDE.md DoD: "runs against a real DataDoe export, not mocked").

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.3 (installed, configured) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths=["tests"]`, `addopts="-ra"`) |
| Quick run command | `uv run pytest -x -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| PROF-01 | Per-SKU ACOS/TACOS/ROI read from premium fixture, labelled w/ source+definition | unit | `uv run pytest tests/test_tacos.py::test_reads_ratios_from_premium -x` | ❌ Wave 0 |
| D-04 | `TACOS ≤ ACOS` sanity guard flags inversions as suspect | unit | `uv run pytest tests/test_tacos.py::test_sanity_guard_flags_inversion -x` | ❌ Wave 0 |
| D-05 | Rows sorted TACOS descending, no-data last | unit | `uv run pytest tests/test_tacos.py::test_sorted_tacos_desc -x` | ❌ Wave 0 |
| D-10 | Catalog SKU absent from export → "no data", never 0/blank | unit | `uv run pytest tests/test_tacos.py::test_missing_sku_no_data -x` | ❌ Wave 0 |
| D-11/TRUST-01 | Empty/failed export → Refusal, not a number | unit | `uv run pytest tests/test_tacos.py::test_empty_export_refuses -x` | ❌ Wave 0 |
| D-07/D-08/TRUST-02 | Breach flagged when ceiling set; "no threshold set" when unset; never a default | unit | `uv run pytest tests/test_thresholds.py -x` | ❌ Wave 0 |
| TRUST-03/D-12 | Every external call emits start+end structured events w/ source id, rows, bytes, ms, status | unit | `uv run pytest tests/test_logging.py::test_one_event_in_one_out -x` | ❌ Wave 0 |
| A2 (units) | acos/tacos percentage convention pinned to the real fixture | unit | `uv run pytest tests/test_tacos.py::test_ratio_units -x` | ❌ Wave 0 |
| DATA-05 (live) | Real export pull create→poll→download against live DataDoe | manual / live | operator runs the skill once connection is live | manual-only |
| TRUST-04 | Answer's per-SKU TACOS matches Seller Central / Campaign Manager for the window | manual | `checkpoint:human-verify` | manual-only |

### Sampling Rate
- **Per task commit:** `uv run pytest -x -q`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** full suite green + the live pull + TRUST-04 sign-off before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/fixtures/profit_by_sku_30d.csv` — a **real** captured premium export (the DoD requires non-mocked data; capture it at the first live pull and commit, sanitizing only if a column is sensitive). Until captured, money-logic tests cannot meet the "real export" DoD — flag as the gating Wave-0 artifact.
- [ ] `tests/test_tacos.py` — covers PROF-01, D-04, D-05, D-10, D-11, A2
- [ ] `tests/test_thresholds.py` — covers D-07/D-08/TRUST-02
- [ ] `tests/test_logging.py` — covers TRUST-03/D-12
- [ ] `src/` on pytest pythonpath (add `pythonpath = ["src"]` to `[tool.pytest.ini_options]`)
- [ ] Library install: `uv add polars==1.41.2 tenacity==9.1.4`

> **Real-fixture chicken-and-egg:** the DoD wants a real export, but the live connection is gated (Environment Availability). Recommended Wave-0 sequencing: build the parser + trust-spine + tests against a **small hand-constructed CSV that mirrors the documented premium columns** to get red→green, then **re-point the fixture to the captured real export** the moment the live pull succeeds, and re-run. The planner should make "capture + commit the real fixture" an explicit task gated on connection, and mark the synthetic CSV as a temporary scaffold to be replaced (not the final DoD artifact).

## Project Constraints (from CLAUDE.md)

- **Data layer READ-ONLY; no write path to Amazon** — Phase 2 only reads via the DataDoe MCP. (Hard rules 1–3.)
- **Money-touching logic hand-written + reviewed + pytest'd against real export fixtures** — the sanity guard, flagging, window math, and refusal classification are hand-written and tested; ratios are read, not computed (D-03). (Hard rule 4 + DoD.)
- **Secrets in `.env`, never in code** — reuse `AMAZON_CA_SELLER_ID`; the seller UUID must not appear in `src/`/`tests/` (enforced by `tests/test_env.py`). (Hard rule 5.)
- **Every external call wrapped + logged** — `logged_call` structlog wrapper, one event in/out. (Hard rule 6 / TRUST-03.)
- **Never invent thresholds** — read from `config/thresholds.toml`; missing → refuse. (Operating principle / TRUST-02 / SOUL.md.)
- **Skills are agentskills.io SKILL.md; live in `~/.hermes/skills/`; body < 500 lines / ~5000 tokens; validate with `skills-ref`.**
- **Use uv + ruff; pin versions; `uv lock`.**
- **What NOT to use:** SP-API/Ads clients, a hand-rolled DataDoe HTTP client, Supabase dashboard click-ops, psycopg2, unpinned pandas, hardcoded thresholds, auto-generated money skills, clock-cron assumptions.
- **DoD per skill:** runs end-to-end against a real DataDoe export; (persistence to Supabase **deferred to 3.5**); surfaces in the desktop workspace; ships a one-paragraph skill doc.

## Security Domain

> `security_enforcement` not present in config → treat as enabled. Phase 2 is a read-only data-answer slice; the threat surface is small but real (secret handling, fabrication, log hygiene).

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No user auth surface; MCP auth handled by Hermes. |
| V3 Session Management | no | — |
| V4 Access Control | no | Single-operator local app; data layer read-only by construction. |
| V5 Input Validation | yes | pydantic-validate the export rows before they touch the answer; tomllib for config. |
| V6 Cryptography | no (don't hand-roll) | No crypto in scope; never hand-roll. |
| V7 Error Handling & Logging | yes | structlog JSON; **do not log secrets** (no seller UUID, no creds in `logs/external-calls.jsonl`); refusals are typed, not swallowed. |
| V8 Data Protection | yes | Secrets only in gitignored `.env`; `logs/` gitignored; no PII persisted (D-01 no persistence). |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Fabricated number on no-data (the core project threat) | Tampering / Repudiation | Typed `Refusal`; no-data sentinels; never substitute (D-08/D-10/D-11); SOUL.md forbids invented figures. |
| Seller UUID / secret leaking into source or logs | Information Disclosure | `.env` only (enforced by `test_env.py`); never log the UUID or creds; `logs/` gitignored. |
| DataDoe schema drift silently producing wrong answers | Tampering | pydantic validation → Refusal on mismatch; pinned real fixture. |
| Skill claiming an action ("I changed the bid") | Repudiation / Spoofing | Recommendation-voice only (SOUL.md); no write path exists; this slice only reports. |
| Unbounded poll loop on a FAILED export (resource) | Denial of Service | tenacity max-attempts + terminal on COMPLETED/FAILED. |

## Sources

### Primary (HIGH confidence)
- `agentskills.io/specification` — SKILL.md frontmatter (name ≤64, description ≤1024, compatibility ≤500, metadata, allowed-tools), directory structure, progressive disclosure (<5000 tokens / <500 lines), `skills-ref validate`. `[CITED]`
- `pypi.org/pypi/polars/json` — polars 1.41.2, requires-python ≥3.10. `[VERIFIED]`
- `pypi.org/pypi/tenacity/json` — tenacity 9.1.4 (2026-02-07), requires-python ≥3.10. `[VERIFIED]`
- Project docs (authoritative for constraints): `docs/datadoe-source-map.md` (premium source `57a0cb319c` ENABLED, verbatim acos/tacos/roi/total_cost definitions, marketplace-local date, read-only confirmation, column set), `docs/04-data-tools-reference.md` (MCP call order), `CLAUDE.md` (hard rules + stack pins), `.planning/ROADMAP.md` (Supabase deferral / live-only boundary), `.planning/REQUIREMENTS.md` (DATA-05/PROF-01/02/TRUST-01..04), `.planning/phases/02-…/02-CONTEXT.md` (D-01..D-12), `.hermes-context/SOUL.md` (recommendation voice, never-invent), `config/thresholds.toml`, `pyproject.toml`, `tests/conftest.py`/`test_env.py`/`test_config_seed.py`/`test_context.py`, `01-01-SUMMARY.md` (MCP not wired; connections pending). `[VERIFIED: read this session]`
- Local environment probes: `uv pip list` (polars/tenacity ABSENT; httpx/pydantic/structlog present), `python3 --version` (3.12.13), `uv --version` (0.11.19). `[VERIFIED]`

### Secondary (MEDIUM confidence)
- WebSearch on agentskills.io SKILL.md format — corroborated by the primary `agentskills.io/specification` fetch.

### Tertiary (LOW confidence)
- Live DataDoe export *wire format* (CSV header casing, percentage convention, server-side ratio-groupby availability) — **not verified this session** (connection not live). Flagged in Assumptions Log A1–A3 / Open Questions — resolve at first real pull.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — pins from CLAUDE.md cross-verified against PyPI; install state probed locally.
- Architecture / trust-spine patterns: HIGH — derived from locked decisions (D-01..D-12) + CLAUDE.md + SOUL.md; the seam (agent-calls-MCP, Python-handles-artifact) is explicit project doctrine.
- SKILL.md authoring: HIGH — official agentskills.io spec fetched.
- DataDoe export *runtime* shape (column casing, units, server-side ratio aggregation): MEDIUM — schema known from the empirical source map, but wire format / groupby behavior pending first live pull (A1–A3).
- Pitfalls: HIGH — grounded in the source map's documented mixed-attribution-window + marketplace-local-date facts and the locked anti-fabrication edges.

**Research date:** 2026-06-09
**Valid until:** 2026-07-09 (stable — project-pinned stack; re-verify only if the DataDoe export wire format surfaces differently at the first live pull, which resolves A1–A3).
