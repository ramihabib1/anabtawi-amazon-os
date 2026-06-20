# Features Research — Milestone v2.0 (Gated PPC Write Path)

**Domain:** Amazon Ads (amazon.ca) Sponsored Products execution layer for Anabtawi Sweets
**Researched:** 2026-06-20
**Mode:** Ecosystem / feature-landscape
**Confidence:** HIGH on mechanics (DataDoe action map verified in execution plan; PPC mechanics
verified against Amazon Ads docs + practitioner sources). MEDIUM on harvest cadence specifics.

> Supersedes the Milestone-1 (read-only intelligence) FEATURES.md, archived in git history.

**Scope reminder (binding):** PPC writes ONLY, against existing FBA stock, governed by a per-SKU
margin-tiered TACOS gate, via DataDoe `actions_start`. No restocks, no listing writes, no catalog
refresh. Standing approval for reversible moves; explicit approval for spend-up / new campaigns.

**Sources read:**
- `.planning/PROJECT.md` (milestone goal, mission metric, key decisions, out-of-scope)
- `deliverables/ppc-rebuild_2026-06-12.md` (teardown, change sheet §8, restructured architecture §7)
- `deliverables/ppc-new-campaigns_2026-06-16.md` (5 new campaigns A–E + gated set, harvest loop)
- `deliverables/ppc-rebuild-execution-plan_2026-06-20.md` (DataDoe action map §A, hard limits, waves)
- Amazon Ads dynamic-bidding guide; Pilothouse/Optmyzr/Sellermetrics harvest + match-type sources (web, MEDIUM)

---

## Table Stakes (must-have execution capabilities)

These are the non-negotiable mechanics. Without them there is no write path. The execution plan
(§A) already proves each maps to a real DataDoe action — so these are "build the wrapper," not
"research if possible."

| # | Capability | DataDoe action(s) | Why table-stakes for this milestone |
|---|---|---|---|
| T1 | **propose → dryRun → approve → apply → reconcile loop** | `actions_start dryRun:true` → approval → `dryRun:false` → `actions_get(actionId)` until `COMPLETED` | The spine. Every write goes through it. `dryRun` must return `VALIDATED` before anything touches the account. This is the structural guardrail the whole milestone exists to deliver. |
| T2 | **Read-the-live-structure FIND primitives** | `CAMPAIGNS_FIND`, `AD_GROUPS_FIND`, `TARGETS_FIND`, `ADS_FIND` | You cannot write a bid/pause/negative without the live `campaignId / adGroupId / targetId / adId`. Wave 0 ("Discovery") is read-only and zero-risk; it makes every other wave executable. |
| T2b | **Pause a campaign / ad / keyword** | `CAMPAIGNS_UPDATE state:PAUSED`, `ADS_UPDATE state:PAUSED`, `TARGETS_UPDATE state:PAUSED` | The single biggest lever in the teardown (pausing dead-SKU ads = −$279/mo, ~43% of spend, zero sales loss). Fully reversible → standing-approval class. |
| T3 | **Add negative keyword / negative product target** | `TARGETS_ADD negative:true` (per campaign/ad-group) | Harvest §2 of teardown; the harvest loop's "block the source campaign" step. Note hard limit: **no shared-negative-list object exists** — the same negative set must be applied to each ENABLED campaign individually and re-added to new campaigns at launch. Reversible. |
| T4 | **Bid change (keyword/target)** | `TARGETS_UPDATE bid` | Bid-down on "watch-don't-negate" terms (pistachio baklava, arabic sweets); bid-up on brand defense (+10%). Bid-DOWN is reversible (standing approval); bid-UP is spend-increasing (explicit approval). |
| T5 | **Budget change (campaign)** | `CAMPAIGNS_UPDATE budgets` | Raise the capped winner SP-Phrase $10→$15; fund proven SKUs. Budget-UP is the canonical explicit-approval action. |
| T6 | **Placement bid adjustments** | `CAMPAIGNS_UPDATE placementBidAdjustments` | TOP_OF_SEARCH + PRODUCT_PAGE both convert; "rest of search"/"Other" lags. The system must bias placement, not just flat bids. Amazon allows up to +900% — gate hard. |
| T7 | **Retarget a campaign's product ad** | `ADS_REMOVE` old + `ADS_ADD` new | Swap dead-SKU ads (FX-M8MA) for live canonical SKUs (T8-2W2X, 18-116Z) inside an already-funded, capped campaign — redirects ~$200/mo to sellable stock. Net-neutral spend but changes *what* sells. |
| T8 | **Build a new campaign (chain)** | `CAMPAIGNS_ADD` → `AD_GROUPS_ADD` → `ADS_ADD` → `TARGETS_ADD` | The 5 coverage-gap campaigns (A–E) and the 09-AJOP HERO campaign. 3–4 chained actions; if a link fails mid-chain the system must detect a partial build (see D6). Explicit approval. |
| T9 | **Match-type-aware keyword targeting** | `TARGETS_ADD` with EXACT / PHRASE / BROAD; SP Auto close+loose | The rebuild architecture is funnel-by-match-type (exact = conversion, phrase = discovery, auto = harvest). The write layer must set match type correctly per the build sheet. |
| T10 | **Archive graveyard campaigns** | `CAMPAIGNS_REMOVE` (= console "archive", recoverable, NOT hard-delete) | ~57 Feb-04 bot/SKW + 2 unnamed ENABLED. Hygiene. **Low reversibility** → its own separately-approved batch, run last. |
| T11 | **Reconcile via action status + console, NOT next-day exports** | `actions_get(actionId)` + manual console check | DataDoe reporting lags ≤24h; writes hit Amazon immediately. Verification reads the action result, not tomorrow's pull. A reconcile that trusts lagged data would raise false "didn't apply" alarms. |
| T12 | **Log every applied action** | append to `state/decisions.md` + `brain/raw/` | Constitution: every money-moving action is a logged, approved proposal. Non-negotiable; the prior-agency abuse is the entire reason this milestone is gated. |

