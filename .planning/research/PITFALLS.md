# Pitfalls Research — Milestone v2.0 (Gated PPC Write Path)

**Domain:** Adding an approval-gated PPC write/execution layer (DataDoe `actions_start`) to sell
through existing FBA stock at a per-SKU margin-tiered TACOS gate. PPC writes only.
**Researched:** 2026-06-20
**Confidence:** HIGH on account-specific traps (sourced from our own audit + verified DataDoe schema);
HIGH on attribution windows (Amazon Ads docs, verified live); MEDIUM on the engineering-pattern pitfalls
(write-automation best practice + our own flagged gaps).

**Sources read:**
- `.planning/PROJECT.md` (milestone scope, hard rules, key decisions)
- `deliverables/ppc-rebuild_2026-06-12.md` (teardown: §1 waste, §2 negatives, §6 internal competition, §7 dependency order, §8 change sheet)
- `deliverables/ppc-rebuild-execution-plan_2026-06-20.md` (§A hard limits, §B EXCLUDE rule, §C waves, §E risk controls)
- `brain/raw/2026-06-20_datadoe-write-path-gating.md` (4-gate chain, org-enable block, dryRun discipline, no engine gate yet)
- Amazon Ads attribution windows verified via web (SP 7-day, SB/SD 14-day for Seller Central) — see Sources.

---

## Pitfall Table

