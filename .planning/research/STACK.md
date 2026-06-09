# Stack Research

**Domain:** AI-first, read-only Amazon FBA PPC/profit analytics workspace built on the Hermes Mac desktop app (agent skills + MCP), DataDoe as the single Amazon data source, Supabase (Postgres + pgvector) as numeric truth.
**Researched:** 2026-06-08
**Confidence:** MEDIUM-HIGH overall. Python data/Supabase stack is HIGH (PyPI + Context7 + official docs verified). Hermes desktop-app internals (paths, cron, MCP config) are MEDIUM — verified against current Nous Research docs but the desktop app is a ~6-day-old public preview (v0.15.2, announced 2026-06-02), so exact behaviors may shift. DataDoe's MCP/API surface is LOW-MEDIUM public confidence — it is a connected, authenticated MCP in this environment but has little public documentation; treat its tool list as ground truth from the live connection, not from web sources.

---

## The three things this stack must do (and the one-line answer for each)

1. **Author Hermes desktop skills + wire MCP + scheduling** → Skills are `SKILL.md` files in agentskills.io format under `~/.hermes/skills/<name>/`; MCP servers live in `~/.hermes/config.yaml` (managed via `hermes mcp add`); scheduling is `hermes cron`, but it runs **only while the Hermes gateway daemon is alive** — on a Mac that means the machine is awake. Milestone 1 is conversational/on-demand, so cron is optional here.
2. **Call DataDoe robustly from Python** → In this architecture the **agent calls the DataDoe MCP tools directly** (`sellers_and_vendors_list → exports_sources_get → exports_create → exports_get poll → exports_raw_download`). The **Python layer's job is the export-handling helper**: parse the downloaded CSV/JSON, validate, reconcile into Supabase, with `httpx` + `tenacity` for any direct HTTP polling and `structlog` wrapping every call. Do **not** build a parallel SP-API/REST client.
3. **Supabase Postgres + pgvector from Python** → Two clients for two jobs: **`supabase` (supabase-py) async client** for app-style reads/writes through PostgREST, and **direct Postgres (`psycopg[binary]` 3.x or `asyncpg`) + SQLAlchemy 2.0 + Alembic** for the analytics/migration work (schema, COGS reconciliation, snapshot upserts). `pgvector` Python adapter for the embedding columns. Migrations as versioned SQL via Alembic — **not** click-ops in the Supabase dashboard.

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | 3.11+ (3.12 sweet spot) | All helpers, reconciliation, money logic | Project standard. 3.11+ unlocks `tomllib`, better asyncio, and is the floor for `psycopg` 3.3, `tenacity` 9, `structlog` 26. Avoid 3.13+ only if a transitive dep lags; 3.12 is the safe target. |
| **Hermes Agent / Desktop** | Agent v0.15.2 (Desktop public preview, 2026-06-02) | The runtime/workspace surface; hosts skills, MCP, memory under `~/.hermes` | This is a fixed project decision, not a choice. Desktop is "the same agent core as CLI + gateway — same config, keys, sessions, skills, memory." **Pin the version** (CLAUDE.md hygiene rule) since it is a fast-moving preview. |
| **agentskills.io SKILL.md format** | Current spec (frontmatter: `name`, `description` required) | Skill authoring format | This is the format Hermes consumes. Stable, simple spec: YAML frontmatter + Markdown body, progressive disclosure via `references/`, `scripts/`, `assets/`. |
| **DataDoe MCP** | (live connected MCP) | Single read-only Amazon data source | Project-locked. Accessed as MCP tools by the agent; Python only handles the downloaded export artifacts. **No write capability exists — do not design one.** |
| **Supabase (Postgres 15+ + pgvector)** | Managed | Numeric source of truth, decision ledger, vector recall | Project-locked. Postgres gives correct money math + transactions; pgvector gives semantic recall over notes/decisions without a second datastore. |
| **Anthropic API** | Sonnet (routine) / Opus (planning/review) | Model provider for the agent | Project-locked, metered. Configured inside Hermes, not in Python helpers. |

