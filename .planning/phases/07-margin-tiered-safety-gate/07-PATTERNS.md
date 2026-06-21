# Phase 7: Margin-Tiered Safety Gate - Pattern Map

**Mapped:** 2026-06-21
**Files analyzed:** 8 (4 new, 4 modified/extended)
**Analogs found:** 8 / 8

This phase is **assembly of proven primitives**: every new file has a direct in-repo analog. The gate is the structural twin of `tacos.py`; the CLI mirrors `answer_tacos.py`; the new result types are siblings of `Refusal`/`Proceed`; the floor read reuses `thresholds.read`; the test mirrors `test_tacos.py`. There is **no novel architecture** — the genuinely new code is five small functions (CM%→ceiling, projected-TACOS-with-Δspend, the spend-direction branch, the catalog reader, two dataclasses).

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `engine/src/habibos/gate.py` (NEW) | money-core module | transform (parse → compute → typed verdict) | `engine/src/habibos/tacos.py` | exact (structural twin) |
| `engine/tests/test_gate.py` (NEW) | test | transform/unit | `engine/tests/test_tacos.py` | exact (fixture-driven) |
| `engine/scripts/gate_action.py` (NEW) | CLI / thin wiring | request-response (argv → JSON stdout) | `engine/scripts/answer_tacos.py` | exact |
| `engine/config/sku_catalog.toml` (NEW) | config | file-I/O (read-only catalog) | `engine/config/thresholds.toml` (TOML shape) + the prose table in `anabtawi-context/SKILL.md` (source data) | role-match |
| `engine/src/habibos/result.py` (EXTEND) | typed-result model | data | existing `Refusal` / `Proceed` / `PollOutcome` frozen dataclasses (same file) | exact (add siblings) |
| `engine/config/thresholds.toml` (EDIT) | config | file-I/O | self (existing `[marketplace.CA]` block) | exact |
| `engine/tests/test_thresholds.py` (EDIT) | test | unit | self (existing `test_missing_threshold_returns_none`) | exact |
| `.claude/skills/anabtawi-context/SKILL.md` (RENDER NOTE) | docs / prose | n/a | self (existing prose SKU table lines 26-53) | exact |

---

## Pattern Assignments

### `engine/src/habibos/gate.py` (NEW — money-core, transform)

**Analog:** `engine/src/habibos/tacos.py` (read in full — the structural twin)

**Module-docstring + imports pattern** (mirror `tacos.py` lines 1-58). Reuse the same provenance constant and reuse `tacos.parse` rather than re-rolling a CSV reader:
```python
from __future__ import annotations
from dataclasses import dataclass
import polars as pl
from . import thresholds
from .result import GateRefusal, GateVerdict, ProposedAction, PREMIUM_SOURCE
from .tacos import PREMIUM_SOURCE_ID, parse  # REUSE the validated window-sum reader — import, don't redefine
```
> **Don't hand-roll the reader.** `tacos.parse(artifact, status)` (lines 80-104) already pydantic-validates `EXPECTED_COLUMNS` via `_PremiumRow` (`extra="ignore"`, fail-loud on drift). `profit_sum`, `ad_spend_sum`, `total_sales_sum` are all in that validated set (lines 50-58) — the gate needs no new columns (Path A back-out, RESEARCH).

**The `_ratio` None-on-zero-denominator grammar to clone** (`tacos.py` lines 107-115):
```python
def _ratio(numerator: float | None, denominator: float | None) -> float | None:
    if numerator is None or denominator is None or denominator == 0:
        return None  # "no sales / undefined" — NEVER 0 or a guess
    return round(numerator / denominator * 100, 1)
```
The gate's `contribution_margin_pct()` and `projected_tacos_pct()` must imitate this exactly (same `round(... * 100, 1)`, same `None` on zero/missing denom). Per RESEARCH:
```python
def contribution_margin_pct(profit_sum, ad_spend_sum, total_sales_sum):
    if total_sales_sum is None or total_sales_sum == 0:
        return None                       # divide-by-zero -> refuse, never 0 (Pitfall 4)
    if profit_sum is None or ad_spend_sum is None:
        return None
    return round((profit_sum + ad_spend_sum) / total_sales_sum * 100, 1)  # ad_spend ADDED BACK (D-03)
```

