---
phase: 07-margin-tiered-safety-gate
plan: 04
status: complete
requirements: [GATE-03, GATE-04, GATE-05]
subsystem: engine / cli-seam
tags: [margin-gate, cli, thin-wrapper, structured-logging, json-contract]
provides: "engine/scripts/gate_action.py — thin argv→gate.evaluate→JSON CLI seam for the Phase 8 apply spine"
requires: ["07-03 (habibos.gate evaluate/parse/PREMIUM_SOURCE_ID)", "07-01 (GateVerdict/GateRefusal/ProposedAction types)", "07-02 (sku_catalog.toml + min_net_margin_pct floor)"]
affects: ["Phase 8 (BUILD→DRYRUN apply spine consumes the gate CLI)", "Phase 9 spend-up queue"]
tech-stack:
  added: []
  patterns: ["mirror answer_tacos.py CLI shape", "logged_call one-in/one-out", "dataclasses.asdict typed result → JSON stdout"]
key-files:
  created: ["engine/scripts/gate_action.py", "engine/tests/test_gate_action.py"]
  modified: []
decisions:
  - "evaluate is called as gate.evaluate(frame, action, catalog_path, marketplace) — the REAL 07-03 signature (frame first), not the (action, frame) order the plan's <interfaces> sketch implied"
  - "the CLI delegates the export read to gate.parse (re-exported by gate from tacos); a FAILED/empty export Refusal serializes as JSON and logs status=refused — the CLI computes nothing"
  - "DEFAULT_CATALOG = config/sku_catalog.toml (the LIVE machine-readable catalog), distinct from answer_tacos.py's tests/fixtures default — gate.evaluate owns the explicit-catalog read (D-05)"
  - "logged_call('gate_action', source_id=PREMIUM_SOURCE_ID, marketplace=...) — seller UUID never passed (T-07-12); end_fields['status'] set from isinstance(GateRefusal) so a refusal can never log/serialize as a pass (T-07-11)"
metrics:
  tasks: 2
  files: 2
  duration: "~15 min"
  completed: "2026-06-22"
---

# Phase 7 Plan 04: Gate Action CLI Summary

`engine/scripts/gate_action.py` — the thin, structurally-twin-of-`answer_tacos.py` CLI seam
that turns a proposed PPC write + a downloaded premium export into the typed margin-gate
verdict as JSON on stdout: `argv → gate.parse() + gate.evaluate() (inside logged_call) →
dataclasses.asdict → JSON`. NO money logic lives in the script — all ratios, ceilings,
projections and the clamp-never/refuse decision are imported from `habibos.gate` (CLAUDE.md
hard rule 3). A refusal serializes verbatim as a refusal and can never be rewritten as a
pass. This is the callable gate seam the Phase 8 BUILD→DRYRUN apply spine consumes.

## What landed

- **`engine/scripts/gate_action.py`** (new, thin CLI) — mirrors `answer_tacos.py`:
  - `REPO_ROOT = Path(__file__).resolve().parent.parent`, `DEFAULT_CATALOG = REPO_ROOT /
    "config" / "sku_catalog.toml"` (the LIVE catalog the gate reads explicitly, D-05).
  - `_build_parser()` — export provenance flags (`--artifact`, `--export-id`, `--marketplace`
    default `CA`, `--status` default `COMPLETED`, `--catalog` default the live catalog) plus
    the `ProposedAction` fields (`--sku`, `--action-type`, `--delta-spend` typed `float`).
  - `main(argv)` — `habibos_logging.configure()` once; builds `ProposedAction(sku,
    action_type, delta_spend, marketplace)`; inside `logged_call("gate_action",
    source_id=gate.PREMIUM_SOURCE_ID, marketplace=...)` calls `gate.parse(artifact, status)`
    (a `Refusal` → JSON, `status="refused"`) else `gate.evaluate(frame, action, catalog_path,
    marketplace)` and sets `end_fields["status"] = "refused" if isinstance(result,
    GateRefusal) else "pass"`. Finally `json.dump(dataclasses.asdict(result), sys.stdout)`.
  - NO ratio / ceiling / projection arithmetic in the script; the seller UUID is never passed
    into `logged_call` fields.
