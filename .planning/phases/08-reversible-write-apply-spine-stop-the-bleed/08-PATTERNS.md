# Phase 8: Reversible-Write Apply Spine + Stop-the-Bleed - Pattern Map

**Mapped:** 2026-06-22
**Files analyzed:** 11 new/extended (3 src modules + 1 src extend + 1 CLI + 1 config + 4 tests + 1 ledger data file + fixtures)
**Analogs found:** 11 / 11 (every new file has a direct in-repo analog — Phase 8 is ~80% wiring of proven substrate)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `engine/src/habibos/apply.py` (NEW) | service (the spine) | request-response → event-driven (poll loop) | `engine/src/habibos/gate.py` (`evaluate` branch-order) + `lifecycle.py` (classify_dryrun/classify_poll it drives) | exact (orchestration twin of `gate.evaluate`) |
| `engine/src/habibos/ledger.py` (NEW) | store (idempotency) | file-I/O (jsonl append + scan), content-hash | `engine/src/habibos/find_cache.py` (`data/*.json` write/lookup-or-refuse) + `logging.py` (jsonl append seam) | role-match (file-backed lookup-or-refuse) |
| `engine/src/habibos/denylist.py` (NEW) | middleware (pre-dryRun refuse-gate) | request-response (typed in → None\|GateRefusal) | `engine/src/habibos/gate.py` (`evaluate` spend-decrease branch + `_load_catalog` tomllib read) | exact (a sibling pre-dryRun gate) |
| magnitude-cap (function in `apply.py` or `magnitude.py`) | middleware (seeded-permissive gate) | request-response (action+cfg → None\|GateRefusal) | `gate.py` ceiling logic + `thresholds.read` None-means-permissive | exact (build-refusal-seed-live, mirrors 07 D-07) |
| `engine/src/habibos/result.py` (EXTEND) | model (typed grammar) | data | `result.py` `ProposedAction` / `GateRefusal` / `Proceed` (add fields + `AppliedResult` + codes) | exact (extend in place) |
| `engine/scripts/apply_action.py` (NEW) | route (thin CLI) | request-response (argv → evaluate → JSON) | `engine/scripts/gate_action.py` (argv→`evaluate`→`asdict`→stdout, `logged_call`-wrapped) | exact |
| `engine/config/owned_asins.toml` OR extended `sku_catalog.toml` (NEW config source) | config | file-I/O (tomllib read) | `engine/config/sku_catalog.toml` (`[sku."…"]` rows) + `thresholds.toml` (`[marketplace.CA]` dial) | exact (structure clone) |
| `engine/tests/test_apply.py` (NEW) | test | unit (mocked agent responses via fixtures) | `engine/tests/test_gate.py` + `test_lifecycle.py` (RED→GREEN, fixture-anchored) | exact |
| `engine/tests/test_ledger.py` (NEW) | test | unit (tmp_path-monkeypatched DATA_DIR) | `engine/tests/test_find_cache.py` (monkeypatch DATA_DIR → tmp_path) | exact |
| `engine/tests/test_denylist.py` (NEW) | test | unit | `engine/tests/test_gate.py` (catalog-fixture refusal assertions) | exact |
| `data/actions_ledger.jsonl` (NEW data) | store artifact | append-only jsonl | `logs/external-calls.jsonl` (append-only) + `data/ads_*_find_*.json` (data/ convention) | exact |
| decisions.md / brain log seam (function in `apply.py`) | utility (log seam) | file-I/O (append a line + write a note) | `engine/scripts/inbox.py` `_log_decision` (`DECISIONS.open("a")`) | exact |

## Pattern Assignments

### `engine/src/habibos/apply.py` (service, the spine)

**Analogs:** `gate.py` (branch-order, refuse-or-proceed at every step) + `lifecycle.py` (the classifiers it drives) + `datadoe.py` (the poll primitive).

