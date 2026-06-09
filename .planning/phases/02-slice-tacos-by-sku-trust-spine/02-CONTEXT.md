# Phase 2: Slice — TACOS by SKU (+ trust spine) - Context

**Gathered:** 2026-06-09
**Status:** Ready for planning

<domain>
## Phase Boundary

From the Hermes desktop workspace, the operator asks "what's my TACOS by SKU" and gets
correct, provenance-cited ACOS/TACOS/ROI per SKU against **live** DataDoe data. In
delivering this first acceptance answer, Phase 2 also builds the reusable substrate every
later slice depends on: the DataDoe export wrapper and the anti-fabrication **trust spine**
(provenance citation, refusal on no-data, every external call wrapped + logged).

**Live-only boundary (Supabase deferred to Phase 3.5):** `metric_snapshots` persistence,
`cogs` FX-reconciliation, and `decision_ledger` are NOT built here. This slice answers
directly from the live DataDoe premium Profit-by-SKU source; thresholds come from
`config/thresholds.toml`. No write path to Amazon exists in this phase.
</domain>

<decisions>
## Implementation Decisions

### Slice scope (live-only)
- **D-01:** Pure pass-through — each question pulls a fresh DataDoe export, parsed in
  memory, with **no local persistence or caching** of export artifacts. Re-asking re-pulls.
  This confirms the ROADMAP Supabase-deferral note: persistence is Phase 3.5's job, not a
  half-built cache here.
- **D-02:** The reusable substrate built in this slice = (a) a DataDoe export wrapper
  handling the create → poll → download cycle with retry/backoff (terminal on
  COMPLETED/FAILED), (b) structlog-wrapped logging on every external call, and (c) the
  anti-fabrication trust spine (provenance, refusal). Built once here, reused by Phases 3–5.

### Margin / ratio source
- **D-03:** ACOS, TACOS, ROI, and profit are read **directly** from the premium
  `amazon_profit_by_sku_and_date` source (`57a0cb319c`, confirmed ENABLED) — never
  hand-rolled in skill prose. Definitions are surfaced **verbatim** from the source map:
  `acos` = ad_spend ÷ 14-day ad-sales; `tacos` = ad_spend ÷ total_sales; `roi` = profit ÷
  total_cost.
- **D-04:** Sanity guard — for the same SKU, `TACOS ≤ ACOS` must hold (total_sales ≥
  ad_sales). A row violating it is flagged as suspect / refused for that row, not displayed
  as if correct.

### Answer shape
- **D-05:** Default view = **all ~30 CA SKUs, sorted by TACOS descending** (worst first, so
  attention goes to the costliest SKUs), over a **trailing-30-day** window. The operator can
  request a different window on any ask.
- **D-06:** Each row shows ACOS, TACOS, ROI, each labelled with its definition and its
  source (DataDoe premium Profit-by-SKU). The answer cites provenance = the DataDoe export
  id it was computed from.

### Thresholds & flagging
- **D-07:** The answer **reports the numbers AND flags** SKUs breaching `acos_ceiling_pct` /
  `tacos_ceiling_pct` read from `config/thresholds.toml` (`(key, marketplace)` grain, CA).
