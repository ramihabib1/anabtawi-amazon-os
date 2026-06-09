# Open Decisions (resolve during /gsd-discuss-phase)

These are the gray areas. Bring them into the discuss phase so the generated plans reflect your intent rather than defaults.

1. **Supabase schema shape.** Confirm or adjust the five tables (`sku_master`, `cogs`, `metric_snapshots`, `decision_ledger`, `config`). What grain for `metric_snapshots` — daily per SKU, or daily per SKU per marketplace? Does `cogs` need FX captured per cost row?

2. **Briefing content & timing.** What exactly goes in the daily Telegram briefing, in what order, and at what local time should the cron fire? What counts as an "anomaly" worth flagging (e.g. sales delta %, margin below floor, unexplained ad change)?

3. **Thresholds to seed `config`.** Real starting numbers: minimum acceptable margin %, days-of-cover that triggers a restock proposal, ACOS ceiling for the ad-spend audit.

4. **Marketplace order.** Harden amazon.ca fully through Phase 2 first, or carry US-expansion fields in the schema from day one even though logic comes later?

5. **DataDoe source selection.** For sales/margin, which specific DataDoe source(s) and columns are authoritative? (Resolve empirically via `exports_sources_get` during Phase 1, but capture the decision here once made.)

6. **Telegram approval UX.** For Phase-2 proposals (restock, clearance candidates): inline Approve/Reject buttons, or a reply-with-keyword flow? Where does the approval token get recorded in `decision_ledger`?

7. **Backups.** Where do `~/.hermes/` snapshots and the Supabase dump land, and on what schedule?