---

## Differentiators (the milestone's actual thesis)

These separate "a button that calls the Ads API" from "a PPC engine that sells through stock at a
margin-safe TACOS." This is where the milestone earns its keep.

### D1 — Per-SKU margin-tiered TACOS/bid gate (the headline)
**What:** Before any spend-increasing write (bid-up, budget-up, new campaign, placement-up) is even
proposed, the engine derives that SKU's TACOS ceiling from its own contribution margin (protect net
≥ ~15%) and **refuses** the write if it would breach. Mirrors the existing `answer_tacos.py` refusal
pattern — a missing margin/threshold → refuse with reason, never a default.
**Why differentiator:** A flat 25% TACOS loses money on thin SKUs (portfolio break-even ≈ 39% t30).
The gate is the difference between "spend more" and "spend more *only where the margin survives it*."
**Status:** PROJECT.md flags this as closing the write-safety gap; execution plan §A note 5 says
**"No engine bid/budget gate yet"** — this is net-new engine work, the critical path.
**Tiering:** aggressive winners up to ~25% TACOS, MAINTAIN ~28% ACOS, thin SKUs ≤ ~12%, CUT/exit = $0.

### D2 — Daily ranked action queue (dollar-ordered, pre-dry-run'd)
**What:** Each day the engine emits a ranked list of proposed PPC writes, each already dry-run-validated,
ordered by dollar impact (waste stopped or efficient revenue unlocked). The existing Action Inbox is the
surface; this feeds it.
**A good queue row contains:** object (campaignId/targetId/adId) + current value → proposed value +
evidence (engine ACOS/TACOS/ROI + source export + window) + estimated monthly Δ + reversibility class
(standing vs explicit) + dryRun status (VALIDATED) + gate result (passed / refused + why).
**What belongs in the queue daily:** (a) overspend brakes — ACOS/TACOS-breaching keywords to bid-down
or pause; (b) waste — zero-order search terms ≥$ threshold to negate; (c) capped winners to fund;
(d) harvested terms ready to graduate; (e) inventory-pacing brakes (D4); (f) gate refusals shown as
"wanted to scale X but the margin floor blocks it."
**Why differentiator:** Turns a one-off teardown into a standing operating rhythm. The teardown found
winners *manually*; the queue finds them every day.

### D3 — Harvest loop (auto → graduate converting terms → exact, with same-session negation)
**What:** One SP Auto campaign per family (close+loose) discovers search terms; a weekly cycle promotes
converting terms (graduation criteria: ≥2–3 orders, ACOS ≤ tier target, repeat volume) into the exact
campaign **and simultaneously adds them as exact negatives in the auto source** — or you pay twice and
bid against yourself.
**Why differentiator:** The teardown's §6 root finding was "**no harvest loop** — all AUTO paused, no
term discovery feeding exact." Campaign E (Auto-Cookies-Harvest) is the seed. Mature accounts run 3–5×
more negatives than positives; the loop is how that ratio gets built. The "negate the source in the
same session" rule is the easy-to-miss correctness requirement (verified against practitioner sources).
**Confidence:** HIGH on the mechanic; MEDIUM on exact graduation thresholds (live in `state/targets.md`,
not invented here).

