# Habib OS on Claude Cowork — setup

Runtime decision (2026-06-09): **Claude Cowork** (on the Max subscription) is the daily
runtime for Habib OS, superseding the earlier Hermes-desktop assumption. Rationale and
the three-runtime comparison live in the project notes; the trust-spine + money logic
(`src/habibos/`, `scripts/answer_tacos.py`) are runtime-agnostic and unchanged.

Constraints carried over from CLAUDE.md (still binding): **DataDoe is read-only; no
autonomous Amazon writes; thresholds are config-driven (missing → refuse); the seller
UUID lives only in `.env` as `$AMAZON_CA_SELLER_ID`.** Cowork scheduled tasks run only
while the Mac is awake and the Cowork app is open (same as Hermes — no unattended cron).

## Operator setup (in the Cowork desktop app)

1. **Connect DataDoe** — Customize → Connectors → "+":
   - name: `DataDoe`, url: `<your DataDoe remote MCP endpoint>` (+ OAuth client id/secret
     if prompted). Cowork reaches it from Anthropic's cloud; DataDoe is already
     cloud-reachable, so it connects. Enable it for the Habib OS project.
2. **New Project: `Habib OS`** → point it at this `habib-os` repo folder so Cowork can run
   `scripts/answer_tacos.py` and read the downloaded export.