### Supporting Libraries (Python)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **supabase** (supabase-py) | 2.31.0 (2026-06-04) | Async/sync Supabase client (PostgREST, auth, storage, realtime) | App-style table reads/writes and any future realtime. Use `create_async_client` / `AsyncClient` for async helpers. Good for "insert this snapshot row," less ideal for bulk analytics. |
| **SQLAlchemy** | 2.0.50 | ORM + Core for the truth-store schema and analytics queries | The reconciliation/margin work (joins of COGS × DataDoe exports, upserts to `metric_snapshots`). 2.0 async engine pairs with asyncpg/psycopg3. |
| **Alembic** | 1.18.4 | Versioned, reviewable DB migrations | Every schema change to `sku_master`, `cogs`, `metric_snapshots`, `decision_ledger`, `config`. Migrations are code-reviewed artifacts — non-negotiable given the "money logic is reviewed" rule. |
| **psycopg[binary]** | 3.3.4 | Direct Postgres driver (sync + async) | Default direct-connection driver. Modern, supports async, server-side cursors, COPY for bulk loads. Use the `[binary]` extra to avoid local libpq build pain on macOS. |
| **asyncpg** | 0.31.0 | Fastest async Postgres driver | Only if you go fully async + need throughput on bulk export loads. Otherwise psycopg3 async is simpler and one driver covers both modes. |
| **pgvector** | 0.4.2 | Python adapter for pgvector columns | Registering/operating vector columns from SQLAlchemy/psycopg for semantic recall over notes/decisions. |
| **httpx** | 0.28.1 | Async-capable HTTP client | Any direct HTTP (export-URL downloads via `exports_raw_url_get`, Tavily, future webhooks). Connection pooling + timeouts + HTTP/2. |
| **tenacity** | 9.1.4 | Retry/backoff decorator | Wrapping the **poll loop** (`exports_get` until COMPLETED/FAILED) and any flaky external call with exponential backoff + jitter + max attempts. Satisfies the "robust with retry" requirement. |
| **structlog** | 26.1.0 | Structured (JSON) logging | The "every external call wrapped and logged" rule. Emit one structured event per DataDoe export and per Supabase write (source, rows, duration, status). Pipe to a file under the project, mirror key events to `decision_ledger`. |
| **pydantic** | 2.13.4 | Schema validation of export rows + config | Validate DataDoe export columns and `config` thresholds before they touch money math. Catches DataDoe schema drift early. |
| **polars** | 1.41.2 | Fast dataframe for export transforms | Parsing/aggregating downloaded CSV/JSON exports (≤2500-row cap, but joins across sources add up). Lighter and faster than pandas for this; lazy API helps. |
| **python-dotenv** | 1.2.2 | Load `.env` | Secrets in env (CLAUDE.md rule): `AMAZON_CA_SELLER_ID`, Supabase keys, Anthropic key, DataDoe creds. Never committed. |
| **mcp** (Python SDK) | 1.27.2 | Model Context Protocol SDK | Only if you later build a **custom MCP** (e.g., a Supabase-truth MCP, or the deferred gated write-MCP). Not needed for Milestone 1. |

### Development Tools

| Tool | Purpose | Notes |
|------|---------|-------|
| **uv** | Python env + dependency manager | Fast, reproducible installs; `uv lock` pins exact versions. Preferred over bare pip/venv for a single-operator box. |
| **ruff** | Lint + format | One tool, fast, replaces flake8+isort+black. |
| **skills-ref** (`skills-ref validate ./my-skill`) | Validate SKILL.md before install | Catches frontmatter/naming errors before `hermes skills install`. From the agentskills repo. |
| **hermes CLI** | `hermes mcp`, `hermes skills`, `hermes cron`, `hermes gateway` | The desktop app and CLI share one agent core; use the CLI for scriptable setup, config inspection, and gateway/cron management. |
| **pytest** | Test the money-touching primitives | Margin/ACOS/TACOS math is hand-written and reviewed → it must be unit-tested against real export fixtures. |

---