- **`engine/tests/test_gate_action.py`** (new) — invokes `gate_action.main([...])`, captures
  stdout JSON via `capsys`, and locks the three CLI contract paths against the committed
  `profit_by_sku_30d.csv` + `sku_catalog_test.toml` fixtures (no network):
  1. spend-decreasing → `auto_pass` True, `projected_tacos` None (GateVerdict, D-06).
  2. over-ceiling spend-up → `code == "over_ceiling"`, non-null `breached_value` + `source`,
     and `"auto_pass" not in payload` (a GateRefusal can never serialize as a pass, T-07-11).
  3. SKU absent from the catalog → `code == "sku_not_in_catalog"` (GATE-05).

## CLI invocation signature (for the Phase 8 apply spine)

```
uv run python scripts/gate_action.py \
  --artifact <downloaded-premium-export.csv> \
  --export-id <datadoe-export-id> \
  [--marketplace CA] [--status COMPLETED] \
  [--catalog config/sku_catalog.toml] \
  --sku <SKU> --action-type <bid_up|budget_up|pause|negative> \
  --delta-spend <CAD float; >0 spend-up gated, <=0 spend-down auto-pass>
```

Exit code is `0`; the verdict/refusal is the single JSON line on stdout. A spend-up over the
SKU's margin-derived ceiling → `{"code": "over_ceiling", "breached_value": ..., "source": ...}`;
the spine MUST treat any payload carrying a `code` field as a refusal and never act on it.

## Verification

- Task 1 verify (spend-down auto-pass): `... --sku EU-Z87B-ZRBZ --action-type pause
  --delta-spend -5 | python -c "...assert d['auto_pass'] is True"` → **`OK`**.
- Live JSON samples (against `sku_catalog_test.toml`):
  - over-ceiling: `{"reason": "projected TACOS breaches the SKU's margin-derived ceiling",
    "code": "over_ceiling", "breached_value": 357.4, "ceiling": 21.0, "source": "DataDoe
    premium Profit by SKU & Date (57a0cb319c)"}`
  - absent SKU: `{"reason": "SKU not in catalog table", "code": "sku_not_in_catalog",
    "breached_value": null, "ceiling": null, "source": null}`
- `cd engine && uv run pytest tests/test_gate_action.py -q` → **`3 passed in 0.25s`**.
- `cd engine && uv run pytest` (full suite) → **`36 passed, 5 skipped in 0.19s`** (the 5 skips
  are pre-existing Supabase/context plans 01-02/01-03, unrelated to this work — no regression).

## Deviations from Plan

None affecting behavior. One naming reconciliation worth recording: the plan's `<interfaces>`
sketch (lines 60–79) wrote the call as `gate.evaluate(action, frame, ...)`, but the actual
07-03 `gate.evaluate` signature is `(frame, action, catalog_path, marketplace)` (frame first),
as the 07-03 SUMMARY and `test_gate.py` confirm. The CLI mirrors the REAL signature. The plan's
prose `<action>` block (lines 106–109) already described the correct frame-first usage, so this
is a transcription nit in the sketch, not a logic change.

## Requirements satisfied

- **GATE-03** — spend-direction branch surfaced through the CLI: a spend-decreasing action
  emits `auto_pass: true` JSON.
- **GATE-04** — an over-ceiling spend-up emits `over_ceiling` JSON naming `breached_value` +
  `source`, never a clamped pass (T-07-11 mitigated and asserted).
- **GATE-05** — a SKU absent from the catalog emits `sku_not_in_catalog` JSON.

## Threat mitigations applied

- **T-07-11** (refusal serializing as a pass) — `end_fields["status"]` derived from
  `isinstance(result, GateRefusal)`; the over-ceiling test asserts `"auto_pass" not in payload`.
- **T-07-12** (seller-UUID disclosure) — `logged_call` carries only op name + source_id +
  marketplace; no field carries the seller UUID.
- **T-07-13** (CLI bypassing gate math) — the CLI contains NO arithmetic; all math is imported
  from `habibos.gate`.

## Known Stubs

None. The CLI is a complete thin seam over the live `habibos.gate` core; it reads real configs
(`config/sku_catalog.toml`, `thresholds.toml`) and emits real typed verdicts.

## Self-Check: PASSED

- Files: `engine/scripts/gate_action.py`, `engine/tests/test_gate_action.py`,
  `.planning/phases/07-margin-tiered-safety-gate/07-04-SUMMARY.md` — all FOUND.
- Commits: `7d110f5` (feat CLI), `c2e382d` (test) — both FOUND in git log.
