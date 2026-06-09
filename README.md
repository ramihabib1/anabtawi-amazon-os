# Anabtawi Amazon OS — a Claude Cowork workspace

A single workspace you open each morning to run the Anabtawi Sweets Amazon business.
You talk to one **orchestrator**; it drives four specialist agents over your DataDoe data,
flags what matters, and produces the artifacts that make each action one click to execute.

## What's in here
```
CLAUDE.md                     # the constitution: business, rhythm, golden rules
.claude/
  skills/                     # the brain — reusable playbooks every agent loads
    datadoe-query/            #   keystone: seller ID + source catalog + query rules
    anabtawi-context/         #   brand, SKU tiers, COGS, seasonality  (fill the SKU table)
    profit-analysis/  ppc-analysis/  inventory-restock/  listing-audit/
  agents/                     # the hands — orchestrator + 4 specialists
tasks/                        # the heartbeat — one prompt per scheduled run
brain/                        # the memory (markdown, Obsidian-compatible)
  raw/                        #   append-only inbox: briefings, decisions, notes, research
  wiki/                       #   compiled knowledge: skus/, playbooks/, customers, competitors
state/
  targets.md                  # the single dial: thresholds that retune the whole system
  decisions.md                # append-only ledger of applied changes
  daily/                      # morning-briefing archive (mirrored into brain/raw/daily/)
data/                         # raw DataDoe exports land here (cached, reused)
deliverables/                 # generated decks, sheets, draft action artifacts
```

## Setup (one time)
1. Put this folder where Claude Desktop can reach it, and point Cowork at it (Cowork → Tasks,
   then grant access to this folder).
2. Confirm connectors are on for this workspace: **DataDoe** (data), **Claude in Chrome**
   (live listing checks), **Tavily** (research). The agent files reference an MCP server named
   `datadoe` — make sure your DataDoe connection resolves to that name (or rename in each
   agent's `mcpServers`).
3. Open `.claude/skills/anabtawi-context/SKILL.md` and paste your real SKU → ASIN → tier →
   landed-COGS table.
4. Tune `state/targets.md` to your actual numbers.
5. Register the files in `tasks/` as Cowork scheduled tasks at the cadences noted in each.

## Daily use
Type **"morning briefing"** (or let the scheduled task fire). You get a one-screen read on
yesterday, ranked anomalies, and the top three actions with draft artifacts waiting in
`deliverables/`. Approve what you want; the system logs it to `state/decisions.md`. Ask any
specialist anything during the day ("ppc-manager, what's bleeding spend this week?").

## The safety model
DataDoe is read-only, so all analysis is safe. **Nothing touches the live account without
your explicit approval** — recommendations are artifacts you review. If you later connect an
SP-API / Ads-API write-back MCP (Phase 2), execution stays a separate, approval-gated step:
dry-run the diff → you say "apply" → write → log.

## Note on portability
Skills, `CLAUDE.md`, and the `tasks/` prompts are the load-bearing pieces and work in Cowork
today. File-based subagents (`.claude/agents/`) follow Claude Code's format; if your Cowork
build doesn't surface them as named agents, they still work as role prompts/skills — move a
copy into `.claude/skills/` or invoke them by pasting their body. Validate once, then forget.
