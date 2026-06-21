# Phase 7: Margin-Tiered Safety Gate - Context

**Gathered:** 2026-06-21
**Status:** Ready for planning

<domain>
## Phase Boundary

A hand-written, pytest-covered engine module (`gate.py` + `test_gate.py`, mirroring
`tacos.py`) that is the load-bearing safety guardrail for every spend-increasing PPC write.
It derives each SKU's TACOS ceiling from that SKU's own contribution margin (to hold net
margin ≥ the configured floor), and **refuses** — never clamps, never defaults — any
spend-up write whose projected TACOS breaches the ceiling, or any write touching a SKU /
threshold whose margin is unset. The gate sits in Python between BUILD and DRYRUN, before
any tool that can change the account.

**In scope:** the gate's money logic (per-SKU contribution margin, ceiling derivation,
projected-TACOS check, typed refusal grammar), the machine-readable SKU→tier/margin table
it consumes, and seeding the net-margin floor.

**Out of scope (later phases):** applying any real write (the apply spine = Phase 8); the
daily ranked queue and dollar estimates (Phase 9); the standing-approval magnitude cap and
act-now-vs-judge-later boundary (Phase 8/9); new-campaign chains and portfolios (Phase 10).
This phase changes nothing on Amazon — it only decides *whether a write would be allowed to
proceed*.
</domain>

<decisions>
## Implementation Decisions

### Ceiling formula (Q2, GATE-02)
- **D-01:** Ceiling is **fully margin-derived, per SKU**:
  `ceiling_tacos_pct(sku) = contribution_margin_pct(sku) − min_net_margin_pct`.
  Every ceiling traces to one floor number; there is **no separate per-tier ceiling table**.
  Worked examples: 39% CM → 24% ceiling; 20% CM → 5% ceiling. A SKU whose contribution
  margin **≤ the floor** yields a ceiling of ≤ 0% → **no spend-up permitted** (any positive
  TACOS breaches), which is the correct, surfaced behavior for the thin/below-floor baklava
  ASINs flagged in PITFALLS.md #2.
- **D-01a:** Tiers (HERO/MAINTAIN/CUT) remain **advisory PPC posture** (`state/targets.md`,
  the prose skills) — they are **NOT** gate inputs. No 25% hard cap is added: the "winners
  up to ~25%" figure in PROJECT.md is descriptive of what a fat-margin SKU's formula output
  looks like, not a separate clamp.

### Contribution-margin source (Q2, GATE-01)
- **D-02:** Contribution margin is **PRE-ad**, computed **live** from the premium
  Profit-by-SKU export's window-summed components (the same A1 window-sum approach as
  `tacos.py`):
  `contribution_margin_pct = (total_sales − COGS − fulfilment/referral fees) / total_sales`.
  Ad spend is **excluded** from the cost basis — otherwise the gate is circular (the ceiling
  would shrink as you spend).
- **D-03:** The researcher **must verify against `docs/datadoe-source-map.md`** whether the
  source's `profit_sum` already nets out ad spend; **if it does, `ad_spend_sum` is added
  back** so the margin is genuinely pre-ad. The catalog table's COGS (D-04) is the
  cross-check. A SKU whose export COGS is 0/null → margin treated **unreliable → gate
  refusal** (anti-fabrication), never a guessed or substituted margin.

### SKU→tier/margin table (Q3, GATE-05)
- **D-04:** A **new machine-readable file** the gate parses directly (e.g.
  `engine/config/sku_catalog.toml` — exact name/format is Claude's discretion), one row per
  SKU carrying: `sku`, `asin`, `tier`, `cogs` (landed = `cogs_total_value`). The gate reads
  **tier + COGS + the canonical SKU set**; per-SKU margin is **computed live** (D-02), **not
  stored** (avoids drift, consistent with the read-live trust-spine pattern).
- **D-05:** The prose SKU table in `anabtawi-context/SKILL.md` becomes a **rendering of this
  file** (single source of truth). A SKU **absent** from the file → typed gate **refusal**
  on funding it ("SKU not in catalog table") — correct GATE-05 behavior, surfaced as such,
  never defaulted.

### Projected TACOS of a write (GATE-03)
- **D-06:** Projected TACOS of a spend-**increasing** action = **sales held flat (worst
  case)**: `projected = (current_ad_spend_sum + Δspend) / current_total_sales_sum`, where
  `Δspend` derives from the `ProposedAction`'s before→after bid/budget. The action **passes
  only if projected ≤ the SKU's ceiling** (D-01). Spend-**decreasing** actions (pause /
  negative / bid-down) **skip the projection and auto-pass** the gate (locked by
  constitution + GATE-03).

