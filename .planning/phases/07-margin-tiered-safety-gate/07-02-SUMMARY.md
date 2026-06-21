---
phase: 07-margin-tiered-safety-gate
plan: 02
status: complete
requirements: [GATE-02, GATE-05]
---

# 07-02 Summary — SKU catalog + net-margin floor (single source of truth)

## What landed

- **`engine/config/sku_catalog.toml`** (new) — the machine-readable single source of truth
  (D-04/D-05). One `[sku."<SKU>"]` table per row carrying exactly `asin`, `tier`, `cogs`
  (landed `cogs_total_value`, CAD). **No stored margin** — margin is computed live in Plan 03.
  Policy header documents: single source of truth, prose renders from it, margin computed
  live, landed-COGS provenance, and the never-invent-a-COGS rule.
- **`engine/config/thresholds.toml`** — renamed empty `min_margin_pct = ""` →
  `min_net_margin_pct = 15` under `[marketplace.CA]` (D-07/D-07a). Removed the superseded
  "hero 35 / maintain 28 / cut 18" tier-ceiling comment; replaced with the D-01a note
  (one floor + per-SKU formula `ceiling = CM% − min_net_margin_pct`, no per-tier table).
- **`engine/tests/fixtures/sku_catalog_test.toml`** (new) — edge fixture: `EU-Z87B-ZRBZ`
  (valid, cogs 29.06) for happy-path/breach, `ZZ-ZERO-COGS0` (cogs 0) for the `no_margin`
  refusal; an absent SKU drives `sku_not_in_catalog`.
- **`.claude/skills/anabtawi-context/SKILL.md`** — D-05 render-from note above the prose
  SKU table: the gate reads the TOML, not the prose; SKUs shown but absent from the TOML
  refuse on funding until a committed COGS exists.

## Verification
- `thresholds.read('min_net_margin_pct','CA')` → `15.0` ✓ (clears the Phase 7 blocking
  precondition; the Plan 01 seeded-floor lock now passes).
- `grep -c "hero 35" thresholds.toml` → 0 ✓
- sku_catalog.toml parses; `T8-2W2X-INOK` = cogs 26.77 / HERO; the 5 remnants absent ✓
- Engine suite: **26 passed, 5 skipped** (pre-existing Supabase/context skips). Only RED is
  `test_gate.py` — the absent `habibos.gate` module, Plan 03's Nyquist target by design.

## Remnant handling + reconciliation (required disclosure)
- **No-COGS remnant group** (ZK-4NDS-MNA9, OA-26MX-IHV0, 5G-ZW6Q-WOZG, 9J-ASSK-BVKC,
  FO-SE3J-T74M): **OMITTED** from the catalog → funding attempts yield `sku_not_in_catalog`
  (D-05). Never given a guessed COGS (CLAUDE.md hard rule 4).
- **Final catalog count: 16 SKUs** (vs 30-SKU `ca_catalog_skus.txt`). A SKU is included only
  if it has BOTH a tier (rollup authority) AND a reviewed, committed landed COGS
  (deep-dive / rollup deliverables). Catalog SKUs lacking a reviewed committed COGS are
  intentionally omitted so they refuse on funding until a real landed cost is supplied.

## Deviations (important — read before Plan 03)
1. **Authoritative COGS table was uncommitted.** The plan's premise — a 26-row
   `sku → asin → tier → cogs` table at `SKILL.md` lines 26–53 — existed only as an
   **uncommitted working-tree modification** at execution time; committed HEAD (which the
   parallel worktree branched off) had a placeholder. The worktree executor therefore could
   not see it and reconstructed COGS from committed deliverables instead.
2. **Rami decision (2026-06-21): Conservative 16-SKU.** Offered "commit the inferred
   2026-06-12 table as the gate's authority → 26-SKU coverage" vs. "only deliverable-backed
   COGS → 16 SKUs, rest refuse-on-funding." Rami chose **conservative 16-SKU**. The inferred
   COGS were therefore NOT made the gate authority; only the 16 deliverable-backed SKUs enter
   the money path. The prose SKILL.md table (fuller reference) is committed but is explicitly
   non-authoritative for the gate.
3. **Execution path:** the parallel worktree executor completed Task 1 (sku_catalog.toml,
   commit `c0f4939` → cherry-picked to main as `989b9d7`) then lost tool permissions
   mid-run. Tasks 2–3 + this SUMMARY were completed inline by the orchestrator on main
   (commits below). `test_thresholds.py` was owned/committed by Plan 01 (it already carried
   the seeded-floor lock), so 07-02 did not re-edit it.

## Commits
- `989b9d7` feat(07-02): author sku_catalog.toml single source of truth (Task 1)
- `524b70d` feat(07-02): seed min_net_margin_pct=15 floor + edge-case catalog fixture
- `25c63fd` docs(07-02): note SKILL.md SKU table renders from sku_catalog.toml (D-05)
