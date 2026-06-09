# Phase 1: Foundation - Research

**Researched:** 2026-06-08
**Domain:** Trustworthy read-only substrate — MCP connection verification, empirical DataDoe source map, Supabase truth store (Alembic/pgvector), `~/.hermes` persona+context+backup — on the Hermes Mac desktop app
**Confidence:** HIGH on stack/schema/Hermes-CLI surface (verified against live `~/.hermes` install + PyPI + agentskills.io spec); MEDIUM on DataDoe column-level specifics (resolve empirically at execution time via `exports_sources_get`)

## Summary

Phase 1 is a **substrate phase, not a question-slice**. It establishes five things, all of which downstream phases assume exist: (1) verified, read-only MCP connections plus the cached amazon.ca seller UUID; (2) an *empirically-confirmed* DataDoe source map (columns, ad-program scope, timezone basis, premium Profit-by-SKU enablement); (3) the five-table Supabase truth store built via reviewed Alembic migrations with `pgvector` enabled and marketplace as a first-class dimension; (4) `config` seeded with the operator's *real* thresholds (empty config is forbidden — it is a fabrication invitation); and (5) a version-controlled `~/.hermes` persona (SOUL.md) + business context, with a decided/documented backup approach.

The stack is locked and was re-verified this session against PyPI — every pinned version (supabase 2.31.0, SQLAlchemy 2.0.50, Alembic 1.18.4, psycopg[binary] 3.3.4, pgvector 0.4.2, structlog 26.1.0, pydantic 2.13.4, python-dotenv 1.2.2) matches exactly. Critically, the **live `~/.hermes` install was inspected directly** and updates the prior project research in three load-bearing ways: Hermes is **v0.16.0 (2026.6.5)** running Python 3.11.15 (not the v0.15.2 the stack doc assumed — the pin must be updated); `SOUL.md` currently exists only as a template stub and `memories/` is empty (so CTX-01/CTX-02 are genuinely unbuilt); and the MCP `servers:` block in `config.yaml` reads empty, meaning **DataDoe/Supabase MCP wiring is an execution-time gate to verify, not an assumed-done state**.

