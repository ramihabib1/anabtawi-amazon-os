# Pitfalls Research

**Domain:** Read-only Amazon FBA PPC & profit intelligence agent (Hermes desktop app + DataDoe + Supabase)
**Researched:** 2026-06-08
**Confidence:** HIGH on metric/attribution and anti-fabrication pitfalls (verified against Amazon Ads docs + text-to-SQL hallucination research); HIGH on DataDoe/Hermes constraints (authoritative internal docs); MEDIUM where DataDoe behavior is inferred from the documented call pattern rather than published API contracts.

This project's failure modes are unusual: the data layer is read-only and the agent cannot move money, so the classic "autonomous spend disaster" is structurally prevented. That shifts the entire risk surface onto **correctness of numbers** and **trust**. The prior agency's two sins — unauthorized actions and *fabricated reporting* — map directly onto the two things this system must never do: act, and lie with numbers. The action vector is already closed by architecture. The fabrication vector is the live threat, and most pitfalls below feed it: a metric that is silently wrong is indistinguishable, to the operator, from a fabricated one. Both destroy trust the same way.

---

## Critical Pitfalls

### Pitfall 1: ACOS/TACOS computed or labeled wrong (the headline-number trust killer)

**What goes wrong:**
The agent reports an ACOS or TACOS figure that is subtly wrong — most often by confusing the two, or by computing TACOS against the wrong sales denominator. ACOS = ad spend ÷ **ad-attributed** sales. TACOS = ad spend ÷ **total** sales (ad + organic). Swapping the denominator, or summing ad spend across SP/SB/SD while dividing by only SP-attributed sales, produces a number that looks plausible and is wrong by a large factor.

**Why it happens:**
The metrics share a name stem and differ only by denominator, so prompt-driven math conflates them. Worse, this build has *two* authorities for these numbers: DataDoe's premium "Profit by SKU & Date" computes ACOS/TACOS/ROI directly, while the PPC sources give raw spend/sales the agent could divide by hand. If the agent ever hand-rolls the ratio instead of reading the premium column, it can disagree with Amazon's own definition and with the premium source — silently.

**How to avoid:**
- Treat DataDoe premium "Profit by SKU & Date" ACOS/TACOS/ROI as the **single authority** (a locked Key Decision already). The agent reads these columns; it does not recompute them from raw spend/sales.
- Where a hand-written denominator is unavoidable (e.g., premium source missing a SKU), the formula lives in a hand-written, version-controlled Python primitive — never in a prompt — and is labeled as a fallback in the output.
- Every reported ratio carries its definition inline ("TACOS = ad spend / total sales") and its source ("premium Profit-by-SKU") so the operator can audit the label, not just the value.

**Warning signs:**
- A reported TACOS that exceeds ACOS for the same SKU (TACOS denominator is larger, so TACOS should be ≤ ACOS — a flip means denominators are swapped).
- ACOS that doesn't reconcile to (spend ÷ ad-sales) on a manual spot-check.
- The agent producing a ratio when asked, without naming which DataDoe column it came from.

**Phase to address:**
Phase 1 (profit/margin primitive). This is the core acceptance test — answers must be spot-checked manually against Seller Central before the milestone is "done."

---

### Pitfall 2: Double-counting ad spend across SP / SB / SD, and attribution-window overlap

**What goes wrong:**
Total ad spend or ad-attributed sales is inflated because the three ad programs are summed naively. Sponsored Display has the most generous attribution model on Amazon — it can attribute *any* brand product purchased within 14 days of a click or view back to the campaign — and Sponsored Brands attributes on day-of-purchase over 14 days, while seller Sponsored Products use a 7-day day-of-click window. Summing attributed *sales* across all three can credit the same conversion more than once; summing *spend* is safe only if you know which sources each table already includes.

**Why it happens:**
The DataDoe PPC sources mix scope: "Ad Performance by ASIN & Date" explicitly covers **SP + SD**, while campaign-level and search-term tables are program-specific. An analyst who assumes one table = one program (or that summing tables = "all ads") will double-count. Different attribution windows mean the same date range pulls different conversion sets per program, so they can't be added as if commensurable.

