# Architecture Research

**Domain:** Read-only Amazon analytics workspace on the Hermes Mac desktop app (single resident agent, DataDoe sense layer, Supabase truth store)
**Researched:** 2026-06-08
**Confidence:** HIGH (component model and read-only contract grounded in project docs + verified Hermes desktop behavior; schema is an opinionated recommendation, MEDIUM on exact DataDoe column names which resolve empirically in Phase 1)

## Standard Architecture

This is not a web app. The "standard architecture" here is a **read-only analytics pipeline driven by one resident agent**: point-in-time exports flow in from a read MCP, get persisted/reconciled into history in Postgres, get computed into margin/PPC answers by hand-written primitives, and surface as conversation in the desktop workspace. There is no write path to Amazon — by design and by toolset.

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│  SURFACE — Hermes Mac desktop workspace (the only surface in M1)     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Conversation: "what's my TACOS by SKU", "where am I wasting   │  │
│  │  ad spend", "which search terms to negate"                     │  │
│  └───────────────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│  THINK — one resident Hermes agent                                  │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │  SOUL.md     │  │  Skills (.md)    │  │  ~/.hermes/ memory   │   │
│  │  persona     │  │  orchestration   │  │  procedural+semantic │   │
│  │  numbers-1st │  │  (the "what")    │  │  business context    │   │
│  └──────────────┘  └────────┬─────────┘  └──────────────────────┘   │
│                             │ calls                                  │
│                    ┌────────┴─────────┐                              │
│                    │ Python primitives│  (the "how" — money logic)   │
│                    │ read + compute   │                              │
│                    └───┬──────────┬───┘                              │
├────────────────────────┼──────────┼─────────────────────────────────┤
│  STATE — Supabase (Postgres + pgvector) = numeric truth             │
│  ┌──────────┐ ┌──────┐ ┌──────────────────┐ ┌──────────────┐ ┌────┐ │
│  │sku_master│ │cogs  │ │metric_snapshots  │ │decision_ledger│ │cfg │ │
│  │(dimension)│ │(SCD) │ │(daily/SKU/mktpl) │ │(audit spine) │ │    │ │
│  └──────────┘ └──────┘ └──────────────────┘ └──────────────┘ └────┘ │
├────────────────────────┬────────────────────────────────────────────┤
│  SENSE — read MCPs (physically cannot write)                        │
│  ┌──────────────────────┴──────┐  ┌──────────────┐  ┌────────────┐  │
│  │ DataDoe MCP (single Amazon   │  │ Gmail/Drive  │  │ Tavily     │  │
│  │ source: PPC + Profit-by-SKU) │  │ Calendar     │  │ web        │  │
│  └──────────────────────────────┘  └──────────────┘  └────────────┘  │
└─────────────────────────────────────────────────────────────────────┘

         NO ACT LAYER IN MILESTONE 1. No write path to Amazon exists.
         (Proposals + decision_ledger approval flow are M2/M3.)
