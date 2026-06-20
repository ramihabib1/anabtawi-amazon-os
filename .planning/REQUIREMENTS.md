# Requirements: Habib OS — Milestone v2.0 (Execution Era — Gated PPC Write Path)

**Defined:** 2026-06-20
**Core Value (milestone):** Turn reviewed PPC artifacts into real, approval-gated account changes via
the DataDoe Ads write actions — selling through existing FBA stock at a per-SKU margin-tiered TACOS
that protects net margin. PPC writes only; catalog refresh / restocks / listing writes deferred.

> Milestone 1 (read-only PPC/profit/inventory intelligence) requirements live in git history and
> `.planning/ROADMAP.md` (Phases 1–5). This file is the active Milestone v2.0 spec.

## v2.0 Requirements

### WRITE — Action execution via DataDoe `actions_start`

- [ ] **WRITE-01**: System validates any PPC write as a `dryRun` (returns VALIDATED + issues) before any real write is permitted
- [ ] **WRITE-02**: System pulls live campaign / ad-group / target / ad IDs via `*_FIND` before any UPDATE or REMOVE (FIND-before-write)
- [ ] **WRITE-03**: System executes a reversible PPC write end-to-end — pause campaign/keyword/ad, add negative keyword, lower a bid — build → dryRun → apply → poll `actions_get` → confirm
- [ ] **WRITE-04**: System executes a spend-increasing PPC write (raise bid/budget; create campaign/ad-group/ad/target) only after passing the margin gate AND explicit approval
- [ ] **WRITE-05**: System reconciles every applied write via `actions_get` (COMPLETED) + a `*_FIND` echo — never via next-day DataDoe exports (≤24h lag); a failed/blocked action refuses cleanly with the returned error
- [ ] **WRITE-06**: Every applied write logs a dated line to `state/decisions.md` and a `brain/raw/` note (what changed, why, expected effect, `actionId`)
- [ ] **WRITE-07**: Apply is idempotent — re-running the same approved action does not double-apply (idempotency key / ledger)

### GATE — Margin-tiered safety gate (engine, hand-written + pytest-covered)

- [ ] **GATE-01**: Engine computes each SKU's contribution margin from DataDoe window-summed components — typed, tested, never prose
- [ ] **GATE-02**: Engine derives a per-SKU TACOS ceiling from that margin to protect a configured minimum net margin; a missing min-margin threshold yields a refusal, never a default
- [ ] **GATE-03**: Spend-increasing writes must pass the gate (projected TACOS ≤ that SKU's ceiling); spend-decreasing writes (pause / negative / bid-down) always pass
- [ ] **GATE-04**: The gate refuses (never silently clamps) an over-ceiling bid/budget or sub-floor price, returning a typed refusal naming the breached number and its source
- [ ] **GATE-05**: The SKU→tier/contribution-margin table is machine-readable so the gate can consume it directly

### QUEUE — Daily action queue + approval spine

- [ ] **QUEUE-01**: System produces a daily dollar-ranked queue of proposed PPC changes — each dry-run-validated, showing current → proposed → expected effect with provenance
- [ ] **QUEUE-02**: Reversible moves carry standing approval (auto-apply after dry-run, within a magnitude cap); spend-increases and new campaigns require explicit approval
- [ ] **QUEUE-03**: A standing-approval magnitude cap prevents a "reversible" bid-down from killing a winner (bounded % change per action)
- [ ] **QUEUE-04**: The queue respects attribution lag — efficiency verdicts wait for a matured window (two-class: act-now reversible vs judge-later)

### EXEC — Apply the rebuild to the account (sell-through)

- [ ] **EXEC-01**: Stop-the-bleed — pause remaining dead/exiting-SKU ad spend + mis-scoped keywords, apply the negative-keyword harvest per-campaign, enforce the EXCLUDE-own-ASIN (B07TV972JT) denylist
- [ ] **EXEC-02**: Fund the engine-verified efficient winners up to their gate ceiling; consolidate internal keyword competition (same term live in multiple campaigns)
- [ ] **EXEC-03**: Build the new coverage-gap campaigns, paced to in-stock inventory, once the gate + apply spine are live
- [ ] **EXEC-04**: Archive the campaign graveyard (`CAMPAIGNS_REMOVE`) in a separate, explicitly-approved final batch
- [ ] **EXEC-05**: Inventory-paced budgets — never scale ad spend onto a SKU below stock-cover or conversion benchmark thresholds

## Out of Scope (Milestone v2.0)

| Feature | Reason |
|---------|--------|
| Listing-content writes (`AMAZON_LISTINGS_UPDATE`) | Deferred — PPC writes only this milestone; listing rebuilds stay manual reviewed artifacts |
| Restocks / new inventory | Work existing FBA stock only; restock funding deferred |
| Retiring products / adding products / new variations | Catalog refresh is a later milestone ("after we make a base in the PPC") |
| 800g-flagship-via-restock push | Depends on restock + listing work, both deferred |
| Portfolio creation/assignment | No DataDoe action exists; tier encoded in campaign name + tags instead (unless operator creates portfolios manually) |
| Shared negative-list library object | No such API object; negatives applied per-campaign |
| Autonomous spend-up | Every budget/bid increase and new campaign needs explicit approval |
| Unattended cron scheduling | Desktop app runs only while the Mac is open; daily queue is on-open/on-demand |

## Traceability

To be populated by the roadmapper — each requirement maps to exactly one phase.

| Requirement | Phase | Status |
|-------------|-------|--------|
| (filled during roadmap creation) | | |

**Coverage:**
- v2.0 requirements: 21 total
- Mapped to phases: (TBD)
- Unmapped: (TBD)

---
*Requirements defined: 2026-06-20*