**How to avoid:**
- Document, per DataDoe source, exactly which ad program(s) and which attribution window it covers (resolve empirically via `exports_sources_get` in Phase 1, then record it in the truth store / skill docs).
- Never sum *attributed sales* across programs to get a "total ad sales" number — use TACOS off the premium table instead, which sidesteps the overlap entirely.
- When reporting spend, state the program scope ("SP+SD per Ad-Performance-by-ASIN") rather than implying "all advertising."
- For negative-keyword and search-term work, stay within the single search-term source (SP) rather than blending programs.

**Warning signs:**
- "Total ad sales" that exceeds the sum of per-program sales reported elsewhere, or that nears total store sales.
- The same conversion appearing in two program reports for overlapping dates.
- A spend total that doesn't reconcile to Seller Central's Advertising > Campaign Manager spend for the same window.

**Phase to address:**
Phase 1 (PPC read/compute primitives), specifically the source-scope mapping step.

---

### Pitfall 3: Date-range and timezone misalignment between PPC, profit, and persisted snapshots

**What goes wrong:**
PPC and profit numbers are compared across different time bases and silently disagree. Amazon reports inconsistently: the Seller Central UI and Business Reports render in **Pacific Time**, while some order data is in **UTC**, and ad reports have their own conventions. If the agent's DataDoe `from`/`to` filters, the premium profit table's day boundaries, and the operator's mental model (Eastern, where the business is) don't agree, "yesterday's ACOS" pulls a different day's spend than "yesterday's sales."

**Why it happens:**
DataDoe `exports_create` requires `from`/`to` when a source has a date column, but the underlying timezone of each source's date column is not obvious. Mixing a PST-bounded ad day with a UTC-bounded order day shifts up to several hours of activity across the date boundary — invisible in aggregate, material at day grain.

**How to avoid:**
- Pin one canonical reporting timezone for the whole system (recommend Amazon's native PST for ad/sales alignment, since most Seller Central surfaces and the operator's spot-checks live there) and convert at the *edges* only.
- Record the timezone basis of each DataDoe source alongside its scope (Phase 1 source-mapping), and never compare two sources at day grain until both bases are confirmed equal.
- Decide `metric_snapshots` grain explicitly (flagged open: daily per SKU per marketplace) and stamp every snapshot row with the date basis used.

**Warning signs:**
- Daily totals that match weekly/monthly rollups in aggregate but are individually off by one day.
- Spend and sales for "the same day" that reconcile in Seller Central only when you shift one by a day.
- A snapshot that disagrees with a fresh DataDoe pull for the same date.

**Phase to address:**
Phase 0 (confirm source date semantics during the by-hand export test) and Phase 1 (snapshot schema + briefing).

---

### Pitfall 4: The agent invents numbers or thresholds instead of reading them (anti-fabrication)

**What goes wrong:**
The agent emits a number, ACOS ceiling, min-margin %, or days-of-cover trigger that it generated rather than retrieved — exactly the fabricated-reporting failure that motivated this entire project. LLMs answering financial questions retrieve the most statistically plausible number from training data when the real value isn't grounded in a tool result; the output looks legitimate and is fiction. In text-to-SQL specifically, a query can execute successfully yet be semantically wrong (wrong filter format → zero rows → a confidently empty or made-up summary).

**Why it happens:**
- Thresholds feel like "knowledge" the model already has, so it answers from priors instead of reading Supabase `config`.
- When a DataDoe export fails, times out, or returns zero rows, an ungrounded agent fills the gap with a plausible figure rather than reporting the failure.
- Prompt-level math invites the model to "compute" rather than retrieve.

**How to avoid:**
- **Hard rule, already in CLAUDE.md:** never invent thresholds — read them from Supabase `config`. Enforce it structurally: money-touching logic is hand-written Python that *reads* config, not prompt math, so there is no code path that can emit an unsourced threshold.
- Every numeric claim must trace to a tool result (a DataDoe export id or a Supabase row). Build the read primitives to return the value *and* its provenance, and have the agent cite the source with the number.
- On any failed/empty/partial export, the skill returns an explicit "no data / failed export" state — never a substituted estimate. Refuse-when-unsure beats plausible-when-wrong.
- Seed `config` with real numbers early (flagged open) so the agent always has something authoritative to read; an empty config tempts fabrication.