**The strict-breach comparison grammar to clone** (`tacos.py` `_present_flag` lines 118-124):
```python
def _present_flag(value: float | None, ceiling: float | None) -> str:
    if ceiling is None:
        return "no threshold set"   # missing ceiling -> refuse the flag, never a default
    if value is None:
        return "no sales"
    return "breach" if value > ceiling else "ok"   # strict: value == ceiling is "ok"
```
> **Load-bearing for GATE-04:** the gate must use the **strict `>`** — `projected > ceiling` → `GateRefusal`; `projected == ceiling` → pass. Never clamp the breaching value to the ceiling.

**The catalog-read + verdict flow** (mirror `tacos.classify` lines 127-182 — the parse → lookup → typed-result orchestration). The branch order per RESEARCH architecture diagram:
1. spend-direction branch FIRST → spend-decreasing → `GateVerdict(auto_pass=True)`, no reads (Pitfall 5)
2. catalog lookup → SKU ∉ catalog → `GateRefusal("SKU not in catalog", code="sku_not_in_catalog")` (D-05)
3. catalog `cogs` ≤ 0 / null / missing OR `total_sales_sum == 0` → `GateRefusal("no margin / unreliable COGS", code="no_margin")` (D-03, Open Q1)
4. `floor = thresholds.read("min_net_margin_pct", marketplace)` → `None` → `GateRefusal("no threshold set", code="no_threshold_set")` (D-07)
5. `ceiling = CM% − floor` (D-01); `projected = (ad_spend_sum + Δspend) / total_sales_sum`; `projected > ceiling` → `GateRefusal("breach", code="over_ceiling", breached_value=projected, ceiling=ceiling, source=PREMIUM_SOURCE)` else `GateVerdict(...)`

---

### `engine/src/habibos/result.py` (EXTEND — add gate types alongside `Refusal`/`Proceed`/`PollOutcome`)

**Analog:** the existing frozen dataclasses in the **same file** (read in full). Imitate `Refusal` (lines 26-32) and `Proceed` (lines 35-46) exactly: `@dataclass(frozen=True)`, a `reason` + `code` string pair for refusals, a never-bare-`True` positive type, and `from dataclasses import dataclass, field` already imported (line 12).

**`Refusal` shape to mirror** (lines 26-32):
```python
@dataclass(frozen=True)
class Refusal:
    reason: str  # human-readable, surfaced verbatim to the operator
    code: str  # "empty_export" | "failed_export" | "missing_threshold"
    export_id: str | None = None
```

**`Proceed` (the "never a bare True" positive type) to mirror** (lines 35-46):
```python
@dataclass(frozen=True)
class Proceed:
    action_type: str
```

**New siblings to add** (from RESEARCH Code Examples — keep the frozen-dataclass + provenance discipline; reuse the existing `PREMIUM_SOURCE` constant on line 23 for the `source` field):
```python
@dataclass(frozen=True)
class ProposedAction:
    """A pure-data write proposal the gate evaluates (no Amazon call). Δspend is
    caller-computed from before→after bid/budget (Open Q3 — gate treats it as given)."""
    sku: str
    action_type: str            # e.g. "bid_up" | "budget_up" | "pause" | "negative"
    delta_spend: float          # CAD; >0 spend-increasing, <=0 spend-decreasing
    marketplace: str = "CA"
    @property
    def is_spend_increasing(self) -> bool:
        return self.delta_spend > 0

@dataclass(frozen=True)
class GateRefusal:
    reason: str               # surfaced verbatim (GATE-04)
    code: str                 # "no_threshold_set" | "no_margin" | "sku_not_in_catalog" | "over_ceiling"
    breached_value: float | None = None
    ceiling: float | None = None
    source: str | None = None   # PREMIUM_SOURCE provenance

@dataclass(frozen=True)
class GateVerdict:
    projected_tacos: float | None
    ceiling: float | None
    contribution_margin: float | None
    auto_pass: bool = False     # True for spend-decreasing actions (D-06)
```
> **Why a sibling, not reuse `Refusal`:** `Refusal` lacks the `breached_value` / `ceiling` / `source` fields GATE-04 needs to "name the breached number and its source" (RESEARCH Alternatives). `ProposedAction` may live in `gate.py` instead — Claude's discretion (D-08).