```

### Component Responsibilities

| Component | Responsibility (owns) | Does NOT own | Typical Implementation |
|-----------|----------------------|--------------|------------------------|
| **DataDoe export wrapper** | The `sources → create → poll → download` call pattern; seller-UUID resolution + caching; retry/timeout; logging every call; returning a clean tabular result (rows/columns) to Python | Any interpretation of the numbers; persistence; margin math | Single Python module (`datadoe.py`) wrapping the MCP/CLI; one function per "get me source X filtered Y from→to" |
| **Python compute primitives** | All money-touching math: margin, ACOS/TACOS reconciliation, days-of-cover, search-term waste, negative-keyword candidates. Reads from the wrapper, persists snapshots, returns structured answers | The conversational framing; deciding *when* to run | Hand-written, version-controlled Python (`primitives/`). One module per analytical concern (`margin.py`, `ppc.py`, `inventory.py`) |
| **Supabase persistence layer** | Storing point-in-time exports as durable history; reconciliation (DataDoe authority vs cogs fallback/FX); upsert idempotency; the marketplace dimension; the audit spine | Computing anything beyond simple SQL rollups; talking to DataDoe | Postgres schema + thin Python data-access module (`store.py`); pgvector for semantic recall |
| **Hermes skills (markdown)** | Orchestration only — *which* primitive to call, *what* to ask, *how* to phrase the answer. The "morning briefing runs these three steps" logic | Money math (delegated to primitives); raw MCP calls (delegated to wrapper) | `.md` skill files (agentskills.io format) that invoke Python primitives and format results |
| **`~/.hermes/` memory + SOUL.md** | Business context (the ~30 SKUs, guardrails, FX assumptions), persona (terse, numbers-first, never invents pricing), procedural recall of how tasks were done | Numeric truth (that lives in Supabase, not memory) | Local markdown; backed up via Time Machine + explicit copy |

**The single most important boundary:** money-touching computation lives in **hand-written Python primitives**, never in a skill's prose and never auto-generated. Skills orchestrate; primitives compute; the wrapper fetches; Postgres remembers. This keeps the reviewable money logic in one auditable place.

## Recommended Project Structure

```
habib-os/
├── primitives/                 # hand-written, version-controlled, money-touching
│   ├── datadoe.py              # the export wrapper (sources→create→poll→download)
│   ├── store.py                # Supabase data-access (upsert snapshots, read cogs/config)
│   ├── margin.py               # net profit / ACOS / TACOS / ROI — DataDoe-authoritative
│   ├── ppc.py                  # search-term waste, negative candidates, placement, budget caps
│   ├── inventory.py            # days-of-cover, velocity (M1 read-only reporting)
│   └── reconcile.py            # DataDoe Profit-by-SKU vs cogs fallback + FX
├── skills/                     # markdown, agentskills.io format — orchestration only
│   ├── daily-briefing.md       # calls margin + ppc primitives, formats the rollup
│   ├── ask-ppc.md              # on-demand PPC questions → ppc.py
│   ├── ask-margin.md           # on-demand margin questions → margin.py
│   └── ingest-snapshot.md      # pull export → persist to metric_snapshots
├── sql/
│   ├── 001_schema.sql          # the five tables + indexes + marketplace dimension
│   └── 002_seed_config.sql     # thresholds (min margin, days-of-cover, ACOS ceiling)
├── .hermes-context/            # source-controlled copy of what loads into ~/.hermes
│   ├── SOUL.md                 # persona
│   └── business-context.md     # SKUs, guardrails, FX policy
├── .env.example                # seller UUID, Supabase URL/key (real .env never committed)
└── .planning/                  # GSD planning artifacts
```

### Structure Rationale

- **`primitives/` is the trust boundary.** Everything that feeds a number a human might act on is here, hand-written and reviewed. CLAUDE.md hard rule #4 ("money-touching logic is hand-written and reviewed") maps directly to this folder. Auto-generated skills (later) may *call* these but never *replace* them.
- **`skills/` holds no math.** A skill is a recipe ("fetch yesterday's profit, list SKUs under min margin, phrase it terse"). If a skill contains a margin formula, that's a smell — move it to a primitive.
- **`datadoe.py` is the only thing that knows the MCP call pattern.** Every other module asks it for tabular data. This isolates the read-only contract and the one place every external call is wrapped+logged (CLAUDE.md rule #6).
- **`store.py` is the only thing that writes to Postgres.** Snapshots, ledger entries, config reads all funnel through it — one place to enforce idempotent upserts and the marketplace dimension.
- **`.hermes-context/` is version-controlled even though it deploys to `~/.hermes/`.** Memory lives locally on the Mac, but the canonical persona/context should be in git so it's recoverable and reviewable — the local copy is a deployment target, not the source of truth.

## Architectural Patterns

### Pattern 1: Point-in-time export → reconciled history (the core data flow)

**What:** DataDoe returns a *snapshot* (Profit-by-SKU for a date range, as of now). Supabase is where you turn a stream of snapshots into durable, queryable history. The pattern: fetch → normalize → upsert keyed on (date, sku, marketplace) → compute from the persisted table, not the raw export.

**When to use:** Every recurring number. You persist first so that (a) history survives DataDoe's point-in-time nature, (b) re-running a day is idempotent, (c) reconciliation (DataDoe vs cogs) happens against stored rows.

**Trade-offs:** Adds a persistence hop before computation (slightly more code than "fetch and answer"). Worth it — without persistence you have no history, no reconciliation, and no audit trail. The alternative (compute straight off live exports) silently loses the past and can't reconcile.

**Example:**
```python
# skill calls this; never inlines the math
def ingest_profit(date_from, date_to, marketplace="amazon.ca"):
    rows = datadoe.export(                       # SENSE: wrapped + logged
        source="amazon_profit_by_sku_and_date",
        columns=[...], date_from=date_from, date_to=date_to,
    )
    snapshots = reconcile.profit_rows(rows, marketplace)   # DataDoe authority, cogs FX fallback
    store.upsert_metric_snapshots(snapshots)     # STATE: idempotent on (date, sku, marketplace)
    return snapshots