| # | Pitfall | Why it bites | Prevention mechanism | Owning phase |
|---|---------|--------------|----------------------|--------------|
| 1 | **Judging campaigns faster than attribution settles** | SP conversions attribute up to **7 days** after click; SB/SD up to **14 days**. DataDoe reporting lags only ≤24h, so a campaign retargeted/launched looks "dead" days before its sales land. Pausing or bid-cutting on day 1–3 kills winners mid-conversion. | Engine tags every metric with **window age vs program** and refuses any pause/cut verdict on an immature window (≥7d SP, ≥14d SB/SD before judging). "3 clean days" = 3 days of *matured* data. Verify writes landed via `actions_get`+console; judge *results* only after the window matures. | Engine gate phase (margin/maturity guard) |
| 2 | **Flat TACOS overspends past the margin floor on thin-margin SKUs** | Portfolio contribution margin ~39% t30, but baklava heroes run ~20% (two baklava ASINs already below the 20% floor per 06-17). A flat TACOS (e.g. 25%) is profitable on fat SKUs and **loss-making on thin ones**. Mission metric is a margin-derived TACOS, not a flat number. | Engine derives **each SKU's TACOS ceiling from its own contribution margin** to hold net ≥ ~15%, and **refuses** any bid/budget write whose projected TACOS breaches that SKU's ceiling (mirror of the existing TACOS refusal). Missing margin → "no threshold set", refuse — never default. | Engine gate phase |
| 3 | **Bidding against yourself (same keyword in 4+ campaigns)** | "baklava" EXACT is live in ≥4 campaigns simultaneously ([SP] Baklava, Low bid baklava, Low bids cookies, [SKW] Baklava); brand terms scattered across 3. Internal auctions inflate CPC and split budget. Writing new bids without de-duping just raises the price you pay yourself. | **Wave-0 discovery FIND** builds a keyword→campaign inventory; a pre-write **duplicate-keyword check** flags any term live in >1 ENABLED campaign and blocks a bid-up until consolidated to one owning campaign (one Brand-defense, one Baklava-exact). | Consolidation phase (Wave 2 logic) |
| 4 | **Archive (`CAMPAIGNS_REMOVE`) treated as reversible** | `state` enum is only ENABLED/PAUSED — no "archive" update; archiving = `CAMPAIGNS_REMOVE` = Amazon "archived" (recoverable in console but **not via the API**). Batch-archiving 75+ graveyard campaigns is the one low-reversibility move; one stale ID removes a live earner. | Archive runs **last, in its own explicitly-approved batch, never bundled** with pauses. Pre-check: every ID PAUSED + zero-spend ≥30d before eligible. The 2 *ENABLED* unnamed "Campaign 2026-05-07…" go **pause → observe → archive**, never ENABLED→REMOVE in one step. | Hygiene phase (Wave 5) |
| 5 | **Negative-keyword collateral damage** | Negating a broad/phrase term silently kills converting long-tails inside it. `chocolate gift box` ($10.71/0 orders) must be negated, but **`baklava gift box` converts and must stay positive** — a phrase negative on "gift box"/"chocolate" would suppress it. Over-negation strangles the harvest loop. | Maintain an explicit **keep-positive allowlist** (`baklava gift box`, `turkish baklava`, `baklava sweets`) checked before any `TARGETS_ADD negative:true`. Negate **exact** by default; phrase/broad only after confirming no converting child term is contained. "Watch, don't negate" terms (`baklava pastry`, `pistachio baklava`, `middle eastern sweets`, `arabic sweets`) → **bid-down, never negate**. | Stop-the-bleed phase (Wave 1) |
| 6 | **Campaign-creation sequencing gotcha** | A new campaign is a **chain**: `CAMPAIGNS_ADD` → `AD_GROUPS_ADD` → `ADS_ADD` → `TARGETS_ADD` (+ associations). Each step needs the prior step's returned ID. A partial failure leaves an **orphan empty campaign** or a campaign with ads but no targets (or targets but no ads → spends on auto with no intended keywords). | Treat creation as a **transactional sequence**: dryRun the *whole* chain first; on real run, gate each step on the prior `actions_get` COMPLETED + returned ID before firing the next; on any step failure, **pause/rollback the partial campaign** rather than leave it live. Re-add shared negatives at launch (no shared-list object). | New-campaign build phase (Wave 4) |
| 7 | **Targeting our own private-label ASIN (B07TV972JT)** | B07TV972JT is **Anabtawi's own private label (the Alreef #1)**, yet it sits as a PATA conquest target in ≥2 campaigns (e.g. "PATA - baklava targeting mamoul" 48032352982605). Advertising against our own ASIN burns spend competing with ourselves and cannibalizes organic. | **Binding EXCLUDE rule** in the engine: B07TV972JT (and any owned ASIN in `sku_master`) is on a hard **never-target denylist**. Any `TARGETS_ADD`/retarget payload containing an owned ASIN is refused at validation, before dryRun. Prune existing instances in the Wave 1 negatives batch. | Stop-the-bleed phase (Wave 1) + engine denylist |
| 8 | **Scaling spend on thin data / weak listings / low stock** | Aggressive posture + budget ramp tempts raising budgets on 3 raw days, on a listing below benchmark conversion, or on a SKU with ~6 weeks stock (GG-0DC1 had **1 FBA unit**). Scaling thin data chases noise; scaling a weak listing wastes traffic; scaling low stock risks stockout + lost rank. | Hard gates before any budget raise: **(a)** ≥3 consecutive clean days *post-attribution-window*; **(b)** listing ≥ benchmark conversion; **(c)** ≥6 weeks sellable stock. Restock-gated SKUs (GG-0DC1) → engine refuses the budget write until stock confirmed. Inventory-paced ramp: start ~$1.2–1.5k/mo, scale only as winners hold the gate. | Fund-winners phase (Wave 3) + engine gate |
| 9 | **Designing against limits that don't exist in the API** | The rebuild architecture assumes "one portfolio per tier" and "one shared negative list" — **neither has an API action**. Waves that depend on portfolio assignment or a shared-list object fail at execution. | Design **around** the limits: encode tier in campaign **name + tags** (or have Rami create 3 portfolios in console once, assign `portfolioId` on create); implement "shared negatives" as the **same set `TARGETS_ADD`'d to every ENABLED campaign** (and re-added to new campaigns at launch). Resolve the portfolio decision **before** Wave 4. | Planning / new-campaign build phase |
| 10 | **Skipping the org-enable gate / firing real before dryRun** | Each action type is **OFF by default** in DataDoe Settings → Actions (4th gate beyond our approval). A real run against a disabled type is rejected. Worse: skipping dryRun and firing `dryRun:false` blind on a malformed payload. | **dryRun→approve→apply→reconcile** mandatory for every write (verified 06-20). Pre-flight: confirm the action type is org-enabled (one-time, Rami) before queueing real runs; the queue marks an action "blocked: org-enable required" rather than attempting it. Enable lowest-risk types first; hold price/bid writes until the engine margin-gate ships. | Every execution phase (binding risk control) |

