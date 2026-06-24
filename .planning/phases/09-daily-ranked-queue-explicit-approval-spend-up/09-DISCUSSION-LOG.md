# Phase 9: Daily Ranked Queue + Explicit-Approval Spend-Up - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-24
**Phase:** 09-daily-ranked-queue-explicit-approval-spend-up
**Mode:** discuss (interactive)
**Areas discussed:** Magnitude cap (reversible), Phrase/broad negatives, Inventory + conversion spend-up gates, Queue render + spend-up approval UX, Keyword consolidation + harvest graduation

---

## Magnitude cap (reversible)

| Option | Description | Selected |
|--------|-------------|----------|
| Set cap at 50% | Refuse any single reversible bid/budget-down steeper than −50% per action; over-cap → explicit review (never clamps). ~2 days to reach −75%. | ✓ |
| Keep permissive | Reversible moves auto-apply at any magnitude (Phase 8 posture). | |
| Set cap at 75% | Only refuse near-total reversible cuts (>−75%). | |

**User's choice:** Set cap at 50% → D-01
**Notes:** Daily standing auto-apply has a bigger blast radius than Phase 8's one-batch canary; flipping the built-but-off SC-5 guardrail on is a `thresholds.toml` edit, not code.

---

## Phrase/broad negatives

| Option | Description | Selected |
|--------|-------------|----------|
| Explicit approval | Exact stays standing; phrase/broad held for explicit approval (wider, harder-to-reverse collateral). | ✓ |
| Standing approval (all) | Phrase/broad auto-apply like exact. | |
| Exact-only this phase | Don't introduce phrase/broad in Phase 9; defer. | |

**User's choice:** Explicit approval → D-02
**Notes:** Classed by blast radius, not just reversibility. Keep-positive allowlist (`baklava gift box`) carried from 08 D-04.

---

## Inventory cover floor (EXEC-05)

| Option | Description | Selected |
|--------|-------------|----------|
| 6 weeks, flat | Refuse spend-up on a SKU with <6 weeks cover (incl. inbound). | ✓ |
| Tier-aware (8/6/3) | Floor varies by tier. | |
| 6 weeks + hard floor | 6wk soft + near-zero hard floor. | |

**User's choice:** 6 weeks, flat → D-03
**Notes:** Matches roadmap "≥6-week" wording + targets.md maintain tier. Refuses GG-0DC1 (1 unit). Encode as one machine-readable number.

---

## Velocity source (EXEC-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Live DataDoe/AgentCentral MCP | Pull velocity + days-of-cover live at queue time. | ✓ |
| Engine trailing-window export | Compute from cached engine sales export. | |

**User's choice:** Live DataDoe/AgentCentral MCP → D-04
**Notes:** Queue is on-open/on-demand so a live read is the right currency. Agent does MCP I/O; engine stays pure.

---

## Below-benchmark conversion gate (EXEC-05)

| Option | Description | Selected |
|--------|-------------|----------|
| Keep 12% provisional | Hard-refuse raises on SKUs below 12% conversion; tune later. | ✓ |
| Portfolio top-quartile | Floor = own catalog top-quartile conversion. | |
| Warn, don't block | Conversion advisory only; only stock-cover hard-refuses. | |

**User's choice:** Keep 12% provisional → D-05
**Notes:** Hard refusal this phase. Retune to top-quartile after a sales_and_traffic pull (deferred).

---

## Explicit-approval mechanism (WRITE-04 / QUEUE-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Batch-approve after review | All raises ranked; one explicit confirm for the batch (deselect first allowed). | ✓ |
| Per-line approve | Each raise approved individually. | |
| By-SKU approve | Approve all raises for a SKU at once. | |

**User's choice:** Batch-approve after review → D-06
**Notes:** Mirrors Phase 8 canary→batch rhythm. Standing reversibles still shown (autonomy ≠ silence).

---

## Daily queue render format (QUEUE-01)

| Option | Description | Selected |
|--------|-------------|----------|
| One $-ranked table, class-tagged | Single table, $-impact desc, no-$ last, class (auto/needs-approval) per row. | ✓ |
| Grouped by approval class | Auto-applied first, then explicit-approval raises. | |
| Grouped by SKU | Changes grouped under each SKU. | |

**User's choice:** One $-ranked table, class-tagged → D-07
**Notes:** Reuses `tacos.classify` sort idiom; dollars-first, one screen; provenance column cites source/window.

---

## Owning-campaign selection (EXEC-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Lowest matured-window ACOS | Most efficient campaign owns the term; paused in others (reversible). | ✓ |
| Highest orders/volume | Proven-volume campaign owns the term. | |
| Flag only, you pick | Surface conflict, block bid-up, manual owner selection. | |

**User's choice:** Lowest matured-window ACOS → D-08
**Notes:** Bid-up blocked until consolidation completes. Pause-in-losers is reversible standing approval; 50% cap doesn't apply to a state-change pause.

---

## Search-term harvest graduation (QUEUE-04 / EXEC-02)

| Option | Description | Selected |
|--------|-------------|----------|
| ≥2 orders + at/under ceiling | Graduate on ≥2 matured-window orders AND ACOS ≤ SKU gate ceiling → new keyword (explicit approval). | ✓ |
| ≥1 order + under ceiling | Lower bar — single order graduates. | |
| Defer harvest to Phase 10 | Fund existing keywords only this phase. | |

**User's choice:** ≥2 orders + at/under ceiling → D-09
**Notes:** Proven conversion AND efficiency before any new dollar; graduation is a spend-up → explicit approval.

---

## Claude's Discretion

- `rank_queue.py` / `queue.py` module + CLI layout (mirror existing thin CLIs).
- Expected-$/wk impact estimator formula (hand-written + pytest-covered; no-estimate rows sort last).
- `days_of_cover_floor` encoding (42 days vs explicit weeks field).
- Matured-window detection per campaign type; poll/idempotency reuse from the Phase 8 spine.

## Deferred Ideas

- New coverage-gap campaigns + portfolios + `CAMPAIGNS_REMOVE` → Phase 10.
- Conversion benchmark retune (portfolio top-quartile) → after a sales_and_traffic pull.
- Tightening the magnitude cap below 50% → config dial.
- Tier-aware cover floors (8/6/3) → revisit if flat 6 proves coarse.
- thresholds/catalog → Supabase → Phase 3.5.
