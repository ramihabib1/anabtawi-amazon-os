# Architecture Research — Milestone v2.0 (Gated PPC Write Path)

**Researched:** 2026-06-20
**Mode:** Architecture integration (build ON the existing read-only engine)
**Confidence:** HIGH (grounded in read source + verified write-path facts; no training-data guesses)

**Paths read:** `.planning/PROJECT.md` · `.planning/ROADMAP.md` ·
`deliverables/ppc-rebuild-execution-plan_2026-06-20.md` ·
`brain/raw/2026-06-20_datadoe-write-path-gating.md` ·
`engine/src/habibos/{tacos,result,thresholds,datadoe,logging}.py` ·
`engine/scripts/answer_tacos.py` · `engine/config/thresholds.toml` ·
`engine/` file tree · `.claude/skills/` · `data/` exports.

> Supersedes the M1 read-only architecture doc previously at this path. M1 architecture
> facts are still in `.planning/ROADMAP.md` and the engine source.

---

## The integration thesis (one paragraph)

M1 proved a pattern: **the agent does the I/O over MCP; hand-written Python owns the
truth.** `answer_tacos.py` is a thin CLI the Hermes skill calls AFTER the agent downloads
a DataDoe export — Python parses, classifies, refuses, and cites provenance, but never
opens a socket (`datadoe.py` "the seam"). M2 extends that exact seam to writes: the agent
runs `actions_start`/`actions_get` over MCP; a new hand-written **`writes` core** builds
the payload, **gates it on margin**, interprets the dryRun/poll JSON, and emits the
decision-log line. The write tool is new; the discipline (typed `Result`, `logged_call`,
threshold-or-refuse, recommendation voice) is reused verbatim.

---

## Component Map (new vs modified)

### NEW — engine (`engine/src/habibos/`)
| Module | Responsibility | Mirrors |
|--------|---------------|---------|
| `actions.py` | Typed action model: `ProposedAction` (kind, target IDs, before→after, reversibility, est. $/day delta), `ActionBatch`, `ValidationResult`, `ApplyResult`. The write analog of `result.py`. | `result.py` |
| `gate.py` | **The margin gate.** `evaluate(action, sku_margin, tier_ceiling) -> Allowed \| GateRefusal`. Refuses any spend-up / bid-up / budget-up / new-campaign whose implied TACOS breaches the SKU's margin-derived ceiling. Same refusal grammar as `tacos._present_flag`. | `tacos.py` + `thresholds.py` |
| `payload.py` | Build the exact `actions_start` JSON per action type from a `ProposedAction` (CAMPAIGNS_UPDATE, TARGETS_UPDATE, TARGETS_ADD negative, ADS_REMOVE/ADD, the CAMPAIGNS_ADD→AD_GROUPS_ADD→ADS_ADD→TARGETS_ADD chain). Pure function: action in, schema-valid JSON out. | (new — pure) |
| `lifecycle.py` | Interpret the async loop's JSON: classify a `dryRun` response (VALIDATED/valid/issues), classify an `actions_get` poll (status → COMPLETED/FAILED/in-flight), decide retry vs terminal. Reuses `datadoe.poll_status` (already terminal-on-FAILED). | `datadoe.py` |
| `queue.py` | Daily ranked action queue: ingest proposed actions, attach $ impact, sort by dollars, emit the queue JSON the skill renders. | `tacos.classify` sort |
| `idempotency.py` | Dedup + retry safety: content hash per action so a re-run doesn't double-apply; map an in-flight `actionId` to its proposal so a poll resumes rather than re-fires. | (new) |

### NEW — scripts (`engine/scripts/`)
| Script | Role |
|--------|------|
| `gate_action.py` | Thin CLI: proposed action + SKU margin → `Allowed`/`GateRefusal` JSON. Called before any dryRun. |
| `build_payload.py` | Thin CLI: proposed action → validated `actions_start` payload JSON (agent fires with `dryRun:true`). |
| `rank_queue.py` | Thin CLI: list of proposed actions → dollar-ranked daily queue JSON. |
| `log_action.py` | Thin CLI: a completed `ApplyResult` → the `decisions.md` line + `brain/raw/` note body (closes the loop deterministically, not in prose). |

