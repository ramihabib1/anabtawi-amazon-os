# Phase 7: Margin-Tiered Safety Gate - Research

**Researched:** 2026-06-21
**Domain:** Hand-written, pytest-covered Python money-logic core (the `tacos.py` analogue) — a per-SKU TACOS-ceiling-from-contribution-margin safety gate
**Confidence:** HIGH (the codebase pattern, the DataDoe column definitions, and the pre/post-ad determination are all verified in-repo; no new third-party stack)

## Summary

Phase 7 adds one hand-written, pytest-covered engine module (`gate.py` + `test_gate.py`) that is the structural twin of `tacos.py`: it reads DataDoe window-summed components, applies a closed-form margin → ceiling formula, and returns a typed `GateVerdict` / `GateRefusal` (new siblings of `Refusal`/`Proceed` in `result.py`). It uses **zero new third-party libraries** — `polars`, `pydantic`, `tomllib`, `argparse`/`json` are all already pinned and proven. The work is code-shaped, not dependency-shaped.

**The load-bearing finding (D-03 — RESOLVED, HIGH confidence):** the premium Profit-by-SKU export's `profit` is **POST-ad**. This is verified two ways: (1) the source-map definition `total_cost = settlement fees + cogs_total + ad_spend` `[CITED: docs/datadoe-source-map.md §3a line 77]`, so `profit = total_sales − total_cost` nets out ad spend; and (2) arithmetically against the live fixture (`EU-Z87B-ZRBZ`: 279.95 − 179.68 = 100.27 = profit, where total_cost 179.68 includes ad_spend 0.5; `9Z-KUHZ-FU2I`: total_sales 0, ad_spend 25.28, total_cost 25.28, profit −25.28) `[VERIFIED: engine/tests/fixtures/profit_by_sku_30d.csv]`. **Therefore D-03's "add ad_spend back" path is mandatory.** The cleanest pre-ad contribution margin is a back-out from the components the groupBy export *already* sums — no new export columns are required (see "THE D-03 RESOLUTION" section).

**Primary recommendation:** Build `gate.py` mirroring `tacos.py` exactly — `parse()` (reuse the existing pydantic-validated window-sum reader), `contribution_margin_pct()` = `(profit_sum + ad_spend_sum) / total_sales_sum` (the pre-ad back-out), `ceiling_tacos_pct()` = `CM% − min_net_margin_pct`, `projected_tacos()` = `(ad_spend_sum + Δspend) / total_sales_sum`, and `evaluate(ProposedAction) -> GateVerdict | GateRefusal`. Add a machine-readable `engine/config/sku_catalog.toml` (tier + COGS + canonical SKU set), seed `min_net_margin_pct = 15` for CA in `thresholds.toml`, and keep the refuse-never-default / refuse-never-clamp grammar verbatim.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Ceiling formula (D-01):** Ceiling is fully margin-derived, per SKU:
`ceiling_tacos_pct(sku) = contribution_margin_pct(sku) − min_net_margin_pct`. Every ceiling traces to one floor number; there is **no separate per-tier ceiling table**. Worked examples: 39% CM → 24% ceiling; 20% CM → 5% ceiling. A SKU whose CM ≤ the floor yields a ceiling of ≤ 0% → no spend-up permitted (any positive TACOS breaches) — the correct, surfaced behavior for thin/below-floor baklava ASINs.

**D-01a:** Tiers (HERO/MAINTAIN/CUT) remain advisory PPC posture (`state/targets.md`, prose skills) — **NOT** gate inputs. No 25% hard cap is added; "winners up to ~25%" is descriptive of a fat-margin SKU's formula output, not a separate clamp.

**Contribution-margin source (D-02):** Contribution margin is PRE-ad, computed live from the premium Profit-by-SKU export's window-summed components (same A1 window-sum approach as `tacos.py`): `contribution_margin_pct = (total_sales − COGS − fulfilment/referral fees) / total_sales`. Ad spend is **excluded** from the cost basis — otherwise the gate is circular (the ceiling would shrink as you spend).

**D-03:** The researcher must verify against `docs/datadoe-source-map.md` whether the source's `profit_sum` already nets out ad spend; if it does, `ad_spend_sum` is added back so the margin is genuinely pre-ad. The catalog table's COGS (D-04) is the cross-check. A SKU whose export COGS is 0/null → margin treated unreliable → gate refusal (anti-fabrication), never a guessed or substituted margin.