---

### `engine/scripts/gate_action.py` (NEW — thin CLI)

**Analog:** `engine/scripts/answer_tacos.py` (read in full)

**Shebang + module-docstring + imports** (mirror lines 1-38): NO business logic in the script — `argv → gate.evaluate() inside logged_call → dataclasses.asdict → JSON stdout`. Reuse the same repo-root resolution:
```python
#!/usr/bin/env python3
from __future__ import annotations
import argparse, dataclasses, json, sys
from pathlib import Path
from habibos import logging as habibos_logging
from habibos.result import GateRefusal, GateVerdict, ProposedAction
from habibos import gate
REPO_ROOT = Path(__file__).resolve().parent.parent          # mirror answer_tacos.py line 37
DEFAULT_CATALOG = REPO_ROOT / "config" / "sku_catalog.toml" # gate reads the real catalog
```

**`_build_parser` shape to mirror** (lines 52-67): `--artifact`, `--export-id`, `--marketplace` (default CA), `--status`, plus the gate's `ProposedAction` fields (`--sku`, `--action-type`, `--delta-spend`) and `--catalog` (default the new `sku_catalog.toml`).

**The `logged_call` wrapper to mirror** (lines 97-127) — one-in/one-out, set `status`, never log the seller UUID:
```python
with habibos_logging.logged_call(
    "gate_action",
    source_id=gate.PREMIUM_SOURCE_ID,
    marketplace=args.marketplace,
) as end_fields:
    result = gate.evaluate(...)
    end_fields["status"] = "refused" if isinstance(result, GateRefusal) else "pass"
json.dump(dataclasses.asdict(result), sys.stdout)
sys.stdout.write("\n")
return 0
```
> `logging.configure()` is called once at the top of `main()` (answer_tacos.py line 79). `logged_call(op, **start_fields)` yields a mutable `end_fields` dict (logging.py line 43).

**The explicit-catalog discipline to imitate** (answer_tacos.py lines 84-95, comment lines 14-21): the catalog source is EXPLICIT and stated in output — never a silent export-rows fallback. For the gate this is stricter: a SKU absent from `sku_catalog.toml` is a **refusal** (D-05), not a labelled last-resort.

---

### `engine/config/sku_catalog.toml` (NEW — machine-readable catalog, D-04)

**Analog (format):** `engine/config/thresholds.toml` (TOML, keyed, typed, committed-numbers-are-policy header comment).
**Analog (source data):** the prose SKU table in `.claude/skills/anabtawi-context/SKILL.md` **lines 26-53** (the COGS authority: landed `cogs_total_value` from export b18aadfd).

**Per-row fields (D-04):** `sku`, `asin`, `tier`, `cogs` (landed). Store **only** these — per-SKU margin is computed live, **NOT** stored (D-04, Anti-Pattern). Suggested shape:
```toml
# Per-SKU catalog — the single machine-readable source of truth (D-04/D-05).
# The gate reads tier + cogs + the canonical SKU set; margin is computed LIVE (never stored).
# The prose table in .claude/skills/anabtawi-context/SKILL.md renders FROM this file (D-05).
[sku."T8-2W2X-INOK"]
asin = "B0FXX3JVR5"
tier = "HERO"
cogs = 26.77
```

**Reconciliation obligation (RESEARCH Runtime State):** reconcile three SKU sets into one file:
- prose table (26 detailed rows, lines 27-53) — COGS authority
- `engine/tests/fixtures/ca_catalog_skus.txt` (30 SKUs)
- The "inactive remnants" line 53 (`ZK-4NDS-MNA9 / OA-26MX-IHV0 / 5G-ZW6Q-WOZG / 9J-ASSK-BVKC / FO-SE3J-T74M`) have **no COGS** → under D-03/D-05 they correctly become **refusals on funding** (no COGS / unreliable). Either omit them or carry them with `cogs = 0` / absent so the gate refuses.

