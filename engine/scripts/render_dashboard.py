#!/usr/bin/env python3
"""Render the live cockpit — a self-contained interactive dashboard from the Action Inbox.

Reads `state/inbox/index.json` (and, optionally, a TACOS-by-SKU answer JSON from
answer_tacos.py via --tacos) and writes `deliverables/dashboard.html`: a single offline-safe
file (no CDN, no network) you open in the browser — the visual, clickable cockpit, not chat.

Each action card has Approve / Snooze / Reject / Done buttons. Because a static file can't
write your files directly, a click (a) records the choice in the page + localStorage and
(b) shows + copies the exact `inbox.py status <id> <choice>` command to apply it — the path
that always works. Upgrade path: published as a Cowork artifact with the Filesystem MCP, the
same buttons write `index.json` back directly (then `inbox.py render` refreshes the cards).

The data is INLINED into the HTML (a file:// page can't fetch a sibling JSON — CORS), so the
morning task regenerates this after updating the inbox. Stdlib only.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INDEX = ROOT / "state" / "inbox" / "index.json"
OUT = ROOT / "deliverables" / "dashboard.html"

_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anabtawi OS — cockpit</title>
<style>
 :root{color-scheme:dark}
 body{margin:0;font:15px/1.45 -apple-system,Segoe UI,Roboto,sans-serif;background:#0f1115;color:#e6e8ee}
 header{padding:16px 20px;border-bottom:1px solid #232838;display:flex;gap:16px;align-items:baseline;flex-wrap:wrap}
 h1{font-size:16px;margin:0;font-weight:600}
 .muted{color:#8b93a7;font-size:13px}
 .wrap{padding:18px 20px;max-width:1040px}
 h2{font-size:13px;text-transform:uppercase;letter-spacing:.06em;color:#8b93a7;margin:22px 0 10px}
 .card{background:#161a24;border:1px solid #232838;border-radius:10px;padding:12px 14px;margin:10px 0}
 .card.done{opacity:.5} .card.rejected{opacity:.4}
 .row{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
 .title{font-weight:600}
 .dollar{font-variant-numeric:tabular-nums;font-weight:700;white-space:nowrap}
 .neg{color:#ff6b6b}.pos{color:#3fb950}
 .why{color:#c2c8d6;margin:6px 0}
 .task{background:#0c0e13;border-left:3px solid #d98c3f;padding:6px 10px;margin:8px 0;border-radius:4px}
 .ev{color:#8b93a7;font-size:12px;font-variant-numeric:tabular-nums}
 .btns{margin-top:10px;display:flex;gap:8px;flex-wrap:wrap}
 button{background:#232838;color:#e6e8ee;border:1px solid #313850;border-radius:6px;padding:6px 12px;cursor:pointer;font-size:13px}
 button:hover{border-color:#4a5474}
 button.approve{border-color:#2c7a3f;color:#7ee19a} button.reject{border-color:#7a2c2c;color:#ff9a9a}
 .pill{font-size:11px;padding:2px 8px;border-radius:99px;border:1px solid #313850;color:#8b93a7}
 table{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;font-size:13px}
 th,td{text-align:right;padding:5px 9px;border-bottom:1px solid #1d2230}
 th:first-child,td:first-child{text-align:left}
 .flag-breach{color:#ff6b6b;font-weight:600}.flag-ok{color:#3fb950}.flag-na{color:#8b93a7}
 #toast{position:fixed;bottom:18px;left:50%;transform:translateX(-50%);background:#1f6feb;color:#fff;padding:10px 16px;border-radius:8px;opacity:0;transition:.2s;font-size:13px;max-width:90vw}
 #toast.show{opacity:1}
 code{background:#0c0e13;padding:2px 6px;border-radius:4px;font-size:12px}
</style></head><body>
<header>
  <h1>Anabtawi OS — cockpit</h1>
  <span class="muted">__GENERATED__ · amazon.ca (CAD)</span>
  <span class="muted">__PENDING__ pending · __TOTAL__ actions</span>
</header>
<div class="wrap">
  <h2>⚠ Actions for you (ranked by $)</h2>
  <div id="actions"></div>
  <h2>TACOS by SKU __TACOS_WINDOW__</h2>
  <div id="tacos"></div>
  <p class="muted" style="margin-top:24px">Clicks record your choice + copy the apply command
  (<code>inbox.py status &lt;id&gt; &lt;choice&gt;</code>). Published as a Cowork artifact with the
  Filesystem MCP, the buttons write <code>index.json</code> back directly.</p>
</div>
<div id="toast"></div>
<script>
const ITEMS = __ITEMS__;
const TACOS = __TACOS__;
const KEY = "anabtawi-inbox-overrides";
const ov = JSON.parse(localStorage.getItem(KEY) || "{}");
function toast(t){const e=document.getElementById("toast");e.textContent=t;e.className="show";setTimeout(()=>e.className="",2600);}
function copy(t){navigator.clipboard&&navigator.clipboard.writeText(t);}
function decide(id,s){ov[id]=s;localStorage.setItem(KEY,JSON.stringify(ov));
  const cmd="cd engine && uv run python scripts/inbox.py status "+id+" "+s;
  copy(cmd);toast("Recorded "+s+" — apply cmd copied: "+cmd);render();}
function dollar(v){if(v===null||v===undefined)return '<span class="muted">—</span>';
  const c=v<0?'neg':'pos';return '<span class="dollar '+c+'">'+(v<0?'-$':'$')+Math.abs(v).toFixed(0)+'</span>';}
function flag(f){const c=f==='breach'?'flag-breach':(f==='ok'?'flag-ok':'flag-na');return '<span class="'+c+'">'+f+'</span>';}
function render(){
  const open=ITEMS.map(i=>({...i,status:ov[i.id]||i.status}));
  const a=document.getElementById("actions");a.innerHTML="";
  open.filter(i=>i.status!=='rejected'&&i.status!=='done').length||(a.innerHTML='<p class="muted">No open actions. 🎉</p>');
  open.forEach(i=>{const d=document.createElement("div");d.className="card "+i.status;
    d.innerHTML=`<div class="row"><div class="title">${i.title} <span class="pill">${i.status}</span></div>${dollar(i.impact_cad)}</div>
      <div class="why">${i.why||''}</div>
      ${i.operator_task?`<div class="task">YOUR TASK: ${i.operator_task}</div>`:''}
      <div class="ev">${i.evidence||''}${i.artifact?` · 📎 ${i.artifact}`:''}</div>
      <div class="btns">
        <button class="approve" onclick="decide('${i.id}','approved')">Approve</button>
        <button onclick="decide('${i.id}','done')">Done</button>
        <button onclick="decide('${i.id}','snoozed')">Snooze</button>
        <button class="reject" onclick="decide('${i.id}','rejected')">Reject</button>
      </div>`;a.appendChild(d);});
  const t=document.getElementById("tacos");
  if(!TACOS||!TACOS.rows){t.innerHTML='<p class="muted">No TACOS answer attached to this render.</p>';return;}
  let h='<table><tr><th>SKU</th><th>ACOS%</th><th>TACOS%</th><th>ROI%</th><th>flags</th></tr>';
  TACOS.rows.forEach(r=>{h+=`<tr><td>${r.seller_sku}</td><td>${r.acos??'—'}</td><td>${r.tacos??'—'}</td>
    <td class="${(r.roi??0)<0?'neg':''}">${r.roi??'—'}</td><td>${flag(r.acos_flag)} / ${flag(r.tacos_flag)}</td></tr>`;});
  t.innerHTML=h+'</table>';
}
render();
</script></body></html>
"""


def render(tacos_path: Path | None) -> Path:
    items = json.loads(INDEX.read_text(encoding="utf-8")) if INDEX.exists() else []
    tacos = None
    window = ""
    if tacos_path and tacos_path.exists():
        tacos = json.loads(tacos_path.read_text(encoding="utf-8"))
        if isinstance(tacos, dict) and tacos.get("window_from"):
            window = f"({tacos['window_from']} → {tacos['window_to']})"
    pending = sum(1 for i in items if i.get("status") == "pending")
    html = (
        _TEMPLATE
        .replace("__GENERATED__", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"))
        .replace("__PENDING__", str(pending))
        .replace("__TOTAL__", str(len(items)))
        .replace("__TACOS_WINDOW__", window)
        .replace("__ITEMS__", json.dumps(items))
        .replace("__TACOS__", json.dumps(tacos))
    )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    return OUT


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Render the live cockpit dashboard from the inbox.")
    p.add_argument("--tacos", default=None, help="Path to an answer_tacos.py JSON answer to render the TACOS table.")
    a = p.parse_args(argv)
    out = render(Path(a.tacos) if a.tacos else None)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