**SKU→tier/margin table (D-04):** A new machine-readable file the gate parses directly (e.g. `engine/config/sku_catalog.toml` — exact name/format is Claude's discretion), one row per SKU carrying: `sku`, `asin`, `tier`, `cogs` (landed = `cogs_total_value`). The gate reads tier + COGS + the canonical SKU set; per-SKU margin is computed live (D-02), **not stored** (avoids drift, consistent with the read-live trust-spine pattern).

**D-05:** The prose SKU table in `anabtawi-context/SKILL.md` becomes a rendering of this file (single source of truth). A SKU absent from the file → typed gate refusal on funding it ("SKU not in catalog table") — correct GATE-05 behavior, surfaced as such, never defaulted.

**Projected TACOS (D-06):** Projected TACOS of a spend-increasing action = sales held flat (worst case): `projected = (current_ad_spend_sum + Δspend) / current_total_sales_sum`, where `Δspend` derives from the `ProposedAction`'s before→after bid/budget. The action passes only if projected ≤ the SKU's ceiling (D-01). Spend-decreasing actions (pause / negative / bid-down) skip the projection and auto-pass the gate (locked by constitution + GATE-03).

**Net-margin floor (D-07):** Seed the real floor now: `min_net_margin_pct = 15` for marketplace CA in `engine/config/thresholds.toml`, clearing the Phase 7 blocking precondition so spend-up can pass in Phase 8+. The empty-refusal path is still built and tested (SC-2: the gate refuses on every write while the floor is `""`) via a fixture/override, independent of the seeded live value.

**D-07a:** Key naming: standardize on `min_net_margin_pct` as the key the gate reads (rename or alias is Claude's discretion; keep `thresholds.read(key, marketplace)`'s refuse-on-empty contract). The file currently has `min_margin_pct = ""`.

**Refusal grammar & types (D-08):** `gate.py` returns a typed `GateVerdict` / `GateRefusal` mirroring `result.Refusal` + the `_present_flag` grammar: a breach names the breached number and its source; `"no threshold set"` when the floor is unset; `"no margin"` / `"SKU not in catalog"` when margin/SKU is missing. It never silently clamps to the limit (GATE-04). New types live in `result.py` alongside `Refusal` / `Proceed` / `PollOutcome`.

### Claude's Discretion
- Exact filename/format of the SKU catalog file; the `min_net_margin_pct` rename-vs-alias mechanics.
- `gate.py` module/function layout, the `ProposedAction` dataclass shape, and the `gate_action.py` thin CLI structure (mirror `answer_tacos.py`).
- Which fee components count as "fees" in D-02 (FBA fulfilment + referral) — researcher pins the exact column set against the source map (see "THE D-03 RESOLUTION").
- Rounding/precision of the derived ceiling and the projected TACOS.

### Deferred Ideas (OUT OF SCOPE)
- The reversible-write apply spine + stop-the-bleed (the gate's first real consumer) → **Phase 8**.
- Daily dollar-ranked queue + projected-$ estimate rows → **Phase 9**.
- Standing-approval magnitude cap on bid-down/negatives (research Q4) and the act-now vs judge-later attribution boundary (research Q1) → **Phase 8 / 9**.
- Portfolios decision (research Q5) and new-campaign projected-TACOS seed for no-history campaigns → **Phase 10**.
- Migrating `thresholds.toml` (incl. `min_net_margin_pct`) and the SKU catalog → the Supabase `config` / `sku_master` tables → **Phase 3.5**.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GATE-01 | Engine computes each SKU's contribution margin from DataDoe window-summed components — typed, tested, never prose | `contribution_margin_pct = (profit_sum + ad_spend_sum) / total_sales_sum` (pre-ad back-out, D-03 resolved); reuses `tacos.parse()` window-sum reader. See "THE D-03 RESOLUTION" + "Code Examples". |
| GATE-02 | Engine derives a per-SKU TACOS ceiling to protect a configured min net margin; missing min-margin → refusal, never a default | `ceiling_tacos_pct = CM% − thresholds.read("min_net_margin_pct", mkt)`; `thresholds.read` returns `None` on empty → `GateRefusal("no threshold set")`. Seed `min_net_margin_pct = 15` (D-07). |
| GATE-03 | Spend-increasing writes must pass (projected TACOS ≤ ceiling); spend-decreasing writes always pass | `ProposedAction.is_spend_increasing` branches: decreasing → auto-pass `GateVerdict`; increasing → `projected_tacos = (ad_spend_sum + Δspend)/total_sales_sum` compared to ceiling (D-06). |
| GATE-04 | Over-ceiling bid/budget refused (typed `GateRefusal` naming the breached number + source), never silently clamped | Mirror `_present_flag` "breach" grammar; `GateRefusal(reason, code, breached_value, ceiling, source=PREMIUM_SOURCE)`. Never returns a clamped value. |
| GATE-05 | SKU→tier/contribution-margin table machine-readable; gate consumes directly; absent SKU → refusal | New `engine/config/sku_catalog.toml` (D-04); SKU absent from catalog → `GateRefusal("SKU not in catalog")` (D-05). |
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Contribution-margin computation | Engine (`gate.py`) | — | Money math is hand-written + pytest-covered (CLAUDE.md hard rule 3); never prose, never agent-computed. |
| Window-summed component read | Engine (`tacos.parse` reuse) | DataDoe MCP (agent fetches artifact) | The agent/MCP downloads the export (the seam); Python only parses the local artifact. No HTTP in Python (`datadoe.py` seam). |
| Floor threshold read | Engine (`thresholds.read`) | `config/thresholds.toml` | Refuse-on-empty contract already implemented; floor plugs straight in. |
| SKU→tier/COGS catalog | `engine/config/sku_catalog.toml` (new) | `anabtawi-context/SKILL.md` (rendered view) | Single machine-readable source of truth (D-04/D-05); prose becomes a rendering. |
| Gate verdict / refusal | Engine (`result.py` types) | `gate_action.py` CLI (serialization only) | Typed result is the anti-fabrication surface; CLI is thin wiring (mirror `answer_tacos.py`). |
| Δspend derivation from a write | Engine (`ProposedAction` dataclass) | — | The before→after bid/budget delta is a pure-data input to the gate; no Amazon call. |

**This phase changes nothing on Amazon.** It decides *whether a write would be allowed to proceed*; it sits between BUILD and DRYRUN (the missing middle step the Phase 8 apply spine will call).

## THE D-03 RESOLUTION (the critical open question — RESOLVED)

> This is the single most load-bearing finding in this research. The planner must build the gate on it. Every claim below is cited to a source-map section/line or verified arithmetically against the committed fixture.

### Q: Is the premium export's `profit` PRE-ad or POST-ad?

**A: POST-ad. Ad spend MUST be added back.** Two independent confirmations:

1. **Definition (verbatim):** `total_cost = settlement fees + cogs_total + ad_spend` `[CITED: docs/datadoe-source-map.md §3a line 77]`. Since the source computes `profit = total_sales − total_cost` (implied by `roi = profit / total_cost` and the standard P&L identity), `profit` has ad spend subtracted. **Profit is POST-ad.**

2. **Arithmetic on the live fixture** `[VERIFIED: engine/tests/fixtures/profit_by_sku_30d.csv]`:
   - `EU-Z87B-ZRBZ`: total_sales=279.95, total_cost=179.68, profit=100.27 → 279.95 − 179.68 = 100.27 ✓ (total_cost 179.68 includes ad_spend 0.50).
   - `9Z-KUHZ-FU2I`: total_sales=0, ad_spend=25.28, total_cost=25.28, profit=−25.28 → with zero sales the entire cost IS the ad spend, and profit = 0 − 25.28. **Direct proof that ad_spend flows into total_cost and out of profit.**

### Q: What columns, exactly, feed the pre-ad contribution margin?

D-02 defines `CM% = (total_sales − COGS − fulfilment/referral fees) / total_sales`. There are **two arithmetically-equivalent ways** to compute this from the premium source. The planner should choose the **back-out** path because it needs no new export columns:

**Path A — RECOMMENDED (back-out; no new export columns):**
```
pre_ad_cost   = total_cost_sum − ad_spend_sum          # strip ad spend from the all-in cost
contribution  = total_sales_sum − pre_ad_cost
            = total_sales_sum − total_cost_sum + ad_spend_sum
            = profit_sum + ad_spend_sum                # since profit = total_sales − total_cost
CM%           = (profit_sum + ad_spend_sum) / total_sales_sum × 100
```
`profit_sum`, `ad_spend_sum`, and `total_sales_sum` are **already in the existing groupBy export** `[VERIFIED: engine/tests/fixtures/profit_by_sku_30d.csv header line 1 + engine/src/habibos/tacos.py EXPECTED_COLUMNS lines 50-58]`. This is the minimal, lowest-risk computation: it reuses `tacos.parse()` unchanged.

Worked check on the fixture (`EU-Z87B-ZRBZ`): CM% = (100.27 + 0.50) / 279.95 × 100 = **36.0%** → ceiling = 36.0 − 15 = **21.0%**. Plausible for a 850g hero. `[VERIFIED: arithmetic on fixture]`

**Path B — explicit decomposition (requires expanding the groupBy export):** sum the source's own fee/cogs columns and subtract them directly:
```
CM% = (total_sales_sum − cogs_total_sum − abs(total_fees_sum)) / total_sales_sum × 100
```
This requires re-pulling the export with `cogs_total_sum` and `total_fees_sum` added to the `*_sum` group-by alias list. Note `total_fees` is **negative**; FBA/AWD fees are subsets of it `[CITED: docs/datadoe-source-map.md §3a line 81]`. Referral fee is NOT a separate column in this premium source — it is rolled into `total_fees` here (the separate `referral_fee` column lives only in the `amazon_settlements_with_cogs` source `732dac689a`) `[CITED: docs/datadoe-source-map.md §3b line 93]`.

**Path A and Path B are mathematically identical** (because `total_cost = total_fees-as-positive + cogs_total + ad_spend`, so `total_cost − ad_spend = fees + cogs`). **Recommend Path A** — it is the back-out D-03 explicitly authorizes, needs no export schema change, and reuses the proven reader.

### Q: Which fee components count as "fees" in D-02?

In the premium source, "fees" = the **full `total_fees` bundle** (FBA fulfilment + referral + AWD, all subsets of `total_fees`) `[CITED: docs/datadoe-source-map.md §3a line 81]`. With Path A you never name individual fee columns — they are implicitly inside `total_cost − ad_spend`. This satisfies D-02's "fulfilment/referral fees" because `total_fees` already contains both.

### Q: COGS — export or catalog?

- The **computed margin** uses the export's COGS implicitly (it's inside `total_cost`/`profit`) — Path A.
- The **catalog `cogs` (landed `cogs_total_value`)** is the **cross-check** (D-04): if a SKU's export-implied COGS is 0/null (detectable when `total_cost_sum − ad_spend_sum ≈ abs(total_fees)` i.e. no COGS component, or when the catalog itself has a 0/null COGS), the margin is **unreliable → `GateRefusal("no margin / unreliable COGS")`**, never a guessed or substituted number (D-03 anti-fabrication).
- **Recommended unreliable-COGS detector:** because Path A doesn't expose COGS directly, the simplest reliable check is the **catalog cross-check**: if `sku_catalog.toml`'s `cogs` for the SKU is 0/null/missing → refuse. Optionally, also refuse if `total_sales_sum == 0` (can't compute a margin — divide-by-zero, the `tacos._ratio` `None` path). The planner should specify exactly which signal triggers the "unreliable COGS" refusal; the catalog cross-check is the most defensible.

### What the source map does NOT define (flag honestly)

- The source map does **not** print a verbatim `profit = total_sales − total_cost` line; that identity is **inferred** from `roi = profit / total_cost` (line 76) + the `total_cost` decomposition (line 77) and **confirmed arithmetically** on the fixture. Confidence is HIGH because the fixture proves it exactly, but the planner should note the identity is derived, not quoted. `[VERIFIED: fixture arithmetic]` `[CITED: §3a lines 76-77]`
- The premium source's exact `referral_fee` breakout is **not** in this table (it's in settlements `732dac689a`); D-02's "referral fees" are satisfied via the `total_fees` bundle, not a standalone column. `[CITED: §3a line 70, §3b line 93]`

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `polars` | 1.41.2 (pinned) | CSV → frame parse + window-sum read of the premium export | Already the reader in `tacos.parse()`; reuse verbatim `[VERIFIED: engine/pyproject.toml]` |
| `pydantic` | 2.13.4 (pinned) | Validate the export row schema (`_PremiumRow`) + the `ProposedAction` shape | Same `BaseModel`+`ConfigDict(extra="ignore")` pattern as `tacos._PremiumRow` `[VERIFIED: engine/pyproject.toml]` |
| `tomllib` | stdlib (3.12) | Read `min_net_margin_pct` floor + the new `sku_catalog.toml` | `thresholds.read()` already uses it; refuse-on-empty contract proven `[VERIFIED: engine/src/habibos/thresholds.py]` |
| `argparse` + `json` | stdlib (3.12) | The thin `gate_action.py` CLI | Mirror `scripts/answer_tacos.py` exactly `[VERIFIED: engine/scripts/answer_tacos.py]` |
| `pytest` | ≥9.0.3 (dev) | `test_gate.py` — money-logic contract | `cd engine && uv run pytest` must stay green `[VERIFIED: engine/pyproject.toml]` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `dataclasses` | stdlib | `GateVerdict` / `GateRefusal` / `ProposedAction` frozen dataclasses | Mirror the frozen-dataclass result types in `result.py` |
| `structlog` (via `logging.logged_call`) | 26.1.0 (pinned) | Wrap the gate CLI op (one in / one out, no seller UUID) | Only if the gate CLI is treated as a logged op; mirror `answer_tacos.py`'s `logged_call` usage `[VERIFIED: engine/src/habibos/logging.py]` |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Path A back-out (`profit_sum + ad_spend_sum`) | Path B explicit decomposition (`cogs_total_sum`, `total_fees_sum`) | Path B re-pulls the export with extra `*_sum` columns; mathematically identical to A; only worth it if a future phase wants a per-component fee breakdown. Recommend A now. |
| New `result.py` types | Reuse `Refusal` directly | `Refusal` lacks `breached_value`/`ceiling`/`source` fields GATE-04 needs to "name the breached number and its source"; a `GateRefusal` sibling is the right shape (D-08). |
| `sku_catalog.toml` | `sku_catalog.csv` / extend `ca_catalog_skus.txt` | TOML matches `thresholds.toml` and is keyed/typed; the existing `ca_catalog_skus.txt` is a flat SKU list with no tier/COGS columns. A new structured file is correct (D-04). |

**Installation:**
```bash
# No new packages. The engine stack is already pinned in engine/pyproject.toml.
cd engine && uv sync
```

**Version verification:**
```bash
cd /Users/mareekhalila/Documents/anabtawi-amazon-os/engine && uv run python -c "import polars, pydantic; print(polars.__version__, pydantic.VERSION)"
```
`[VERIFIED: engine/pyproject.toml — polars==1.41.2, pydantic==2.13.4, pytest>=9.0.3, requires-python>=3.12]`

## Package Legitimacy Audit

> No external packages are installed in this phase. Every dependency the gate uses is already pinned in `engine/pyproject.toml` (verified above) and was legitimacy-checked in prior phases. slopcheck not run because no new install occurs.

| Package | Registry | Disposition |
|---------|----------|-------------|
| polars 1.41.2 | PyPI (already pinned) | Approved — no new install |
| pydantic 2.13.4 | PyPI (already pinned) | Approved — no new install |
| tomllib / argparse / json / dataclasses / hashlib | stdlib (3.12) | Approved — stdlib |

**Packages removed due to slopcheck [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                         ┌─────────────────────────────────────────────────┐
  ProposedAction ───────►│                  gate.py                         │
  (target sku/asin,      │  (hand-written money core — the tacos.py twin)   │
   before→after          │                                                  │
   bid/budget, type)     │  1. spend-direction branch (D-06):               │
                         │       decreasing → GateVerdict(auto_pass)         │──► spend-DOWN: auto-pass
                         │       increasing → continue ▼                     │
                         │                                                   │
  sku_catalog.toml ─────►│  2. catalog lookup (D-04/05):                     │
   (tier, cogs, set)     │       sku ∉ catalog → GateRefusal("not in catalog")│──► REFUSE
                         │                                                   │
  premium export ───────►│  3. CM% = (profit_sum+ad_spend_sum)/total_sales   │
   *_sum components      │       (Path A pre-ad back-out, D-03)              │
   (via tacos.parse,     │       cogs 0/null in catalog → GateRefusal("no margin")│──► REFUSE
    agent/MCP fetch)     │                                                   │
                         │  4. floor = thresholds.read("min_net_margin_pct") │
  thresholds.toml ──────►│       None → GateRefusal("no threshold set")      │──► REFUSE
   min_net_margin_pct=15 │                                                   │
                         │  5. ceiling = CM% − floor       (D-01)            │
                         │     projected = (ad_spend_sum+Δspend)/total_sales │ (D-06, sales flat)
                         │       projected > ceiling → GateRefusal("breach", │──► REFUSE (names #+source)
                         │                              breached, ceiling)   │
                         │       projected ≤ ceiling → GateVerdict(pass)     │──► PASS
                         └─────────────────────────────────────────────────┘
                                              │
                                              ▼
                         gate_action.py (thin CLI: argv → evaluate → JSON stdout)
                                              │
                                              ▼
                    [Phase 8 apply spine calls this BEFORE actions_start dryRun]
```

The gate is a **pure decision function** — it touches no socket, no Amazon API, no DataDoe network call. The agent/MCP fetches the export artifact; Python parses the local file (the documented seam in `datadoe.py`).

### Recommended Project Structure
```
engine/
├── src/habibos/
│   ├── gate.py          # NEW — the money core (parse-reuse, CM%, ceiling, projected, evaluate)
│   └── result.py        # EXTEND — add GateVerdict + GateRefusal + ProposedAction (or ProposedAction in gate.py)
├── scripts/
│   └── gate_action.py   # NEW — thin CLI mirroring answer_tacos.py
├── config/
│   ├── thresholds.toml  # EDIT — add min_net_margin_pct=15 for [marketplace.CA]
│   └── sku_catalog.toml # NEW — per-SKU tier + cogs + canonical set (D-04)
└── tests/
    ├── test_gate.py     # NEW — the mandatory pytest contract
    └── fixtures/
        └── profit_by_sku_30d.csv  # REUSE — already has profit_sum/ad_spend_sum/total_sales_sum
```

### Pattern 1: Mirror `tacos.py`'s parse → compute → typed-result shape
**What:** `gate.py` reuses `tacos.parse()` (or imports `EXPECTED_COLUMNS` and the `_PremiumRow` validator) to read the window-summed export, computes the margin/ceiling/projection from the summed components, and returns a frozen typed result.
**When to use:** Always — this is the established money-core contract (CLAUDE.md hard rule 3).
**Example:**
```python
# Source: engine/src/habibos/tacos.py (the pattern to mirror) lines 107-125
def _ratio(numerator, denominator):
    if numerator is None or denominator is None or denominator == 0:
        return None  # "no sales / undefined" — NEVER 0 or a guess
    return round(numerator / denominator * 100, 1)
```

### Pattern 2: Refuse-never-default (threshold) + refuse-never-clamp (gate verdict)
**What:** `thresholds.read("min_net_margin_pct", "CA")` returns `None` when empty → `GateRefusal("no threshold set")`. A breach returns a `GateRefusal` naming the breached number — never a clamped value.
**When to use:** Every missing-input and over-ceiling path.
**Example:**
```python
# Source: engine/src/habibos/tacos.py _present_flag lines 118-124
def _present_flag(value, ceiling):
    if ceiling is None:
        return "no threshold set"   # missing ceiling -> refuse the flag, never a default
    if value is None:
        return "no sales"
    return "breach" if value > ceiling else "ok"   # strict: value == ceiling is "ok"
```
Note the **strict** comparison (`value > ceiling` is breach; equal is ok). The gate should mirror this: `projected > ceiling` → refuse; `projected == ceiling` → pass.

### Pattern 3: Thin CLI wiring (no business logic in the script)
**What:** `gate_action.py` parses argv, calls `gate.evaluate(...)` inside `logged_call`, `dataclasses.asdict`s the result to JSON on stdout. No ratios, no dates, no decisions in the CLI.
**Example:**
```python
# Source: engine/scripts/answer_tacos.py lines 97-127 (the shape to mirror)
with habibos_logging.logged_call("gate_action", source_id=PREMIUM_SOURCE_ID, marketplace=args.marketplace) as end_fields:
    result = gate.evaluate(...)
    end_fields["status"] = "refused" if isinstance(result, GateRefusal) else "pass"
json.dump(dataclasses.asdict(result), sys.stdout)
```

### Anti-Patterns to Avoid
- **Computing the margin in chat / agent prose.** Forbidden by CLAUDE.md hard rule 3. The number must come from `gate.py`.
- **Clamping an over-ceiling write to the ceiling.** GATE-04 forbids it — refuse, never clamp.
- **Defaulting a missing floor to 25% (or any number).** GATE-02 forbids it — `None` → refuse.
- **Including ad spend in the cost basis** (using `profit_sum` raw without adding `ad_spend_sum` back). Makes the gate circular (D-02/D-03). The fixture proves `profit` is post-ad.
- **Storing the per-SKU margin in the catalog file.** D-04 says compute live; store only tier + COGS + the SKU set.
- **Silently falling back to export rows for the canonical SKU set.** D-05: a SKU absent from the catalog is a refusal, not a silent default (the same discipline `answer_tacos.py` documents for the `ca_catalog_skus.txt` D-10 path).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Reading the window-summed export | A new CSV parser/validator | Reuse `tacos.parse()` + `_PremiumRow` | Already pydantic-validated, fail-loud on schema drift (Pitfall 1) `[VERIFIED: tacos.py lines 80-104]` |
| Reading the floor threshold | A new TOML reader | `thresholds.read("min_net_margin_pct", "CA")` | Refuse-on-empty already implemented `[VERIFIED: thresholds.py]` |
| The ratio (margin/projected TACOS) | A custom divide with ad-hoc zero handling | `tacos._ratio()` (or a clone) returning `None` on zero denom | Zero-denominator → `None` ("no sales"), never 0 or a guess `[VERIFIED: tacos.py lines 107-115]` |
| Typed refusal envelope | A dict / bare string / None | `GateRefusal` dataclass sibling of `Refusal` | The whole anti-fabrication contract is typed results (`result.py` docstring) |
| Structured call logging | print / custom logger | `logging.logged_call` | One-in/one-out, never logs seller UUID `[VERIFIED: logging.py]` |

**Key insight:** Phase 7 is almost entirely *assembly of proven primitives*. The genuinely new code is: (1) the CM%→ceiling formula, (2) the projected-TACOS-with-Δspend formula, (3) the spend-direction branch, (4) the catalog reader, (5) two new dataclasses. Everything else is reuse.

## Runtime State Inventory

> Phase 7 is a code/config-additive phase (new module + new config files + one threshold edit). It does **not** rename or migrate stored runtime state. The one cross-system consistency obligation is D-05.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — the gate stores no data; per-SKU margin is computed live (D-04), not persisted. Verified by D-04 ("not stored"). | none |
| Live service config | None — no external service config embeds gate state. The DataDoe export is read-only and fetched per-run. | none |
| OS-registered state | None — no scheduled task, daemon, or OS registration. Desktop on-demand only (PROJECT.md: no unattended cron). | none |
| Secrets/env vars | None new. The gate reads no secret; `AMAZON_CA_SELLER_ID` is never touched by `gate.py` (the export artifact is pre-fetched, UUID-sanitized per §6 of the source map). | none |
| Build artifacts | The `sku_catalog.toml` becomes the single source of truth (D-05); the prose table in `.claude/skills/anabtawi-context/SKILL.md` must be re-derived as a *rendering* of it. **Two-direction obligation:** (1) author `sku_catalog.toml` from the current prose table (26 SKUs incl. tier + landed COGS, lines 27-53), (2) note in `SKILL.md` that the prose table now renders the TOML. | catalog authoring + SKILL.md note (a plan task, not a data migration) |

**Drift risk to surface to the planner:** the current `ca_catalog_skus.txt` fixture (30 SKUs) and the prose table in `anabtawi-context/SKILL.md` (26 detailed rows + a remnant line) must reconcile into one `sku_catalog.toml`. The prose table is the COGS authority (landed `cogs_total_value` from export `b18aadfd`). The planner should reconcile the two SKU sets explicitly — some `ca_catalog_skus.txt` SKUs (e.g. `OA-26MX-IHV0`, `5G-ZW6Q-WOZG`, `9J-ASSK-BVKC`, `FO-SE3J-T74M`) appear as "inactive remnants" in the prose table with no COGS, which under D-03/D-05 correctly become **refusals on funding** (no COGS / unreliable). `[VERIFIED: .claude/skills/anabtawi-context/SKILL.md lines 26-53; engine/tests/fixtures/ca_catalog_skus.txt]`

## Common Pitfalls

### Pitfall 1: Treating `profit_sum` as pre-ad (the circular-gate trap)
**What goes wrong:** Computing CM% directly from `profit_sum/total_sales_sum` makes the ceiling shrink as you spend, so the gate refuses winners precisely when they're working.
**Why it happens:** `profit` LOOKS like contribution margin but is POST-ad (`total_cost` includes `ad_spend`).
**How to avoid:** Always add `ad_spend_sum` back: `CM% = (profit_sum + ad_spend_sum)/total_sales_sum`. This is D-03, now arithmetically proven on the fixture.
**Warning signs:** A high-spend SKU's computed CM% is much lower than its catalog COGS implies; the ceiling for a known-fat-margin SKU comes out negative.

### Pitfall 2: Flat TACOS overspends past the margin floor on thin SKUs (the mission-metric failure)
**What goes wrong:** A flat ceiling (e.g. 25%) is profitable on fat SKUs and loss-making on thin ones; two baklava ASINs already sit below the ~20% contribution floor.
**Why it happens:** Blended portfolio margin (~39% t30) masks per-SKU thinness.
**How to avoid:** The whole point of D-01 — derive each ceiling from that SKU's *own* CM%. A SKU with CM% ≤ 15 yields a ≤0% ceiling → no spend-up. This is a **feature** (surface it plainly), not a bug.
**Warning signs:** A request to add a flat clamp "so thin SKUs can still spend a little" — reject it; that reintroduces the failure.
`[CITED: .planning/research/PITFALLS.md #2]`

### Pitfall 3: Schema drift in the export silently mis-feeds the gate
**What goes wrong:** A renamed/missing `*_sum` column gets coerced to a wrong number.
**Why it happens:** DataDoe could change the export shape.
**How to avoid:** Reuse `tacos._PremiumRow` pydantic validation (`extra="ignore"` tolerates utility columns; a missing REQUIRED column raises → caller surfaces a Refusal). Never coerce.
**Warning signs:** A `ValidationError`/`ValueError` from `parse()` — that is correct fail-loud behavior, not a bug to swallow.
`[CITED: engine/src/habibos/tacos.py lines 28-31, 96-104]`

### Pitfall 4: Divide-by-zero on a zero-sales SKU
**What goes wrong:** `total_sales_sum == 0` (e.g. `ASW-H50`, `9Z-KUHZ-FU2I` in the fixture) → CM% undefined.
**Why it happens:** A SKU has ad spend but no sales in the window.
**How to avoid:** Use the `_ratio` `None`-on-zero-denominator pattern → a zero-sales SKU yields an unreliable margin → `GateRefusal("no margin / no sales")`. Never 0%, never a guess.
**Warning signs:** A ceiling computed for a SKU with `total_sales_sum == 0`.
`[VERIFIED: fixture rows ASW-H50, 9Z-KUHZ-FU2I, H8-PWJ0-3B1Y all have total_sales_sum=0]`

### Pitfall 5: Spend-decreasing writes wrongly routed through the projection
**What goes wrong:** A pause/negative/bid-down gets refused because its projected TACOS is computed and compared.
**Why it happens:** Forgetting the D-06/GATE-03 auto-pass branch.
**How to avoid:** Branch on `ProposedAction.is_spend_increasing` FIRST; spend-decreasing → immediate `GateVerdict(auto_pass=True)`, no projection, no catalog/margin/floor read required.
**Warning signs:** A bid-down on a thin SKU getting "breach" — it should always pass.

## Code Examples

### Pre-ad contribution margin (Path A back-out, D-03)
```python
# Source: derived from engine/src/habibos/tacos.py _ratio + the D-03 resolution.
def contribution_margin_pct(profit_sum, ad_spend_sum, total_sales_sum):
    """Pre-ad contribution margin %, or None if undefined (zero/missing sales).

    PRE-ad (D-02/D-03): profit_sum is POST-ad (total_cost includes ad_spend), so we
    add ad_spend_sum back. CM% = (profit + ad_spend) / total_sales * 100.
    """
    if total_sales_sum is None or total_sales_sum == 0:
        return None  # undefined — refuse, never 0 or a guess (mirror _ratio)
    if profit_sum is None or ad_spend_sum is None:
        return None
    return round((profit_sum + ad_spend_sum) / total_sales_sum * 100, 1)
```

### Ceiling + projected-TACOS + verdict (D-01 / D-06 / GATE-04)
```python
# Source: derived from tacos._present_flag (strict > comparison) + D-01/D-06.
def ceiling_tacos_pct(cm_pct, floor):
    """ceiling = CM% - floor (D-01). Caller refuses earlier if cm_pct or floor is None."""
    return round(cm_pct - floor, 1)

def projected_tacos_pct(ad_spend_sum, delta_spend, total_sales_sum):
    """Worst-case projection: sales held flat (D-06). None on zero/missing sales."""
    if total_sales_sum is None or total_sales_sum == 0:
        return None
    return round((ad_spend_sum + delta_spend) / total_sales_sum * 100, 1)

# Verdict (mirrors the strict 'value > ceiling' breach grammar):
#   projected > ceiling -> GateRefusal("breach", breached_value=projected, ceiling=ceiling, source=PREMIUM_SOURCE)
#   projected <= ceiling -> GateVerdict(pass=True, projected_tacos=projected, ceiling=ceiling)
```

### New typed results in result.py (D-08)
```python
# Source: mirror of engine/src/habibos/result.py Refusal/Proceed (frozen dataclasses).
@dataclass(frozen=True)
class GateRefusal:
    """A typed gate refusal — names the breached number and its source (GATE-04)."""
    reason: str               # surfaced verbatim
    code: str                 # "no_threshold_set" | "no_margin" | "sku_not_in_catalog" | "over_ceiling"
    breached_value: float | None = None   # e.g. the projected TACOS that breached
    ceiling: float | None = None
    source: str | None = None  # PREMIUM_SOURCE provenance

@dataclass(frozen=True)
class GateVerdict:
    """A typed PASS — never a bare True (mirror of Proceed)."""
    projected_tacos: float | None   # None for an auto-passed spend-decrease
    ceiling: float | None
    contribution_margin: float | None
    auto_pass: bool = False         # True for spend-decreasing actions (D-06)
```

### thresholds.toml edit (D-07 / D-07a)
```toml
# Source: engine/config/thresholds.toml [marketplace.CA] block — add the floor key.
[marketplace.CA]
min_net_margin_pct = 15   # D-07: seed the real floor (was min_margin_pct = "")
# (rename min_margin_pct -> min_net_margin_pct, or keep both as alias — D-07a, Claude's discretion.
#  Keep thresholds.read's refuse-on-empty contract: an empty value still returns None.)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat 25% TACOS clamp instinct ($2,500→$10k) | Per-SKU margin-derived ceiling (D-01) | M2 (this milestone) | The flat number survives only as the *descriptive* aggressive-winner output, not a clamp `[CITED: PROJECT.md lines 18-22]` |
| `min_margin_pct = ""` (unset, refuse-everything) | `min_net_margin_pct = 15` seeded (D-07) | Phase 7 | Clears the blocking precondition so Phase 8+ spend-up can pass `[CITED: ROADMAP.md line 141]` |
| Per-tier ceiling table (hero 35 / maintain 28 / cut 18, in thresholds.toml comments) | NO per-tier ceiling table; one floor + per-SKU formula (D-01a) | Phase 7 | Tiers are advisory only; the formula replaces the tier ceilings the thresholds.toml comment anticipated `[CITED: thresholds.toml lines 22-23; D-01a]` |

**Deprecated/outdated:**
- The `thresholds.toml` comment (lines 22-23) anticipating "Tier-aware ceilings (hero 35 / maintain 28 / cut 18) activate once the SKU→tier table is filled" is **superseded by D-01a** — no per-tier ceilings; the gate is one floor + per-SKU formula. The planner should update or remove that comment to avoid future confusion.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `profit = total_sales − total_cost` (the P&L identity the source uses) is inferred from `roi = profit/total_cost` + the `total_cost` decomposition, not quoted verbatim. | THE D-03 RESOLUTION | LOW — confirmed exactly on two fixture rows; if wrong the CM% formula is off, but the fixture arithmetic would have to be coincidental. Mitigation: `test_gate.py` should assert the CM% back-out against the same fixture rows used in `test_tacos.py`. |
| A2 | The "unreliable COGS → refuse" trigger is best implemented via the **catalog cross-check** (0/null catalog `cogs`), since Path A doesn't expose COGS directly. | THE D-03 RESOLUTION (COGS) | MEDIUM — if the operator wants the export-side COGS as the trigger instead, the gate would need Path B (extra `cogs_total_sum` column). Flag for the planner: confirm which signal triggers the refusal. This is a Claude's-discretion boundary the planner should pin in a task. |
| A3 | The new catalog file format is `sku_catalog.toml` (TOML, matching `thresholds.toml`). | Standard Stack / Structure | LOW — explicitly Claude's discretion (D-04). Format choice doesn't affect the money logic. |

**Note:** The core D-03 finding (profit is POST-ad, add ad_spend back) is **VERIFIED, not assumed** — it is proven both by the source-map definition and by exact fixture arithmetic. Only the secondary items above carry residual assumption risk.

## Open Questions (RESOLVED)

1. **Unreliable-COGS refusal trigger (A2 above).**
   - What we know: D-03 says a 0/null export COGS → unreliable → refuse; the catalog `cogs` is the cross-check.
   - What's unclear: with Path A (back-out) the export COGS isn't a separate column, so the most practical trigger is the catalog cross-check (catalog `cogs` is 0/null/missing).
   - Recommendation: planner pins "catalog `cogs` ≤ 0 or missing → `GateRefusal('no margin / unreliable COGS')`" as the trigger, plus `total_sales_sum == 0 → refuse`. If the operator insists on export-side COGS detection, that pulls in Path B (extra column) — a small scope add to flag.

2. **`min_margin_pct` rename vs alias (D-07a — Claude's discretion).**
   - What we know: the gate reads `min_net_margin_pct`; the file has `min_margin_pct = ""`.
   - What's unclear: rename in place, or add the new key and leave the old one.
   - Recommendation: rename `min_margin_pct` → `min_net_margin_pct` and seed `= 15`. Update `test_thresholds.py::test_missing_threshold_returns_none` (which currently asserts `read("min_margin_pct", "CA") is None`) to use a still-empty key, or it will break once the floor is seeded. **Flag: this existing test references the old key name — the plan must update it.** `[VERIFIED: engine/tests/test_thresholds.py line 31]`

3. **Δspend derivation from a `ProposedAction`.**
   - What we know: D-06 says Δspend derives from before→after bid/budget; sales held flat.
   - What's unclear: for a *bid* change (vs a *budget* change) the spend delta isn't 1:1 with the bid delta (spend depends on impressions × CPC). For Phase 7 (gate-exists, not gate-passes-real-traffic) the worst-case assumption (Δspend = budget delta, or for a bid-up the full proposed budget headroom) is acceptable.
   - Recommendation: planner defines `ProposedAction` to carry an explicit `delta_spend` (CAD) field that the *caller* computes from before→after; the gate treats it as given (keeps the gate a pure function and defers the bid→spend modeling to Phase 9's queue). This keeps Phase 7 honest and testable.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | engine | ✓ | ≥3.12 (pyproject `requires-python`) | — |
| uv | test runner (`uv run pytest`) | assumed ✓ (used by all prior phases) | — | `python -m pytest` |
| polars / pydantic | gate parse + validate | ✓ (pinned in pyproject) | 1.41.2 / 2.13.4 | — |
| DataDoe MCP | export fetch (agent-side, not Python) | ✓ (connected, premium ENABLED) | — | reuse committed fixture for tests |

**No external dependency blocks this phase.** The gate consumes a *local, already-downloaded* export artifact (the seam); the committed `profit_by_sku_30d.csv` fixture is sufficient for the entire `test_gate.py` contract — no live pull required to build or test the gate. `[VERIFIED: engine/src/habibos/datadoe.py seam docstring; engine/tests/fixtures/profit_by_sku_30d.csv]`

## Validation Architecture

> `workflow.nyquist_validation: true` in config.json — section required.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest ≥9.0.3 (dev dependency) |
| Config file | `engine/pyproject.toml` `[tool.pytest.ini_options]` (testpaths=["tests"], pythonpath=["src"], addopts="-ra") |
| Quick run command | `cd engine && uv run pytest tests/test_gate.py -x` |
| Full suite command | `cd engine && uv run pytest` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GATE-01 | CM% computed from window-summed components (pre-ad back-out), asserted against the fixture | unit | `uv run pytest tests/test_gate.py::test_contribution_margin_pre_ad -x` | ❌ Wave 0 |
| GATE-02 | ceiling = CM% − floor; floor unset (`""`) → "no threshold set" refusal on every write | unit | `uv run pytest tests/test_gate.py::test_ceiling_and_unset_floor_refuses -x` | ❌ Wave 0 |
| GATE-03 | spend-increasing: projected ≤ ceiling passes, > ceiling refuses; spend-decreasing auto-passes | unit | `uv run pytest tests/test_gate.py::test_spend_direction_branch -x` | ❌ Wave 0 |
| GATE-04 | over-ceiling → `GateRefusal` naming breached value + source, never clamped | unit | `uv run pytest tests/test_gate.py::test_breach_refuses_never_clamps -x` | ❌ Wave 0 |
| GATE-05 | SKU absent from `sku_catalog.toml` → "SKU not in catalog" refusal; catalog is parseable | unit | `uv run pytest tests/test_gate.py::test_sku_not_in_catalog_refuses -x` | ❌ Wave 0 |
| (D-03) | CM% back-out matches fixture arithmetic for EU-Z87B-ZRBZ / 9Z-KUHZ-FU2I | unit | `uv run pytest tests/test_gate.py::test_profit_is_post_ad_addback -x` | ❌ Wave 0 |
| (D-04/05) | unreliable/zero COGS → "no margin" refusal | unit | `uv run pytest tests/test_gate.py::test_unreliable_cogs_refuses -x` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `cd engine && uv run pytest tests/test_gate.py -x`
- **Per wave merge:** `cd engine && uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `engine/tests/test_gate.py` — covers GATE-01..05 + D-03/D-04 edges (mirror `test_tacos.py`'s fixture-driven structure)
- [ ] `engine/config/sku_catalog.toml` — the catalog fixture the gate parses (and a small `tests/fixtures/sku_catalog_*.toml` for edge cases, e.g. a SKU with 0 COGS, a SKU absent from the catalog)
- [ ] `engine/config/thresholds.toml` — seed `min_net_margin_pct = 15`; a test-only override (monkeypatch / temp config) to exercise the empty-floor refusal path (SC-2) independently of the seeded live value
- [ ] No framework install needed — pytest is already the engine test runner

## Security Domain

> `security_enforcement` not present in config.json → treat as enabled. This phase is a pure local computation with no network, no auth, no user input surface — most ASVS categories are N/A.

### Applicable ASVS Categories
| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | No auth surface — local engine module |
| V3 Session Management | no | No sessions |
| V4 Access Control | no | No access-control surface |
| V5 Input Validation | yes | pydantic validation of the export row schema (`_PremiumRow` reuse) + `ProposedAction` shape; fail-loud on drift, never coerce |
| V6 Cryptography | no | No crypto in this phase (idempotency hashing is Phase 8) |
| V7 Logging (secrets) | yes | `logging.logged_call` must NOT receive the seller UUID or any secret (existing contract); the gate reads no secret |

### Known Threat Patterns for the engine money-core
| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Fabricated margin/ceiling (a wrong number passed as fact) | Tampering / Repudiation | Typed `GateRefusal` on every missing/undefined input; never default, never clamp, never guess (the project's core anti-fabrication contract) |
| Schema drift mis-coerced into the gate | Tampering | pydantic `_PremiumRow` validation raises on a missing REQUIRED column → surfaced Refusal |
| Seller UUID leaked into logs | Information Disclosure | `logged_call` start/end fields never carry the UUID; the groupBy export is UUID-sanitized (source map §6) |
| Circular ceiling (ad spend in cost basis) shrinks ceilings under spend | (logic safety, not classic STRIDE) | D-02/D-03 pre-ad back-out — `test_gate.py` asserts the addback |

## Sources

### Primary (HIGH confidence)
- `engine/src/habibos/tacos.py` — the exact mirror pattern: `parse()` / `_PremiumRow` / `EXPECTED_COLUMNS` / `_ratio()` / `_present_flag()` / `classify()`
- `engine/src/habibos/result.py` — `Refusal` / `Proceed` / `PollOutcome` / `SkuRow` frozen-dataclass grammar + `DEFINITIONS` + `PREMIUM_SOURCE`
- `engine/src/habibos/thresholds.py` — `read(key, marketplace)` refuse-on-empty contract
- `engine/scripts/answer_tacos.py` — the thin-CLI shape `gate_action.py` mirrors
- `engine/config/thresholds.toml` — current `min_margin_pct = ""`; the floor key to seed
- `engine/tests/fixtures/profit_by_sku_30d.csv` — the live window-summed fixture; arithmetic proof that `profit` is POST-ad
- `engine/tests/test_tacos.py` — the pytest layout/fixture-driven structure `test_gate.py` mirrors
- `docs/datadoe-source-map.md` §3a (lines 70, 76-81) — verbatim `total_cost`/`roi`/`total_fees` definitions; §3b line 93 (referral_fee location); §6 (groupBy `*_sum` aggregation + UUID sanitization)
- `.planning/ROADMAP.md` Phase 7 (lines 173-183) — SC-1..5 + blocking preconditions (lines 141-145)
- `.planning/REQUIREMENTS.md` — GATE-01..05 (lines 25-29)
- `.planning/research/STACK.md` — "Engine Margin-Gate Module" + OQ1; `.planning/research/PITFALLS.md` #2

### Secondary (MEDIUM confidence)
- `.claude/skills/anabtawi-context/SKILL.md` — the prose SKU→tier/COGS table (lines 26-53) that becomes `sku_catalog.toml`
- `.planning/PROJECT.md` (lines 18-22) — mission metric (net ≥ ~15%, break-even ≈ 39% t30, winners ≤ ~25%, thin ≤ ~12%)
- `.claude/skills/datadoe-query/SKILL.md` — money-math section + the groupBy `*_sum` alias list

### Tertiary (LOW confidence)
- None — all claims are grounded in in-repo files or the source map.

## Metadata

**Confidence breakdown:**
- D-03 pre/post-ad determination: HIGH — proven by source-map definition AND exact fixture arithmetic
- Standard stack: HIGH — every dependency is already pinned and proven in `tacos.py`/`thresholds.py`
- Architecture / mirror pattern: HIGH — `gate.py` is a structural twin of an existing, tested module
- Pitfalls: HIGH — drawn from the project's own audit + verified fixture edges
- Catalog reconciliation (`sku_catalog.toml` ↔ prose ↔ `ca_catalog_skus.txt`): MEDIUM — three sources to reconcile; the SKU sets differ slightly (remnants without COGS)

**Research date:** 2026-06-21
**Valid until:** 2026-07-21 (stable — internal codebase + a documented, enabled DataDoe source; re-verify only if the premium export schema changes)