## How each of the three requirements maps to the stack

### 1. Hermes desktop skills, MCP wiring, scheduling

**Skill authoring (agentskills.io format).** A skill is a directory whose name matches its frontmatter `name` (lowercase, hyphens, ≤64 chars), containing `SKILL.md`:

- Required frontmatter: `name`, `description` (≤1024 chars — describe *what it does and when to use it*, with keywords so the agent picks it).
- Optional: `license`, `compatibility` (≤500 chars, e.g. "Requires Python 3.11+"), `metadata` (e.g. `version`), `allowed-tools` (experimental — space-separated pre-approved tools).
- Body: Markdown, **keep under 500 lines / ~5000 tokens**. Push detail into `references/*.md`, executable code into `scripts/`, templates into `assets/`. Reference with relative paths, one level deep.
- Progressive disclosure: only `name`+`description` load at startup; full body loads on activation; `references/`/`scripts/` load on demand. Structure skills to exploit this (thin SKILL.md, fat references).
- **Where they live:** `~/.hermes/skills/<name>/` (`HERMES_HOME` = `~/.hermes` on macOS). User-created, hub-installed, and bundled skills all live here; manage with `hermes skills install|list|inspect|uninstall`. Single-file `SKILL.md` install from a URL is supported.
- Validate with `skills-ref validate ./<skill>` before installing.

**MCP wiring.** MCP servers are registered with `hermes mcp add <name> [--url URL | --command CMD --args ...] [--auth oauth|header]`; `hermes mcp list`, `hermes mcp test <name>` to verify. Config persists in `~/.hermes/config.yaml`. In this project DataDoe, Supabase, Gmail/Drive/Calendar, and Tavily are already authenticated MCPs — confirm each with `hermes mcp test` on first run. The desktop app surfaces an "MCP servers" settings pane over the same config.

**Scheduling — the load-bearing caveat.** `hermes cron <list|create|edit|pause|resume|run|remove|status|tick>` schedules prompt+skill jobs. **But cron is driven by the Hermes gateway daemon, which ticks every ~60s; without a running gateway, jobs do not fire** — true for CLI, desktop, and dashboard alike. On a Mac desktop that means *the machine must be awake and the gateway running*. To approximate "always-on" you can `hermes gateway install` (background service) on an always-awake Mac. **This exactly matches the CLAUDE.md constraint: Milestone 1 is conversational/on-demand, so do not depend on clock-cron.** When later milestones need scheduling, the options are (a) an always-on Mac with the gateway installed, or (b) on-open / on-demand triggering (`hermes cron run` / `tick`, or a "run my morning briefing" skill the operator invokes). Confirm the desktop preview actually exposes the cron pane and a persistent gateway before relying on it.

### 2. Calling DataDoe robustly from Python

**Architecture note (important):** DataDoe is consumed as an **MCP** by the Hermes agent. The canonical call sequence (`sellers_and_vendors_list → exports_sources_get → exports_create → exports_get` poll → `exports_raw_download` / `exports_raw_url_get`) is executed as **agent tool calls**, not as a hand-rolled Python REST client. Your Python helpers sit *downstream*: they receive/parse the downloaded export artifact and reconcile it into Supabase.

The robust Python helper therefore needs:
- **`tenacity`** around any polling or download retry — exponential backoff + jitter, cap attempts, stop on terminal `FAILED`/`COMPLETED`. (The poll loop is the part most likely to be flaky.)
- **`httpx`** if/when you fetch `exports_raw_url_get` signed URLs directly (timeouts + pooling).
- **`pydantic`** to validate the export's columns against the expected schema for that `sourceId` (DataDoe schema drift is a real risk — see PITFALLS) *before* any money math runs.
- **`polars`** (or pandas) to parse and aggregate, respecting the **2500-row export cap** (paginate via `skip` / date windows when a query would exceed it).
- **`structlog`** wrapping every export: log `sourceId`, filters, row count, byte size, duration, status — one event in, one event out. Mirror material results into `metric_snapshots` and the run into the decision/run record.
- Cache `AMAZON_CA_SELLER_ID` (`5692b95f-f3f0-4063-9c1c-40177c54f408`) in `.env` so step 1 isn't repeated.

