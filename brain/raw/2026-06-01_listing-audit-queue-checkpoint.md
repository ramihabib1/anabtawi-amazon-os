# Listing Audit — Priority Queue Checkpoint (2026-06-01)

Full catalog content audit. Universe = 25 ACTIVE ASINs (amazon_listings_with_cogs, listing_status=Active).
Sources: amazon_listings_with_cogs (live); amazon_profit_by_sku_and_date t90 (2026-03-03→06-01);
amazon_sales_and_traffic_with_cogs t30 (2026-05-02→06-01); amazon_products_by_child_asin (content).

**Benchmark reset:** conversion_benchmark in targets.md is provisional 12%. Reset to portfolio
top-quartile (P75) conversion among ASINs with ≥20 t30 sessions = **4.94%**. Used for ranking.
Recommend Rami update state/targets.md conversion_benchmark 12 → ~5.

**Tier weights** are NOT defined in state/targets.md (only ACOS targets per tier). Used provisional
weights HERO 1.5 / MAINTAIN 1.0 / CUT 0.5 — flagged as inferred, not authoritative.

**Tiers inferred at runtime** from t90 profit+velocity (anabtawi-context has no authoritative table yet).
Counts: HERO 5, MAINTAIN 7, CUT 13.

Ranking formula: t30 sessions × max(0, 4.94 − actual conv%) × tier weight.

Top of queue (full table in _rollup):
1 B0FXX46ST8 (Baklava 180g, HERO) prio 954 — high traffic, conv 3.6 < bench
2 B0FTSM2HSJ (Baklava 180g, CUT) prio 644 — 666 sess, conv 3.0, margin 1.4% STRUCTURAL LOSER + dup of #1
3 B0FTM6Y263 (Barazek 400g, HERO) prio 450
4 B0FTSMTDGP (Baklava 400g, MAINTAIN) prio 369
5 B0FY6SX9RP (Assorted 250g, MAINTAIN) prio 299

Systemic findings (apply to most ASINs):
- No variation families: every ASIN parent_asin is blank. Baklava sizes, Maamoul flavors,
  Barazek, Ghraybeh, Fingers should each be one parent-child family. Reviews/traffic fragmented.
- Duplicates/cannibalization: TWO 180g baklava (B0FXX46ST8 vs B0FTSM2HSJ), TWO 400g baklava
  (B0FTSMTDGP vs B0FXX3JVR5), TWO 250g barazek (B0FXXM1CK8 vs B0FTSNBX57).
- Wrong browse nodes: baklava under Sweet Rolls/Tarts/Snack Gifts; barazek under Digestive Cookies/Nut;
  cashew fingers under Indian Sweets.
- Titles brand-first ("Anabtawi Sweets…"), not keyword-first; no Halal/Kosher; size attribute blank on ~10 SKUs.
- Bullets are templated/generic across catalog — no dietary (Halal) or allergen lead, weak gifting/Eid angle.
- A+ presence, gallery image count, and review counts are NOT in the DataDoe feed — flagged as
  unverified; need a Chrome pass. Scored conservatively (Amber) rather than fabricated.