- **D-08:** Missing ceiling → the flag column **refuses** for that ratio ("no threshold
  set"), never guesses. The numeric report still renders fully — the numbers themselves do
  not depend on any threshold; only the flag does.
- **D-09:** Operator delegated PPC ceiling-setting to the advisor (non-expert in
  advertising). **Recommended starting seeds** to write into `config/thresholds.toml`:
  `acos_ceiling_pct = 30`, `tacos_ceiling_pct = 15`. Rationale: 30% is a conservative
  catalog-wide break-even-ACOS proxy for a food/sweets catalog; 15% TACOS is a common
  healthy band for an established (non-launch) catalog. These are **operator-adopted
  recommendations, not runtime-invented values** — to be TUNED after the first real
  TACOS-by-SKU answer reveals the actual distribution, and eventually set to true per-SKU
  break-even once Profit/`cogs` margins reconcile in Phase 3.5.

### Trust-spine edges
- **D-10:** A SKU missing from the premium export → **show the SKU** with ACOS/TACOS/ROI =
  "no data (not in premium export)" — never 0 or blank. This distinguishes "not covered"
  from "no spend." (No `cogs` fallback exists until 3.5.)
- **D-11:** A whole export that is empty or failed → **refuse** ("no data") rather than
  substitute any number (locked TRUST-01).
- **D-12:** Every DataDoe call is wrapped and logged via structlog to a **local structured
  log file** (the `decision_ledger` is deferred to 3.5): log source id, filters, row count,
  byte size, duration, and status — one event in, one event out.

### Claude's Discretion
- Exact Python package/module layout and the Hermes `SKILL.md` structure.
- Export parsing approach (polars vs stdlib) and trailing-window date math.
- Local log file path and format; typographic rendering of "no data" and flag cells.
</decisions>

<specifics>
## Specific Ideas

- Operator: "i am not an expert on advertisement so your help is needed here." → Keep PPC
  threshold guidance in plain language and explicitly tunable; surface recommendations with
  their reasoning, never as opaque numbers.
- The answer is in **recommendation voice** (numbers-first, terse) per SOUL.md — it reports
  and flags; it never claims to have changed anything on Amazon.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope & requirements
- `.planning/ROADMAP.md` — Phase 2 section + the "Supabase deferral" note (live-only
  boundary, what moves to Phase 3.5).
- `.planning/REQUIREMENTS.md` — DATA-05, PROF-01, PROF-02, TRUST-01, TRUST-02, TRUST-03,
  TRUST-04.

### DataDoe contract (authoritative, empirical)
- `docs/datadoe-source-map.md` — source ids, columns, **verbatim** acos/tacos/roi
  definitions, premium Profit-by-SKU enablement, read-only confirmation, 2500-row cap notes.
- `docs/04-data-tools-reference.md` — DataDoe MCP tool call pattern and order
  (exports_create → exports_get poll → exports_raw_download / exports_raw_url_get).

### Architecture & rules
- `docs/01-architecture.md` — system architecture.
- `config/thresholds.toml` — interim threshold home (`(key, marketplace)` grain); the file
  to seed with D-09 values.
- `CLAUDE.md` — hard rules: data layer read-only, no autonomous writes, money-touching math
  hand-written + reviewed, secrets in `.env`, every external call wrapped + logged.
- `.hermes-context/SOUL.md` — operator persona: numbers-first, terse, recommends-never-acts,
  never invents pricing/thresholds.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `config/thresholds.toml` — the threshold reader's target file (currently empty values;
  D-09 seeds it).
- `tests/` — pytest harness already scaffolded (`conftest.py`, `test_config_seed.py`,
  `test_env.py`, `test_schema.py`, `test_context.py`). New money-touching primitives must be
  unit-tested here against real export fixtures.
- `.env` — `AMAZON_CA_SELLER_ID` already cached (5692b95f-…); never re-resolve.

### Established Patterns
- **No Python source package exists yet** — Phase 2 creates the first runtime modules
  (DataDoe wrapper, ratio/answer logic, threshold reader, logging). `pyproject.toml` + `uv`
  environment are in place; stack libs per CLAUDE.md are tenacity (poll-loop backoff),
  structlog (wrapped logging), pydantic (export-row validation), polars (parse/aggregate).
- Money-touching logic is hand-written + reviewed + pytest-covered, never auto-generated.

### Integration Points
- DataDoe MCP tools (`exports_create`, `exports_get`, `exports_raw_download` /
  `exports_raw_url_get`) — the only Amazon data source.
- Hermes desktop workspace surfaces the answer (skill under `~/.hermes/skills/`).
- Supabase is **NOT** integrated this phase (deferred to 3.5).
</code_context>

<deferred>
## Deferred Ideas

- `metric_snapshots` persistence, `cogs` FX-reconciliation, `decision_ledger`, and the
  `config`-table migration (from `thresholds.toml`) → **Phase 3.5** (Supabase truth store).
- Per-SKU **break-even** ACOS ceiling (needs reconciled per-SKU margin) → revisit at 3.5.
- Wasted-spend ranking and deeper threshold-based flagging → **Phase 3**.

</deferred>

---

*Phase: 02-slice-tacos-by-sku-trust-spine*
*Context gathered: 2026-06-09*