**Test-edge fixtures to also create** (RESEARCH Wave 0): a small `tests/fixtures/sku_catalog_*.toml` carrying (a) a SKU with `cogs = 0`, and (b) the absence of a SKU the test funds — to exercise the `no_margin` and `sku_not_in_catalog` refusals independently of the live catalog.

---

### `engine/config/thresholds.toml` (EDIT — seed the floor, D-07/D-07a)

**Analog:** the existing `[marketplace.CA]` block (lines 25-41, read in full).

**Current state (line 27):** `min_margin_pct = ""`. **Change:** rename to `min_net_margin_pct` and seed `= 15` (RESEARCH recommends rename-in-place over alias):
```toml
[marketplace.CA]
# Minimum acceptable net margin % the gate protects (D-07).
min_net_margin_pct = 15   # was min_margin_pct = "" — seeds the Phase 7 blocking precondition
```
**Also update the deprecated comment** (lines 22-23): the "Tier-aware ceilings (hero 35 / maintain 28 / cut 18) activate once the SKU→tier table is filled" line is **superseded by D-01a** — there is no per-tier ceiling table; the gate is one floor + per-SKU formula. Update or remove it (RESEARCH State of the Art).
> Keep `thresholds.read`'s refuse-on-empty contract intact (thresholds.py lines 19-31): an empty value still returns `None`. No code change to `thresholds.py` is needed — the gate calls `thresholds.read("min_net_margin_pct", mkt)`.

---

### `engine/tests/test_thresholds.py` (EDIT — the rename breaks an existing assertion)

**Analog:** itself — `test_missing_threshold_returns_none` (lines 28-34, read in full).

**Load-bearing breakage (RESEARCH Open Q2):** line 30 currently asserts `thresholds.read("min_margin_pct", "CA") is None`. Once the key is renamed to `min_net_margin_pct = 15`, this assertion must change — re-point it to a **still-empty** key (e.g. `days_of_cover_floor`, which is `""` on line 38) so the empty-refusal path stays covered:
```python
def test_missing_threshold_returns_none() -> None:
    assert thresholds.read("days_of_cover_floor", "CA") is None   # was min_margin_pct (now seeded)
    assert thresholds.read("a_key_that_does_not_exist", "CA") is None
    assert thresholds.read("acos_ceiling_pct", "ZZ") is None
```
Optionally add `assert thresholds.read("min_net_margin_pct", "CA") == 15.0` to lock the seeded floor.

---

### `engine/tests/test_gate.py` (NEW — the mandatory pytest contract)

**Analog:** `engine/tests/test_tacos.py` (read in full — the fixture-driven structure to mirror)

**Fixture wiring to clone** (test_tacos.py lines 31-48): reuse the **same committed fixture** `tests/fixtures/profit_by_sku_30d.csv` (header confirmed: `sku,currency,ad_spend_sum,ad_sales_sum,total_sales_sum,profit_sum,total_cost_sum,units_sum`), the same `REPO_ROOT` / `FIXTURE` resolution, the same named-SKU constants, and a local `_pct`-style helper for building expected values from the fixture sums:
```python
REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "profit_by_sku_30d.csv"
def _frame() -> pl.DataFrame:
    return parse(FIXTURE, "COMPLETED")
```

**The D-03 arithmetic assertion to imitate** (test_tacos.py lines 60-67 spot-check the operator-signed-off live numbers). For the gate, assert the pre-ad back-out on the same fixture rows RESEARCH proved:
- `EU-Z87B-ZRBZ`: CM% = (100.27 + 0.50) / 279.95 × 100 = **36.0%** → ceiling = 36.0 − 15 = **21.0%**
- `9Z-KUHZ-FU2I`: `total_sales_sum == 0` → CM% `None` → `no_margin` refusal (Pitfall 4)