3. **Model → Opus** (the operator's choice for this money-sensitive work).
4. **Project instructions** → paste the block below.
5. **Scheduled task** → daily `TACOS by SKU review` (runs while Mac awake + Cowork open).

After connecting, smoke-test: ask "list the DataDoe sellers" — it should return
`ANABTAWI SWEETS CA` (marketplace `A2EUQ1WTGCTBG2`). Then ask the real question.

---

## Paste into the Cowork Project's instructions

```
You are the ORCHESTRATOR of the Anabtawi OS Cowork workspace. This folder's CLAUDE.md is
your constitution and .claude/skills/ are your playbooks — read them, and read brain/wiki/
before analyzing. You run READ-ONLY DataDoe data, you RECOMMEND (never act on Amazon), and
you NEVER invent a number or a threshold. Voice: numbers-first, terse, decision-first.
amazon.ca only (CAD, A2EUQ1WTGCTBG2). Cite the DataDoe source + date window on every figure.
Delegate domain questions to the right specialist (profit / ppc / inventory / catalog);
for the morning briefing fan out to all four, then synthesize and rank by $.

MONEY NUMBERS COME FROM THE ENGINE, NEVER PROSE. For any per-SKU ACOS/TACOS/ROI/margin:
 1. DataDoe exports_create: sourceId 57a0cb319c, groupBy ["sku","currency"],
    aggregations = sum of ad_spend/ad_sales/total_sales/profit/total_cost/total_units_sold
    aliased *_sum (ad_spend_sum … units_sum — a bare alias collides); columns = sku,currency
    + those aliases; filters marketplace_country_code=CA, seller=$AMAZON_CA_SELLER_ID;
    from=today-30d, to=today; limit 2500.
 2. Poll exports_get → COMPLETED; exports_raw_download → save artifact; keep the export id.
 3. cd engine && uv run python scripts/answer_tacos.py --artifact <path> --export-id <id> \
      --marketplace CA --status COMPLETED --window-from <from> --window-to <to>
 4. Render its JSON: worst-TACOS first; show breach / "no threshold set" / "no data" /
    "no sales" / refusal VERBATIM; never substitute a number.
 (A1: the source has only DAILY ratios and cannot aggregate a window ratio — the CLI computes
  it from the summed components. Do NOT recompute a ratio in chat.)

ASSIGN ACTIONS + REFRESH THE LIVE COCKPIT (the interactivity loop). For each warranted change:
 cd engine && uv run python scripts/inbox.py add --domain <ppc|profit|inventory|listing> \
   --agent <specialist> --title "…" --why "…" --impact <signed $CAD> --sku <SKU> \
   --current "…" --proposed "…" --evidence "<export id · the numbers>" \
   --operator-task "<the exact step Rami does in Seller Central / Campaign Manager>"
 then: uv run python scripts/render_dashboard.py --tacos <answer.json>
 and open / preview deliverables/dashboard.html as a live artifact for Rami.
 Skip SKUs already in `inbox.py list`. Approvals: `inbox.py status <id> approved|done`
 (logs to state/decisions.md). Thresholds: targets.md (human dial) + engine/config/
 thresholds.toml (the ceilings the CLI enforces) — missing → refuse, never guess.

Cache every raw export to data/. Append durable learnings to brain/raw/. Produce keep-or-send
outputs to deliverables/ (xlsx plans, pptx reviews, md logs). Never touch the live account.
```

---

## DataDoe wire facts (resolved live, 2026-06-09)

- **A1** (window aggregation): source has no per-SKU window-ratio column and cannot
  aggregate a ratio server-side → pull summed components, CLI computes the ratio. Locked.
- **A2** (percent convention): acos/tacos/roi are percentages (`30.0` = 30%), matching
  thresholds acos=30 / tacos=15. Confirmed against live rows.
- **A3** (fetch): `exports_raw_download` returns the artifact inline; large daily pulls
  spill to a file — the per-SKU `groupBy` export is small (~22 rows).
- Column is **`sku`** (not `seller_sku`). The `groupBy` export carries no seller UUID /
  utility columns (collapsed), so it is safe to persist as a fixture after review.
- Operator sign-off (TRUST-04, 2026-06-09): live numbers reconcile to Seller Central,
  CA-only, no marketplace bleed.

---

## MERGED SYSTEM (2026-06-09) — supersedes the above where they differ

The workspace is now the **merged home** `anabtawi-amazon-os/` (this folder, a git repo):
the Cowork operating shell (orchestrator + 4 specialists, tasks, brain, deliverables) +
the tested money **engine** in `engine/` (the `habibos` package, `answer_tacos.py`, pytest).
Decisions: **Opus everywhere · file-based state · this folder is home.**

### Cowork app setup (your steps)
1. **Connectors** → add **DataDoe** (your MCP endpoint), **Claude in Chrome** + **Tavily**
   (for the catalog-auditor's live checks), and the **Filesystem MCP** scoped to this folder
   (lets the live cockpit write your approvals back to `state/inbox/index.json`).
2. **New Project "Anabtawi OS"** → point it at **this folder** (`anabtawi-amazon-os/`).
   It loads `CLAUDE.md` (the constitution) + the skills automatically.
3. **Model → Opus.**
4. **Scheduled tasks** (while Mac awake + Cowork open): `morning-briefing` (~07:00),
   `ppc-daily` (midday), `restock-weekly`, `business-review-weekly`, `pnl-monthly`,
   `brain-compaction-weekly`.

### Daily use — the interactivity loop
- Each task **computes via the engine** (never prose), then files ranked **Action-Inbox**
  items (`state/inbox/`) and refreshes the **cockpit** at `deliverables/dashboard.html`.
- You open the cockpit: clickable **Approve / Snooze / Reject / Done** cards (ranked by $) +
  the TACOS-by-SKU table. A click copies the apply command
  (`cd engine && uv run python scripts/inbox.py status <id> <choice>`); with the Filesystem
  MCP wired, the published artifact writes `index.json` directly.
- `approved`/`done` log to `state/decisions.md`; the weekly review measures whether it paid off.

### Run it now (even before Cowork wiring), from this folder:
```
cd engine
uv run python scripts/answer_tacos.py --artifact <export.csv> --export-id <id> \
  --marketplace CA --window-from <from> --window-to <to> > /tmp/ans.json
uv run python scripts/inbox.py add --domain ppc --agent ppc-manager --title "…" --impact <$> …
uv run python scripts/render_dashboard.py --tacos /tmp/ans.json   # open deliverables/dashboard.html
```

### Still your input (step 9)
- Fill the **SKU → ASIN → tier → landed-COGS** table in
  `.claude/skills/anabtawi-context/SKILL.md` (highest-leverage 30 min — profit math depends on it).
- Set **`assumed_lead_time_weeks`** in `state/targets.md`.
- Close out the `pending` statuses in `state/decisions.md`.