**Branch-order / short-circuit discipline to replicate** — `gate.evaluate` returns the first refusal and never falls through (`gate.py:147-238`). The spine threads denylist → margin gate → magnitude cap → ledger lookup → FIND → dryRun → apply → poll → echo → log, short-circuiting on the first `Refusal`/`GateRefusal`. The agent supplies MCP-call results (dryRun resp, actionId, poll responses, echo); **Python never opens a socket** (the seam — `datadoe.py:1-14`, `find_cache.py:18-23`).

**Reuse: spend-down auto-passes the margin gate with NO config read** (`gate.py:150-156`):
```python
if not action.is_spend_increasing:           # delta_spend <= 0  (pause/negative/bid-down)
    return GateVerdict(projected_tacos=None, ceiling=None,
                       contribution_margin=None, auto_pass=True)
```
The spine sets `delta_spend = 0` (or a negative estimate) for pause/negative/bid-down so `is_spend_increasing` is False and `gate.evaluate` auto-passes (Open Q3). The spine, not the operator, sets the sign for reversible actions.

**Reuse: drive the Phase-6 poll primitive to terminal** (`datadoe.py:65-82`) — do NOT rewrite the loop:
```python
@retry(stop=stop_after_attempt(20),
       wait=wait_exponential_jitter(initial=1, max=15),
       retry=retry_if_result(_action_not_terminal))
def poll_action_status(get_status) -> str:
    return get_status()
```
The spine calls `datadoe.poll_action_status(get_status)` where `get_status` is a zero-arg callable the agent re-invokes (`actions_get(actionId)`); each response → `lifecycle.classify_poll` for the typed `PollOutcome`. After 20 attempts without terminal → surface `unresolved_in_flight` carrying the `actionId` (resumable, D-10) — never assume success. Terminal sets are pinned in `datadoe.py:54-58` (note: **no `FAILED`** — it is `ERROR`; `CANCELED` has one L).

**Reuse: the dryRun PROCEED gate before the real run** (`lifecycle.py:86-109`) — call `classify_dryrun(resp)`; a `Refusal(code="dryrun_invalid")` short-circuits before any `dryRun:false` fires.

**Reuse: FIND-before-write + FIND-echo** (`find_cache.py:111-138`) — `find_cache.lookup(entity_type, ad_product, entity_id)` gates the build (MISS → `Refusal("…","find_cache_miss")` STOP); after apply, re-`lookup`/`write` and compare for the echo confirm.

**Error handling pattern** — every edge is a typed `Refusal`/`GateRefusal`, never a bare `None`/`raise` (`result.py:26-33, 84-105`). New codes this phase needs: `own_asin_denied`, `over_cap`, `stale_find_cache`, `canary_unconfirmed`, `action_type_disabled`, `unresolved_in_flight` (plus reuse of `dryrun_invalid`, `action_error`, `unknown_status`, `find_cache_miss`).

---

### `engine/src/habibos/ledger.py` (store, idempotency content-hash)

**Analogs:** `find_cache.py` (the `data/` read/write + lookup-or-refuse pattern) + `logging.py` (the jsonl append seam).

**DATA_DIR pattern to replicate** (`find_cache.py:39-41`) — repo-root-relative, monkeypatched in tests:
```python
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
```
Ledger lives at `DATA_DIR / "actions_ledger.jsonl"`. Mirror `find_cache`'s newest-wins scan (`find_cache.py:128`) but append-only over jsonl lines (one JSON object per line).

**jsonl append seam to replicate** (`logging.py:26, 31-39`) — append-only, never edit past lines (mirrors `state/decisions.md` discipline and `logs/external-calls.jsonl`):
```python
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
# ... WriteLoggerFactory(file=LOG_PATH.open("a", encoding="utf-8"))
```

**Content-hash identity (NEW, D-10)** — `sha256` over canonical JSON of `{entity_type, entity_id, action_type, normalized_params}`, **NOT date**:
```python
import hashlib, json
def action_hash(entity_type, entity_id, action_type, params) -> str:
    canonical = json.dumps(
        {"entity_type": entity_type, "entity_id": entity_id,
         "action_type": action_type, "normalized_params": params},
        sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(canonical.encode()).hexdigest()
```
Normalize: lowercase + strip keyword text; round bids to 2 dp; sort dict keys before hashing (document in the module docstring — it is load-bearing). Lookup semantics: COMPLETED hash → no-op (`LedgerHit`); in-flight hash → resume at poll on its `action_id`, never re-fire start; no entry → proceed.