**Do not** build an SP-API or Amazon Ads API client of any kind. There is no write path and none may be assumed (CLAUDE.md hard rule 1 & 2).

### 3. Supabase Postgres + pgvector from Python

Use **two clients for two distinct jobs** — this is the prescriptive call:

- **Truth-store schema, migrations, money math → direct Postgres.** Use **SQLAlchemy 2.0 + Alembic** over **psycopg 3 (`psycopg[binary]`)**. This is where `sku_master`, `cogs`, `metric_snapshots`, `decision_ledger`, `config` get defined and where COGS×export reconciliation happens. Transactions and reviewable SQL migrations matter for money correctness. Connect via the Supabase connection string (use the **pooled/transaction-pooler** connection for short-lived helper runs; direct connection for migrations). Register pgvector types via the **`pgvector`** adapter.
  - Async variant: SQLAlchemy 2.0 async engine + **asyncpg** *or* psycopg3 async. Default to **psycopg3** (one driver, sync+async, simpler) unless you measure a throughput need.
- **App-style row reads/writes, future realtime → `supabase` (supabase-py) 2.31.0.** Async via `create_async_client` / `AsyncClient`. Use it for ergonomic single-row inserts (e.g., appending a `decision_ledger` entry from a skill) and any future realtime/storage needs. PostgREST under the hood; not the tool for bulk analytics.
- **Migrations discipline:** all DDL through **Alembic** versioned scripts checked into git — **never** click-ops in the Supabase dashboard (un-reviewable, un-reproducible, breaks the "money logic is reviewed" principle). Enable the `vector` extension in an early migration.

---

## Installation

```bash
# Environment (preferred: uv)
uv init && uv python pin 3.12

# Core helper + Supabase truth store
uv add supabase==2.31.0 \
       sqlalchemy==2.0.50 \
       alembic==1.18.4 \
       "psycopg[binary]==3.3.4" \
       pgvector==0.4.2

# DataDoe export handling + robustness + logging
uv add httpx==0.28.1 \
       tenacity==9.1.4 \
       structlog==26.1.0 \
       pydantic==2.13.4 \
       polars==1.41.2 \
       python-dotenv==1.2.2

# Optional: fully-async bulk loads, or a future custom MCP
uv add asyncpg==0.31.0          # only if async throughput demands it
uv add mcp==1.27.2              # only if/when building a custom MCP (deferred)

# Dev
uv add --dev ruff pytest

# Hermes / skills (CLI side; the desktop app shares this config)
hermes mcp list                 # confirm DataDoe, Supabase, Gmail, Tavily are connected
hermes mcp test datadoe
# skills-ref for SKILL.md validation:
#   git clone https://github.com/agentskills/agentskills && use skills-ref/
```

