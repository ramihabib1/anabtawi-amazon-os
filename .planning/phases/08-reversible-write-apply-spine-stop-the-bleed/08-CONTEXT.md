# Phase 8: Reversible-Write Apply Spine + Stop-the-Bleed - Context

**Gathered:** 2026-06-22
**Status:** Ready for planning

<domain>
## Phase Boundary

The first **real** account writes land — but only **reversible** ones (pause campaign/keyword/ad,
add negative keyword, lower a bid) under standing approval. Each write runs the full spine:
BUILD → own-ASIN denylist gate → margin gate (auto-pass as spend-decreasing, per 07 D-06) →
dryRun (`classify_dryrun`) → apply (`actions_start dryRun:false` → `actionId`) → poll
`actions_get` to a terminal state → FIND-echo confirm → idempotent log. Applied to the runbook,
this spine **stops the dead-SKU spend bleed** (~$279/mo, ~43% of spend, ~$0 sales loss) and
**enforces the own-ASIN denylist**.

**In scope:** the apply-spine module + thin CLI (poll loop, idempotency ledger, reconcile),
the own-ASIN denylist pre-dryRun gate, the standing-approval magnitude-cap mechanism, the
decisions.md + brain/raw logging seam, and the first stop-the-bleed batch.

**Out of scope (later phases):** spend-increasing writes + explicit-approval daily queue +
dollar-ranked rendering (Phase 9); act-now-vs-judge-later attribution boundary (Phase 9,
QUEUE-04); new-campaign chains + portfolios + the graveyard `CAMPAIGNS_REMOVE` (Phase 10).
</domain>

<decisions>
## Implementation Decisions

### Standing-approval boundary / magnitude cap (Q1, SC-5)
- **D-01:** Standing approval is **permissive for all reversible actions** — pause,
  negative-keyword add, and bid-down **auto-apply at any magnitude** after a clean dryRun.
  Only spend-**increasing** actions (Phase 9) require explicit approval. Rationale: reversibility
  is the protection — any auto-applied reversible move can be undone, and Rami's posture is
  aggressive (move fast on reversible cleanup).
- **D-02:** **SC-5 reconciliation (deviation flagged, not silent).** ROADMAP SC-5 requires a
  bounded magnitude cap so a reversible bid-down "cannot kill a winner." D-01 chose permissive.
  Resolution mirrors Phase 7 **D-07** (build the refusal path, seed the live value): the
  magnitude-cap **mechanism is still built and pytest-tested** — a configurable bounded-%
  gate that *would* route an over-cap reversible move to explicit review — but it is **seeded
  permissive** (effectively unlimited for reversible actions) so live behavior matches D-01.
  SC-5's machinery is present and verifiable; tightening the cap later is a **config change**
  (the bounded-% lives as a documented dial in `thresholds.toml` / `sku_catalog.toml`), not a
  code change. The verifier should treat SC-5 as "mechanism exists + tested, seeded permissive
  by operator decision," not as an unbuilt requirement.

### Stop-the-bleed batch scope & sequencing (Q2, EXEC-01 / SC-4)
- **D-03:** First batch = **pause the whole campaigns** for the 4 dead SKUs
  (**FX-M8MA, 9Z-KUHZ, VH-ZTOC, ZK-4NDS**) **+** apply the **exact-match** negative-keyword
  harvest per-campaign, all in **one batch** — gated behind the canary verify (D-08).
- **D-04:** Negative harvest is **exact-by-default**. The **keep-positive allowlist** protects
  **`baklava gift box`** (never negated). **"Watch-don't-negate"** terms are **bid-down, not
  negated**. Phrase/broad negatives are **not** in this batch (exact only).
- **D-05:** Pausing **whole campaigns** (not just keywords/targets) is chosen deliberately: it
  is the cleanest fully-reversible stop and leaves **no empty ENABLED shell** that can
  re-accrue spend.

### Own-ASIN denylist (Q3, EXEC-01 / SC-4)
- **D-06:** The denylist covers the **full set of ~30 owned ASINs**. Any payload that points an
  ad at an owned ASIN is refused — never deliberate to advertise our own product on our own page.
  **B07TV972JT is one row in that set, not a special case.**