**Warning signs:**
- A threshold appears in output that isn't present in `config`.
- Numbers that don't carry a provenance reference (export id / table row).
- Confident summaries over date ranges where the export actually failed or returned zero rows.
- Round, "typical" figures (e.g., "ACOS around 25%") with no source.

**Phase to address:**
Phase 1 (config table + grounded read primitives + provenance in every numeric output). This is the milestone's trust spine and the most important pitfall in this document.

---

### Pitfall 5: Treating DataDoe point-in-time exports as immutable truth (restatement drift)

**What goes wrong:**
A snapshot persisted to Supabase is later contradicted by a fresh DataDoe pull for the same date, and the operator can't tell which is "right." Amazon **constantly restates attributed sales** (attribution can update over a window up to ~60 days), sales reports are explicitly estimates subject to later adjustment, and financial/fee data settles over weeks. A number captured today for last week is provisional.

**Why it happens:**
The whole point of the Supabase truth store is to persist point-in-time DataDoe exports — but if snapshots are stored as if final, the system loses the ability to reconcile against later-restated values and may surface stale figures as current.

**How to avoid:**
- Stamp every `metric_snapshots` row with `captured_at` and the source export id; treat snapshots as *versioned observations*, not final facts.
- For PPC/attributed metrics, allow a re-pull window (don't freeze a day's ad numbers until past the attribution-settlement horizon).
- When the briefing reports recent days, label them provisional; reconcile and optionally re-snapshot after settlement.
- Use `cogs` as the stated FX/reconciliation fallback so margin doesn't silently inherit a stale fee snapshot.

**Warning signs:**
- A snapshot's ACOS for a recent day drifts on re-pull.
- Month-end fee reconciliation moves margins the daily briefing had already reported as final.
- Operator notices the same SKU/day reported with two different values across runs.

**Phase to address:**
Phase 1 (snapshot schema must carry capture metadata) and Phase 2 (reconciliation skill — flagged for M2/M3 but the schema decision happens now).

---

### Pitfall 6: Wrong seller scope / marketplace bleed

**What goes wrong:**
An export omits or mis-scopes `sellerOrVendorIds`, returning data for the wrong (or no) seller, or US data contaminates CA logic. Numbers come back plausible but for the wrong entity.