---

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative |
|-------------|-------------|-------------------------|
| psycopg 3 (direct) + SQLAlchemy + Alembic for truth store | supabase-py for *everything* | Fine for tiny apps with only single-row CRUD. Here, reconciliation/joins/migrations need real SQL + transactions → keep supabase-py for app-style writes only. |
| psycopg 3 | asyncpg | asyncpg is faster and a great fit if you commit to fully-async helpers and have measurable bulk-load throughput needs. psycopg3 wins on "one driver, sync+async, simpler ops." |
| polars | pandas 3.0.3 | pandas if you have an existing pandas-heavy codebase or need a niche pandas-only library. For fresh export transforms, polars is faster/leaner. |
| Alembic migrations | Supabase CLI migrations / dashboard | Supabase CLI migrations are reasonable if you standardize on the Supabase toolchain end-to-end; but Alembic keeps schema + Python in one reviewable, git-tracked place, which suits the "reviewed money logic" rule. Do **not** use the dashboard GUI for schema. |
| `hermes cron` (gateway) | macOS `launchd` / system `cron` invoking `hermes` | If you need a trigger that survives without the gateway pane, a `launchd` job (on an awake Mac) calling a Hermes skill via CLI is a fallback. Still requires the Mac awake. |
| tenacity | hand-rolled retry loops | Hand-rolled is acceptable only for trivial one-shot calls; tenacity standardizes backoff/jitter/caps across every external call and is self-documenting. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **Any Amazon SP-API / Amazon Ads API client (python-amazon-sp-api, etc.)** | Structurally forbidden — there is no write path and the data layer is read-only (CLAUDE.md hard rules 1–3). Even read-only direct SP-API reintroduces the abuse vector the architecture was built to eliminate. | DataDoe MCP only. |
| **A hand-rolled DataDoe REST client duplicating the MCP** | The agent already has the DataDoe MCP; a parallel HTTP client is unmaintained surface area and risks drifting from the MCP's auth/contract. | Let the agent call the MCP; Python handles the downloaded artifact. |
| **Supabase dashboard click-ops for schema** | Un-reviewable, un-reproducible, no git history — violates the reviewed-money-logic principle. | Alembic migrations in git. |
| **Service-role Supabase key in skills/helpers that don't need it** | Over-broad secret; a leak is catastrophic. | Scope to least privilege; secrets in `.env`; prefer RLS + anon/limited keys where possible. |
| **Clock-cron assumptions for Milestone 1** | Desktop gateway only ticks while the Mac is awake + gateway running; assuming unattended cron will silently miss jobs. | On-demand / on-open triggering now; revisit always-on Mac + `hermes gateway install` later. |
| **psycopg2 (legacy)** | Old sync-only driver, weaker async story, more build friction on macOS. | psycopg 3 (`psycopg[binary]`). |
| **pandas 2.x / unpinned pandas** | pandas 3.0 has breaking changes; unpinned installs drift. For export transforms polars is leaner anyway. | polars (pinned), or pandas pinned to 3.0.x if needed. |
| **Auto-generated money-touching skills** | CLAUDE.md: margin/ACOS/TACOS/threshold logic is hand-written + reviewed + tested. | Hand-write + pytest against real export fixtures; let Hermes auto-generate only low-stakes formatting. |
| **Hardcoded thresholds in prompts/skills** | Operating principle: never invent thresholds; read from Supabase `config`. | `config` table, validated with pydantic, read at runtime. |

---

## Stack Patterns by Variant

**If Milestone 1 (conversational, read-only PPC/profit Q&A):**
- Skills + DataDoe MCP + Supabase truth store + the helper libs above. **No cron, no realtime, no mcp SDK.** Keep it synchronous (psycopg3 sync) unless you hit a wall — simpler to reason about and test.
- Because the value is correct answers on demand with zero write surface; async/scheduling are unnecessary complexity here.

**If later you need scheduled briefings (M3):**
- Add `hermes gateway install` on an always-awake Mac (or accept on-open triggering), define `hermes cron` jobs that invoke hand-written skills.
- Because scheduling only works while the gateway is alive; design around the Mac's wake state explicitly.

**If you build the gated write-MCP (deferred milestone):**
- Add the `mcp` Python SDK to author a **custom, human-gated** MCP; enforce one-time approval tokens and log every call to `decision_ledger`.
- Because the only sanctioned write path is an explicit, approved, logged MCP — never an ad-hoc API client.

---

## Version Compatibility

| Package A | Compatible With | Notes |
|-----------|-----------------|-------|
| psycopg 3.3.4 | Python ≥3.10, Postgres 12–16 | `[binary]` extra avoids local libpq build on macOS. |
| SQLAlchemy 2.0.50 | psycopg3 (sync+async), asyncpg | Use 2.0-style `select()` / async engine; not legacy 1.4 patterns. |
| Alembic 1.18.4 | SQLAlchemy 2.0 | Autogenerate works with the 2.0 metadata API. |
| pgvector 0.4.2 | psycopg3, SQLAlchemy, asyncpg | Enable `vector` extension in an Alembic migration before using vector columns. |
| supabase 2.31.0 | Python ≥3.9 | Async via `create_async_client` / `AsyncClient`; HTTP/2 used automatically when available. |
| tenacity 9.1.4 / structlog 26.1.0 | Python ≥3.10 | Reinforces the Python 3.11+ floor. |
| polars 1.41.2 | Python ≥3.10 | pandas 3.0.3 needs ≥3.11 — another reason to target 3.12. |
| mcp 1.27.2 | Python ≥3.10 | Only needed for a custom MCP. |
| Hermes Desktop (v0.15.2 core) | macOS; `~/.hermes` (`HERMES_HOME`) | Pin the version; preview is fast-moving. Cron needs the gateway daemon running. |