```

### Pattern 2: DataDoe-authoritative with cogs reconciliation fallback

**What:** Margin authority is DataDoe premium "Profit by SKU & Date" (it already computes net profit, ACOS, TACOS, ROI). `cogs` in Supabase is the *fallback and FX reconciliation* — used when the premium source misses a SKU, or to cross-check landed cost / currency drift.

**When to use:** All margin computation. `reconcile.py` decides per row: if DataDoe gives a clean profit number, use it and record `source='datadoe_profit'`; if not, fall back to `units × price − fees − cogs` using the `cogs` table and record `source='cogs_fallback'`. Always stamp which source won.

**Trade-offs:** Two sources of margin truth must be kept consistent; the reconciliation layer is extra code. But it's exactly the layer that catches "DataDoe and my cost sheet disagree" — which is the kind of silent error that burned this business before.

### Pattern 3: Skill-orchestrates / primitive-computes / wrapper-fetches

**What:** Strict three-tier call direction. A skill (markdown) decides intent and formatting. It calls a Python primitive for any math. The primitive calls the DataDoe wrapper for data and `store.py` for persistence. Data flows up; control flows down. No layer skips a layer (a skill never calls DataDoe directly; the wrapper never computes margin).

**When to use:** Always. This is what makes the system auditable — money logic is isolated in primitives, the read-only contract is isolated in the wrapper.

**Trade-offs:** More indirection than "let the agent freestyle SQL against DataDoe." That freestyling is precisely the anti-pattern (below) — it puts un-reviewed money math in agent prose.

## Data Flow

### The Milestone-1 flow (export → persist → compute → surface)

```
[User in desktop workspace: "what's my TACOS by SKU this week?"]
        ↓  (control flows DOWN)
[ask-margin.md skill]  — decides intent, date range, marketplace
        ↓
[margin.py primitive]  — orchestrates the computation
        ↓                                    ↓
[datadoe.py wrapper]                   [store.py]
   sources→create→poll→download          read cogs + config
   (Profit by SKU & Date, this week)
        ↓                                    ↓
[reconcile.py]  ← DataDoe authority, cogs FX fallback, stamp source
        ↓
[store.upsert_metric_snapshots]  — persist daily/SKU/marketplace rows (idempotent)
        ↓  (data flows UP)
[margin.py returns structured per-SKU TACOS]
        ↓
[ask-margin.md formats terse, numbers-first answer]
        ↓
