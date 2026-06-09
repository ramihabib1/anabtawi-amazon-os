# Merge Map — `anabtawi-amazon-os` (Cowork shell) ⨉ `habib-os` (tested engine)

**Date:** 2026-06-09 · **Status:** plan for review (read-only — nothing moved yet)
**Decision being executed:** (A) merge the two into one Cowork-first workspace.

---

## 1. The thesis

Two parallel efforts, complementary, should become one:

| | `anabtawi-amazon-os` (built ~May 31) | `habib-os` (GSD, this repo) |
|---|---|---|
| Role | **The Cowork home** — runtime shell | **The truth engine** — computation + verified facts |
| Strength | Breadth: orchestrator + 4 specialists, 7 task playbooks, brain memory, targets dial, deliverables, **real prior work** (25+ listing audits, rebuild packets, 13-row decision log) | Rigor: hand-written + pytest'd money core, trust-spine (typed Result/Refusal, config-driven refusal, structured logging), empirically-verified DataDoe facts |
| Weakness | **Numbers are model-reasoned in prose** (the exact fabrication risk the project exists to kill) | Narrow (one slice), no operating shell, no brain/tasks |
| Verdict | **KEEP as the home.** Do not rebuild. | **PORT IN** as the computation/truth layer. |

**Merge direction:** adopt `anabtawi-amazon-os` as the workspace; graft habib-os's tested
money core + verified DataDoe facts into it so every dollar figure comes from reviewed code,
not prose. Then build the interactivity layer (Action Inbox + live-artifact cockpit) on top.

---

## 2. The crux — prose-computed → code-verified

The single most important reconciliation. Today, anabtawi-amazon-os's analysis skills have the
agent **read tables and reason about ratios in chat**:

- `profit-analysis` / `ppc-analysis` tell the agent to read `acos`/`tacos`/`roi` and aggregate
  over a window. But the live pull proved (**A1**) those are DAILY ratios with no correct
  server-side window aggregation — a prose agent averaging them is wrong, and "a wrong number
  is worse than no number" is the founding rule.
- habib-os's `tacos.py` already solved this: pull `groupBy sku + sum` of components, compute
  the window ratio from sums, typed refusals, config-driven flags, tests.

**Resolution:** the money-touching skills must **call the tested CLI** (`scripts/answer_tacos.py`
and its successors) for any ratio/margin/threshold number, and render its JSON — never compute
the number in prose. The skill prose stays for *interpretation*; the *arithmetic* moves to code.

---

## 3. Conflicts to resolve (with recommended resolution)

