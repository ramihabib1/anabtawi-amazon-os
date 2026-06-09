# Pricing strategy & sea-freight shift (from Rami, 2026-06-02)

**Strategic stance:** Rami is deliberately prioritizing **velocity + review-building over margin right now**, not chasing the 25% margin floor on the profit-core SKUs. Reason: he's moving to **sea freight** which will sharply lower landed cost (~$1/kg shipping; a 400g box ≈ $0.40 freight vs the higher air cost baked into today's COGS).

## Implications for the system
- **Don't flag thin-but-positive margin as a problem** on these SKUs while in the growth/review-building phase. The margin floor in `state/targets.md` (30/25/20%) is a *future* target, not a current constraint — note this when running profit/listing audits so it doesn't keep surfacing "below floor" on intentionally-discounted SKUs.
- **Negative margin is still a problem** — e.g. FX-M8MA duplicate at −18% t30 (paying customers to buy a listing we're retiring). Thin-positive = OK; negative = not OK.
- Coupons currently running: 400g B0FXX3JVR5 sells at ~$44 vs $55.99 list (~21% off) → realized t30 margin ~7.5%. This is intentional for now. Keep, but stay ≥ breakeven.

## Action when sea costs land
- Get the real per-unit sea freight + updated product cost, update COGS in DataDoe so floor math reflects reality. Current 400g COGS breakdown: cogs_item $20.05 + freight ~$6.72 = $26.77 total (air). Sea freight would cut the ~$6.72 toward ~$0.40 → landed ~$20.45 → margin at $55.99 jumps to ~41% (or ~29% even at the $44 coupon price).
- Note tension: the recent PI/proforma *raised product cost* (850g → $37.74) while sea freight *lowers* the freight component — net landed cost per SKU TBD once both are known. Get the full updated proforma + sea freight rate to resettle every floor.

## Open
- Need: current air freight $/unit per SKU + confirmed sea rate, and the updated proforma product costs for 180g/400g/250g. See [[2026-06-02_top5-deep-dive-findings]].