### Net-margin floor (precondition)
- **D-07:** **Seed the real floor now:** `min_net_margin_pct = 15` for marketplace CA in
  `engine/config/thresholds.toml`, clearing the Phase 7 blocking precondition so spend-up
  can pass in Phase 8+. The **empty-refusal path is still built and tested** (SC-2: the gate
  refuses on *every* write while the floor is `""`) via a fixture/override, independent of
  the seeded live value.
- **D-07a:** **Key naming:** the roadmap/research term is `min_net_margin_pct`; the file
  currently has `min_margin_pct = ""`. Standardize on `min_net_margin_pct` as the key the
  gate reads (rename or alias is Claude's discretion; keep `thresholds.read(key,
  marketplace)`'s refuse-on-empty contract).

### Refusal grammar & types (GATE-04, carried from trust spine)
- **D-08:** `gate.py` returns a typed `GateVerdict` / `GateRefusal` mirroring
  `result.Refusal` + the `_present_flag` grammar: a breach **names the breached number and
  its source**; `"no threshold set"` when the floor is unset; `"no margin"` /
  `"SKU not in catalog"` when margin/SKU is missing. It **never silently clamps** to the
  limit (GATE-04). New types live in `result.py` alongside `Refusal` / `Proceed` /
  `PollOutcome`.

### Claude's Discretion
- Exact filename/format of the SKU catalog file; the `min_net_margin_pct` rename-vs-alias
  mechanics.
- `gate.py` module/function layout, the `ProposedAction` dataclass shape, and the
  `gate_action.py` thin CLI structure (mirror `answer_tacos.py`).
- Which fee components count as "fees" in D-02 (FBA fulfilment + referral) — researcher pins
  the exact column set against the source map.
- Rounding/precision of the derived ceiling and the projected TACOS.
</decisions>

<specifics>
## Specific Ideas

- The gate is the deliberate analog of `tacos.py`: the money decision is hand-written and
  tested, **never reasoned in chat** (CLAUDE.md hard rule 3). Refusal voice mirrors the
  existing `_present_flag` / `Refusal` grammar exactly so the operator sees a consistent
  anti-fabrication surface.
- Rami's posture (operator memory): aggressive growth, willing to "spend whatever it takes"
  on proven winners — but the gate is the floor that keeps that aggression from going
  loss-making on thin-margin SKUs. The formula (D-01) is what lets a high-margin winner ride
  a high ceiling *without* a flat number letting a thin SKU bleed.
- Below-floor SKUs (CM ≤ 15%) producing a ≤0% ceiling is a **feature, not a bug** — it is
  the gate correctly refusing to fund a SKU that can't carry ad spend at the target net
  margin. Surface it plainly, don't suppress it.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope, requirements & posture
- `.planning/ROADMAP.md` — Phase 7 section (goal + SC-1..5), the M2 "Constitution
  constraints" and "Blocking preconditions" tables (the gate is a hard predecessor to any
  spend increase).
- `.planning/REQUIREMENTS.md` — GATE-01, GATE-02, GATE-03, GATE-04, GATE-05.
- `.planning/PROJECT.md` — mission metric (net ≥ ~15%, break-even TACOS ≈ 39% t30, winners
  ≤ ~25%, thin ≤ ~12%) — the posture D-01's formula operationalizes.

### Open questions this phase resolves
- `.planning/research/STACK.md` — OQ1 (ceiling-formula derivation + margin source) and the
  "Engine Margin-Gate Module" section.
- `.planning/research/ARCHITECTURE.md` — "Where the Margin Gate Sits" (BUILD→DRYRUN
  enforcement point) and the component map (machine-readable SKU→margin/tier row).
- `.planning/research/PITFALLS.md` — #2 (flat TACOS overspends past the margin floor on
  thin-margin SKUs) — the failure D-01 prevents.
- `.planning/research/SUMMARY.md` — Q2/Q3 and Preconditions 1–3.

### Engine mirror pattern (the code to imitate)
- `engine/src/habibos/tacos.py` — parse / `_ratio` / `classify` window-sum pattern + the A1
  window-aggregation contract the margin computation reuses.
- `engine/src/habibos/result.py` — typed `Refusal` / `Proceed` / `PollOutcome` / `SkuRow`
  and the `_present_flag` grammar `GateRefusal` mirrors; add the gate types here.
- `engine/src/habibos/thresholds.py` — `read(key, marketplace)` refuse-on-empty contract the
  floor read must honor.
- `engine/scripts/answer_tacos.py` — the thin-CLI shape `gate_action.py` mirrors.

### DataDoe contract & config
- `docs/datadoe-source-map.md` — §3a premium Profit-by-SKU source (57a0cb319c), **verbatim**
  acos/tacos/roi/profit/cost definitions; researcher confirms here whether `profit_sum` is
  pre- or post-ad (D-03).
- `engine/config/thresholds.toml` — the `min_net_margin_pct` floor key to seed at 15 (D-07).
- `.claude/skills/anabtawi-context/SKILL.md` — the prose SKU→tier/COGS table that becomes a
  rendering of the new machine-readable catalog file (D-04/D-05).
- `state/targets.md` — the human tier dial (advisory tiers, kept in sync; NOT a gate input).
- `CLAUDE.md` — hard rules: data layer read-only, no autonomous writes, money math
  hand-written + reviewed + tested, never invent a threshold.
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `tacos.py` — `parse()` (pydantic-validated window-summed export), `_ratio()`, and
  `classify()` are the direct template; the margin computation is the same window-sum-then-
  divide shape over `total_sales_sum` / `total_cost_sum` / `ad_spend_sum`.
- `result.py` — `Refusal` (reason/code/export_id) and `_present_flag`'s "breach" /
  "no threshold set" grammar; `GateVerdict`/`GateRefusal` are new siblings here.
- `thresholds.py` — `read(key, marketplace)` already implements refuse-on-empty; the floor
  read plugs straight in.
- Phase 6 substrate (`lifecycle.py`, `find_cache.py`) — the gate's verdict is what gates the
  BUILD→DRYRUN handoff those modules feed; the gate is the missing middle step (§A.5 gap).

### Established Patterns
- Money-touching logic is hand-written + pytest-covered, never auto-generated (`test_gate.py`
  is mandatory; `cd engine && uv run pytest` must stay green).
- A1 window aggregation: ratios/margins computed from server-side `groupBy sku` + `*_sum`
  components, applying verbatim definitions — never re-deriving a metric, never averaging a
  daily ratio.
- Refuse-never-default / refuse-never-clamp is the project's core anti-fabrication contract.

### Integration Points
- `gate.py` consumes a `ProposedAction` (target SKU(s), before→after spend/bid/budget) + the
  SKU catalog file (D-04) + the premium export components + `thresholds.read`.
- It sits **between BUILD and DRYRUN** — Phase 8's apply spine calls the gate before any
  `actions_start dryRun` so a margin-breaching write never reaches Amazon's validator.
- A thin `gate_action.py` CLI mirrors `answer_tacos.py` for direct/agent invocation.
- No Supabase, no Amazon write in this phase.
</code_context>

<deferred>
## Deferred Ideas

- The reversible-write apply spine + stop-the-bleed (the gate's first real consumer) →
  **Phase 8**.
- Daily dollar-ranked queue + projected-$ estimate rows → **Phase 9**.
- Standing-approval magnitude cap on bid-down/negatives (research Q4) and the act-now vs
  judge-later attribution boundary (research Q1) → **Phase 8 / 9**.
- Portfolios decision (research Q5) and new-campaign projected-TACOS seed for no-history
  campaigns → **Phase 10**.
- Migrating `thresholds.toml` (incl. `min_net_margin_pct`) and the SKU catalog → the
  Supabase `config` / `sku_master` tables → **Phase 3.5** (Supabase truth store).

</deferred>

---

*Phase: 07-margin-tiered-safety-gate*
*Context gathered: 2026-06-21*
