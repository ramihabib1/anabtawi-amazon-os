# Phase 9: Daily Ranked Queue + Explicit-Approval Spend-Up - Context

**Gathered:** 2026-06-24
**Status:** Ready for planning

<domain>
## Phase Boundary

A daily, dollar-ranked, dry-run-validated queue of proposed PPC changes becomes the standing
operating rhythm — each line showing **current → proposed → expected effect** with provenance —
and gate-passed bid/budget **raises** fund the engine-verified efficient winners under
**explicit approval**, never scaling onto immature attribution data, internal keyword
competition, sub-cover stock, or below-benchmark conversion. (Runbook Waves 2–3.)

**In scope:** the daily queue ranker + renderer (`rank_queue.py` + `queue.py`, reusing the
`tacos.classify` sort idiom), the spend-up path (raise bid/budget) gated by the margin gate +
explicit approval, the inventory/conversion spend-up gates (≥6-week cover, ≥12% conversion),
internal-keyword-competition consolidation, search-term harvest graduation, the two-class
attribution model (act-now reversible vs judge-later matured-window), phrase/broad negatives as
an explicit-approval class, and flipping the magnitude cap from permissive to a real 50% bound.

**Out of scope (later phases / deferred):** building brand-NEW coverage-gap campaigns,
portfolios, and the graveyard `CAMPAIGNS_REMOVE` archive → **Phase 10** (EXEC-03/04). Listing
writes, restocks, catalog refresh → deferred milestones. Unattended cron → out of scope (queue
is on-open / on-demand). Migrating thresholds/catalog to Supabase → Phase 3.5.
</domain>

<decisions>
## Implementation Decisions

### Autonomy classification — magnitude cap & negative scope (QUEUE-02, QUEUE-03, SC-5)
- **D-01:** **Flip the reversible-move magnitude cap ON at 50%.** Set
  `max_reversible_pct_change = 50` in `engine/config/thresholds.toml[marketplace.CA]`. A single
  reversible bid/budget-**down** steeper than −50% per action is **refused and routed to explicit
  review** — `magnitude.check` already returns `GateRefusal(over_cap)` and **never clamps** (it
  surfaces the breaching % verbatim). The mechanism is built + pytest-covered from Phase 8 (08
  D-02); this is a config flip, not new code. Rationale: a daily *standing* auto-apply rhythm has
  a bigger blast radius than Phase 8's one-batch canary, so the SC-5 guardrail goes live now.
  (Equal-to-cap passes — strict `> cap` breach, mirrors GATE-04.)
- **D-02:** **Phrase/broad negative keywords require explicit approval.** Exact-match negatives
  keep **standing approval** (auto-apply after dryRun — they are reversible, narrow-collateral
  spend cuts, per 08 D-04). Phrase/broad negatives suppress a wider, harder-to-see net of
  adjacent traffic, so they are classed with the spend-ups: **held for explicit approval**. The
  decision is driven by **blast radius, not just reversibility**. The keep-positive allowlist
  (`baklava gift box`) still guards known-good terms before any negate (08 D-04 carried forward).

### Inventory & conversion spend-up gates (EXEC-05)
- **D-03:** **Stock-cover floor = 6 weeks, flat.** Refuse any spend-**increase** (raise bid/budget)
  on a SKU with **< 6 weeks of cover** (on-hand + inbound ÷ velocity). Encode as a single
  machine-readable number (`days_of_cover_floor = 42` in `thresholds.toml`, or an explicit
  weeks field) — refuse-never-default: a missing floor refuses, never assumes. This is the gate
  that refuses GG-0DC1 (1 FBA unit) from any budget scale-up.
- **D-04:** **Velocity / cover read live from the DataDoe / AgentCentral MCP at queue time**
  (`get_sales_velocity` / `get_days_of_cover` / `get_fba_inventory`). The agent does the MCP I/O
  and feeds the numbers into the **pure** engine ranker/gate (engine opens no socket — CLAUDE.md
  hard rule 1 + the M2 architecture: agent does MCP I/O, engine owns the math). The queue is
  on-open/on-demand, so a fresh live read is the right currency for a daily gate.