### NEW — config / state
| Artifact | Role |
|----------|------|
| `config/thresholds.toml` → `[marketplace.CA.tiers]` | Per-tier margin-derived TACOS ceilings (hero ≤~25 / maintain ~28 / cut ≤~12; floor protecting net ≥~15%). Gate reads these; missing → refuse, never default. |
| machine-readable SKU→margin/tier | Per-SKU contribution margin + tier the gate needs. Partly present in `anabtawi-context` SKILL as prose; gate needs it parseable. |
| `data/ads_*_find_*.json` | Cached FIND results (live campaignId/targetId/adId) — the read that makes any UPDATE/REMOVE executable. |

### NEW — skill (`.claude/skills/`)
| Skill | Role |
|-------|------|
| `ppc-execute` (or extend `ppc-analysis`) | The write playbook: FIND → build payload → gate → dryRun → approve → start → poll → reconcile → log. Encodes standing-vs-explicit approval + the dryRun-first rule. |

### MODIFIED — existing
| File | Change |
|------|--------|
| `engine/config/thresholds.toml` | Add tier ceilings + set `min_margin_pct` (currently empty `""` → gate refuses while empty). |
| `.claude/skills/datadoe-query/SKILL.md` | Add write-action section: `actions_start`/`actions_get`/`actions_list`/`actions_details_schema_get`, FIND-before-write, dryRun discipline. |
| `.claude/skills/ppc-analysis/SKILL.md` | Hand off flagged waste/negatives/bid-downs to the queue as `ProposedAction`s instead of ending at prose. |
| `state/decisions.md` | Already append-only; now also fed by `log_action.py` with `actionId` + before/after. |
| `CLAUDE.md` Golden Rule 1 | Already "never act silently" — name the standing-approval class explicitly. |

### REUSED UNCHANGED (the spine)
`result.py` (typed Refusal/Answer pattern), `logging.py` (`logged_call` wraps every
`actions_start`/`actions_get`), `datadoe.py:poll_status` (terminal-on-FAILED poll),
`thresholds.py:read` (missing→refuse reader), the thin-CLI-over-MCP seam.

---

## The Write Action Lifecycle (build → dryRun → approve → start → poll → reconcile → log)

```
0. FIND (read-only, no approval)     agent: AMAZON_ADS_*_FIND (one adProduct/req)
   └─ cache live campaignId/targetId/adId → data/ads_*_find_*.json
                                       (prerequisite — no UPDATE/REMOVE without it)

1. BUILD     payload.build(action)   engine: ProposedAction → actions_start JSON
   └─ pure, schema-shaped, IDs from step 0

2. GATE      gate.evaluate(...)      engine: margin ceiling check  ◀── ENFORCEMENT POINT
   └─ Allowed → continue ; GateRefusal → STOP, surface verbatim (never a default)

3. DRYRUN    agent: actions_start(dryRun:true)  → VALIDATED / valid / issues[]
   └─ lifecycle.classify_dryrun(resp): invalid or issues → STOP & report

4. APPROVE   standing | explicit (policy below)
   └─ reversible (pause/negative/bid-down) → standing, auto-proceed
   └─ spend-up / budget-up / new-campaign / CAMPAIGNS_REMOVE → explicit human OK

5. START     agent: actions_start(dryRun:false)  → actionId (async)
   └─ wrapped in logged_call("action_start", ...) ; idempotency hash recorded

6. POLL      agent: actions_get(actionId) until COMPLETED|FAILED
   └─ lifecycle uses datadoe.poll_status semantics (terminal on FAILED — no infinite spin)

7. RECONCILE verify via actions_get + Amazon console, NOT next-day DataDoe
   └─ DataDoe reporting lags ≤24h (verified) → console is the same-day source of truth

8. LOG       log_action.py(ApplyResult)
   └─ one line → state/decisions.md (what, before→after, actionId, expected $)
   └─ one note → brain/raw/ (what the change was, why; compiled into brain/wiki/)
```

**Idempotency/retry (5–6):** each `ProposedAction` carries a content hash; a re-run with
a hash that already has a COMPLETED `actionId` (looked up via `actions_list`) is a no-op.
A FAILED action is terminal — surfaced, not blindly retried (mirrors `poll_status`
refusing to spin on FAILED). An in-flight `actionId` resumes at step 6, never re-fires 5.