**Test functions to write** (RESEARCH Phase Requirements → Test Map — names are the contract):
| Test fn | Requirement |
|---------|-------------|
| `test_contribution_margin_pre_ad` | GATE-01 — CM% from window sums, ad_spend added back |
| `test_profit_is_post_ad_addback` | D-03 — back-out matches fixture arithmetic (EU-Z87B / 9Z) |
| `test_ceiling_and_unset_floor_refuses` | GATE-02 — ceiling = CM−floor; floor `""` → `no_threshold_set` on every write (SC-2) via monkeypatch/temp config |
| `test_spend_direction_branch` | GATE-03 — increasing: ≤ceiling passes, >ceiling refuses; decreasing auto-passes |
| `test_breach_refuses_never_clamps` | GATE-04 — `GateRefusal` names `breached_value`+`source`, never a clamped value |
| `test_sku_not_in_catalog_refuses` | GATE-05 — SKU ∉ catalog → `sku_not_in_catalog` |
| `test_unreliable_cogs_refuses` | D-04 — `cogs` 0/null → `no_margin` |

**The unset-floor test pattern to imitate** (test_tacos.py lines 131-136 exercise the `None`-ceiling path via `marketplace="XX"`). The gate's SC-2 empty-floor refusal can use the same trick (a marketplace with no floor) OR a monkeypatch/temp-config override — independent of the seeded live `min_net_margin_pct = 15`.

---

## Shared Patterns

### Anti-fabrication: refuse-never-default / refuse-never-clamp
**Source:** `engine/src/habibos/result.py` (docstring lines 1-8) + `tacos._present_flag` (lines 118-124) + `thresholds.read` (lines 19-31).
**Apply to:** every missing-input and over-ceiling path in `gate.py`.
Every no-data / unset-threshold / missing-SKU / over-ceiling edge returns a typed `GateRefusal` — never a bare `None`, a fabricated 0, a guessed margin, or a clamped ceiling. The strict `value > ceiling` comparison (equal is OK) is the exact breach grammar.

### Window-sum read (A1) — reuse, don't re-roll
**Source:** `engine/src/habibos/tacos.py` `parse()` + `_PremiumRow` + `EXPECTED_COLUMNS` (lines 50-104).
**Apply to:** `gate.py` (import `parse`) and `test_gate.py` (call `parse(FIXTURE, "COMPLETED")`).
Margins/ratios are computed from server-side `groupBy sku` + `*_sum` components applying verbatim definitions — never re-deriving a metric, never averaging a daily ratio. pydantic `extra="ignore"` tolerates `units_sum`; a missing REQUIRED column raises (fail-loud, Pitfall 3).

### Threshold read (refuse-on-empty)
**Source:** `engine/src/habibos/thresholds.py` `read(key, marketplace)` (lines 19-31).
**Apply to:** the floor read in `gate.py`: `thresholds.read("min_net_margin_pct", marketplace)` → `None` → `GateRefusal("no threshold set")`. No change to `thresholds.py`.

### Thin-CLI wiring (no business logic in scripts) + structured logging
**Source:** `engine/scripts/answer_tacos.py` (lines 77-128) + `habibos.logging.logged_call` / `configure` (logging.py lines 29, 43).
**Apply to:** `gate_action.py` — `argv → gate.evaluate() inside logged_call → dataclasses.asdict → JSON stdout`. One-in/one-out logging; NEVER log the seller UUID; the gate reads no secret.

### Typed positive result (never a bare True)
**Source:** `engine/src/habibos/result.py` `Proceed` (lines 35-46), `Answer` (lines 82-95).
**Apply to:** `GateVerdict` — a PASS is a typed object carrying `projected_tacos` / `ceiling` / `contribution_margin` / `auto_pass`, never `True`.

---

## No Analog Found

None. Every file has a direct in-repo analog (the explicit design intent of this phase: the gate is the deliberate `tacos.py` twin). Genuinely-new logic (CM%→ceiling formula, projected-TACOS-with-Δspend, spend-direction branch, catalog reader, two dataclasses) is small and composed from the patterns above; RESEARCH §Code Examples gives the exact function bodies to use.

## Metadata

**Analog search scope:** `engine/src/habibos/` (gate.py, tacos.py, result.py, thresholds.py, logging.py), `engine/scripts/` (answer_tacos.py), `engine/config/` (thresholds.toml), `engine/tests/` (test_tacos.py, test_thresholds.py, fixtures/profit_by_sku_30d.csv), `.claude/skills/anabtawi-context/SKILL.md`.
**Files scanned:** 10 (8 read in full; fixture header + logging signatures via grep).
**Pattern extraction date:** 2026-06-21