[Answer in the desktop workspace]   ← NO write to Amazon anywhere in this path
```

### The morning-briefing flow (honoring docs/01 §4, minus the M2/M3 act + cron parts)

In M1 this is **on-open / on-demand**, not clock-cron — the desktop app runs only while the Mac is awake (CLAUDE.md Runtime). The briefing skill:
1. Pulls yesterday's Profit-by-SKU (sales/units/fees/ad-spend) from DataDoe for the CA seller.
2. Reconciles against `cogs` → true margin per SKU.
3. Pulls PPC (search-term + campaign) for the same window.
4. Upserts the day into `metric_snapshots`.
5. Surfaces: top movers, total margin, any SKU under `config.min_margin`, budget-capped campaigns, high-ACOS search terms. **Flags only — no proposals, no writes in M1.**

### State Management (where each computation lives)

| Computation | Lives in | Why |
|-------------|----------|-----|
| Fetching an export | `datadoe.py` (Python) | Single place for the read-only MCP contract + logging |
| Net profit / ACOS / TACOS / ROI | `margin.py` (Python) | Money-touching → hand-written, reviewed |
| Search-term waste / negative candidates | `ppc.py` (Python) | Money-adjacent recommendation logic → hand-written |
| DataDoe-vs-cogs / FX reconciliation | `reconcile.py` (Python) | Authority resolution must be explicit + testable |
| Snapshot upsert, simple rollups, "latest cogs for SKU" | SQL via `store.py` | Set-based, idempotent, belongs in Postgres |
| "Which question, how to phrase it" | skill `.md` | Orchestration + tone, not math |

**Rule of thumb:** if a number could feed a spend decision, it's Python. If it's a set-based join/rollup with no judgment, it's SQL. If it's "what to do and how to say it," it's a skill.

## Supabase Schema (concrete)

Marketplace is a **first-class dimension on every fact and most dimensions** — CA-first, US-ready, no later migration. `marketplace` values: `'amazon.ca'`, `'amazon.com'` (text or an enum).

```sql
-- DIMENSION: the SKU catalog
CREATE TABLE sku_master (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace   text NOT NULL,                 -- 'amazon.ca' | 'amazon.com'
    seller_sku    text NOT NULL,                 -- the merchant SKU
    asin          text,
    fnsku         text,
    title         text,
    brand         text,                          -- 'Anabtawi Sweets'
    status        text DEFAULT 'active',         -- active | inactive | clearance
    created_at    timestamptz DEFAULT now(),
    updated_at    timestamptz DEFAULT now(),
    UNIQUE (marketplace, seller_sku)             -- a SKU is unique per marketplace
);

-- DIMENSION (slowly-changing): landed cost over time, with FX
CREATE TABLE cogs (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace     text NOT NULL,
    seller_sku      text NOT NULL,
    effective_from  date NOT NULL,               -- SCD: cost valid from this date
    effective_to    date,                        -- NULL = current
    unit_cost       numeric(12,4) NOT NULL,      -- landed cost in cost_currency
    cost_currency   text NOT NULL DEFAULT 'USD', -- supplier invoices may be USD
    fx_rate         numeric(12,6),               -- cost_currency → marketplace currency
    fx_as_of        date,                        -- when that rate was captured
    marketplace_currency text NOT NULL DEFAULT 'CAD',
    notes           text,
    created_at      timestamptz DEFAULT now(),
    UNIQUE (marketplace, seller_sku, effective_from)
);

-- FACT: the persisted, reconciled daily history
CREATE TABLE metric_snapshots (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace     text NOT NULL,
    seller_sku      text NOT NULL,
    snapshot_date   date NOT NULL,               -- the business day the metrics describe
    -- sales / units
    units           integer,
    gross_sales     numeric(12,2),
    -- margin (DataDoe-authoritative)
    net_profit      numeric(12,2),
    total_cost      numeric(12,2),               -- fees + COGS + ad spend (DataDoe)
    fba_fees        numeric(12,2),
    ad_spend        numeric(12,2),
    ad_sales        numeric(12,2),
    acos            numeric(8,4),
    tacos           numeric(8,4),
    roi             numeric(8,4),
    -- traffic (when available)
    page_views      integer,
    buybox_pct      numeric(6,4),
    -- provenance / reconciliation
    margin_source   text NOT NULL,               -- 'datadoe_profit' | 'cogs_fallback'
    datadoe_export_id text,                      -- traceability to the export run
    ingested_at     timestamptz DEFAULT now(),
    UNIQUE (marketplace, seller_sku, snapshot_date)   -- idempotent upsert key
);
CREATE INDEX ON metric_snapshots (marketplace, snapshot_date);
CREATE INDEX ON metric_snapshots (seller_sku, snapshot_date);