| # | Conflict | `anabtawi-amazon-os` | `habib-os` | Recommended resolution |
|---|---|---|---|---|
| C1 | **Money math** | prose in skills | tested `tacos.py` | Skills call the CLI; prose only interprets. (§2) |
| C2 | **Model** | agents = `sonnet` | operator wants **Opus** | Orchestrator + money/PPC/profit = **Opus**; high-volume listing/inventory pulls may stay Sonnet to save quota. **Operator decides** (you said Opus everywhere — fine, just costs more quota). |
| C3 | **Thresholds** | `state/targets.md` — rich, tier-aware (ACOS 35/28/18, margin floor 30/25/20, TACOS 15, inventory weeks, ROI 40) | `config/thresholds.toml` — flat (acos 30 / tacos 15) | **`targets.md` becomes the single source of truth** (it's richer). `tacos.py` reads ceilings from it (tier-aware), not its own TOML. Reconcile flat-30 → tiered. |
| C4 | **Export column names** | cached CSVs use `profit_sum, sales_sum, adspend_sum, adsales_sum, conv_avg, bb_avg` | verified pull uses `ad_spend_sum, ad_sales_sum, total_sales_sum, profit_sum, total_cost_sum` | **Standardize one export recipe** in `datadoe-query` to the names `tacos.py` consumes (or widen `parse` to accept aliases). New pulls use the standard; old cached CSVs are historical. |
| C5 | **Two constitutions** | `CLAUDE.md` (orchestrator operating rules + golden rules) | `CLAUDE.md` (hard rules, stack, money-logic discipline) | **One merged `CLAUDE.md`** in the home: keep anabtawi's operating constitution + golden rules, fold in habib's hard rules (money math hand-written+tested, secrets in `.env`, config-driven refusal, log every external call) + the verified DataDoe facts. |
| C6 | **DataDoe catalog** | broad `datadoe-query` catalog, some unverified columns | `datadoe-source-map.md` — empirically verified profit source + A1/A2/A3 + `sku` column | **Merge:** habib's verified facts supersede/augment the catalog (the `sku` column, the `groupBy + *_sum` recipe, percent convention, premium columns). |
| C7 | **MCP name** | agents reference `mcpServers: - datadoe` | Cowork custom connector "DataDoe" | Align the connector name to `datadoe` (or rename in agents). |
| C8 | **State store** | **file-based** (`targets.md`, `decisions.md`, `brain/`) | **Supabase** (`config`, `decision_ledger`, `metric_snapshots`) + Alembic | **Cowork-first favors files.** Keep file-based state as primary for M1 (`config`→`targets.md`, `decision_ledger`→`decisions.md`, snapshots→cached exports + brain). **Defer Supabase** (brain README already says layer pgvector under `raw/` *later*). **Operator decides** if Supabase comes now or later. |
| C9 | **Connectors** | expects DataDoe + **Chrome + Tavily** (listing audit) | DataDoe only | Add Chrome + Tavily as Cowork connectors for the catalog-auditor. (Cowork setup step.) |

---

## 4. Defects / cleanup found (read-only audit)

- **Stray literal dir:** `.claude/skills/{datadoe-query,anabtawi-context,...}` — a brace-expansion
  that didn't expand; created as a literal folder. Delete.
- **`tasks/listing-audit-full.md`** has trailing junk baked in (`EOF` + `echo "task written"`) —
  leftover heredoc terminator. Strip.
- **`anabtawi-context` SKU→ASIN→tier→landed-COGS table is unfilled** (TODO). COGS is load-bearing
  for profit math — **highest-leverage 30 min in the whole build** (per the BUILD-PLAN). Operator input.
- **`assumed_lead_time_weeks` TODO** in `targets.md` — drives every restock date. Operator input.
- **`decisions.md`:** all 13 listing decisions are `pending — Rami to close`. Needs a status pass
  (which are applied?) so the brain/weekly-review can measure payoff.
- **`conversion_benchmark` is provisional** (12%) — reset to portfolio top-quartile after a
  sales-and-traffic pull (the skill says so).

---

## 5. What to KEEP as-is (do not rebuild)

- The **4 agents** + orchestrator (thin role prompts — good).
- The **7 task playbooks** (morning-briefing, ppc-daily, restock-weekly, business-review-weekly,
  pnl-monthly, listing-audit-full, brain-compaction-weekly).
- The **brain protocol** (raw→wiki) + existing `brain/raw/` notes.
- The **listing-audit framework** (excellent, 10-dimension rubric) + its **25+ existing audits,
  rebuild packets, rollups, account audit, decision log** — real institutional work; preserve.
- `inventory-restock`, `anabtawi-context`, `datadoe-query` skill scaffolds.

## 6. What to PORT from `habib-os`

- `src/habibos/` trust-spine package (result, logging, thresholds, datadoe primitives).
- `scripts/answer_tacos.py` + `src/habibos/tacos.py` (the tested money core).
- `tests/` (pytest against the real fixture) + `config/thresholds.toml` (→ reconcile into `targets.md`).
- The verified DataDoe facts (`docs/datadoe-source-map.md §6`) → into `datadoe-query`.
- (Deferred) Alembic schema + Supabase truth store — only if/when C8 says "Supabase now".

---

## 7. Target merged layout (in `anabtawi-amazon-os/`)

```
anabtawi-amazon-os/
  CLAUDE.md                 # ONE merged constitution (C5)
  .claude/skills/ agents/   # kept; money skills now call the CLI (§2)
  engine/                   # PORTED: habibos package + scripts + tests (the truth layer)
    habibos/  scripts/  tests/  config/
  tasks/                    # kept; emit Action-Inbox items (interactivity)
  state/
    targets.md              # single threshold source of truth (C3)
    decisions.md            # kept (the write-back ledger)
    inbox/                  # NEW — Action Inbox (file spine of the interactivity layer)
  brain/                    # kept (raw→wiki memory)
  deliverables/
    dashboard.html / artifact   # NEW — live cockpit render
  docs/                     # merged source-map (verified facts)
```

## 8. Where the interactivity layer slots in (the build after the merge)

- **Action Inbox** = `state/inbox/` — each task playbook, after computing via the CLI, writes
  ranked, evidenced action items (the agent assigning *you* work). System of record.
- **Live-artifact cockpit** = a published React artifact that reads the inbox + tested numbers
  and lets you Approve/Snooze/Reject, writing decisions back via the **Filesystem MCP**
  (fallback: agent writes on your click). Persists across sessions.
- **Round-trip** = approvals → `decisions.md` + `brain/raw/` → weekly review measures payoff.

## 9. Open decisions for you (only you can call these)

1. **Model (C2):** Opus everywhere (your stated preference, more quota), or Opus for
   orchestrator/money + Sonnet for bulk listing/inventory pulls (cheaper)?
2. **Supabase (C8):** file-based state only for now (recommended, Cowork-native), or stand up
   the Supabase truth store now?
3. **Repo home:** keep `anabtawi-amazon-os/` as the canonical folder (and `git init` it — it's
   not a git repo yet), or relocate? (habib-os IS a git repo with `.planning/`.)
4. **Thresholds (C3):** confirm the tiered targets in `targets.md` are your real numbers (and
   fill the COGS table + lead time) so the engine computes against truth, not placeholders.

## 10. Proposed execution sequence (post-approval)

1. **Prep the home:** `git init` anabtawi-amazon-os (decision 3); fix defects (§4).
2. **Port the engine:** copy `habibos/` + scripts + tests into `engine/`; verify tests pass there.
3. **Reconcile config:** merge thresholds into `targets.md` (C3); point `tacos.py` at it.
4. **Standardize the export recipe** (C4) + merge verified facts into `datadoe-query` (C6).
5. **Rewire money skills** to call the CLI (§2); one merged `CLAUDE.md` (C5).
6. **Build the Action Inbox** (file spine) + wire the task playbooks to emit items.
7. **Build the live-artifact cockpit** + Filesystem-MCP write-back (with fallback).
8. **Cowork setup** (your app steps): connectors (DataDoe/Chrome/Tavily), Project on the folder,
   model, scheduled tasks.
9. Fill COGS + lead time (decision 4); close out `decisions.md` statuses.
```