---

## Open / Lower-Confidence Items (flag for validation)

- **Hermes desktop preview specifics (MEDIUM):** exact presence of the Cron and MCP-servers panes, whether `hermes gateway install` runs cleanly as a macOS background service, and the precise `~/.hermes` layout (`config.yaml`, `skills/`, `logs/desktop.log`) are from current Nous docs but the app is ~6 days into public preview. **Verify empirically on first run** (`hermes mcp list`, `hermes skills list`, `hermes cron status`).
- **DataDoe MCP contract (LOW-MEDIUM public confidence):** the tool names and call order are from the project's own `docs/04-data-tools-reference.md` and the live connection, not public docs. Treat the live MCP's `exports_sources_get` output as the authority for sources/columns; expect to resolve exact margin/sales source columns empirically in Phase 1 (already flagged in `docs/05-open-decisions.md`).
- **supabase-py async surface (MEDIUM-HIGH):** async client exists (`create_async_client` / `AsyncClient`, async PostgREST/Auth clients confirmed in repo docs), but the official reference page still leads with sync examples. If you go async, validate the exact import against the installed 2.31.0 package.

---

## Sources

- Hermes Desktop App docs — https://hermes-agent.nousresearch.com/docs/user-guide/desktop — `HERMES_HOME`=`~/.hermes`, skills/MCP/cron panes, `logs/desktop.log` (MEDIUM, current preview)
- Hermes CLI commands — https://hermes-agent.nousresearch.com/docs/reference/cli-commands — `hermes mcp/skills/cron` commands, `config.yaml`, `skills/` location (MEDIUM)
- Hermes Cron / gateway — https://hermes-agent.nousresearch.com/docs/user-guide/features/cron — gateway daemon ticks ~60s; no gateway = no jobs; `hermes gateway install` (MEDIUM, load-bearing for scheduling caveat)
- Hermes Desktop release (v0.15.2, 2026-06-02) — https://www.marktechpost.com/2026/06/03/nous-research-releases-hermes-desktop... (MEDIUM)
- agentskills.io specification — https://agentskills.io/specification — full SKILL.md frontmatter fields/limits, directory structure, progressive disclosure, `skills-ref validate` (HIGH)
- PyPI (versions verified 2026-06-08): supabase 2.31.0, sqlalchemy 2.0.50, alembic 1.18.4, psycopg 3.3.4, asyncpg 0.31.0, pgvector 0.4.2, httpx 0.28.1, tenacity 9.1.4, structlog 26.1.0, pydantic 2.13.4, polars 1.41.2, pandas 3.0.3, mcp 1.27.2, python-dotenv 1.2.2 (HIGH)
- Context7 `/supabase/supabase-py` — async client (`AsyncGoTrueClient`, `AsyncPostgrestClient`) confirmation (HIGH)
- Supabase vecs / AI docs — https://github.com/supabase/vecs , https://supabase.com/docs/guides/ai — pgvector Python options (HIGH)
- Project docs read: `.planning/PROJECT.md`, `CLAUDE.md`, `docs/01-architecture.md`, `docs/02-context-and-constraints.md`, `docs/04-data-tools-reference.md` — read-only/no-write constraints, DataDoe call pattern, Supabase truth tables (authoritative for project constraints)

---
*Stack research for: read-only Amazon FBA PPC/profit analytics workspace on Hermes desktop + DataDoe + Supabase*
*Researched: 2026-06-08*