---

### `engine/src/habibos/denylist.py` (middleware, own-ASIN refuse-gate)

**Analogs:** `gate.py` (the pre-dryRun refuse-gate beside the margin gate) + `gate._load_catalog` (the tomllib read).

**tomllib catalog read to replicate** (`gate.py:104-113`) — explicit source, missing file raises (no silent fallback):
```python
def _load_catalog(catalog_path: str | Path) -> dict:
    with Path(catalog_path).open("rb") as fh:
        data = tomllib.load(fh)
    return data.get("sku", {})
```
The denylist reads the `asin` value from every `[sku."…"]` row (D-06). **Open issue flagged in RESEARCH Q4:** `sku_catalog.toml` has 16 COGS-gated ASINs; B07TV972JT and the full ~30-ASIN owned set are NOT all present. The planner must resolve whether the owned set comes from `sku_catalog.toml` or a broader dedicated `owned_asins.toml` — the denylist owned-set source may need to be a superset of the gate's catalog. **This is the single most important pre-plan clarification.**

**Refuse pattern to replicate** (`gate.py:174-179`) — a hard `GateRefusal`, never warn-and-confirm:
```python
return GateRefusal("SKU not in catalog table", code="sku_not_in_catalog")
# Phase 8 denylist analog:
# return GateRefusal("payload targets an owned ASIN", code="own_asin_denied", source=...)
```
Extraction challenge (RESEARCH Pattern 4 / A7): a pause/bid-down carries no target ASIN → pass cleanly; the denylist's real job is refusing an ADD/targeting write whose target value is an owned ASIN. Pin the extraction field (`expression`/`value`) against `actions_details_schema_get`.

---

### magnitude-cap mechanism (middleware, seeded permissive — function in `apply.py` or `magnitude.py`)

**Analogs:** `gate.py` strict-breach ceiling logic (`gate.py:226-233`) + `thresholds.read` None-means-refuse (`thresholds.py:19-31`).

**Strict-breach-never-clamp to replicate** (`gate.py:226-233`):
```python
if projected > ceiling:  # STRICT: equal passes
    return GateRefusal("…breaches the SKU's margin-derived ceiling",
                       code="over_ceiling", breached_value=projected,
                       ceiling=ceiling, source=PREMIUM_SOURCE)
```
The cap refuses (typed `GateRefusal(code="over_cap")`), **never clamps** to the limit (mirror GATE-04).

**Seeded-permissive dial to replicate** (`thresholds.py:19-31` + `thresholds.toml:30-47`) — build the refusal path, seed the live value permissive (07 D-07 pattern, D-02): a `thresholds.read("max_reversible_pct_change", mkt)` returning `None` (absent/empty) means **permissive** (pass at any magnitude), not refuse — so the mechanism exists + is tested while live behavior matches D-01. Tightening later is a config edit, not code. Document the dial in `thresholds.toml` as a commented, absent-by-default key (mirror the empty `days_of_cover_floor = ""` convention at `thresholds.toml:44`).

---

### `engine/src/habibos/result.py` (model, EXTEND in place)

**Analog:** `result.py` itself — extend, don't fork.

**`ProposedAction` extension** (`result.py:64-81`) — ADD optional fields with defaults so the Phase-7 gate CLI contract (`test_gate_action.py`) stays green (the gate ignores them; only the spine reads them):
```python
@dataclass(frozen=True)
class ProposedAction:
    sku: str
    action_type: str
    delta_spend: float
    marketplace: str = "CA"
    # NEW (Phase 8 — defaults so gate CLI unaffected):
    entity_type: str | None = None      # "campaigns" | "targets" | …
    entity_id: str | None = None        # the FIND-verified campaignId/targetId
    params: dict = field(default_factory=dict)
```
Add an `AppliedResult` dataclass (frozen, like `GateVerdict` at `result.py:107-119`) carrying `action_id`, terminal `status`, `hash`, applied-at, marketplace — the spine's typed positive counterpart. Reuse `GateRefusal` (`result.py:84-105`) for the new denylist/cap codes.