**FIND-before-write (binding):** UPDATE/REMOVE/ADD-onto-existing all require a live entity
ID. FIND is read-only and ungated — run it first, cache to `data/`. A write whose IDs
aren't in cache is refused at BUILD ("stale/missing entity ID").

---

## Where the Margin Gate Sits (the enforcement point)

**Between BUILD (step 1) and DRYRUN (step 3) — step 2, in Python, before any tool that can
change the account.** The deliberate analog of `tacos.py`: the money decision is
hand-written and tested, never reasoned in chat.

- **Input:** a `ProposedAction` (its target SKU(s), before→after spend/bid/budget) + the
  SKU's contribution margin + its tier ceiling from `thresholds.toml`.
- **Rule:** compute the *implied* TACOS the action moves toward; if it would breach the
  SKU's margin-derived ceiling (the net-margin ≥~15% floor), return `GateRefusal` with the
  same grammar as `_present_flag` ("breach"; "no threshold set" when ceiling/margin
  unset). **A missing margin or ceiling REFUSES the write — never a default 25%** (the
  exact anti-fabrication rule from `thresholds.py`).
- **Scope (two different axes):** only **spend-increasing** actions must *pass* the gate
  (bid-up, budget-up, new-campaign, placement-up). **Spend-decreasing** actions (pause,
  negative, bid-down) are always gate-allowed (they protect margin) and route to standing
  approval.
- **Why here, not at dryRun:** dryRun validates the payload against *Amazon's* schema; it
  knows nothing about *our* margin floor. The gate is OUR guardrail and must run first so a
  margin-breaching write never even reaches Amazon's validator.

Closes the gap flagged in `2026-06-20_datadoe-write-path-gating.md` §"Open engineering
gap" and runbook §A.5 ("No engine bid/budget gate yet").

---

## Daily Action Queue Generation + Ranking

**Sources of proposed actions:**
1. The standing rebuild runbook (`ppc-rebuild-execution-plan_2026-06-20.md` Waves 0–5) — a
   finite, sequenced backlog of ID-level moves.
2. The M1 read primitives once they emit `ProposedAction`s instead of prose: wasted-spend
   (Phase 3) → bid-down/pause; negatives (Phase 4) → TARGETS_ADD negative; budget-capped
   (Phase 5) → budget-up (gated).