### D4 — Inventory-paced spend (don't overspend a 4-unit SKU)
**What:** Spend is gated on sellable stock, not just demand. Before funding/scaling a SKU, check FBA
qty × velocity ≥ ~6 weeks of cover (CLAUDE.md / rebuild §7: "never scale spend onto a listing under
6 weeks of stock"). Low-stock SKUs are *capped or held*, not funded. GG-0DC1 (1 unit) and EU-Z87B
(0 FBA) are gated examples already in the docs.
**Why differentiator:** Without this, the queue would pour budget into a SKU that sells out in days,
generating clicks that hit out-of-stock / buy-box-lost listings — pure waste. This is the "sell
*through* existing inventory" half of the mission metric.
**Note:** the read-only inventory check (FBA qty from listings export) is in-scope as a *gate input*;
actually changing inventory (restocks) is OUT.

### D5 — Reversibility-classed autonomy (standing vs explicit approval)
**What:** The write layer tags each proposed action by reversibility. Pause / negative / bid-down →
**standing approval** (auto-apply after dry-run validates). Budget-up / bid-up / new campaign / placement-up
→ **explicit per-action approval**. `CAMPAIGNS_REMOVE` (archive) → explicit + batched separately.
**Why differentiator:** Lets the system act fast on the safe, high-frequency moves (daily brake-tapping)
without nagging, while keeping a human firmly on every dollar of new spend. This is the autonomy model in
PROJECT.md key decisions, made operational.

### D6 — Partial-build detection & rollback for chained writes
**What:** A new campaign is 3–4 chained async actions. If link 3 fails, the system must detect the
half-built campaign (empty ad group / no targets), surface it, and either complete or remove it — never
leave an orphan ENABLED campaign that could spend.
**Why differentiator:** DataDoe actions are async and per-object; nothing guarantees atomicity across the
chain. Quietly leaving a budgeted-but-malformed campaign live is exactly the silent spend the constitution
forbids.

---

## Anti-Features (explicitly OUT for this milestone)

| Anti-feature | Why OUT | What to do instead |
|---|---|---|
| **Listing-content writes** (`AMAZON_LISTINGS_UPDATE`) — titles, bullets, images, A+ | PROJECT.md: PPC-only milestone; listing rebuilds stay reviewed artifacts applied manually. | Gate PPC on listing readiness as a *read-only input* (don't scale a 1.1% converter); leave the fix to the operator. |
| **Restocks / new inventory / AWD POs** | Out of scope; "work the existing FBA stock only." | Inventory is a *spend gate input* (D4), never a write target. Gated SKUs (GG-0DC1, EU-Z87B) wait. |
| **Catalog refresh** — retire/add SKUs, build variations, the 800g-flagship restock push | Deferred: "after we make a base in the PPC." | Advertise only the current active catalog. |
| **Autonomous spend-up** — any bid/budget/placement increase or new campaign applied without explicit human approval | Constitution hard rule; prior third party abused PPC writes. | Standing approval covers only reversible *down/stop* moves; every dollar of *new* spend is explicit. |
| **Portfolio creation/assignment via API** | Execution plan §A limit 1: **no portfolio action exists** in DataDoe. | Either skip portfolios and encode tier in campaign **name + tags**, OR operator creates 3 tier portfolios once in console and we assign `portfolioId` on create. (Open decision.) |
| **Shared-negative-list (library) object** | §A limit 2: no library object exists. | Apply the negative set to each ENABLED campaign individually; re-add at every new-campaign launch. More calls, same effect. |
| **Hard-delete of campaigns** | §A limit 3: `state` enum is only ENABLED/PAUSED; `CAMPAIGNS_REMOVE` = recoverable archive. | Treat archive as low-reversibility; batch it, approve separately, run last. |
| **Trusting next-day DataDoe exports to confirm a write** | ≤24h reporting lag; writes are immediate. | Reconcile via `actions_get` + console only (T11). |
| **Sponsored Brands / Sponsored Display builds** | Teardown §6: SB/SD fully paused; SB revisit is gated behind listing/A+ fixes (themselves OUT). | Sponsored Products only this milestone. Re-enable SB ToS-only later, after listing fixes land. |
| **Up-and-down dynamic bidding as default** | "Amazon can double your bids" — conflicts with a margin-floor, sell-through-stock posture. | Default **dynamic down-only** (budget-safe); reserve up-and-down for engine-verified high-margin winners, under the D1 gate. (MEDIUM-confidence recommendation.) |
| **Inventing a bid, budget, or threshold** | Constitution rule 4; §A limit 5: no engine bid gate exists yet. | Bids/budgets come from the approved 06-12/06-16 sheets or the engine; a missing threshold → refuse the write ("no threshold set"). |

---

## Feature → Existing-Artifact Dependencies

| Feature | Depends on (existing) | Net-new work this milestone |
|---|---|---|
| T1 propose→dryRun→reconcile loop | DataDoe `actions_start`/`actions_get` (enabled 2026-06-20, dryRun verified); Action Inbox surface | The orchestration wrapper + reconcile-via-status logic |
| T2 FIND primitives | Live SP pull already exists (`data/ads_sp_campaigns_live_2026-06-20.json`, action `04aa6489`) | FIND wrappers per object type; cache to `data/` |
| T3 negatives / T4 bids / T5 budgets / T6 placement / T7 retarget | Change sheet §8 (06-12) supplies exact current→proposed values + evidence | Per-action payload builders |
| T8/T9 new campaign chain + match types | Build sheet (06-16) campaigns A–E with seed keywords + match types + budgets | Chain orchestration + D6 partial-build safety |
| **D1 margin-tiered TACOS/bid gate** | Existing `engine/scripts/answer_tacos.py` (refusal pattern to mirror); `state/targets.md` tiers; COGS/margin from `anabtawi-context` + DataDoe Profit-by-SKU | **Critical path** — engine grows a bid/budget guard (§A note 5: "no engine bid/budget gate yet") |
| D2 daily ranked queue | Action Inbox; engine ACOS/TACOS/ROI JSON outputs; cached exports in `data/` | Ranking + queue-assembly logic; daily run trigger (on-open, no cron) |
| D3 harvest loop | Search-term exports (e9509054 pattern); Campaign E (auto seed) in 06-16; rebuild §7 HERO-TOF-Auto | Weekly harvest job: pull terms → graduation filter → `TARGETS_ADD` exact + negate source |
| D4 inventory-paced spend | Listings-with-COGS export (b18aadfd) for FBA qty; rebuild §7 6-week rule | Stock-cover check as a gate input before any fund/scale proposal |
| D5 reversibility classes | PROJECT.md autonomy decision; `state/decisions.md` ledger | Tag each action type; standing vs explicit routing in the Inbox |
| D6 partial-build rollback | DataDoe action async semantics | Chain-state tracker + orphan detection |
| T12 logging | `state/decisions.md` (append-only), `brain/raw/` | Action-result → ledger writer |

**Build/rollout order = the execution-plan waves (06-20 §C):** Wave 0 (FIND) + Wave 1 (stop-the-bleed:
pauses, negatives, bid-downs — all standing-approval class) ship first and exercise T1–T4 + D5. Waves 2–5
layer in budgets, new builds, and hygiene, and require D1 (the gate) before any scaling. **Build D1
alongside Wave 1** so it's ready before Wave 2 spend-up.

---

## Open Questions for Planning

1. **Portfolios (blocks clean Wave 4 structure, not Wave 1):** skip and encode tier in name+tags, or
   operator creates 3 tier portfolios in console once and we assign `portfolioId` on create? (§D.1.)
2. **Margin-gate inputs:** is per-SKU contribution margin reliably available from DataDoe Profit-by-SKU
   for *every* advertised SKU, or do some fall back to `cogs`/FX? A SKU with no margin data → the gate
   must refuse to scale it (no default). Confirm coverage before Wave 2.
3. **Graduation thresholds for the harvest loop:** set the exact criteria in `state/targets.md`
   (orders ≥ N, ACOS ≤ tier target, min weekly volume). Practitioner norm ≈ 3 orders / ACOS ≤ break-even /
   5+ weekly searches — operator dials, not invented constants.
4. **Inventory-cover threshold as a hard gate value:** rebuild §7 says "6 weeks." Confirm as the binding
   number in `state/targets.md` and define the velocity source/window for the cover calc.
5. **Daily-queue trigger under the desktop constraint:** no unattended cron (Mac must be awake). Is the
   "daily" queue on-open / on-demand, or does it assume an always-on Mac? Affects D2's cadence promise.
6. **Bid-strategy default:** confirm dynamic **down-only** as the portfolio default, with up-and-down
   reserved (under D1) for named high-margin winners — or leave per-campaign strategies untouched this
   milestone and only change the bids/budgets/placement explicitly listed in the sheets.
7. **Archive batch authorization:** `CAMPAIGNS_REMOVE` the ~57+2 graveyard now, or leave PAUSED?
   (Low reversibility — §D.3.)
8. **Standing-approval magnitude cap:** does standing approval on bid-DOWN have a ceiling (auto-apply
   ≤ −X% but route a −80% slash to explicit review)? Define the boundary so "reversible" doesn't quietly
   include a winner-killing cut.

---

_File is the deliverable. No account changes; no commit (orchestrator commits after all researchers complete)._