---

### `engine/scripts/apply_action.py` (route, thin CLI)

**Analog:** `engine/scripts/gate_action.py` — the THIN argv→evaluate→JSON template (no business logic).

**CLI contract shape to replicate** (`gate_action.py:72-102`):
```python
def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    habibos_logging.configure()
    action = ProposedAction(sku=args.sku, action_type=args.action_type,
                            delta_spend=args.delta_spend, marketplace=args.marketplace)
    with habibos_logging.logged_call("apply_action", marketplace=args.marketplace) as end_fields:
        result = apply.apply(action, ...)        # the spine
        end_fields["status"] = "refused" if isinstance(result, (Refusal, GateRefusal)) else "applied"
    json.dump(dataclasses.asdict(result), sys.stdout); sys.stdout.write("\n")
    return 0
```
`end_fields["status"]` is set from `isinstance(result, (Refusal, GateRefusal))` so a refusal can NEVER serialize as a pass (T-07-11). Repo-root-relative default paths (`gate_action.py:40-42`). Add the canary `--confirm-canary` flag (RESEARCH Pattern 5): marker absent + flag not passed → `canary_unconfirmed` refusal; flag passed → proceed then write marker; marker present → auto-apply (D-08/D-09).

---

### `engine/config/owned_asins.toml` (config — NEW source, planner-decided) / extended `sku_catalog.toml`

**Analogs:** `sku_catalog.toml` (the `[sku."…"]` row structure + the "missing → refuse, never invent" header discipline at `sku_catalog.toml:30-43`) + `thresholds.toml` (the `[marketplace.CA]` dial + commented-empty-key convention at `thresholds.toml:30-47`).

If a separate owned-ASIN source is chosen, clone `sku_catalog.toml`'s header rules verbatim (never invent an ASIN; absent = surfaced refusal). The magnitude-cap dial (`max_reversible_pct_change`) is added to `thresholds.toml` under `[marketplace.CA]`, seeded absent (permissive).

---

### Tests: `test_apply.py` / `test_ledger.py` / `test_denylist.py`

**Analogs:** `test_gate.py` (RED-baseline docstring, fixture-anchored refusal assertions, real-SKU edge selection) + `test_find_cache.py` (the `monkeypatch DATA_DIR → tmp_path` fixture) + `test_gate_action.py` (CLI `main([...])` + capsys JSON contract).

**RED-on-import baseline to replicate** (`test_gate.py:40-43`, `test_find_cache.py:24-25`):
```python
from habibos import apply   # RED until the module exists — intended Wave 0 state
from habibos.result import GateRefusal, ProposedAction, Refusal
```

**tmp_path monkeypatch for the ledger** (`test_find_cache.py:31-35`):
```python
@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(ledger, "DATA_DIR", tmp_path)   # no real data/ writes
    return tmp_path
```

**Refusal-shape assertion style** (`test_find_cache.py:57-64`):
```python
miss = ledger.lookup(...)
assert isinstance(miss, Refusal)
assert miss.code == "..."   # e.g. own_asin_denied / over_cap / find_cache_miss
```

**CLI JSON contract style for `apply_action`** (`test_gate_action.py:40-60`) — invoke `apply_action.main([...])`, parse `capsys.readouterr().out` as JSON, assert `code`/`status`/`auto_pass` fields.

Fixtures to add under `engine/tests/fixtures/` (mirror `actions_get_completed.json` / `dryrun_validated.json` style — sanitized, **no seller UUID**): `actions_start_dryrun_pause.json`, negative-create dryRun, bid-down dryRun, `*_FIND` echo, a seed `actions_ledger.jsonl`. **These payload fixtures must be captured from a live `actions_details_schema_get` + `dryRun:true` Wave-0 round-trip — NOT fabricated** (RESEARCH Pitfall 1, A1-A3).

