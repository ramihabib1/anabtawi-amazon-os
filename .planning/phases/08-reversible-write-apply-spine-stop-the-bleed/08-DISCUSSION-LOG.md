# Phase 8: Reversible-Write Apply Spine + Stop-the-Bleed - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-22
**Phase:** 08-reversible-write-apply-spine-stop-the-bleed
**Areas discussed:** Magnitude cap, Stop-the-bleed batch, Own-ASIN denylist, First-write rollout

---

## Magnitude cap (standing-approval boundary, SC-5)

| Option | Description | Selected |
|--------|-------------|----------|
| Pauses+exact auto, bid-down ≤30% | Pauses + exact negatives auto any size; single bid-down auto ≤−30%; bigger + phrase/broad → explicit | |
| Conservative — bid-down ≤15% | Bid-down auto ≤−15%; pausing recent-sales targets + phrase/broad → explicit | |
| Permissive — all reversible auto | Any reversible move (pause/negative/bid-down, any magnitude) auto; only spend-up explicit | ✓ |

**User's choice:** Permissive — all reversible auto.
**Notes:** Reconciled against ROADMAP SC-5 (which mandates a magnitude cap). Resolution (CONTEXT
D-02): build + test the cap mechanism but seed it permissive — mirrors Phase 7 D-07
(build-refusal-path, seed-live-value). Reversibility + the canary (D-08) are the safety net.

---

## Stop-the-bleed batch (EXEC-01 / SC-4)

| Option | Description | Selected |
|--------|-------------|----------|
| Pause dead campaigns + negatives, one batch | Pause whole campaigns for the 4 dead SKUs + exact negative harvest, one batch after canary | ✓ |
| Surgical — keywords only | Leave campaigns ENABLED, pause only wasteful keywords/targets | |
| Staged — pauses first, negatives later | Batch 1 pauses, observe, Batch 2 negatives | |

**User's choice:** Pause dead campaigns + negatives, one batch.
**Notes:** Whole-campaign pause chosen for cleanest reversible stop + no empty ENABLED shell.
`baklava gift box` kept positive; watch-don't-negate terms bid-down not negated; exact-only.

---

## Own-ASIN denylist (EXEC-01 / SC-4)

| Option | Description | Selected |
|--------|-------------|----------|
| All ~30 owned ASINs, hard block | Block ad-targeting at any owned ASIN, from sku_catalog, refused before dryRun | ✓ |
| Only B07TV972JT for now | Hard-block just the one known offender | |
| Flag all ~30, ask each time | Detect across full set but surface for confirm, not auto-refuse | |

**User's choice:** All ~30 owned ASINs, hard block.
**Notes:** Initial response was a clarification request ("what do you mean"); concept re-explained
(paying to advertise our own product on our own page = wasted spend). User then chose the full-set
hard block. B07TV972JT becomes one row in the catalog, not a special case.

---

## First-write rollout posture (WRITE-03)

| Option | Description | Selected |
|--------|-------------|----------|
| Canary pause + manual confirm, then batch | One pause end-to-end with manual confirm on first apply, verify, then run batch | ✓ |
| No canary — trust dryRun + tests | Run full standing-approved batch directly | |
| Manual confirm on every apply this phase | Treat all of Phase 8 as canary | |

**User's choice:** Canary pause + manual confirm, then batch.
**Notes:** One-time manual confirm on the first apply only (not per-action). After the canary
reconciles, reversible moves auto-apply per D-01.

---

## Claude's Discretion

- Poll-loop interval/backoff + max-attempts (reuse `datadoe.poll_status`).
- `find_cache` staleness-window value (documented dial, not silent default).
- `actions_ledger.jsonl` format, hash field set, apply-spine module/CLI layout.
- Negative-add via dedicated negative-create vs target-state (pin against `actions_details_schema_get`).

## Deferred Ideas

- External precondition: org-owner must enable the Ads action types in DataDoe → Settings → Actions before any real write.
- Spend-up + daily ranked queue, act-now-vs-judge-later boundary → Phase 9.
- Tightening the magnitude cap if a winner is ever hurt → config change (D-02 dial).
- New-campaign chains, portfolios, `CAMPAIGNS_REMOVE` → Phase 10.
- thresholds/catalog → Supabase → Phase 3.5.