---

## Top 3 Highest-Severity (expanded)

### 1. Judging campaigns faster than attribution settles (Pitfall #1)
**Highest severity — silently destroys the winners we're building.**
The milestone is a *daily* ranked queue with standing approval for reversible moves (pause / bid-down).
That cadence is exactly the speed at which attribution lag does damage: a campaign retargeted today shows
near-zero sales for up to 7 days (SP) / 14 (SB/SD) because the conversions haven't attributed yet —
DataDoe's ≤24h reporting makes the data *look* fresh and final when it isn't. A naive engine would
auto-pause a converting campaign inside its own attribution window and log it as "stopped the bleed." We
already have a live example: SP - Phrase showed raw $184→$783 t30; a fast verdict would have killed it.
**Prevention:** the engine tags every metric with **window age vs program** and refuses any pause/cut
verdict on an immature window (≥7d SP, ≥14d SB/SD before judging). "3 clean days" must mean 3 days of
*matured* data, not 3 calendar days post-change. Reversibility ≠ free — a paused winner loses rank/momentum
even if re-enabled.
**Owning phase:** engine margin/maturity gate phase (build alongside Pitfall #2's guard).

### 2. Flat TACOS overspends past the margin floor (Pitfall #2)
**Highest severity — it's the literal mission metric, and the failure is invisible (still "profitable on
average") while it loses money per thin SKU.**
The retained $2,500→$10k / 25% TACOS instinct is explicitly only the *aggressive ceiling on high-margin
winners*, never the blended target. Two baklava ASINs already sit below the 20% contribution floor; a flat
25% TACOS on them is a guaranteed per-unit loss masked by the fat-margin SKUs in the blended number. With
an aggressive growth posture and an inventory-paced ramp, the system will *want* to push spend — the only
thing stopping a thin-margin bleed is a per-SKU floor.
**Prevention:** engine derives each SKU's TACOS ceiling from its **own** contribution margin to hold net ≥
~15%, and **refuses** any bid/budget write whose projected TACOS breaches that SKU's ceiling — same refusal
pattern as the existing fabricated-TACOS refusal and the flagged price-gate. No margin on file → "no
threshold set" → refuse, never default.
**Owning phase:** engine margin gate phase (closes the flagged write-safety gap).

### 3. Archive irreversibility via `CAMPAIGNS_REMOVE` (Pitfall #4)
**High severity — lowest-frequency but the only structurally irreversible-via-API move in the milestone.**
Every other write (pause, bid, budget, negative) is reversible through the API. `CAMPAIGNS_REMOVE` archives —
recoverable only by hand in console, not by us. The graveyard cleanup touches 75+ IDs at once; one wrong/stale
ID archives a live earner and we can't `actions`-undo it. Two targets are still **ENABLED** (unnamed "Campaign
2026-05-07…"), so an ENABLED→REMOVE in one step would archive a possibly-spending campaign with no observation
period.
**Prevention:** archive is **always last, always its own explicitly-approved batch**, never bundled with
reversible moves. Pre-check: PAUSED + zero-spend ≥30d before eligible. ENABLED graveyard candidates go
**pause → observe → archive** across separate batches. The one move that needs human eyes on every ID.
**Owning phase:** hygiene phase (Wave 5), run dead-last.

---

## Account-Specific Traps (from our own audit)

Not generic — documented in our teardown/execution docs with dollar figures and live IDs:

- **Own private-label ASIN as a conquest target.** B07TV972JT (Alreef #1, our own PL) is a live PATA target
  in ≥2 campaigns. Binding EXCLUDE rule: never target an owned ASIN. (06-20 exec plan §B; 06-17 baklava research)
- **Ads still ENABLED on dead/exiting SKUs.** $546 t90 ($279/mo) bled on FX-M8MA, ZK-4NDS, 9Z-KUHZ, VH-ZTOC —
  listings inactive/discontinued, campaigns still live. Verify-and-pause in Wave 1. This is the single biggest
  lever (~43% of t30 spend, ~$0 sales loss on continuing SKUs). (06-12 §1, §8 item 1)
- **"baklava" EXACT live in ≥4 campaigns + brand terms in 3** — internal auction; de-dupe before any bid-up. (06-12 §6)
- **`baklava gift box` must stay positive** while `chocolate gift box`/"gift box" intent gets negated — the
  textbook over-negation trap, already flagged in our own negative harvest. (06-12 §2)
- **94 campaigns, ~57 a Feb-04 bot/SKW graveyard, no naming convention, no portfolios** — the archive batch is
  large and error-prone; needs the per-ID pre-check above. (06-12 §6; 06-20 Wave 5)
- **GG-0DC1 = 1 FBA unit** — a HERO the engine would otherwise fund; hard-gated on restock so we don't scale
  into a stockout. (06-12 §8 item 8; 06-20 Wave 3)
- **No engine write-gate exists yet.** Today a write is hand-built JSON → dryRun → run. Fine for pauses/negatives;
  **not fine for bids/budgets/price** until the margin/bid guard ships. The flagged open gap this milestone must
  close before scaling spend. (06-20 brain note, "Open engineering gap")
- **API shape constraints:** no portfolio action, no shared-negative-list object, `state` enum ENABLED/PAUSED
  only, writes hit Amazon immediately but DataDoe reporting lags ≤24h. Design around all four. (06-20 exec plan §A)

---

## Open Questions for Planning

1. **Window-maturity vs daily cadence:** the queue is daily but verdicts need 7/14-day matured data. Should the
   engine emit "act now" (reversible stop-loss on *obvious* dead SKUs, e.g. inactive listing) separately from
   "judge later" (efficiency verdicts that wait for the window)? Recommend two verdict classes so attribution lag
   doesn't freeze stop-the-bleed.
2. **Portfolio decision (blocks Wave 4):** skip portfolios (tier in name+tags) or Rami creates 3 tier portfolios
   in console once for `portfolioId`-on-create? Must resolve before new-campaign builds.
3. **Engine bid/budget gate scope:** does the margin guard refuse only at write-time, or also continuously
   re-flag a SKU that drifts over its ceiling after a market change? (mirrors the TACOS refusal — write-gate,
   monitor, or both?)
4. **"Projected TACOS" input:** what does the engine use to project a write's TACOS impact before it lands (since
   results lag the window)? Last-matured-window margin × proposed spend delta? Define it so the gate isn't itself
   acting on immature data.
5. **Standing-approval boundary on negatives:** negatives are "reversible" (standing approval), but over-negation
   suppresses a converting term for its duration. Should phrase/broad negatives require *explicit* approval while
   only exact negatives ride standing approval?
6. **Archive eligibility threshold:** confirm the PAUSED + zero-spend ≥30d rule (and who owns the final per-ID
   review) before any `CAMPAIGNS_REMOVE` batch is built.

---

## Sources

- Amazon Ads attribution windows (SP 7-day, SB/SD 14-day for Seller Central) — [bidx](https://www.bidx.io/blog/amazon-attribution-window), [Intentwise](https://www.intentwise.com/blog/ad-performance-optimization/explained-how-does-amazon-attribute-ad-sales/), [Feedvisor](https://feedvisor.com/university/amazon-sponsored-products-attributed-sales/) (MEDIUM, multi-source agreement; matches milestone brief). Verified 2026-06-20.
- DataDoe action surface, gating chain, API hard limits, dryRun discipline — `brain/raw/2026-06-20_datadoe-write-path-gating.md` + `deliverables/ppc-rebuild-execution-plan_2026-06-20.md §A` (HIGH, verified live against the org).
- Account-specific dollar figures, internal competition, negatives, EXCLUDE rule, dependency order — `deliverables/ppc-rebuild_2026-06-12.md` (engine-computed, exports cached in `data/`) + execution plan §B (HIGH).
- Margin tiers, mission metric, scope/decisions — `.planning/PROJECT.md` (HIGH).