---

## Shared Patterns

### Typed refuse-never-default / never-clamp grammar
**Source:** `engine/src/habibos/result.py:26-33` (`Refusal`), `84-105` (`GateRefusal`)
**Apply to:** denylist, magnitude cap, ledger, apply spine — every no-data/over-limit/missing edge.
```python
@dataclass(frozen=True)
class GateRefusal:
    reason: str          # surfaced verbatim to the operator
    code: str
    breached_value: float | None = None
    ceiling: float | None = None
    source: str | None = None
```

### The logged-call seam (one .start / one .end, no seller UUID)
**Source:** `engine/src/habibos/logging.py:42-67`; usage at `lifecycle.py:155-159`
**Apply to:** every `actions_start` / `actions_get` / `*_FIND` op in the spine + the `apply_action` CLI.
```python
habibos_logging.configure()
with habibos_logging.logged_call("actions_get") as end_fields:
    result = classify_poll(resp)
    end_fields["status"] = "refused" if isinstance(result, Refusal) else result.state
```
NEVER pass `$AMAZON_CA_SELLER_ID` (or any secret) into the log fields (CLAUDE.md hard rule 5).

### The seam: Python never opens a socket
**Source:** `engine/src/habibos/datadoe.py:1-14`, `find_cache.py:18-23`
**Apply to:** apply spine + ledger + denylist. The agent makes every MCP call; the modules import no HTTP/socket library and handle only agent-handed responses + LOCAL file I/O.

### decisions.md log line append (D-11)
**Source:** `engine/scripts/inbox.py:98-105`
**Apply to:** the spine's log seam — append one dated pipe-delimited line per applied write.
```python
def _log_decision(it, result):
    line = (f"{_today()} | {it['domain']} | {it.get('sku') or '-'} | "
            f"{it.get('current') or '-'} → {it.get('proposed') or it['title']} | "
            f"{it['why']} | {it.get('impact_cad') or '-'} | {result}")
    with DECISIONS.open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")
```
Phase 8 line shape (RESEARCH:417): `YYYY-MM-DD | ppc | [SKW] … (CMP-…) | Paused whole campaign via apply spine (actionId ACT-…) | dead FX-M8MA, $8.83/0 orders t90 | stops ~$9/mo | COMPLETED`. Plus one `brain/raw/` note (what/why/effect/actionId). Standing-approved auto actions log too — autonomy ≠ silence.

### tomllib config read, missing → refuse / permissive
**Source:** `engine/src/habibos/thresholds.py:19-31` (read), `gate.py:104-113` (`_load_catalog`)
**Apply to:** denylist owned-set read + magnitude-cap dial read. Missing key → `None`; for the gate floor that means `no_threshold_set` refusal, for the magnitude cap (D-02) `None` means **permissive** by deliberate operator choice (document the asymmetry).

## No Analog Found

None. Every Phase-8 new file maps to a concrete in-repo analog. The only genuinely-new code (ledger hash, denylist ASIN extraction, seeded-permissive cap, canary marker) still reuses the established `Refusal`/`GateRefusal`/`logged_call`/tomllib grammar above.

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| (none) | — | — | Full analog coverage. |

## Metadata

**Analog search scope:** `engine/src/habibos/` (gate, result, lifecycle, find_cache, logging, datadoe, thresholds), `engine/scripts/` (gate_action, inbox), `engine/config/` (sku_catalog.toml, thresholds.toml), `engine/tests/` (test_gate, test_find_cache, test_gate_action), `engine/tests/fixtures/`.
**Files scanned:** 14 read directly.
**Pattern extraction date:** 2026-06-22
**Unresolved (flag to planner):** owned-ASIN config source (RESEARCH Q4 — `sku_catalog.toml` 16 ASINs vs the ~30-ASIN owned set incl. B07TV972JT); DataDoe payload schemas per action type (pin via `actions_details_schema_get` + `dryRun:true` in a Wave-0 recon task — fixtures must NOT be fabricated).