- **D-05:** **Conversion floor = 12% (provisional), hard-refuse.** Refuse a spend-up on a SKU
  converting below `conversion_benchmark` (12%, from `state/targets.md`). It is a hard refusal
  this phase, not advisory. Marked PROVISIONAL — retune to portfolio top-quartile after a
  `get_sales_and_traffic` / `sales_and_traffic` pull reveals the real distribution (deferred).

### Daily queue rendering & approval UX (QUEUE-01, QUEUE-02, WRITE-04)
- **D-06:** **Explicit approval = batch-approve after review.** The queue renders every proposed
  **raise** dollar-ranked; Rami reviews and approves the whole spend-up batch with **one
  deliberate explicit confirm** (deselecting lines first is allowed). Mirrors the Phase 8
  canary→batch rhythm — fast daily cadence, still one human gate. Standing-approved reversibles
  auto-apply and appear on the queue as already-actioned (autonomy ≠ silence, 08 D-11).
- **D-07:** **Render as ONE dollar-ranked, class-tagged table.** Sorted by **expected weekly $
  impact, descending**, with **no-$-estimate rows last** (SC-1; reuse the `tacos.classify` sort
  idiom). Each row carries: `rank | SKU | entity | action | current → proposed | expected $/wk |
  provenance | class (auto / needs-approval)`. Dollars-first, one screen (CLAUDE.md rank-by-dollars
  rule). Provenance cites the DataDoe source + window behind each number (hard rule 5).

### Internal keyword competition & harvest graduation (EXEC-02, QUEUE-04)
- **D-08:** **Owning campaign = lowest matured-window ACOS.** When a term is live in >1 ENABLED
  campaign, the **most efficient** campaign (lowest ACOS over a matured window) owns the term; the
  term is **paused in the others** (a reversible spend-cut → standing approval; the 50% bounded-%
  cap does **not** apply to a state-change pause, only to bounded bid/budget % moves). The bid-**up**
  on the owning campaign is **blocked until consolidation completes** — no bidding against yourself.
- **D-09:** **Harvest graduation = ≥2 attributed orders AND ACOS at/under that SKU's gate ceiling**,
  measured over a **matured window (≥7d SP / ≥14d SB/SD)**. A search term meeting both bars is
  **proposed** as a new funded keyword — which is a spend-up, so it carries **explicit approval**.
  Demands proven conversion *and* efficiency before any new dollar is committed.