- **D-06a (REVISED 2026-06-22 — operator decision during plan-phase; supersedes D-06's source):**
  The denylist reads its owned-ASIN set from a **dedicated `engine/config/owned_asins.toml`**,
  **NOT** from `sku_catalog.toml`. Rationale (research Open Question 4): `sku_catalog.toml` holds
  only the ~16 COGS-gated SKUs the *margin gate* funds and **B07TV972JT is absent** from it; the
  denylist must cover the broader ~30-ASIN owned set and must stay **decoupled from the gate's
  COGS catalog** so Phase 7's "absent SKU → refuse funding" semantics are not polluted by
  denylist-only rows that carry no margin data. The dedicated source is populated from the
  authoritative owned-ASIN list (`anabtawi-context` SKU/ASIN table + B07TV972JT from
  `brain/raw/2026-06-17_baklava-rebuild-research.md`); ASINs are **never invented** — seed what
  is authoritative and document any gap. Rami selected "Separate denylist source" when this
  16-vs-30 conflict was surfaced at plan time.
- **D-07:** Denylist enforcement sits in Python **before BUILD→DRYRUN** (another pre-dryRun
  refuse-gate beside the margin gate), is a **hard refusal** (not warn-and-confirm), and uses
  the existing typed-refusal grammar surfaced verbatim — never silently dropped.

### First-write rollout posture (Q4, WRITE-03)
- **D-08:** The debut is a **canary**: run exactly ONE reversible write (a single pause)
  end-to-end — apply → poll `actions_get` to COMPLETED → FIND-echo confirm — with a **one-time
  manual confirm on that first apply**, and verify it reconciles cleanly. Only after the canary
  confirms does the standing-approved batch (D-03) run under D-01's permissive auto-apply.
- **D-09:** The canary's manual confirm is a **one-time gate for the first apply of the phase**,
  not per-action (Rami declined "manual confirm on every apply"). After the canary, reversible
  moves auto-apply.

### Idempotency & reconcile (WRITE-07 / WRITE-03)
- **D-10:** Idempotency identity — two actions are "the same" (a no-op re-run) when their
  **content hash over {entity type + entity ID + action type + normalized params}** matches a
  COMPLETED entry in `data/actions_ledger.jsonl`. An **in-flight `actionId` resumes at poll**,
  never re-fires `actions_start`. Identity is keyed on the targeted entity + action + params,
  **NOT on date** — so re-pausing an already-paused campaign is always a no-op.

### Logging (WRITE-06)
- **D-11:** Every applied write logs a dated line to **`state/decisions.md`** AND a
  **`brain/raw/`** note capturing what changed, why, expected effect, and the `actionId`.
  **Standing-approved (auto) actions log too** — autonomy ≠ silence.

### Claude's Discretion
- Poll-loop interval/backoff and max-attempts before an in-flight action is surfaced as
  unresolved (reuse `datadoe.poll_status` terminal-on-FAILED).
- `find_cache` staleness-window value (Assumption A2) — pick a sane documented default
  (e.g. same-day / 24h), not a silent hard-code.
- Exact `actions_ledger.jsonl` format, hash field set, apply-spine module/function layout,
  CLI shape (mirror the existing thin CLIs `answer_tacos.py` / `gate_action.py`).
- Whether a negative is added via a dedicated negative-create action vs a target-state write —
  pin against `actions_details_schema_get`.
</decisions>

<specifics>
## Specific Ideas

- **The spine is the analog of the gate:** every real-write decision is hand-written and
  pytest-covered, never reasoned in chat (CLAUDE.md hard rule 3). The poll loop, ledger, and
  denylist all use the existing typed refuse-never-default / refuse-never-clamp grammar.
- **Permissive is a deliberate operator choice, not an omission.** Rami wants reversible cleanup
  to move at speed; the canary (D-08) buys the confidence that the spine works before the
  permissive auto-apply takes over, and reversibility is the safety net behind it.
- **The bleed is the proof:** the first batch's whole job is to flip ~43% of spend ($279/mo) off
  the 4 dead SKUs with $0 sales loss — the cleanest possible first real-write to demonstrate the
  spine end-to-end.
</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase scope, requirements & posture
- `.planning/ROADMAP.md` — Phase 8 section (goal + SC-1..5), the M2 "Constitution constraints"
  and "Blocking preconditions" tables.
- `.planning/REQUIREMENTS.md` — WRITE-03, WRITE-06, WRITE-07, EXEC-01.
- `.planning/PROJECT.md` — mission metric (net ≥ ~15%), reversibility-classed autonomy posture.
- `.planning/phases/07-margin-tiered-safety-gate/07-CONTEXT.md` — carried decisions: gate
  auto-passes spend-decreasing (D-06), gate sits BUILD→DRYRUN, build-refusal-path-seed-live
  pattern (D-07) that D-02 reuses.

### Operational intel (the runbook this batch executes)
- `brain/raw/2026-06-20_datadoe-write-path-gating.md` — the **4-gate chain**, granted Ads action
  types, dryRun discipline, and the **Settings → Actions org-enable** precondition (see below).
- `brain/raw/2026-06-16_ppc-coverage-gap.md` — the 4 dead SKUs, the ~$279/mo bleed, own-ASIN
  context, and the keep-positive / watch-don't-negate intent.

### Engine substrate (the code to drive / imitate)
- `engine/src/habibos/lifecycle.py` — `classify_dryrun` / `classify_poll` (the poll loop's
  per-response classifier; **Phase 8 drives the in-flight→terminal loop** — the docstring says so).
- `engine/src/habibos/find_cache.py` — `write` / `lookup`, FIND-before-write, the **staleness
  window dial (A2)** Phase 8 enforces.
- `engine/src/habibos/gate.py` + `engine/src/habibos/result.py` — `ProposedAction`,
  `GateVerdict`/`GateRefusal`, the gate that auto-passes spend-decreasing; reuse the typed
  refusal grammar for the denylist + cap.
- `engine/src/habibos/datadoe.py` — the seam, the pinned `ACTION_*` status sets,
  `poll_status` terminal-on-FAILED.
- `engine/src/habibos/logging.py` — `logged_call` (one `.start` + one `.end`, **no seller UUID**)
  for every `actions_start` / `actions_get`.
- `engine/config/sku_catalog.toml` — the **owned-ASIN set** source (D-06); `thresholds.toml` —
  the magnitude-cap dial (D-02).

### Constitution
- `CLAUDE.md` — hard rules: no autonomous writes to Amazon without approval, money/write logic
  hand-written + reviewed + tested, log every external call, secrets in `.env`
  (`$AMAZON_CA_SELLER_ID` never inlined).
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lifecycle.classify_dryrun` / `classify_poll` — the spine wraps these; the poll loop calls
  `classify_poll` per response until terminal.
- `find_cache.write` / `lookup` — FIND-before-write + the FIND-echo confirm after apply.
- `gate.evaluate` (Phase 7) — reversible writes route through it and auto-pass (07 D-06).
- `logging.logged_call` — the logged seam for `actions_start` / `actions_get`.
- `datadoe` `poll_status` + pinned `ACTION_*` sets — terminal classification for the loop.
- `result.py` typed `Refusal` grammar — the denylist + cap reuse it.

### Established Patterns
- Refuse-never-default / refuse-never-clamp; typed verdicts, never bare True/None.
- **Build-the-refusal-path-then-seed-the-live-value** (Phase 7 D-07) — D-02 reuses it for the
  magnitude cap (mechanism built + tested, seeded permissive).
- Hand-written + pytest-covered for any money/write logic; `cd engine && uv run pytest` stays green.
- `logged_call` leaks no seller UUID; every external call cited + logged.

### Integration Points
- New apply-spine module (e.g. `apply.py`) + thin CLI consuming a `ProposedAction`:
  **denylist gate → margin gate → dryRun classify → `actions_start(dryRun:false)` → poll loop
  (`classify_poll`) → FIND echo → ledger + `decisions.md`/`brain/raw` log.**
- Denylist + magnitude cap are **new pre-dryRun gates** beside `gate.py`.
- `data/actions_ledger.jsonl` is new (idempotency); reuses the `data/` cache dir convention.
- No Supabase, no spend-up, no new campaigns in this phase.
</code_context>

<deferred>
## Deferred Ideas

- **External precondition (blocker, not deferred-scope):** Rami (org owner) must **enable the
  required Ads action types in DataDoe → Settings → Actions** (OFF by default) before any real
  write lands — pause/campaign-state, the negative-keyword create, target-state for bid-down.
  The phase can BUILD + dryRun without it; the canary apply (D-08) and the batch (D-03) are
  blocked until enabled. Surface this clearly at execution time.
- Spend-increasing writes + explicit-approval **daily ranked queue** + dollar-ranked rendering
  → **Phase 9**.
- **Act-now vs judge-later** attribution boundary (matured-window logic) → **Phase 9** (QUEUE-04).
- **Tightening the magnitude cap** to a real bounded-% if a reversible move ever hurts a winner
  → config change (D-02 dial); revisit posture then.
- New-campaign chains, portfolios, the graveyard `CAMPAIGNS_REMOVE` → **Phase 10**.
- Migrating `thresholds.toml` + the SKU catalog → Supabase `config` / `sku_master` → **Phase 3.5**.

</deferred>

---

*Phase: 08-reversible-write-apply-spine-stop-the-bleed*
*Context gathered: 2026-06-22*
