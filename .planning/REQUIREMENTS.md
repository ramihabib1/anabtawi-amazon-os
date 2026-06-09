# Requirements: Habib OS

**Defined:** 2026-06-08
**Core Value:** From the desktop workspace I can ask real PPC/profit questions and get correct answers against live DataDoe data — with zero risk of the system changing anything on Amazon.
**Milestone:** 1 — Foundation + PPC/profit intelligence (read-only, conversational)

## v1 Requirements

Requirements for Milestone 1. Each maps to roadmap phases. All are read-only — no writes to Amazon. The four ★ requirements are the literal M1 acceptance questions.

### Connections & Source Map

- [ ] **CONN-01**: Operator can verify DataDoe, Supabase, and Gmail/Drive MCP connections respond and DataDoe is read-only, from the Hermes desktop workspace
- [ ] **CONN-02**: System resolves and caches the amazon.ca seller UUID to `.env` as `AMAZON_CA_SELLER_ID`
- [ ] **CONN-03**: System records a DataDoe source map (confirmed sources, columns, ad-program scope, date-column timezone, premium Profit-by-SKU enablement status) empirically via `exports_sources_get`

### Supabase Truth Store

- [ ] **DATA-01**: Supabase schema exists for `sku_master`, `cogs`, `metric_snapshots`, `decision_ledger`, `config`, created via reviewed Alembic migrations with `pgvector` enabled
- [ ] **DATA-02**: `metric_snapshots` persists at daily × SKU × marketplace grain, idempotent on `(marketplace, seller_sku, snapshot_date)`, carrying `captured_at` + DataDoe export id
- [ ] **DATA-03**: `cogs` captures per-row landed cost with FX (`unit_cost`, `cost_currency`, `fx_rate`, `fx_as_of`) as a slowly-changing dimension
- [ ] **DATA-04**: `config` holds operator-supplied thresholds keyed by `(key, marketplace)`, seeded with real values (min margin %, ACOS ceiling, days-of-cover)
- [ ] **DATA-05**: A DataDoe export is persisted into `metric_snapshots` end-to-end against live data

### Agent Context & Persona

- [ ] **CTX-01**: Business context (business, SKUs, guardrails) is loaded into `~/.hermes` and version-controlled in the repo
- [ ] **CTX-02**: SOUL.md defines the operator persona (numbers-first, terse, flags risk, never invents pricing/thresholds)
- [ ] **CTX-03**: `~/.hermes` backup target and schedule are decided and documented

### PPC Intelligence (read-only)

- [ ] **PPC-01** ★: From the workspace, operator can ask "where am I wasting ad spend" and get correct, provenance-cited answers against live data
- [ ] **PPC-02** ★: Operator can ask "which search terms should I negate" and get a candidate list (proposal only, never auto-applied) with the spend/conversion data behind each
- [ ] **PPC-03** ★: Operator can ask "which campaigns are budget-capped" and get flagged campaigns (approximate, labelled as such — no native Lost-IS column in DataDoe)
- [ ] **PPC-04**: PPC primitives handle the DataDoe 2500-row cap (pre-aggregate or paginate) without silent truncation

### Profit & Margin (read-only)

- [ ] **PROF-01** ★: Operator can ask "what's my TACOS by SKU" and get correct ACOS/TACOS/ROI, preferring DataDoe premium Profit-by-SKU, each ratio labelled with its definition + source
- [ ] **PROF-02**: Per-SKU true margin reconciles DataDoe Profit against `cogs` with FX, stamping which source was authoritative; falls back cleanly when premium is unavailable

### Provenance & Anti-Fabrication

- [ ] **TRUST-01**: Every numeric answer cites provenance (DataDoe export id + config row); on a failed/empty export the system refuses ("no data") rather than substituting a number
- [ ] **TRUST-02**: All thresholds are read from Supabase `config` — never invented; a missing threshold yields refusal, not a default
- [ ] **TRUST-03**: Every external call (DataDoe export, Supabase) is wrapped and logged
- [ ] **TRUST-04**: The four acceptance answers are spot-checked manually against Seller Central and signed off

## v2 Requirements

Deferred to future milestones. Tracked but not in the current roadmap.

### PPC (deeper)

- **PPC-V2-01**: Keyword/target bid-context surfacing (top-of-search impression share, current bid) from Keyword Targeting Performance
- **PPC-V2-02**: Placement analysis — top-of-search vs rest-of-search vs product-page
- **PPC-V2-03**: Explicit margin-aware PPC reasoning (Profit-by-SKU × PPC spend join: "unprofitable for this SKU")
- **PPC-V2-04**: Budget-cap impact quantification (estimated lost sales from capping)

### Retention / Marketplace

- **RET-V2-01**: Repeat-purchase / CLV reconstruction from Order Line Items hashed buyer_email
- **MKT-V2-01**: US-marketplace-specific logic (schema is already US-ready in v1)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Any autonomous write to Amazon (bids, budgets, negatives, pricing, inventory, listings) | Structural guardrail; prior agency abused PPC/listing writes. Always human-approved, logged proposals. |
| Custom Amazon Ads / SP-API write-MCP | Deferred, gated milestone; manual execution until recommendations earn trust |
| Listing optimization intelligence | Milestone 2 |
| Scheduled / recurring PPC review | Milestone 3 |
| Agent Central as a data source | Removed; DataDoe (with attached Ads connection) is the single Amazon source |
| Invented thresholds or numbers | Anti-fabrication guardrail; all thresholds read from `config`, all numbers cite provenance |
| Hand-rolled ACOS/TACOS when premium column exists | Use DataDoe premium Profit-by-SKU as authority to avoid definition drift |
| Unattended clock-cron scheduling | Desktop app runs only while Mac is awake; M1 is conversational/on-demand |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| CONN-01 | Phase 1 | Pending |
| CONN-02 | Phase 1 | Pending |
| CONN-03 | Phase 1 | Pending |
| DATA-01 | Phase 1 | Pending |
| DATA-02 | Phase 1 | Pending |
| DATA-03 | Phase 1 | Pending |
| DATA-04 | Phase 1 | Pending |
| DATA-05 | Phase 2 | Planned |
| CTX-01 | Phase 1 | Pending |
| CTX-02 | Phase 1 | Pending |
| CTX-03 | Phase 1 | Pending |
| PROF-01 | Phase 2 | Planned |
| PROF-02 | Phase 2 | Planned |
| TRUST-01 | Phase 2 | Planned |
| TRUST-02 | Phase 2 | Planned |
| TRUST-03 | Phase 2 | Planned |
| TRUST-04 | Phase 2, 3, 4, 5 | Planned (P2) |
| PPC-01 | Phase 3 | Pending |
| PPC-04 | Phase 3 | Pending |
| PPC-02 | Phase 4 | Pending |
| PPC-03 | Phase 5 | Pending |

**Notes:**
- TRUST-01/02/03 (the trust spine) are built in Phase 2 (first slice) and apply throughout every later slice.
- TRUST-04 (manual Seller-Central spot-check) recurs as a success criterion in every acceptance-question slice (Phases 2–5).

**Coverage:**
- v1 requirements: 21 total
- Mapped to phases: 21 ✓
- Unmapped: 0

---
*Requirements defined: 2026-06-08*
*Last updated: 2026-06-08 after roadmap creation (traceability populated)*