### Two-class attribution model (QUEUE-04 — locked by roadmap, carried forward)
- **D-10:** **Act-now (reversible stop-loss, standing approval)** fires only on *obviously-dead*
  signals that do **not** depend on a matured window: inactive listing / zero lifetime orders /
  ENABLED on a discontinued SKU. **Judge-later (efficiency verdicts)** wait for a matured window
  (≥7d SP / ≥14d SB/SD); "3 clean days" means 3 days of **matured** data. No efficiency verdict
  ever acts on an immature window (the #1 pitfall).

### Spend-up amount bound (WRITE-04, EXEC-02 — carried forward)
- **D-11:** A funded winner is raised **up to its margin-gate ceiling** (projected TACOS ≤ that
  SKU's per-SKU ceiling); an over-ceiling raise is **refused, not clamped** (WRITE-04 / GATE-04).
  The spend-up runs the full apply spine from Phase 8 (denylist → margin gate → dryRun → apply →
  poll → FIND-echo → idempotent ledger + `decisions.md`/`brain/raw` log).

### Claude's Discretion
- Exact `rank_queue.py` / `queue.py` module + function layout and the thin CLI shape (mirror the
  existing thin CLIs `answer_tacos.py` / `gate_action.py` / `apply_action.py`).
- The expected-$/wk impact estimator's exact formula (must be hand-written + pytest-covered;
  provenance-cited; no-estimate rows sort last rather than guess).
- Precise rendering layer (terminal table vs markdown deliverable) — keep dollars-first, one screen.
- The `days_of_cover_floor` encoding (42 days vs an explicit weeks field) — pick one, document it.
- Poll/backoff reuse from the Phase 8 spine; idempotency identity reuse (08 D-10).
- How "matured window" is detected per campaign type (data-availability check vs fixed lookback).
</decisions>

<specifics>
## Specific Ideas

- **The queue IS the standing operating rhythm** — it replaces ad-hoc analysis with a daily,
  dollar-ranked, dry-run-validated artifact. Everything reversible has already happened (shown for
  transparency); everything that spends *up* waits in one batch for an explicit yes.
- **Every number on the queue traces to reviewed code or a cited live pull** — expected-$ impacts
  are hand-written + pytest-covered, never chat estimates (CLAUDE.md hard rule 3); a row with no
  defensible $ estimate sorts last rather than fabricating one (hard rule 4).
- **Permissive→capped is the deliberate Phase-8→9 transition:** the magnitude cap was built-but-off
  for the canary; daily standing operation is exactly when the 50% guardrail should bind.
- **Efficiency before volume** runs through every spend decision: lowest-ACOS owns a contested term
  (D-08); harvest needs at/under-ceiling efficiency *and* ≥2 orders (D-09); raises stop at the
  margin-gate ceiling (D-11).
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope, requirements & posture
- `.planning/ROADMAP.md` — Phase 9 section (goal + SC-1..5), the M2 Constitution constraints and
  Blocking-preconditions tables.
- `.planning/REQUIREMENTS.md` — WRITE-04, QUEUE-01, QUEUE-02, QUEUE-03, QUEUE-04, EXEC-02, EXEC-05.
- `.planning/PROJECT.md` — mission metric (net ≥ ~15%), reversibility-classed autonomy posture,
  rank-by-dollars.
- `.planning/phases/08-reversible-write-apply-spine-stop-the-bleed/08-CONTEXT.md` — carried
  decisions: standing vs explicit (D-01), magnitude-cap mechanism seeded permissive (D-02),
  negative scope/keep-positive allowlist (D-04), idempotency identity (D-10), logging (D-11).
- `.planning/phases/07-margin-tiered-safety-gate/07-CONTEXT.md` — gate auto-passes spend-decreasing
  (D-06), gate sits BUILD→DRYRUN, build-refusal-then-seed-live pattern.

### Operational intel
- `brain/raw/2026-06-16_ppc-coverage-gap.md` — internal keyword competition, the funded-winner
  candidates, keep-positive / watch-don't-negate intent.
- `brain/raw/2026-06-20_datadoe-write-path-gating.md` — the 4-gate chain, granted Ads action types,
  dryRun discipline, Settings→Actions org-enable precondition.

### Engine substrate (the code to drive / imitate)
- `engine/src/habibos/tacos.py` — the `classify` sort idiom the queue ranker reuses (dollars-first).
- `engine/src/habibos/magnitude.py` — `check(action, max_reversible_pct_change)`: refuse-over-cap /
  never-clamp; D-01 flips its dial to 50.
- `engine/src/habibos/gate.py` + `engine/src/habibos/result.py` — `gate.evaluate`, `ProposedAction`,
  `GateVerdict`/`GateRefusal`; projected-TACOS-≤-ceiling, refuse-never-clamp grammar (D-11).
- `engine/src/habibos/apply.py` + `engine/src/habibos/ledger.py` — the Phase-8 apply spine +
  idempotency ledger every spend-up reuses end-to-end.
- `engine/src/habibos/find_cache.py`, `engine/src/habibos/lifecycle.py`,
  `engine/src/habibos/datadoe.py`, `engine/src/habibos/logging.py` — FIND-before-write/echo, poll
  classifiers, the seam, the logged call.
- `engine/config/thresholds.toml` — `max_reversible_pct_change` (D-01), `days_of_cover_floor`
  (D-03), `min_net_margin_pct` (gate floor); `engine/config/sku_catalog.toml` — per-SKU COGS/tier;
  `engine/config/owned_asins.toml` — denylist (08 D-06a).
- `state/targets.md` — `min_weeks_cover_*` (6 = maintain, D-03), `conversion_benchmark` (12%, D-05),
  tiered ACOS postures.

### Project skills (read SKILL.md patterns)
- `.claude/skills/datadoe-query/SKILL.md` — the live data pulls behind D-04 (velocity/cover) and
  provenance; `.claude/skills/ppc-analysis/SKILL.md` — bid/budget change-sheet idioms;
  `.claude/skills/anabtawi-context/SKILL.md` — SKU tiers / ASIN map.

### Constitution
- `CLAUDE.md` — hard rules: data layer read-only (engine opens no socket), no autonomous writes
  without approval, money/write logic hand-written + reviewed + tested, never invent a
  threshold (missing → refuse), log every external call + cite source/window, secrets in `.env`.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tacos.classify` — the dollars-first sort idiom the queue ranker reuses (D-07).
- `magnitude.check` — already built + tested; D-01 only sets its config value to 50.
- `gate.evaluate` — every spend-up routes through it (projected TACOS ≤ ceiling; D-11).
- `apply.py` + `ledger.py` + `find_cache` + `lifecycle` poll classifiers — the full Phase-8 spine
  a spend-up reuses unchanged (BUILD → denylist → gate → dryRun → apply → poll → FIND-echo → log).
- `result.py` typed `Refusal` grammar — the inventory/conversion/cap refusals reuse it.

### Established Patterns
- Refuse-never-default / refuse-never-clamp; typed verdicts, never bare True/None.
- Build-the-mechanism-then-flip-the-dial (07 D-07 / 08 D-02) — D-01 is the dial flip.
- Hand-written + pytest-covered for any money/write logic; `cd engine && uv run pytest` stays green.
- Agent does MCP I/O; engine is pure (D-04 live reads happen in the agent/CLI layer, not engine).
- Every external call logged + source/window cited (provenance column, D-07).

### Integration Points
- New `rank_queue.py` (ranker/estimator) + `queue.py` (render + class tagging) in
  `engine/src/habibos/`, plus a thin CLI script under `engine/scripts/` (mirror `apply_action.py`).
- The CLI orchestrates: agent pulls live velocity/cover/conversion + campaign/term data → feeds
  the pure engine ranker + gate → renders the class-tagged table → batch-approval gate → drives the
  existing apply spine for approved raises and auto-applies standing-approved reversibles.
- New thresholds consumed: `max_reversible_pct_change=50`, `days_of_cover_floor=42`; existing:
  `min_net_margin_pct`, `conversion_benchmark`, per-SKU COGS/tier.
- No new campaigns, no portfolios, no `CAMPAIGNS_REMOVE`, no Supabase this phase.
</code_context>

<deferred>
## Deferred Ideas

- Building brand-NEW coverage-gap campaigns + portfolios + the graveyard `CAMPAIGNS_REMOVE` archive
  → **Phase 10** (EXEC-03/04).
- Retuning the conversion benchmark from 12% provisional to portfolio top-quartile (needs a
  `sales_and_traffic` pull + computed value) → after this phase.
- Tightening the magnitude cap below 50% if a reversible move ever still hurts a winner → config
  dial edit, not code.
- Tier-aware cover floors (hero 8 / maintain 6 / cut 3) instead of a flat 6 → revisit if the flat
  floor proves too coarse.
- Migrating `thresholds.toml` + SKU catalog → Supabase `config` / `sku_master` → Phase 3.5.

</deferred>

---

*Phase: 09-daily-ranked-queue-explicit-approval-spend-up*
*Context gathered: 2026-06-24*