**Why it happens:**
Every DataDoe call requires resolving the seller UUID first (`sellers_and_vendors_list`), and the schema is deliberately CA-first-but-US-ready with marketplace as a first-class column. A skill that forgets to filter by marketplace, or hardcodes the wrong UUID, mixes markets. (Note: the Agent Central MCP key in this environment is CA-scoped — but the build's single source is DataDoe, which is multi-seller and *does* require explicit scoping.)

**How to avoid:**
- Cache the amazon.ca UUID (`5692b95f-f3f0-4063-9c1c-40177c54f408`) in `.env` as `AMAZON_CA_SELLER_ID`; never inline it.
- Make marketplace a required parameter on every read primitive and a required column on every snapshot — fail loudly if absent.
- Until CA is solid, US logic stays deferred; the column carries the dimension without inviting cross-market math.

**Warning signs:**
- Row counts or totals that don't match the known ~30-SKU CA catalog.
- SKUs appearing that belong to the US expansion.
- An export that ran without a seller filter.

**Phase to address:**
Phase 0 (resolve + cache UUID, confirm sources) and Phase 1 (marketplace as required dimension).

---

### Pitfall 7: The 2500-row export cap silently truncates results

**What goes wrong:**
A search-term or order-line export hits DataDoe's hard `limit` cap of 2500 rows and returns a truncated set with no error, so totals undercount and "top wasted-spend search terms" misses the long tail. Search-term tables for even a modest catalog can exceed 2500 rows over a multi-week window.

**Why it happens:**
`limit` caps at 2500; an agent that doesn't paginate (`skip`) or pre-aggregate (`groupBy` + `aggregations`) assumes one export = complete data. Truncation is silent — the export still COMPLETES.

**How to avoid:**
- Prefer server-side `groupBy` + `aggregations` to collapse rows before they hit the cap (e.g., aggregate spend by search term across the window rather than pulling row-per-day).
- Where raw rows are genuinely needed, paginate with `skip` and detect truncation: if a result returns exactly 2500 rows, assume more exist and page until a short page.
- Narrow date windows and filter early.

**Warning signs:**
- An export returns exactly 2500 rows.
- Aggregate spend from a row-level pull undercounts the campaign-level total.
- "Top N" lists that feel suspiciously shallow for the catalog size.

**Phase to address:**
Phase 1 (PPC read primitives must handle the cap by design).

---

### Pitfall 8: Search-term vs targeting (keyword) confusion in negative-keyword work

**What goes wrong:**
The agent recommends negating a *targeting keyword* when it should negate a *customer search term*, or vice versa — proposing changes against the wrong entity. Search Term Performance maps customer search term → matched keyword; Keyword Targeting Performance is the bid target per campaign. These are different objects, and negation acts on search terms harvested under a keyword/target.

**Why it happens:**
The two DataDoe sources both contain "keyword-ish" fields (matched keyword, keyword bid, match type), and the conceptual distinction between "what the customer typed" and "what I'm bidding on" blurs in natural-language prompts.

**How to avoid:**
- Keep the two sources in separate primitives with distinct output vocabularies ("customer search term" vs "targeting keyword/bid").
- Negative-keyword harvesting reads from Search Term Performance only, and proposals explicitly name the search term, its matched keyword, the campaign, and the spend/orders behind it — proposal-only, human-approved (no autonomous write, per hard rule).

**Warning signs:**
- A proposal to "negate" something that is actually a bid target, not a search term.
- Recommendations that reference a keyword without the customer search term that triggered the spend.

**Phase to address:**
Phase 1 (PPC primitives) and the negative-keyword proposal logic.

---

### Pitfall 9: Premium "Profit by SKU & Date" assumed complete / always enabled

**What goes wrong:**
The margin primitive depends on the premium source, but it may not be enabled on the plan, may omit some SKUs, or may embed cost assumptions (its "total cost" bundles fees + COGS + ad spend) that don't match Habib's actual landed cost/FX. Margins are then reported confidently from a source that's missing data or using a different COGS than the truth store.

**Why it happens:**
The locked decision is to prefer the premium source for ACOS/TACOS/ROI, with `cogs` as fallback — correct, but it creates a dependency on a premium feature whose enablement and SKU coverage must be verified, and whose COGS basis may differ from the FX-aware `cogs` table.

**How to avoid:**
- Confirm the premium source is enabled (Phase 0/1) before building margin logic on it.
- Reconcile premium "total cost" / COGS against the `cogs` table on a sample; where they disagree, surface the gap rather than silently trusting one.
- For SKUs the premium source misses, fall back to hand-written margin math over Order Line Items + `cogs` (with FX), clearly labeled as fallback.
- Resolve the open question of whether `cogs` captures FX per cost row — margin correctness for an importer depends on it.

**Warning signs:**
- Premium source returns fewer SKUs than the ~30-SKU catalog.
- Premium net profit disagrees with `cogs`-based margin beyond expected fee variance.
- A SKU's margin reported without indication of whether it came from premium or fallback.

**Phase to address:**
Phase 0 (confirm premium enablement) and Phase 1 (margin primitive + reconciliation).

---

### Pitfall 10: Hermes desktop-app scheduling assumed always-on

**What goes wrong:**
A skill is designed as a clock-cron daily briefing, but the Hermes Mac desktop app runs **only while the Mac is awake and open**. The "05:30 daily briefing" pattern from the older server architecture silently doesn't fire when the Mac is asleep, producing gaps the operator may not notice — and a missing briefing can read as "nothing to report."

**Why it happens:**
The superseded architecture doc still describes a Hetzner cron scheduler; that mental model leaks into skill design. The current runtime has no assumed unattended cron.

**How to avoid:**
- Design Milestone 1 as conversational / on-demand and on-open, not clock-cron (already a locked constraint — keep skills triggerable, not time-fired).
- If a recurring briefing is wanted, trigger it on app-open or on first query of the day, and stamp it with the data window it actually covers so a missed day is visible.
- Defer true scheduling to a later milestone that explicitly chooses an always-on Mac or an on-open trigger; never silently assume cron.

**Warning signs:**
- A skill spec that says "runs at 05:30" with no on-open fallback.
- Missing snapshots on days the Mac was closed.
- Briefings that don't state their covered date window.

**Phase to address:**
Phase 1 (skill cadence design — on-demand/on-open, not cron).

---

### Pitfall 11: `~/.hermes` loss / MCP credential over-scoping

**What goes wrong:**
The agent's procedural memory, skills, and persona live locally in `~/.hermes`; a disk loss or Mac failure wipes them with no backup. Separately, MCP credentials scoped too broadly could, in a future write-MCP milestone, exceed the read-only intent — re-opening the action vector this whole architecture closes.

**Why it happens:**
Local-only state is easy to forget to back up; backup target/schedule is still an open decision. Credential scope is invisible until something writes.

**How to avoid:**
- Back up `~/.hermes` (Time Machine + an explicit copy) and the Supabase dump on a schedule; resolve the open backup-target decision before relying on local memory.
- Keep DataDoe and Supabase credentials read-only-scoped; verify the desktop preview's MCP credential filtering before trusting it.
- Any future write-MCP is a separate gated milestone with one-time approval tokens — never a widened credential on the existing connection.

**Warning signs:**
- No tested restore of `~/.hermes`.
- A credential that grants more than read where read is all that's intended.

**Phase to address:**
Phase 0 (read-only credential scoping) and Phase 1 (backup of `~/.hermes` + Supabase).

---

### Pitfall 12: Recommendation phrasing that implies the system can act

**What goes wrong:**
A proposal is worded as though the agent will execute it ("Lowering bid on keyword X"), eroding the structural read-only contract in the operator's perception and inviting eventual autopilot — the exact pattern the prior agency abused.

**Why it happens:**
Natural-language output drifts toward active voice; the line between "I recommend" and "I did" blurs under terse, numbers-first phrasing.

**How to avoid:**
- All write-adjacent output is a **proposal** with the data behind it, phrased as a recommendation requiring human approval, logged to `decision_ledger`.
- Persona (SOUL.md) explicitly: recommends, never acts on Amazon; never invents pricing/thresholds.
- Every proposal carries Approve/Reject and is recorded — the ledger is the trust spine.

**Warning signs:**
- Output in the past/active tense about Amazon changes.
- A recommendation without an approval gate or ledger entry.

**Phase to address:**
Phase 1 (persona + proposal/ledger pattern), reinforced in every later write-path milestone.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Hand-rolling ACOS/TACOS in a prompt instead of reading the premium column | Fast answer without wiring the premium source | Diverges from Amazon's definition; fabrication risk; two conflicting authorities | Never for money metrics; only a labeled fallback in hand-written Python when premium misses a SKU |
| Storing `metric_snapshots` without `captured_at` / export id | Simpler schema | Can't reconcile against Amazon restatement; stale numbers surface as current | Never — capture metadata is cheap and load-bearing |
| Single-export pulls ignoring the 2500-row cap | Less code | Silent truncation, undercounted totals | Only when a `groupBy` aggregation provably returns <2500 rows |
| Clock-cron briefing on the desktop app | Familiar pattern | Silently misses days the Mac is closed | Never on Milestone 1; only with a confirmed always-on Mac in a later milestone |
| Hardcoding thresholds in prompts/skills | Quick to write | Fabrication vector; un-auditable; violates a hard rule | Never — always read from `config` |
| Empty/seeded-later `config` | Ship sooner | Agent tempted to invent thresholds | Only with a refuse-when-missing guard so absence never yields a made-up number |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| DataDoe `exports_create` | Skipping `from`/`to` or ignoring source timezone | Always pass date bounds; record each source's timezone + program scope before comparing at day grain |
| DataDoe results | Assuming COMPLETED = full data | Detect 2500-row truncation; paginate with `skip` or pre-aggregate; treat FAILED/empty as "no data," never substitute |
| DataDoe seller scope | Forgetting `sellerOrVendorIds` / wrong UUID | Resolve via `sellers_and_vendors_list`, cache CA UUID in `.env`, require marketplace on every call |
| Premium Profit-by-SKU | Assuming enabled + complete + matching COGS | Confirm plan enablement; reconcile its cost basis against `cogs` (with FX); fall back + label per missing SKU |
| Supabase snapshots | Storing point-in-time pulls as final truth | Version with capture metadata; allow re-pull within attribution-settlement window |
| Amazon Ads attribution | Summing attributed sales across SP/SB/SD | Don't add across programs; use premium TACOS; report spend with explicit program scope |
| Hermes MCP credentials | Broad scope "to be safe" | Read-only scope verified; write only via a future gated MCP with one-time tokens |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Row-level search-term pulls over wide windows | Exactly-2500 results; slow exports | Aggregate server-side; narrow windows | As search-term volume × date range exceeds 2500 rows (well within ~30 SKUs over a few weeks) |
| Re-pulling full history every briefing | Slow runs; redundant exports | Incremental snapshots keyed by date + captured_at | As history grows past a few months |
| High `skip` offsets for pagination | Slow page fetches | Prefer aggregation over deep pagination | Large raw result sets |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Secrets / seller UUID inline in code or skills | Credential/identity leak; committed secrets | `.env` only; never commit; CLAUDE.md hard rule |
| Over-scoped MCP credentials | Future write capability beyond read-only intent | Verify read-only scoping in the desktop preview before trusting it |
| No backup of `~/.hermes` / Supabase | Loss of audit ledger + procedural memory | Scheduled Time Machine + explicit copy + DB dump; test restore |
| Unlogged external calls | No audit trail for a trust-critical system | Wrap and log every DataDoe/Supabase call (CLAUDE.md observability rule) |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Numbers reported without provenance/definition | Operator can't audit; trust erodes after the prior agency's fabrication | Every figure cites source (export id / config row) + definition inline |
| Provisional recent-day numbers shown as final | Operator acts on figures that restate later | Label recent days provisional; reconcile after settlement |
| Briefings that don't state their date window | A missed (Mac-asleep) day reads as "nothing to report" | Stamp every briefing with the exact window it covers |
| Proposals phrased as completed actions | Implies autopilot; breaches read-only trust | Recommendation voice + explicit approval gate + ledger entry |

## "Looks Done But Isn't" Checklist

- [ ] **ACOS/TACOS answer:** Often missing definition + source label — verify it names the premium column and reconciles to a manual Seller Central spot-check.
- [ ] **PPC spend total:** Often missing program scope — verify it states SP/SB/SD coverage and doesn't double-count attributed sales.
- [ ] **Daily snapshot:** Often missing `captured_at`/export id and timezone basis — verify it can be reconciled after Amazon restates.
- [ ] **Any threshold in output:** Often invented — verify it traces to a Supabase `config` row, and that a missing config yields refusal, not a guess.
- [ ] **Search-term export:** Often silently truncated — verify it handles the 2500-row cap (aggregation or pagination).
- [ ] **Margin figure:** Often from premium source without coverage check — verify premium enablement, FX-aware COGS reconciliation, and labeled fallback for missing SKUs.
- [ ] **Recurring briefing:** Often assumes cron — verify on-open/on-demand trigger and visible coverage window on the desktop app.
- [ ] **Every external call:** Often unlogged — verify DataDoe/Supabase calls are wrapped and logged.

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Wrong ACOS/TACOS shipped | MEDIUM | Re-derive from premium column; correct the output; add the definition+provenance guard so it can't recur; spot-check the rest |
| Double-counted ad spend | MEDIUM | Re-map source program scopes; switch totals to premium TACOS; re-issue affected reports |
| Fabricated number/threshold | HIGH (trust) | Trace the claim; if no provenance, retract and correct; add refuse-when-ungrounded guard; audit `config` reads — this is the cardinal sin for this project |
| Stale snapshot vs restatement | LOW | Re-pull for the date; compare via captured_at; re-snapshot; label provisional going forward |
| Truncated 2500-row export | LOW | Re-run with aggregation or pagination; recompute the affected total |
| Missed briefing (Mac asleep) | LOW | Trigger on next open with explicit catch-up window; add on-open trigger |
| `~/.hermes` loss | HIGH | Restore from backup; if none, rebuild skills/persona from version control — back up immediately after |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| ACOS/TACOS wrong/swapped | Phase 1 (profit primitive) | Manual Seller Central spot-check of each acceptance question |
| SP/SB/SD double-counting + attribution overlap | Phase 1 (PPC primitives) | Per-source program/window map recorded; spend reconciles to Campaign Manager |
| Date/timezone misalignment | Phase 0 + Phase 1 | Source timezones documented; daily totals reconcile to weekly rollups |
| Invented numbers/thresholds | Phase 1 (config + grounded reads) | Every numeric output carries provenance; missing config → refusal, not a guess |
| Restatement drift in snapshots | Phase 1 (schema) + Phase 2 (reconciliation) | Snapshots carry captured_at + export id; re-pull comparison works |
| Wrong seller/marketplace scope | Phase 0 + Phase 1 | UUID cached; marketplace required on every primitive; row counts match CA catalog |
| 2500-row truncation | Phase 1 (PPC primitives) | No export returns exactly 2500 silently; aggregation/pagination in place |
| Search-term vs targeting confusion | Phase 1 (PPC primitives) | Negation proposals name the customer search term + matched keyword + campaign |
| Premium-source completeness/COGS basis | Phase 0 + Phase 1 | Premium enablement confirmed; FX-aware COGS reconciled; fallback labeled |
| Desktop cron assumption | Phase 1 (skill cadence) | Skills are on-demand/on-open; briefings stamp coverage window |
| `~/.hermes` loss / credential scope | Phase 0 + Phase 1 | Read-only scope verified; tested backup/restore of `~/.hermes` + Supabase |
| Action-implying phrasing | Phase 1 (persona + ledger) | All write-adjacent output is a logged, approval-gated proposal |

## Sources

- Amazon Ads — attribution basics & windows (SP 7-day seller / 14-day vendor; SB 14-day day-of-purchase; SD 14-day, most generous brand-halo model): https://advertising.amazon.com/library/guides/basics-of-amazon-attribution and https://omnitail.net/amazon-sponsored-ad-types/ (MEDIUM–HIGH; multiple sources agree)
- ACOS vs TACOS definitions and formulas: https://www.datadoe.com/blog-posts/amazon-acos-vs-tacos and https://myamazonguy.com/press/acos-vs-tacos-on-amazon/ (HIGH; consistent across many sources)
- Amazon reporting timezone (PST UI vs UTC order data), data lag, and constant attribution restatement (~60-day window): https://docs.openbridge.com/en/articles/5053618-understanding-timezones-within-amazon-seller-central-and-amazon-advertising and https://developer.amazon.com/docs/reports-promo/reporting-FAQ.html (HIGH)
- LLM/text-to-SQL hallucination classes (schema/logic/content; syntactically-valid-but-semantically-wrong; grounding/refuse-when-unsure as the fix): https://arxiv.org/html/2512.22250v1 and https://dev.to/valyuai/why-your-ai-agent-keeps-hallucinating-financial-data-and-how-to-fix-it-180d (HIGH)
- DataDoe call pattern, 2500-row cap, source scope (SP+SD on Ad-Performance-by-ASIN), premium Profit-by-SKU caveats, seller-UUID scoping: authoritative internal docs `docs/04-data-tools-reference.md` and `docs/01-architecture.md` (HIGH for project-specific constraints)
- Hermes desktop runtime constraints (awake/open only; no unattended cron; `~/.hermes` local memory + backup), read-only data layer, no autonomous writes, never-invent-thresholds, money-logic-hand-written: `CLAUDE.md`, `.planning/PROJECT.md`, `docs/02-context-and-constraints.md` (HIGH; binding project conventions)

---
*Pitfalls research for: read-only Amazon FBA PPC & profit intelligence agent (Hermes desktop + DataDoe + Supabase)*
*Researched: 2026-06-08*
