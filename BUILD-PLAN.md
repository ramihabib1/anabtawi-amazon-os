# Build Plan — Anabtawi Amazon OS on Claude Cowork

A staged rollout. Each phase is shippable on its own and earns its keep before the next.
Don't boil the ocean: get the daily loop breathing first, then widen coverage, then add the
edges that actually separate top operators.

Honest framing up front: tooling doesn't make a top-1% seller — sourcing, product, and your
judgment do. What this system does is remove the two things that keep good sellers average:
**blind spots** (you don't see the problem until it's expensive) and **latency** (you see it
but react days late). It also forces **decision logging**, so your learning compounds instead
of evaporating. The edges that matter — accurate landed COGS, never stocking out a hero,
ruthless negative-keyword discipline, conversion and review velocity, fast anomaly response —
are all operationalized below. The calls stay yours.

---

## Phase 0 — Foundation (Day 1)
**Goal: the system reads your real numbers.**
- [ ] Put `anabtawi-amazon-os/` where Claude Desktop can reach it; point Cowork at the folder.
- [ ] Turn on connectors for this workspace: **DataDoe** (data), **Claude in Chrome** (live
      listing checks), **Tavily** (research). Confirm the DataDoe server resolves to the name
      `datadoe` used in the agent files (or rename in each `mcpServers`).
- [ ] Fill the SKU → ASIN → tier → landed-COGS table in
      `.claude/skills/anabtawi-context/SKILL.md`. **This is the highest-leverage 30 minutes in
      the whole build** — profit math is only as good as COGS.
- [ ] Set real numbers in `state/targets.md`.
- [ ] Manually run `tasks/morning-briefing.md` once. Verify the data path end-to-end (export →
      poll → download → analysis). Correct any source/column mismatch in `datadoe-query`.
**Done when:** a briefing comes back with your actual yesterday numbers and no errors.

## Phase 1 — The daily loop, live (Week 1)
**Goal: you wake up to a ranked briefing instead of opening Seller Central.**
- [ ] Register `morning-briefing` (daily ~07:00) and `ppc-daily` (daily midday) as Cowork
      scheduled tasks.
- [ ] Run for 3–5 days. Each morning, correct what it got wrong — wrong threshold, missed
      nuance, noisy flag. The brain (`brain/raw/daily/`) starts filling automatically.
- [ ] Tune `targets.md` until the briefing surfaces only things you'd actually act on.
**Done when:** the briefing is trustworthy enough that you act on it without re-checking.

## Phase 2 — Full coverage (Week 2)
**Goal: PPC, inventory, profit, and listings all covered on cadence.**
- [ ] Wire in the missing DataDoe sources (discover via `exports_sources_get`, verify columns,
      add to `datadoe-query`):
      - **Search-term / targeting** → unlocks negative-keyword mining (biggest PPC waste lever).
      - **Returns / concessions** → true profit + product-quality signal.
      - **Settlement / fee detail** → catch fee changes and reimbursements.
      - **Reviews / ratings** → feeds the review-intelligence loop in Phase 4.
- [ ] Stand up `restock-weekly`, `business-review-weekly`, and `pnl-monthly` as scheduled tasks.
- [ ] Confirm deliverables render: restock xlsx, review pptx, monthly P&L xlsx.
**Done when:** every domain has an owner and a cadence, and nothing relies on you remembering.

## Phase 3 — The brain (Week 2–3)
**Goal: the system remembers and gets sharper each week.**
- [ ] Turn on `brain-compaction-weekly`.
- [ ] Seed `brain/wiki/skus/` from the monthly tiering (one profile per active SKU).
- [ ] Point **Obsidian** at `brain/` for the human view (graph, backlinks, mobile). Keep it a
      plain note vault — no plugin rabbit hole.
- [ ] After two compactions, sanity-check that `wiki/` is staying tight and useful.
**Done when:** agents cite prior context ("last time this SKU's conversion dropped it was the
main image") instead of starting cold.

## Phase 4 — Intelligence edges (Week 3–4)
**Goal: react faster than competitors and turn customers into product signal.**
- [ ] **Competitor / hijacker watch** — a scheduled Chrome+Tavily task: buy-box owner, price
      moves, new competitors, listing changes on your hero ASINs. Anomalies → `brain/raw/` +
      next briefing.
- [ ] **Review-intelligence loop** — mine new reviews/returns weekly for themes → concrete
      listing fixes, product/packaging notes, and PPC negative signals. Themes → `wiki/customers.md`.
- [ ] **Anomaly alerts** — buy-box loss, listing suppression, sudden sales/ACOS swings flagged
      same-day, not next briefing.
**Done when:** you find out about a hijacker or a suppressed listing the day it happens.

## Phase 5 — Close the loop (when the recommendations are trustworthy)
**Goal: approved changes execute from the workspace.**
- [ ] Build an **approval-gated write-back MCP in Python** (Amazon Ads API for bids/budgets,
      SP-API for price/restock/listing). This is your Phase-2 from the design.
- [ ] Flow: agent proposes → **dry-run diff** → you say "apply" → write → append to
      `state/decisions.md`. Never auto-apply; the gate is the point.
- [ ] Start with the lowest-risk surface (PPC bid/budget) before prices or listings.
**Done when:** "approve the PPC sheet" actually pushes the changes, logged.

## Phase 6 — Compounding & scale (ongoing)
**Goal: the flywheel.**
- [ ] Weekly: review `state/decisions.md` against outcomes in the business review — did the
      change pay off? Retune `targets.md`. Graduate repeated wins into `wiki/playbooks/`.
- [ ] Quarterly: re-tier the catalog; prune CUT SKUs; double down on HEROs.
- [ ] **Scale the same brain to new surfaces** — add Amazon US / Walmart as DataDoe
      sellers/connections and reuse every skill, agent, and playbook unchanged. The marginal
      cost of the next marketplace is near zero once this exists.

---

## Connector & data checklist
| Need | Source | Status |
|------|--------|--------|
| Sales / profit / ads / inventory | DataDoe (connected) | ready |
| Live listing & competitor checks | Claude in Chrome | enable per workspace |
| Web/keyword research | Tavily | enable per workspace |
| Negative-keyword mining | DataDoe search-term source | discover (Phase 2) |
| Returns, fees, reviews | DataDoe sources | discover (Phase 2) |
| Write-back (execute changes) | Custom Ads/SP-API MCP (Python) | build (Phase 5) |

## The one-line operating loop
**Pull (DataDoe) → Reason (skills) → Recommend (deliverables) → Approve (you) → Act (Phase 5)
→ Remember (brain) → Compound (weekly review).** Everything above is just filling in that loop
and widening what it covers.
