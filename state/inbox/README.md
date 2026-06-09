# Action Inbox — the operator's task queue

The interactivity layer's **file spine**. Instead of burying recommendations in chat, the
agents assign the operator ranked, evidenced **actions** here. This is what turns the system
from chat-based into a stateful "the agent gave me a to-do list" loop.

## Layout
- `index.json` — machine source of truth (a list of action items). The **live dashboard**
  (`deliverables/dashboard.html`) reads this.
- `items/{id}.md` — generated human/Obsidian-readable card per item (do not hand-edit; they
  regenerate from `index.json`).

## Item shape
`id · created · status · domain · agent · title · why · impact_cad (for ranking) · sku ·
current → proposed · evidence (export id + numbers) · operator_task · artifact · note`

Statuses: `pending → approved | snoozed | rejected | done`. Items rank **open-first, then by
absolute $ impact** (biggest money first).

## How agents use it (via `engine/scripts/inbox.py`, stdlib-only)
```
# Assign an action (numbers must come from the engine CLI, never prose):
cd engine && uv run python scripts/inbox.py add \
  --domain ppc --agent ppc-manager --title "Cut FX-M8MA bid ~30%" \
  --why "TACOS 69.2%, ROI -27.1% over trailing 30d" --impact -140 --sku FX-M8MA-MMSA \
  --current "current bid" --proposed "cut ~30%" \
  --evidence "exp 103e0769 · TACOS 69.2 / ACOS 74.0 / ROI -27.1" \
  --operator-task "Campaign Manager → reduce FX-M8MA bid ~30%"

# Operator decisions (the dashboard buttons emit these):
uv run python scripts/inbox.py status <id> approved   # logs to state/decisions.md
uv run python scripts/inbox.py status <id> done
uv run python scripts/inbox.py list --status pending
```
`approved`/`done` append a line to `state/decisions.md` (the ledger that the weekly review
reads to measure whether the change paid off).

## The loop
agent computes via the engine → `inbox.py add` → dashboard shows the card → operator clicks
Approve/Done → `inbox.py status` logs to `decisions.md` → brain remembers → weekly review
measures payoff. (When a write-back MCP exists later, `approved` items become "dry-run → apply".)