-- AUDIT SPINE: present (empty path) in M1, load-bearing in M2/M3
CREATE TABLE decision_ledger (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace     text NOT NULL,
    kind            text NOT NULL,               -- 'recommendation' | 'proposal' | 'approval' | 'outcome'
    subject_sku     text,
    summary         text NOT NULL,               -- human-readable what
    payload         jsonb,                       -- the numbers behind it
    proposed_at     timestamptz DEFAULT now(),
    approved_by     text,                        -- NULL until a human approves (M2/M3)
    approved_at     timestamptz,
    approval_token  text,                        -- the one-time token (M2/M3 write path)
    executed_at     timestamptz,
    outcome         text,
    created_at      timestamptz DEFAULT now()
);

-- CONFIG: thresholds, not hard-coded in prompts (CLAUDE.md rule + docs/01 L89)
CREATE TABLE config (
    key             text NOT NULL,
    marketplace     text NOT NULL DEFAULT 'amazon.ca',
    value           jsonb NOT NULL,
    description     text,
    updated_at      timestamptz DEFAULT now(),
    PRIMARY KEY (key, marketplace)               -- thresholds can differ CA vs US
);
-- seed examples: ('min_margin_pct',...), ('days_of_cover_trigger',...), ('acos_ceiling',...)
```

### Schema decisions (resolving docs/05 open items)

- **`metric_snapshots` grain = daily per SKU per marketplace.** Recommended unambiguously. Daily is the finest grain the Profit-by-SKU source supports and is what restock/margin/PPC questions need; weekly/monthly are rollups you derive from daily, not store separately. Marketplace in the key means US data lands in the same table with zero migration. Unique on `(marketplace, seller_sku, snapshot_date)` makes re-ingesting a day idempotent (re-pull yesterday → upsert, no duplicates).
- **`cogs` carries FX per cost row — yes.** Supplier invoices are USD; the CA marketplace settles in CAD; US in USD. Capturing `cost_currency`, `fx_rate`, `fx_as_of`, and `marketplace_currency` *on each cost row* is the only way margin reconciliation is correct over time as both the cost and the rate change. A single global FX constant would silently corrupt historical margin. This is the `cogs`-as-FX-fallback role from the Key Decisions table.
- **`cogs` is slowly-changing (SCD), not a single current value.** `effective_from`/`effective_to` so a margin computed for March uses March's landed cost, not today's. Without this, recomputing history gives wrong numbers.
- **`decision_ledger` exists in M1 but its write/approval columns stay NULL.** M1 is read-only conversational; no proposals execute. Building the table now (audit spine) means M2's proposal flow has somewhere to land without a migration. `approval_token` is the one-time-token slot for the future gated write-MCP — present in schema, unused in M1.
- **`config` is keyed `(key, marketplace)`** so CA and US can carry different thresholds (e.g. different min-margin) without schema change.

## Scaling Considerations

This is a ~30-SKU, single-operator, single-marketplace-of-logic system. "Scale" here means data volume and US expansion, not user concurrency.

| Scale | Architecture Adjustments |
|-------|--------------------------|
| M1: ~30 SKUs, CA only, on-demand | Nothing special. Daily snapshots × 30 SKUs × 365 = ~11k rows/yr. Postgres laughs at this. |
| US expansion (~60 SKUs, 2 marketplaces) | Already handled — marketplace dimension means US rows just append. The work is US-specific *logic* (deferred), not schema. |
| Multi-year history / pgvector recall | Daily grain stays fine for years. pgvector over notes/decisions grows slowly; no tuning needed at this size. |
| If/when DataDoe export limits bite (cap 2500 rows) | Paginate via `skip` in the wrapper; partition exports by date window. The wrapper is the only place this matters. |

### Scaling Priorities

1. **First "bottleneck" is export latency, not DB size.** DataDoe is create-then-poll; a briefing that pulls several sources waits on several exports. Mitigate by issuing exports concurrently in the wrapper and persisting once. Don't optimize Postgres — it's nowhere near a limit.
2. **Second is the Mac-awake constraint, not throughput.** Because the desktop app only runs while the Mac is awake, "scheduled" work is on-open/on-demand in M1. Real cron (M3) needs an always-on Mac or a different trigger — a roadmap decision, not an architecture-rewrite.

## Anti-Patterns

### Anti-Pattern 1: Letting the agent freestyle margin math in prose

**What people do:** Have the skill/agent compute net profit, ACOS, or TACOS inline in markdown/LLM reasoning ("multiply units by price, subtract fees…").
**Why it's wrong:** Money-touching math becomes un-reviewable, non-deterministic, and un-version-controlled — the exact failure mode the guardrails exist to prevent. It also can't be unit-tested or reconciled.
**Do this instead:** All margin/ACOS/TACOS/reconciliation lives in hand-written `primitives/`. Skills call them and only format the result.

### Anti-Pattern 2: Computing off live exports without persisting

**What people do:** Skill pulls a DataDoe export and answers directly, never writing to `metric_snapshots`.
**Why it's wrong:** DataDoe is point-in-time. With no persistence you have no history, can't reconcile DataDoe vs cogs, can't show trends, and can't audit what the numbers were on a given day.
**Do this instead:** Persist-then-compute. Upsert the snapshot (idempotent on date/SKU/marketplace), then compute from the stored table.

### Anti-Pattern 3: Treating `cogs` as a single current cost

**What people do:** One `unit_cost` column, overwritten when cost changes.
**Why it's wrong:** Historical margin recomputes wrong (March margin uses June's cost), and FX drift is invisible.
**Do this instead:** SCD with `effective_from/to` and per-row FX. Margin for a date selects the cost row effective on that date.

### Anti-Pattern 4: Assuming a write capability "just in case"

**What people do:** Build a generic "execute on Amazon" abstraction in M1 to "save time later."
**Why it's wrong:** Violates the read-only hard rule; creates a path the toolset shouldn't have; defeats the structural guardrail. There is no Act layer in M1.
**Do this instead:** No write path until the gated write-MCP milestone. `decision_ledger`'s write columns exist but stay NULL.

### Anti-Pattern 5: Storing numeric truth in `~/.hermes/` memory

**What people do:** Let the agent "remember" margins or COGS in MEMORY.md.
**Why it's wrong:** Memory is procedural/semantic and lossy; numbers must be exact and queryable. Two stores, different jobs (docs/01 §3).
**Do this instead:** Numeric truth in Supabase only. `~/.hermes/` holds persona, business context, and how-to — never the numbers themselves.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| DataDoe MCP | `sellers_and_vendors_list` → `exports_sources_get` → `exports_create` → poll `exports_get` → `exports_raw_download`. Wrapped in `datadoe.py`, every call logged | Read-only. Cap 2500 rows/export → paginate via `skip`. Seller UUID `5692b95f-…54f408` cached in `.env`. Premium "Profit by SKU & Date" must be confirmed enabled (Phase 1, `exports_sources_get`) |
| Supabase | Direct Postgres (psycopg/SQLAlchemy) or Supabase client via `store.py`; pgvector extension for semantic recall | All schema writes funnel through `store.py`. Secrets in `.env` |
| Gmail/Drive/Calendar | Read MCPs for supplier threads / compliance docs (context, not numeric truth) | Not on the margin path in M1 |
| Tavily | Web research MCP | Out of the core data flow; context enrichment only |
| Hermes desktop app | Hosts the agent, surfaces skills + (later) cron; MCP connections configured in app settings; memory + skills in `~/.hermes/` | Runs only while Mac awake → on-demand in M1, no clock-cron assumed |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| skill ↔ primitive | Skill calls Python primitive; primitive returns structured data | Skill never does math; primitive never formats prose |
| primitive ↔ datadoe wrapper | Primitive requests tabular export; wrapper returns rows | Only the wrapper knows the MCP call pattern (read-only contract isolated here) |
| primitive ↔ store | Primitive upserts snapshots / reads cogs+config | Only `store.py` writes Postgres (idempotency + marketplace dimension enforced here) |
| reconcile ↔ margin | `reconcile.py` resolves DataDoe-vs-cogs authority; `margin.py` consumes resolved rows | Provenance (`margin_source`) stamped at reconcile, persisted on the snapshot |

## Build Order / Dependency Graph (Milestone 1)

Strict bottom-up: you can't compute margin before you can fetch and persist; you can't persist before the schema exists; you can't fetch before connections + seller UUID resolve.

```
[0] Connect MCPs read-only (DataDoe, Supabase, Gmail/Drive) + resolve & cache seller UUID
        └─ confirm Profit-by-SKU premium + Ads sources via exports_sources_get
                 ↓
