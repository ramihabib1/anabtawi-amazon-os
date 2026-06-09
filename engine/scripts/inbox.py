#!/usr/bin/env python3
"""Action Inbox — the file spine of the interactivity layer.

The agents/tasks assign the operator ranked, evidenced actions here instead of burying
them in chat. `state/inbox/index.json` is the machine source of truth (the live dashboard
reads it); `state/inbox/items/{id}.md` are generated human/Obsidian-readable cards.

Anti-fabrication note (CLAUDE.md): an item's money figures must come from the engine
(answer_tacos.py etc.) — this tool only stores/ranks/renders them; it computes no ratios.

Stdlib only (no deps) so it runs anywhere. Usage:

  add      inbox.py add --domain ppc --agent ppc-manager --title "..." --why "..." \
                       --impact -140 --sku FX-M8MA-MMSA --current "bid $X" \
                       --proposed "cut ~30%" --evidence "exp 103e… TACOS 69% ROI -27%" \
                       --operator-task "In Campaign Manager, reduce FX-M8MA bid ~30%" \
                       [--artifact deliverables/ppc-changes_2026-06-09.xlsx]
  status   inbox.py status <id> approved|snoozed|rejected|done [--note "..."]
  list     inbox.py list [--status pending] [--json]
  render   inbox.py render          # regenerate items/*.md from index.json

`status approved|done` also appends a line to state/decisions.md (the ledger).
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

# scripts/ is engine/scripts; the workspace root is two levels up.
ROOT = Path(__file__).resolve().parents[2]
INBOX = ROOT / "state" / "inbox"
ITEMS = INBOX / "items"
INDEX = INBOX / "index.json"
DECISIONS = ROOT / "state" / "decisions.md"

STATUSES = ("pending", "approved", "snoozed", "rejected", "done")
_OPEN = {"pending", "approved", "snoozed"}  # shown by default; rejected/done are closed


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:48]


def _load() -> list[dict]:
    if not INDEX.exists():
        return []
    return json.loads(INDEX.read_text(encoding="utf-8") or "[]")


def _save(items: list[dict]) -> None:
    INBOX.mkdir(parents=True, exist_ok=True)
    # Rank: open first, then by absolute $ impact desc (biggest money first), then newest.
    items.sort(key=lambda x: (x["status"] not in _OPEN, -abs(x.get("impact_cad") or 0), x["created"]))
    INDEX.write_text(json.dumps(items, indent=2) + "\n", encoding="utf-8")
    _render(items)


def _render(items: list[dict]) -> None:
    """Regenerate one human-readable card per item (Obsidian-friendly)."""
    ITEMS.mkdir(parents=True, exist_ok=True)
    for it in items:
        body = [
            f"# {it['title']}",
            "",
            f"- **status:** {it['status']}",
            f"- **domain / agent:** {it['domain']} / {it['agent']}",
            f"- **SKU:** {it.get('sku') or '—'}",
            f"- **$ impact (CAD):** {it.get('impact_cad') if it.get('impact_cad') is not None else '—'}",
            f"- **created:** {it['created']}",
            "",
            f"**Why:** {it['why']}",
            "",
            f"**Change:** {it.get('current') or '—'} → {it.get('proposed') or '—'}",
            "",
            f"**Evidence:** {it.get('evidence') or '—'}",
            "",
            f"**YOUR TASK:** {it.get('operator_task') or '—'}",
        ]
        if it.get("artifact"):
            body += ["", f"**Artifact:** `{it['artifact']}`"]
        if it.get("note"):
            body += ["", f"**Note:** {it['note']}"]
        (ITEMS / f"{it['id']}.md").write_text("\n".join(body) + "\n", encoding="utf-8")


def _log_decision(it: dict, result: str) -> None:
    line = (
        f"{_today()} | {it['domain']} | {it.get('sku') or '-'} | "
        f"{it.get('current') or '-'} → {it.get('proposed') or it['title']} | "
        f"{it['why']} | {it.get('impact_cad') if it.get('impact_cad') is not None else '-'} | {result}"
    )
    with DECISIONS.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def cmd_add(a: argparse.Namespace) -> int:
    items = _load()
    base = _slug(f"{_today()}-{a.domain}-{a.sku or a.title}")
    item_id = base
    n = 2
    existing = {i["id"] for i in items}
    while item_id in existing:
        item_id = f"{base}-{n}"
        n += 1
    items.append({
        "id": item_id, "created": _now(), "status": "pending",
        "domain": a.domain, "agent": a.agent, "title": a.title, "why": a.why,
        "impact_cad": a.impact, "sku": a.sku, "current": a.current, "proposed": a.proposed,
        "evidence": a.evidence, "operator_task": a.operator_task, "artifact": a.artifact,
        "note": None,
    })
    _save(items)
    print(f"added {item_id}")
    return 0


def cmd_status(a: argparse.Namespace) -> int:
    items = _load()
    hit = next((i for i in items if i["id"] == a.id), None)
    if hit is None:
        print(f"no such item: {a.id}")
        return 1
    if a.new_status not in STATUSES:
        print(f"status must be one of {STATUSES}")
        return 1
    hit["status"] = a.new_status
    if a.note:
        hit["note"] = a.note
    _save(items)
    if a.new_status in ("approved", "done"):
        _log_decision(hit, "approved (pending apply)" if a.new_status == "approved" else "applied")
    print(f"{a.id} -> {a.new_status}")
    return 0


def cmd_list(a: argparse.Namespace) -> int:
    items = _load()
    if a.status:
        items = [i for i in items if i["status"] == a.status]
    if a.json:
        print(json.dumps(items, indent=2))
        return 0
    for i in items:
        imp = i.get("impact_cad")
        print(f"[{i['status']:8}] {i['id']}  ${imp if imp is not None else '—'}  — {i['title']}")
    if not items:
        print("(inbox empty)")
    return 0


def cmd_render(_a: argparse.Namespace) -> int:
    _save(_load())
    print("rendered items/ from index.json")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Action Inbox CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    ad = sub.add_parser("add")
    ad.add_argument("--domain", required=True, choices=["ppc", "profit", "inventory", "listing", "ops"])
    ad.add_argument("--agent", required=True)
    ad.add_argument("--title", required=True)
    ad.add_argument("--why", required=True)
    ad.add_argument("--impact", type=float, default=None, help="$ impact (CAD), signed; for ranking")
    ad.add_argument("--sku", default=None)
    ad.add_argument("--current", default=None)
    ad.add_argument("--proposed", default=None)
    ad.add_argument("--evidence", default=None, help="export id + the numbers behind it")
    ad.add_argument("--operator-task", dest="operator_task", default=None)
    ad.add_argument("--artifact", default=None)
    ad.set_defaults(func=cmd_add)

    st = sub.add_parser("status")
    st.add_argument("id")
    st.add_argument("new_status")
    st.add_argument("--note", default=None)
    st.set_defaults(func=cmd_status)

    ls = sub.add_parser("list")
    ls.add_argument("--status", default=None, choices=list(STATUSES))
    ls.add_argument("--json", action="store_true")
    ls.set_defaults(func=cmd_list)

    rn = sub.add_parser("render")
    rn.set_defaults(func=cmd_render)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