**Generation (daily, on-open):** agent runs the read primitives + reads the runbook wave
pointer → assembles candidate `ProposedAction`s → `rank_queue.py` attaches each action's
**$ impact** (est. monthly waste removed, or efficient spend added at the SKU's ROI) →
sorts **by dollars descending** (reusing the `tacos.classify` sort idiom: no-$-estimate
rows last). Output: a dry-run-able, dollar-ranked queue JSON the skill renders
one-screen-first (CLAUDE.md Golden Rule 4).

**Ranking key:** absolute monthly dollar effect — `|expected Δ net contribution|`.
Stop-the-bleed pauses/negatives (Wave 1, −$50–69/mo, reversible, standing) rank above
fund-winners spend (Wave 3, +$150–240, explicit), so highest-$ lowest-risk surfaces first
— matching the runbook ordering.

**Dependency ordering inside the queue (hard predecessors, not just sort):** FIND (Wave 0)
precedes its writes; budget raises gate on "3 clean days post-retarget"; `CAMPAIGNS_REMOVE`
(archive) runs last in its own batch (low reversibility).

---

## Integration Points with Existing Engine/Skills/decisions.md/brain

| Existing piece | M2 integration |
|----------------|----------------|
| `logging.logged_call` | Wraps **every** `actions_start` (dryRun + real) and `actions_get` — one `.start`/`.end` into `external-calls.jsonl`. Never log the seller UUID. Satisfies Hard Rule 6 for writes. |
| `result.py` typed results | `actions.py` extends the pattern: `Allowed`/`GateRefusal`/`ApplyResult` frozen dataclasses; no bare None, no swallowed error. |
| `thresholds.read` | Gate calls it for tier ceilings + `min_margin_pct`; empty → `GateRefusal("no threshold set")`. No new reader. |
| `datadoe.poll_status` | `lifecycle.py` reuses terminal-on-FAILED semantics for the `actions_get` poll. |
| Thin-CLI-over-MCP seam | `gate_action.py`/`build_payload.py`/`rank_queue.py`/`log_action.py` are the write-side `answer_tacos.py`: agent does MCP, Python does truth. |
| `state/decisions.md` | `log_action.py` appends the dated line (what, before→after, `actionId`, expected $). Standing-approved actions still log — autonomy ≠ silence. |
| `brain/raw/` → `brain/wiki/` | Each applied action drops a `raw/` note; weekly compaction folds proven moves into `wiki/playbooks/`. Gate refusals also teach (which SKUs can't take spend). |
| `anabtawi-context` SKU→tier | The gate's margin/tier source. Needs machine-readable per-SKU margin (today partly prose) — the gate's hard dependency. |
| `datadoe-query` SKILL | Gains the write-action reference (the four `actions_*` tools, FIND-before-write, dryRun). |
| `tests/` (pytest contract) | New `test_gate.py`, `test_payload.py`, `test_lifecycle.py`, `test_queue.py`, `test_idempotency.py`. Gate logic is the new money-logic contract — must stay green (Hard Rule 3). |

---

## Suggested Build Order (seeds phases)

**Phase A — FIND + lifecycle substrate (read-only, zero account risk).**
`lifecycle.py` (dryRun/poll classifiers) + cache FIND results to `data/` + extend
`datadoe-query` with the write-action reference. Proves the async loop on a no-op. Runbook
Wave 0. *No write lands.*

**Phase B — The margin gate (the safety core, before any real write).**
`gate.py` + tier ceilings in `thresholds.toml` + machine-readable SKU→margin/tier +
`gate_action.py` + `test_gate.py`. The load-bearing guardrail; prove it (refuses a
sub-floor spend the way `tacos` refuses a fabricated number) BEFORE wiring any
`dryRun:false`. Closes the write-safety gap.

**Phase C — Payload + apply spine + logging loop (reversible writes only).**
`payload.py` + `actions.py` types + `idempotency.py` + `log_action.py` + `ppc-execute`
skill with **standing approval** for pause/negative/bid-down. First real writes = runbook
Wave 1 (stop the bleed) — highest-$, fully reversible. Every action logs to `decisions.md`
+ `brain/raw/`.

**Phase D — Daily ranked queue + explicit-approval class.**
`queue.py` + `rank_queue.py` + wire spend-up/budget-up/new-campaign through **explicit**
approval and the **passing** margin gate. Runbook Waves 2–3 (tune survivors, fund winners).

**Phase E — New-campaign chains + archive hygiene (lowest reversibility, last).**
The `CAMPAIGNS_ADD→AD_GROUPS_ADD→ADS_ADD→TARGETS_ADD` chain (Wave 4) and
`CAMPAIGNS_REMOVE` graveyard archive (Wave 5) in its own explicit, separate-approval batch.

*Ordering rationale:* read-only substrate → safety gate → reversible writes → ranked spend
→ irreversible last. Exactly the runbook's risk-ascending wave order lifted into phases,
with the gate inserted as a hard predecessor to any spend increase.

---

## Open Questions for Planning

1. **Portfolios** (runbook §D.1, §A.1): no portfolio-create action exists. Encode tier in
   campaign **name + tags**, or have Rami create 3 tier portfolios in console once so we
   assign `portfolioId` on create? Blocks clean Wave 4, not Wave 1. **Decide before Phase E.**
2. **SKU margin source of truth:** is `anabtawi-context` SKU→tier authoritative for the
   gate, or does the gate derive margin live from DataDoe premium Profit-by-SKU each run?
   (Live = fresher but adds a read dependency to every gate call.)
3. **Standing-approval precision:** is "bid-down" always reversible-enough for standing
   approval, or only below a $ delta cap? Define the exact reversible set + any magnitude
   ceiling in `CLAUDE.md`.
4. **Idempotency window:** how long does a content-hash dedup hold — per-day queue or
   persistent across days? (Bounds the `actions_list` lookback.)
5. **Reconciliation proof:** with DataDoe lagging ≤24h, what's the agreed same-day
   "applied & correct" check — `actions_get` COMPLETED alone, or COMPLETED + a console
   confirmation logged to `brain/`?
6. **Gate input for new campaigns:** a brand-new campaign has no historical TACOS — does
   the gate evaluate it on *projected* spend vs margin ceiling, and what spend assumption
   seeds that projection?
7. **`min_margin_pct` is still empty** in `thresholds.toml` — Rami must set the real floor
   before Phase B can pass the gate on anything (it correctly refuses until then).