[1] Supabase schema (sql/001) — all five tables + marketplace dimension + indexes
        └─ seed config (sql/002): min_margin, days_of_cover, acos_ceiling
                 ↓
[2] datadoe.py wrapper — the read-only call pattern, wrapped + logged, paginated
                 ↓
[3] store.py — idempotent upserts into metric_snapshots; read cogs/config
                 ↓
[4] reconcile.py — DataDoe-authoritative margin, cogs FX fallback, stamp source
                 ↓        ↓
[5a] margin.py        [5b] ppc.py        (both depend on wrapper+store; margin also on reconcile)
   net profit/ACOS/      search-term waste,
   TACOS/ROI             negatives, placement, budget caps
                 ↓        ↓
[6] Load ~/.hermes/ context + SOUL.md (persona, business, guardrails)   ← parallelizable from [1]
                 ↓
[7] Skills: ingest-snapshot.md, ask-margin.md, ask-ppc.md, daily-briefing.md
                 ↓
[8] Acceptance: answer the four M1 questions conversationally vs live data, spot-checked
```

**Build-order implications for the roadmap:**
- **Schema (1) and wrapper (2) are the gate** — nothing computes until both exist. Sequence them first.
- **`reconcile.py` (4) blocks margin but not PPC** — PPC primitives can proceed in parallel once wrapper+store land, which lets margin and PPC tracks run concurrently.
- **`~/.hermes/` context (6) parallelizes** with the Python build — it's persona/context, independent of the data plumbing, needed before skills (7).
- **Skills come last (7)** — they're thin orchestration over finished primitives. Building skills before primitives forces math into prose (Anti-Pattern 1).
- **The empirical Phase-1 task (confirm DataDoe source columns) gates the schema's exact column names** — keep `metric_snapshots` columns close to the Profit-by-SKU output to minimize transformation, but expect to finalize names after `exports_sources_get` in step 0.
- **No Act-layer work in M1** — `decision_ledger` ships as a table but its approval/write columns stay NULL until the M2/M3 gated-write milestone.

## Sources

- `/Users/mareekhalila/Documents/habib-os/.planning/PROJECT.md` — CA-first/US-ready schema, DataDoe-Profit authority, one resident agent, read-only/no-autonomous-write decisions
- `/Users/mareekhalila/Documents/habib-os/docs/01-architecture.md` — layered sense/think/state/surface model, morning-briefing flow, two-store rationale (revised 2026-06-08)
- `/Users/mareekhalila/Documents/habib-os/docs/04-data-tools-reference.md` — DataDoe call pattern, confirmed PPC + Profit-by-SKU sources, read-only contract
- `/Users/mareekhalila/Documents/habib-os/docs/05-open-decisions.md` — open schema/grain/FX questions this doc resolves
- `/Users/mareekhalila/Documents/habib-os/CLAUDE.md` — runtime (desktop app, Mac-awake), hard rules (read-only, hand-written money logic, secrets, logging)
- Hermes Agent desktop docs — skills as agentskills.io markdown, memory in `~/.hermes/`, MCP connections + cron in the desktop app (https://hermes-agent.nousresearch.com/docs/user-guide/desktop) [MEDIUM — confirms project's runtime assumptions]

---
*Architecture research for: read-only Amazon analytics workspace on Hermes desktop, single agent, DataDoe sense + Supabase truth*
*Researched: 2026-06-08*