**Primary recommendation:** Build bottom-up in a strict order — verify+wire connections (`hermes mcp test`) and cache the UUID first; produce the empirical source map second (it gates the schema's exact column names and the premium-vs-fallback decision); then build the Alembic-migrated schema (enable `vector` in the *first* migration, before any vector column) and seed `config` with operator-supplied real numbers; in parallel, replace the SOUL.md stub and load `.hermes-context/` business context; finish by deciding the backup approach — which is **native**: `hermes backup` (full zip) / `hermes backup --quick` + `hermes import` for `~/.hermes`, plus a `pg_dump`/Supabase dump for the DB, scheduled on-open (no clock-cron, Mac-awake constraint).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| MCP connection verification (DataDoe/Supabase/Gmail-Drive) | Hermes runtime (`hermes mcp test`) | — | Connections are configured in `~/.hermes/config.yaml` and probed by the Hermes CLI; not a Python concern |
| Seller-UUID resolution + caching | DataDoe MCP (resolve) → `.env` (cache) | Python helper reads `.env` | `sellers_and_vendors_list` resolves; value lives in `.env` as `AMAZON_CA_SELLER_ID`, never inlined |
| DataDoe source map (columns/scope/tz/premium) | DataDoe MCP (`exports_sources_get`) | Repo artifact (markdown) | Empirical output of an MCP call, recorded to a durable repo file the planner/primitives read |
| Schema definition + migration | Postgres / Alembic (direct connection) | SQLAlchemy 2.0 metadata | DDL must be reviewable git artifacts; migrations run on the *direct* (non-pooled) connection |
| `pgvector` enablement | Postgres extension (Alembic op) | — | `CREATE EXTENSION vector` in the first migration, before any `vector` column |
| `config` threshold seeding | Postgres (seed migration / data step) | Operator input | Real values supplied by operator; persisted as `(key, marketplace)` rows |
| Persona (SOUL.md) + business context | `~/.hermes` (deploy target) | `.hermes-context/` in git (source of truth) | Local Hermes memory is the runtime; git holds the canonical, recoverable copy |
| Backup of `~/.hermes` + Supabase | Hermes CLI (`hermes backup`) + `pg_dump` | Time Machine (belt-and-suspenders) | Native zip backup + DB dump; scheduled on-open, not clock-cron |

## Standard Stack

> The stack is **LOCKED** by CLAUDE.md — no alternatives surveyed. Versions below were re-verified against PyPI on 2026-06-08 this session (all match the pins exactly) `[VERIFIED: PyPI]`.

### Core (Phase-1 relevant)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy | 2.0.50 | Schema metadata + Core for truth-store DDL | 2.0 metadata API pairs with Alembic autogenerate; project-locked `[VERIFIED: PyPI]` |
| Alembic | 1.18.4 | Versioned, reviewable migrations (the *only* way schema changes) | Reviewable git artifacts satisfy "money logic is reviewed"; never dashboard click-ops `[VERIFIED: PyPI]` |
| psycopg[binary] | 3.3.4 | Direct Postgres driver (sync+async) | `[binary]` avoids libpq build pain on macOS; one driver both modes `[VERIFIED: PyPI]` |
| pgvector | 0.4.2 | Python adapter for `vector` columns | Registers vector types; extension enabled in first migration `[VERIFIED: PyPI]` |
| pydantic | 2.13.4 | Validate `config` thresholds + DataDoe export columns | Catches schema drift before money math `[VERIFIED: PyPI]` |
| python-dotenv | 1.2.2 | Load `.env` (`AMAZON_CA_SELLER_ID`, Supabase keys) | Secrets in env (CLAUDE.md hard rule) `[VERIFIED: PyPI]` |
| structlog | 26.1.0 | Structured JSON logging on every external call | "Every external call wrapped and logged" rule `[VERIFIED: PyPI]` |

### Supporting (used in Phase 1 or wired now for later phases)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| supabase (supabase-py) | 2.31.0 | App-style row writes (e.g. a `decision_ledger` entry from a skill) | Ergonomic single-row inserts; NOT for schema/bulk `[VERIFIED: PyPI]` |
| tenacity | 9.1.4 | Retry/backoff on the export poll loop | Phase 2 wrapper; not strictly needed for Phase-1 schema work `[VERIFIED: PyPI]` |
| polars | 1.41.2 | Export transforms | Phase 2; not Phase-1 `[VERIFIED: PyPI]` |
| httpx | 0.28.1 | Direct HTTP (signed export URLs) | Phase 2; not Phase-1 `[VERIFIED: PyPI]` |

### Hermes runtime (live-verified this session)
| Component | Value | Source |
|-----------|-------|--------|
| Hermes Agent version | **v0.16.0 (2026.6.5)**, upstream `b99c6c42` | `[VERIFIED: hermes --version]` — supersedes the v0.15.2 in STACK.md; **update the pin** |
| Runtime Python | 3.11.15 | `[VERIFIED: hermes --version]` |
| `HERMES_HOME` | `~/.hermes` (exists, populated) | `[VERIFIED: ls ~/.hermes]` |
| SOUL.md | `~/.hermes/SOUL.md` — currently a **template stub** (no operator persona yet) | `[VERIFIED: cat ~/.hermes/SOUL.md]` |
| Skills root | `~/.hermes/skills/<category>/<skill>/SKILL.md` | `[VERIFIED: ls ~/.hermes/skills]` |
| MCP config | `~/.hermes/config.yaml` (MCP `servers:` block reads **empty** — wiring is an execution gate) | `[VERIFIED: grep config.yaml]` |

**Installation (Phase-1 subset):**
```bash
uv init && uv python pin 3.12   # 3.12 sweet spot; runtime Hermes is 3.11.15 — helpers can target 3.12 independently
uv add sqlalchemy==2.0.50 alembic==1.18.4 "psycopg[binary]==3.3.4" pgvector==0.4.2 \
       pydantic==2.13.4 python-dotenv==1.2.2 structlog==26.1.0 supabase==2.31.0
uv add --dev ruff pytest
```

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Alembic migrations | Supabase dashboard / Supabase CLI | **Forbidden** for schema — dashboard is un-reviewable/un-reproducible; violates reviewed-money-logic rule |
| psycopg3 | asyncpg | Only if measured async throughput need; Phase 1 is schema/seed — keep sync psycopg3, simpler |

## Package Legitimacy Audit

> All Phase-1 packages are from the **locked, project-mandated** stack and were re-verified against PyPI this session. `slopcheck` could not be installed in this environment, so per protocol every package is tagged with its registry-verification status; however, these are not LLM-discovered names — they are the exact pins in CLAUDE.md, independently confirmed on PyPI. Hermes also ships a native supply-chain gate (`hermes security`, OSV.dev) usable at install time.

| Package | Registry | Version verified | slopcheck | Disposition |
|---------|----------|------------------|-----------|-------------|
| sqlalchemy | PyPI | 2.0.50 | unavailable | Approved (locked + PyPI-verified) |
| alembic | PyPI | 1.18.4 | unavailable | Approved (locked + PyPI-verified) |
| psycopg[binary] | PyPI | 3.3.4 | unavailable | Approved (locked + PyPI-verified) |
| pgvector | PyPI | 0.4.2 | unavailable | Approved (locked + PyPI-verified) |
| pydantic | PyPI | 2.13.4 | unavailable | Approved (locked + PyPI-verified) |
| python-dotenv | PyPI | 1.2.2 | unavailable | Approved (locked + PyPI-verified) |
| structlog | PyPI | 26.1.0 | unavailable | Approved (locked + PyPI-verified) |
| supabase | PyPI | 2.31.0 | unavailable | Approved (locked + PyPI-verified) |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none
**Note for planner:** slopcheck was unavailable. Because every package is a CLAUDE.md-locked pin independently confirmed present on PyPI at the exact pinned version, a `checkpoint:human-verify` gate is low-value here; if the project prefers strictness, run `hermes security` (native OSV.dev audit) against the venv after `uv add` as the install-time gate instead.

## Architecture Patterns

### System Architecture Diagram (Phase-1 data/control flow)

```
[Operator in Hermes desktop workspace]
        │
        │ 1. "verify connections"            (CONN-01)
        ▼
[hermes mcp test datadoe | supabase | gmail]  ──► responds? read-only confirmed?
        │
        │ 2. resolve seller UUID             (CONN-02)
        ▼
[DataDoe MCP: sellers_and_vendors_list] ──► UUID ──► write to .env AMAZON_CA_SELLER_ID
        │
        │ 3. map sources EMPIRICALLY         (CONN-03)
        ▼
[DataDoe MCP: exports_sources_get(query, sellerOrVendorIds)]
        │   records per source: columns · ad-program scope (SP/SB/SD) ·
        │   date-column timezone basis · premium "Profit by SKU & Date" enabled?
        ▼
[repo artifact: docs/datadoe-source-map.md]  ◄── durable, version-controlled
        │
        │ 4. schema gated by confirmed columns   (DATA-01..04)
        ▼
[Alembic: 001 enable vector ext ─► tables ─► indexes ─► 002 seed config]
        │                                              ▲
        │ runs on DIRECT connection (migrations)       │ real operator thresholds
        ▼                                              │ (key, marketplace)
[Supabase Postgres: sku_master · cogs(SCD+FX) · metric_snapshots(unique key) ·
                    decision_ledger · config]
        │
        │ 5. persona + context (parallel track)   (CTX-01..03)
        ▼
[.hermes-context/ in git] ──deploy──► [~/.hermes/SOUL.md + business-context]
        │
        ▼
[backup decided: hermes backup (zip) + pg_dump, on-open]   (CTX-03)
```

### Recommended Project Structure (Phase-1 additions to the architecture's layout)
```
habib-os/
├── db/
│   ├── alembic.ini
│   ├── migrations/
│   │   ├── env.py                  # target_metadata = Base.metadata; reads DB URL from .env
│   │   └── versions/
│   │       ├── 0001_enable_vector_and_core_tables.py   # CREATE EXTENSION vector FIRST
│   │       └── 0002_seed_config.py                     # real thresholds (key, marketplace)
│   └── models.py                   # SQLAlchemy 2.0 declarative models (5 tables)
├── docs/
│   └── datadoe-source-map.md       # CONN-03 empirical artifact (the durable source map)
├── .hermes-context/                # version-controlled source of truth for ~/.hermes
│   ├── SOUL.md                     # operator persona (replaces the stub)
│   └── business-context.md         # ~30 SKUs, guardrails, FX policy, marketplace scope
├── .env.example                    # AMAZON_CA_SELLER_ID=, SUPABASE_DB_URL=, ... (real .env never committed)
└── scripts/
    └── backup.sh                   # hermes backup --quick + pg_dump; run on-open
```

### Pattern 1: Enable `pgvector` in the FIRST migration, before any vector column
**What:** The very first Alembic migration runs `op.execute("CREATE EXTENSION IF NOT EXISTS vector")` before creating any table that uses a `vector` column. Register the pgvector type in `models.py` / `env.py` so autogenerate recognizes it.
**When to use:** Always, for the initial schema migration. A `vector` column DDL fails if the extension is absent.
**Example:**
```python
# Source: pgvector-python README pattern [CITED: github.com/pgvector/pgvector-python]
# db/migrations/versions/0001_enable_vector_and_core_tables.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")   # MUST precede any vector column
    op.create_table(
        "config",
        sa.Column("key", sa.Text, nullable=False),
        sa.Column("marketplace", sa.Text, nullable=False, server_default="amazon.ca"),
        sa.Column("value", sa.dialects.postgresql.JSONB, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("key", "marketplace"),
    )
    # ... sku_master, cogs (SCD+FX), metric_snapshots (unique key), decision_ledger ...
```
> Confidence: `[CITED: pgvector-python]` for the extension-first ordering; the exact `vector(dim)` columns are optional in Phase 1 (semantic recall is M-later) — enabling the extension now satisfies DATA-01 "with pgvector enabled" without forcing a dimension choice.

### Pattern 2: `cogs` as an SCD-2 with per-row FX
**What:** Each cost row is dated (`effective_from`/`effective_to`, NULL = current) and carries its own FX (`unit_cost`, `cost_currency`, `fx_rate`, `fx_as_of`, `marketplace_currency`). Margin for a date selects the row effective on that date.
**When to use:** All landed-cost storage. A single overwritten `unit_cost` silently corrupts historical margin (March margin must use March's cost + March's FX).
**Concrete DDL** (from ARCHITECTURE.md, schema already locked by STATE.md):
```sql
CREATE TABLE cogs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace     text NOT NULL,
    seller_sku      text NOT NULL,
    effective_from  date NOT NULL,
    effective_to    date,                          -- NULL = current
    unit_cost       numeric(12,4) NOT NULL,        -- in cost_currency
    cost_currency   text NOT NULL DEFAULT 'USD',
    fx_rate         numeric(12,6),                 -- cost_currency → marketplace currency
    fx_as_of        date,
    marketplace_currency text NOT NULL DEFAULT 'CAD',
    notes           text,
    created_at      timestamptz DEFAULT now(),
    UNIQUE (marketplace, seller_sku, effective_from)
);
```

### Pattern 3: `metric_snapshots` idempotent on `(marketplace, seller_sku, snapshot_date)` + provenance
**What:** Unique constraint on the grain key makes re-pulling a day an upsert (no duplicates); `captured_at` + `datadoe_export_id` + `margin_source` make every row a *versioned observation* reconcilable against Amazon restatement.
**When to use:** The fact table. (Full DDL in ARCHITECTURE.md lines 221-248 — copy verbatim; it is already locked.)
```sql
-- key columns the success criteria mandate:
UNIQUE (marketplace, seller_sku, snapshot_date),     -- idempotent upsert key
captured_at        timestamptz,                      -- when this observation was taken
datadoe_export_id  text,                             -- provenance to the export run
margin_source      text NOT NULL                     -- 'datadoe_profit' | 'cogs_fallback'
```
> Note: ARCHITECTURE.md names the timestamp `ingested_at`; the success criteria call it `captured_at`. **Use `captured_at`** (matches REQUIREMENTS DATA-02 and STATE.md). Flag for planner: pick one name and use it consistently.

### Pattern 4: Migrations on the DIRECT connection, runtime helpers on the POOLED connection
**What:** Supabase exposes a direct (5432) connection and a transaction pooler (6543). Alembic migrations and DDL run on the **direct** connection; short-lived helper reads/writes use the **pooled** connection.
**When to use:** Direct for `alembic upgrade`; pooled for skill/primitive runtime. The transaction pooler does not support all session-level features migrations may need (e.g. advisory locks, some `SET`s).
> Confidence: `[ASSUMED]` on the exact ports/behavior for *this* Supabase instance — verify the two connection strings at execution time from the Supabase project settings. Pattern itself is standard Supabase guidance `[CITED: supabase.com/docs/guides/database/connecting-to-postgres]`.

### Pattern 5: agentskills.io SKILL.md shape for any Phase-1 skill
**What:** A skill is a directory whose name matches frontmatter `name`, containing `SKILL.md`. Required frontmatter: `name` (≤64 chars, lowercase/digits/hyphens, no leading/trailing/double hyphen, matches dir name) and `description` (≤1024 chars, says *what + when*, keyword-rich). Optional: `license`, `compatibility` (≤500), `metadata`, `allowed-tools` (experimental). Body < 500 lines / ~5000 tokens; push detail into `references/`, code into `scripts/`, templates into `assets/` (one level deep).
**When to use:** Any Phase-1 skill (e.g. a `connection-check` or `source-map` skill). Most Phase-1 work is Python/SQL/migrations — skills are thin orchestration only and may not be strictly required until Phase 2.
**Example (verified against the live `dogfood` skill on this machine):**
```markdown
---
name: connection-check
description: Verifies DataDoe, Supabase, and Gmail/Drive MCP connections respond and DataDoe is read-only. Use at session start or when the operator asks to confirm data connections before running an analysis.
metadata:
  hermes:
    tags: [mcp, health-check, datadoe, supabase]
---
# Connection Check
...orchestration only — no money math...
```
> Confidence: `[VERIFIED: agentskills.io/specification]` for the spec, cross-confirmed `[VERIFIED: cat ~/.hermes/skills/dogfood/SKILL.md]` that live Hermes uses exactly this frontmatter (`name`, `description`, `version`, `metadata.hermes.tags`). Skills install under `~/.hermes/skills/<name>/`; validate with `skills-ref validate ./<skill>` before install.

### Anti-Patterns to Avoid
- **Schema via Supabase dashboard click-ops:** un-reviewable, no git history — forbidden. Use Alembic.
- **Empty/seed-later `config`:** a fabrication invitation. Seed real values in Phase 1; missing threshold → refusal, never a default.
- **Vector column before `CREATE EXTENSION vector`:** migration fails. Extension goes first.
- **Single overwritten `unit_cost` in `cogs`:** corrupts historical margin. SCD-2 + per-row FX is mandatory.
- **Inlining the seller UUID in code/skills:** secret/identity in `.env` only.
- **Math in a skill (`SKILL.md`) body:** all money-touching computation is hand-written Python; skills orchestrate.
- **Assuming clock-cron for backups/briefings:** Mac-awake-only; use on-open / on-demand.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema migrations | Hand-written DDL .sql run manually / dashboard | Alembic versioned migrations | Reviewable, reversible, git-tracked; satisfies reviewed-money-logic rule |
| `~/.hermes` backup | Custom tar/rsync script of `~/.hermes` | `hermes backup` (full zip) + `hermes backup --quick` (config/state/.env/auth/cron) + `hermes import` (restore) | **Native, verified this session.** Knows what to include/exclude; restore path tested by the vendor |
| MCP connection probe | Custom auth/ping script | `hermes mcp test <name>` and `hermes mcp list` | Native, non-destructive; uses the same config the agent uses |
| Supply-chain check on installed deps | Manual CVE lookup | `hermes security` (OSV.dev audit of venv/plugins/MCP) | Native; covers the slopcheck gap in this environment |
| Retry/backoff (Phase 2 wrapper) | Hand-rolled retry loop | tenacity | Standardized backoff/jitter/caps; self-documenting |
| Structured logging | print/JSON-by-hand | structlog | One event in/out per external call; the observability rule |

**Key insight:** Hermes ships native commands for exactly the three operational risks this phase touches — connection verification (`hermes mcp test`), backup/restore (`hermes backup`/`import`), and supply-chain audit (`hermes security`). Do not reinvent any of them; the Phase-1 work is *configuring and invoking* them, not building substitutes.

## Runtime State Inventory

> Phase 1 is greenfield substrate creation, but it touches live runtime state (`~/.hermes`, Supabase, `.env`). This inventory records what exists NOW so the plan accounts for it.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data (Supabase) | None — the five tables do not exist yet (Phase 1 creates them). Verify no stale/partial schema in the target Supabase project before first migration. | Run `alembic upgrade head` against a confirmed-empty schema; if a prior partial schema exists, reconcile before migrating |
| Live service config (Hermes MCP) | `~/.hermes/config.yaml` MCP `servers:` block reads **empty** in inspection — DataDoe/Supabase/Gmail MCPs may not yet be wired (or are configured via a different mechanism: `hermes mcp catalog`/`install`). | Execution-time: run `hermes mcp list`; if DataDoe/Supabase absent, wire via `hermes mcp add`/`install` before CONN-01 can pass |
| OS-registered state | None relevant. No Task Scheduler / launchd jobs for Habib OS yet. `hermes cron` jobs: none for this project (and M1 assumes no clock-cron). | None |
| Secrets / env vars | `~/.hermes/.env` exists (Hermes's own, 23KB). **Project** `.env` (repo) does not yet exist — `AMAZON_CA_SELLER_ID` not yet cached. Supabase DB URL/keys not yet in a project `.env`. | Create repo `.env` (gitignored) + `.env.example`; cache `AMAZON_CA_SELLER_ID=5692b95f-f3f0-4063-9c1c-40177c54f408` and `SUPABASE_DB_URL` |
| Build artifacts | None — no `uv`/`alembic` project initialized yet in the repo (`db/`, `pyproject.toml` absent). | `uv init`, scaffold `db/` + Alembic on first plan task |
| `~/.hermes` persona/context | `SOUL.md` is a **template stub** (no operator persona); `memories/` is **empty**; no Habib business-context file. | Replace SOUL.md with the operator persona; create `.hermes-context/business-context.md`; deploy to `~/.hermes` |

**Verified empty/clean:** `memories/` (empty dir), project `.env` (does not exist), `db/` schema (not initialized) — all confirmed by direct `ls`/`grep` this session.

## Common Pitfalls

### Pitfall 1: Treating the DataDoe source map as assumed rather than empirical
**What goes wrong:** Schema column names, the premium-vs-fallback margin path, and SP/SB/SD double-counting guards are all built on *guessed* DataDoe columns/scope/timezone; they silently disagree with reality.
**Why it happens:** The DataDoe MCP contract is LOW-MEDIUM public confidence — `docs/04` lists confirmed source IDs but exact columns, per-source timezone, and premium enablement are only knowable from the live `exports_sources_get`.
**How to avoid:** Make the source map an **execution-time empirical task** producing `docs/datadoe-source-map.md`. Record per confirmed source: columns, ad-program scope (which of SP/SB/SD), date-column timezone basis, and whether premium "Profit by SKU & Date" is enabled. Keep `metric_snapshots` columns close to the Profit-by-SKU output to minimize transformation.
**Warning signs:** A plan task that writes specific DataDoe column names without first running `exports_sources_get`; a schema finalized before the source map exists.

### Pitfall 2: Empty `config` shipped "to seed later"
**What goes wrong:** The agent, lacking a real threshold to read, fabricates one — the cardinal sin of this project.
**Why it happens:** Seeding feels deferrable; real numbers require operator input.
**How to avoid:** Treat config seeding as a *blocking* Phase-1 deliverable. Operator must supply real `min_margin_pct`, `acos_ceiling`, `days_of_cover_trigger`, keyed `(key, marketplace='amazon.ca')`. The seed is a reviewed Alembic data migration, not a dashboard insert.
**Warning signs:** A "TODO: seed config" left open; config table created but empty at phase end.

### Pitfall 3: `pgvector` column created before the extension is enabled
**What goes wrong:** The migration fails mid-run, leaving a partial schema.
**Why it happens:** Author adds a `vector` column to a table in the same migration without `CREATE EXTENSION` first.
**How to avoid:** First statement of the first migration is `CREATE EXTENSION IF NOT EXISTS vector`. (Phase 1 may not even add a vector column yet — but enabling the extension satisfies DATA-01 and de-risks later phases.)
**Warning signs:** Migration ordering that creates tables before the extension op.

### Pitfall 4: Backup decided as clock-cron on a Mac-awake-only runtime
**What goes wrong:** A scheduled `~/.hermes`/DB backup silently never fires when the Mac is asleep; `~/.hermes` loss (persona, skills, future ledger) becomes unrecoverable.
**Why it happens:** The superseded Hetzner/cron mental model leaks in.
**How to avoid:** Use `hermes backup --quick` + `pg_dump` triggered **on-open / on-demand** (or Time Machine for the disk-level belt-and-suspenders). Document the target (where the zip + dump land) and cadence. Test one restore (`hermes import`) before relying on it.
**Warning signs:** A backup plan that says "nightly at 02:00" with no on-open fallback.

### Pitfall 5: MCP connection assumed wired (it may not be)
**What goes wrong:** CONN-01 is marked done because the desktop app "has" the connections, but `config.yaml`'s MCP `servers:` block is empty and `hermes mcp test datadoe` actually fails.
**Why it happens:** The connected-systems doc (`docs/02`) says "all already authenticated," but live inspection shows the MCP servers block empty — authentication state and MCP-server registration are not the same thing.
**How to avoid:** First Phase-1 task runs `hermes mcp list` and `hermes mcp test <each>`; if DataDoe/Supabase are absent, wire them (`hermes mcp add`/`install`) before declaring CONN-01 met. Confirm read-only by a non-destructive probe (below).
**Warning signs:** CONN-01 checked off without a captured `hermes mcp test` transcript.

## Code Examples

### Confirm a connection responds, non-destructively (CONN-01)
```bash
# Source: hermes mcp --help (verified this session) [VERIFIED: hermes mcp --help]
hermes mcp list                    # what is actually wired
hermes mcp test datadoe            # round-trips a tool call; non-destructive
hermes mcp test supabase
hermes mcp test gmail              # or the gmail/drive server name from `list`
```
**Read-only confirmation for DataDoe:** DataDoe exposes only read tools (`sellers_and_vendors_list`, `exports_sources_get`, `exports_create`, `exports_get`, `exports_raw_download`). Confirm read-only by enumerating its tool surface (`hermes mcp configure datadoe` / inspect tool list) and verifying **no** write/mutate tool exists — *not* by attempting a write. There is structurally no write tool to call.

### Resolve + cache the seller UUID (CONN-02)
```bash
# Agent calls DataDoe MCP: sellers_and_vendors_list → returns the amazon.ca seller UUID
# Known value (still confirm via the call, don't hardcode blindly):
#   5692b95f-f3f0-4063-9c1c-40177c54f408
# Cache to the repo .env (gitignored), never inline:
echo 'AMAZON_CA_SELLER_ID=5692b95f-f3f0-4063-9c1c-40177c54f408' >> .env
```

### Native backup (CTX-03)
```bash
# Source: hermes backup --help (verified this session) [VERIFIED: hermes backup --help]
hermes backup --quick -l pre-phase1     # config, state.db, .env, auth, cron — fast
hermes backup -o ~/Backups/hermes-$(date +%Y%m%d).zip   # full: skills, sessions, data
pg_dump "$SUPABASE_DB_URL" > ~/Backups/supabase-$(date +%Y%m%d).sql   # DB truth store
# Restore path (test once): hermes import ~/Backups/hermes-YYYYMMDD.zip
```

### Alembic init + first migration ordering
```bash
uv run alembic init db/migrations          # scaffold
# edit db/migrations/env.py: target_metadata = Base.metadata; URL from .env (DIRECT conn)
uv run alembic revision -m "enable vector and core tables"   # author 0001 (extension FIRST)
uv run alembic upgrade head                # run on the DIRECT (5432) connection
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Hermes pinned v0.15.2 (STACK.md) | Installed runtime is **v0.16.0 (2026.6.5)** | This session (live check) | Update the CLAUDE.md/stack pin to v0.16.0; preview moves fast (already "16 commits behind") |
| Hetzner server + clock-cron (docs/01) | Hermes Mac desktop app, on-open/on-demand | Locked by CLAUDE.md | No assumed cron; backups & briefings are on-open |
| Agent Central as a data source (docs/01) | DataDoe single source | Locked | All PPC/profit/listing data from DataDoe |
| Custom backup scripting | `hermes backup`/`import` native | Verified this session | Don't hand-roll backup |

**Deprecated/outdated:**
- The v0.15.2 pin in `.planning/research/STACK.md` and CLAUDE.md — supersede with v0.16.0.
- `docs/01-architecture.md` Hetzner/cron/Agent-Central sections — explicitly overridden by its own 2026-06-08 header note; do not plan from them.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Supabase direct (5432) vs pooled (6543) ports/behavior for *this* project | Pattern 4 | Migrations may need the direct conn; wrong conn string fails `alembic upgrade`. Verify in Supabase project settings at execution time |
| A2 | DataDoe MCP server is named `datadoe` (and Supabase/Gmail similarly) in `hermes mcp list` | Code Examples | `hermes mcp test <name>` fails if the registered name differs; resolve from `hermes mcp list` output |
| A3 | DataDoe/Supabase MCPs still need wiring (config `servers:` empty) | Runtime State Inventory, Pitfall 5 | If already wired elsewhere, the wiring task is a no-op verification — low risk |
| A4 | Phase 1 does not yet require a `vector(dim)` column (semantic recall is later) | Pattern 1 | If a vector column is needed now, must choose embedding dimension; enabling the extension is sufficient for DATA-01 regardless |
| A5 | Exact DataDoe columns / per-source timezone / premium Profit-by-SKU enablement | Pitfall 1, source map | Schema column names and margin path depend on it — **explicitly an execution-time empirical step**, not a guess |

**These assumptions must be confirmed at execution time** — none should be treated as locked decisions by the planner. A1–A2 are connection-string/naming details; A5 is the load-bearing empirical source-map step.

## Open Questions (RESOLVED)

> All four questions are legitimately execution-time empirical steps — each is owned by a specific Phase-1 task that resolves it against the live runtime. They are annotated below with their owning task, not left open.

1. **Are the project MCPs already wired in `~/.hermes/config.yaml`?**
   - What we know: the `servers:` block read empty in inspection; `docs/02` claims all systems "already authenticated."
   - What's unclear: whether DataDoe/Supabase/Gmail are registered as MCP servers vs merely authenticated, or wired via `hermes mcp catalog`.
   - Recommendation: First Phase-1 task = `hermes mcp list`; wire any missing server before CONN-01.
   - **(RESOLVED at execution by plan 01-01 Task 2)** — `hermes mcp list` / `hermes mcp test <name>` run in the blocking-human MCP verification gate; any missing server is wired (`hermes mcp add`/`install`) before CONN-01 is declared met.

2. **Real `config` seed values (min margin %, ACOS ceiling, days-of-cover)?**
   - What we know: must be real, operator-supplied, keyed `(key, 'amazon.ca')`.
   - What's unclear: the actual numbers.
   - Recommendation: Operator input — gather in discuss-phase or as a blocking Phase-1 task; seed via Alembic data migration.
   - **(RESOLVED at execution by plan 01-04 Task 1)** — operator decision gate supplies the real `min_margin_pct`, `acos_ceiling`, `days_of_cover_trigger` values, seeded via the reviewed Alembic data migration; empty/placeholder config is forbidden.

3. **Backup target + cadence?**
   - What we know: `hermes backup` (native) + `pg_dump`; on-open not cron.
   - What's unclear: where the zip + dump land (local dir? external disk? Drive?) and on what trigger.
   - Recommendation: Decide and document (e.g. `~/Backups/` + Time Machine, run on-open via a `scripts/backup.sh`).
   - **(RESOLVED at execution by plan 01-03 Task 2)** — operator decision gate selects the backup target + on-open trigger; documented and a single restore (`hermes import`) tested before reliance.

4. **Is premium "Profit by SKU & Date" enabled on the DataDoe plan?**
   - What we know: it's the locked margin authority; `cogs` is the fallback.
   - What's unclear: enablement + SKU coverage — only knowable empirically.
   - Recommendation: Confirm via `exports_sources_get` in the source-map task; if disabled/incomplete, note the fallback path must be proven in Phase 2.
   - **(RESOLVED at execution by plan 01-01 Task 3)** — the empirical source-map task calls `exports_sources_get` and records the premium "Profit by SKU & Date" enablement (and SKU coverage) explicitly in `docs/datadoe-source-map.md`; if disabled/incomplete, the map says so and flags the Phase-2 fallback.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Hermes Agent (desktop/CLI) | All Phase-1 connection/backup/skill work | ✓ | v0.16.0 (2026.6.5) | — |
| `hermes mcp` subcommands | CONN-01 verification | ✓ | — | — |
| `hermes backup` / `import` | CTX-03 backup | ✓ | — | Time Machine (disk-level) |
| `hermes cron` | (NOT used in M1) | ✓ | — | on-open trigger |
| Python (system) | helper runtime | ✓ | 3.11.0 (system); Hermes uses 3.11.15 | target 3.12 via `uv python pin` |
| uv | env/dep management | ✗ (not found on PATH) | — | pip + venv (less reproducible) |
| Supabase project (Postgres+pgvector) | DATA-01..04 | ⚠ unverified | — | none — required; confirm connection string + empty schema |
| DataDoe MCP wired | CONN-01/02/03 | ⚠ unverified (`servers:` empty) | — | `hermes mcp add`/`install` |
| `pg_dump` | DB backup | ⚠ unverified | — | Supabase dashboard export (manual) |
| slopcheck | package audit | ✗ | — | `hermes security` (OSV.dev native) |

**Missing dependencies with no fallback:**
- A reachable Supabase project with a confirmed connection string and an empty/known schema — blocks DATA-01..04. Must be confirmed at execution time.

**Missing dependencies with fallback:**
- `uv` not on PATH → install it (preferred) or fall back to `pip`+`venv`.
- DataDoe/Supabase MCP not confirmed wired → `hermes mcp add`/`install`.
- slopcheck absent → `hermes security` covers supply-chain.
- `pg_dump` unconfirmed → Supabase dashboard manual export as fallback.

## Validation Architecture

> `workflow.nyquist_validation` is `true` in config — section included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (locked dev dep; install `uv add --dev pytest`) |
| Config file | none yet — see Wave 0 (`pyproject.toml [tool.pytest.ini_options]`) |
| Quick run command | `uv run pytest -x -q` |
| Full suite command | `uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CONN-02 | `.env` carries `AMAZON_CA_SELLER_ID`, never inlined | unit | `uv run pytest tests/test_env.py::test_seller_id_in_env_not_code -x` | ❌ Wave 0 |
| DATA-01 | All 5 tables exist after `alembic upgrade head`; `vector` extension present | integration | `uv run pytest tests/test_schema.py::test_tables_and_vector_ext -x` | ❌ Wave 0 |
| DATA-02 | `metric_snapshots` unique on `(marketplace, seller_sku, snapshot_date)`; has `captured_at`, `datadoe_export_id` | integration | `uv run pytest tests/test_schema.py::test_snapshot_idempotency_key -x` | ❌ Wave 0 |
| DATA-03 | `cogs` SCD columns + per-row FX present; `(marketplace, seller_sku, effective_from)` unique | integration | `uv run pytest tests/test_schema.py::test_cogs_scd_fx -x` | ❌ Wave 0 |
| DATA-04 | `config` non-empty after seed; keyed `(key, marketplace)`; required keys present | integration | `uv run pytest tests/test_config_seed.py::test_required_thresholds_seeded -x` | ❌ Wave 0 |
| CTX-01/02 | `.hermes-context/SOUL.md` + `business-context.md` exist, are non-stub, deployed to `~/.hermes` | unit | `uv run pytest tests/test_context.py::test_soul_and_context_deployed -x` | ❌ Wave 0 |
| CONN-01/03 | connection probe + source map | manual-only | `hermes mcp test <name>`; inspect `docs/datadoe-source-map.md` | manual (live MCP) |

> CONN-01 and CONN-03 are **manual/empirical** (depend on the live DataDoe MCP and operator confirmation) — they cannot be fully automated and should be verified by captured CLI transcript + the source-map artifact's existence/completeness.

### Sampling Rate
- **Per task commit:** `uv run pytest -x -q`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green + `docs/datadoe-source-map.md` complete + `config` seeded + `hermes mcp test` transcripts captured, before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `pyproject.toml [tool.pytest.ini_options]` + `uv add --dev pytest` — framework not yet present
- [ ] `tests/conftest.py` — fixture spinning up a test Postgres (or a disposable Supabase schema) for schema/seed integration tests
- [ ] `tests/test_schema.py` — DATA-01/02/03 (post-`alembic upgrade` introspection)
- [ ] `tests/test_config_seed.py` — DATA-04 (required thresholds present, non-empty)
- [ ] `tests/test_env.py` — CONN-02 (UUID in `.env`, not in source)
- [ ] `tests/test_context.py` — CTX-01/02 (SOUL.md non-stub + deployed)

## Security Domain

> `security_enforcement` not set to `false` — section included. This is a read-only, single-operator system; the dominant threat is **fabrication / wrong numbers**, not classic web attacks, but credential and supply-chain controls apply.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | partial | MCP OAuth/header auth managed by Hermes; no app-level auth in M1 |
| V3 Session Management | no | No user sessions; single-operator desktop app |
| V4 Access Control | yes | DataDoe is structurally read-only; Supabase keys least-privilege (prefer anon/limited over service-role); RLS where feasible |
| V5 Input Validation | yes | pydantic validates `config` thresholds + DataDoe export columns before money math |
| V6 Cryptography | partial | Secrets in `.env` only (python-dotenv); never committed; never hand-roll crypto |
| V14 Configuration/Supply-chain | yes | Pinned versions; `hermes security` (OSV.dev) audit of venv/MCP; no unpinned installs |

### Known Threat Patterns for this stack
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Fabricated number/threshold | Spoofing (of truth) | Every number traces to an export id / config row; missing threshold → refusal; seed real config |
| Secret/UUID leak (committed `.env` or inlined) | Information disclosure | `.env` gitignored; `.env.example` only; UUID never inlined |
| Over-scoped Supabase service-role key | Elevation of privilege | Least-privilege key; RLS; service-role only where strictly needed |
| Over-scoped MCP credential (future write vector) | Elevation of privilege | Verify read-only scope; no write-MCP in M1; future write-MCP is a separate gated milestone |
| Supply-chain (malicious dep) | Tampering | Pinned versions + `hermes security` OSV.dev audit (slopcheck unavailable) |
| `~/.hermes` loss (no audit trail) | Repudiation/availability | `hermes backup` + DB dump; tested restore |

## Project Constraints (from CLAUDE.md)

| Directive | Phase-1 implication |
|-----------|---------------------|
| Data layer READ-ONLY; DataDoe only; no SP-API/Ads client | Verify DataDoe read-only; never build any Amazon API client |
| No autonomous writes to Amazon | No ACT layer; `decision_ledger` ships with write/approval columns NULL |
| Secrets in `.env` only | `AMAZON_CA_SELLER_ID`, Supabase URL/keys in gitignored `.env`; `.env.example` committed |
| Money-touching logic hand-written + reviewed + pytest | Schema/seed reviewed via Alembic; thresholds in `config`, validated by pydantic; no math in skills |
| Migrations via Alembic in git — never dashboard click-ops | All five tables + seed via Alembic versioned migrations |
| Stack LOCKED (Python 3.11+/3.12 + the pinned libs) | Use the exact pins; no alternative survey |
| Runtime = Hermes Mac desktop, Mac-awake only, no assumed cron | Backups/briefings on-open/on-demand; update Hermes pin to v0.16.0 |
| Deliverables = Hermes skills (agentskills.io SKILL.md) + Python + SQL | Any Phase-1 skill follows the verified frontmatter spec; skills orchestrate, primitives compute |

## Sources

### Primary (HIGH confidence)
- Live `~/.hermes` install inspection (this session): `hermes --version` (v0.16.0, Python 3.11.15), `hermes mcp/backup/cron --help`, `cat ~/.hermes/SOUL.md` (stub), `ls ~/.hermes/skills` (category→skill→SKILL.md), `grep config.yaml` (MCP `servers:` empty), `cat skills/dogfood/SKILL.md` (frontmatter)
- PyPI version verification (this session, `pip index versions`): all 11 locked packages match pins exactly
- agentskills.io/specification — SKILL.md frontmatter fields, limits, directory structure, progressive disclosure, `skills-ref validate`
- Project docs: CLAUDE.md (binding rules), `docs/02-context-and-constraints.md`, `docs/04-data-tools-reference.md`, `docs/05-open-decisions.md`
- `.planning/research/{STACK,ARCHITECTURE,PITFALLS,SUMMARY}.md` — reused (locked schema, build order, pitfalls); not re-derived

### Secondary (MEDIUM confidence)
- pgvector-python README (extension-first migration ordering) — github.com/pgvector/pgvector-python
- Supabase connecting-to-postgres docs (direct vs pooled connection) — supabase.com/docs/guides/database/connecting-to-postgres

### Tertiary (LOW confidence — execution-time empirical)
- DataDoe `exports_sources_get` output (exact columns, per-source timezone, premium enablement) — resolve live against the connected MCP; `docs/04` lists confirmed source IDs but not column-level detail

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all pins re-verified on PyPI; Hermes runtime live-verified (v0.16.0)
- Schema/migrations: HIGH — locked in STATE.md/ARCHITECTURE.md; Alembic/pgvector patterns standard and cited
- Hermes CLI surface (mcp/backup/cron): HIGH — verified directly via `--help` this session
- DataDoe source map specifics: MEDIUM-LOW — explicitly an execution-time empirical step (A5)
- MCP wiring state: MEDIUM — `config.yaml servers:` empty; resolve via `hermes mcp list` at execution

**Research date:** 2026-06-08
**Valid until:** ~2026-06-15 for Hermes preview specifics (fast-moving, already 16 commits behind); ~2026-07-08 for the pinned Python stack
