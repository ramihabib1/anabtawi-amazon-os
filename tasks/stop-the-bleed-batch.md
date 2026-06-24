# Task: Stop-the-Bleed Batch  (schedule: one-shot, on Rami's go — the first real reversible writes)

Act as the orchestrator coordinating **ppc-manager**. This runbook applies the FIRST real
`dryRun:false` writes this account has ever taken. It pauses the 4 dead/exiting SKUs that hold
~43% of ad spend (~$279/mo) at ~$0 sales loss, then harvests exact-match negatives — all gated
behind a one-time canary. **Load the `datadoe-query` skill before any DataDoe call.**

Golden rule (CLAUDE.md hard rule 1/2): no write fires silently. Every applied move is logged to
`state/decisions.md` + `brain/raw/` with its `actionId`. The seller UUID
(`$AMAZON_CA_SELLER_ID`) is **NEVER** inlined in any logged line, decisions entry, brain note,
or fixture (CLAUDE.md hard rule 5) — it goes only into the live `actions_start` payload the MCP
sends, never to disk.

---

## The 4 dead SKUs this batch pauses (EXEC-01)

| SKU | ASIN | Why it's dead | In sku_catalog? |
|-----|------|---------------|-----------------|
| **FX-M8MA**-MMSA | B0FTSM2HSJ | Baklava 180g DUP — EXIT ("pause ads") | yes |
| **9Z-KUHZ**-FU2I | B0FTSMTDGP | Baklava 400g DUP — EXIT ("stop ads") | yes |
| **VH-ZTOC**-GW1Q | B0FTM5PBZW | Maamoul Pistachio 550g — EXIT | **no** |
| **ZK-4NDS**-MNA9 | (none) | inactive remnant, no ASIN/COGS | **no** |

**Campaign identity for ALL FOUR comes from a live `*_FIND`, never from `sku_catalog.toml`.**
Only 2 of the 4 are in the catalog (VH-ZTOC and ZK-4NDS are absent), and a pause is
spend-**decreasing** so the margin gate auto-passes with **no catalog read** (RESEARCH Pitfall 5,
07 D-06). Do **not** route dead-SKU identity through `sku_catalog.toml`.

**keep-positive allowlist (D-04):** `baklava gift box` is a converting term — it is **NEVER
negated** in this batch. The harvest must skip it on every campaign.

---

## STEP 0 — PRECONDITION: the org-enable gate (do not skip; do not retry a 412)

The DataDoe **Settings → Actions** org-enable for the three reversible action types is a 4th
access-control gate beyond our own approval, **OFF by default** (`brain/raw/2026-06-20_datadoe-write-path-gating.md`).
The BUILD + `dryRun:true` paths work without it; the real apply does **not**.

- Confirm Rami has flipped on: **campaign-state update (pause)** = `AMAZON_ADS_CAMPAIGNS_UPDATE`,
  **negative-keyword create (exact)** = `AMAZON_ADS_TARGETS_ADD`, and **target-state update
  (bid-down)** = `AMAZON_ADS_TARGETS_UPDATE`. `CAMPAIGNS_ADD` / `CAMPAIGNS_REMOVE` stay **OFF**
  (Phase 10). This is **Task 2 of plan 08-04** — a blocking human checkpoint. Do not proceed
  until Rami replies "enabled".
- If a real `actions_start dryRun:false` returns **412 → `action_type_disabled`**, the switch is
  not on. **Do NOT retry** — surface it and stop (`datadoe-query` SKILL line 192). A `dryRun:true`
  validates regardless; only the real write reveals the disabled state.

---

## STEP 1 — FIND the live campaigns (identity from FIND, cached — never the catalog)

For **each** of the 4 dead SKUs:

1. Run the matching `*_FIND` (`AMAZON_ADS_CAMPAIGNS_FIND`, `adProductFilter.include` =
   `SPONSORED_PRODUCTS`, `maxItems:1` — one ad-product per FIND) to get the live `campaignId`(s)
   for that SKU/ASIN. Repeat per ad-product if the SKU also has SB/SD.
2. Hand the FIND response to the cache: `engine/src/habibos/find_cache.py` `write()` persists it
   to `data/ads_campaigns_SPONSORED_PRODUCTS_find_{date}.json`. Every later pause reads its
   `campaignId` from this cache — a write whose entity ID is **not** in the cache is **refused at
   build** (`find_cache_miss`), never executed on a fabricated or stale ID (WRITE-02).
3. The FIND result is the only source of `campaignId`. **Never read `sku_catalog.toml` for
   dead-SKU identity.**

Identity from FIND also seeds the post-write **FIND-echo** (STEP 4): pause confirm field is the
campaign's `state` flipping to `"PAUSED"`.

---

## STEP 2 — CANARY: ONE pause, end-to-end, with the one-time `--confirm-canary` (D-08/D-09)

The phase's **first** apply is a canary — exactly ONE reversible write — to prove the spine
end-to-end before the batch. Pick **one** dead-SKU campaign (e.g. FX-M8MA's SP campaign).

Run the full spine the agent way: make the 4 MCP calls and hand the downloaded JSON to the CLI.

1. `actions_start dryRun:true` (pause payload — see SCHEMA below) → download response →
   PROCEED only when `status:"VALIDATED"`, `validation.valid:true`, `issues:[]`
   (`classify_dryrun.py` owns the verdict, never chat).
2. `actions_start dryRun:false` (the real write) → download response. A 412 here = STEP 0 not
   cleared; stop.
3. `actions_get(actionId)` → poll to a terminal status; download the latest response.
4. `AMAZON_ADS_CAMPAIGNS_FIND` echo → download; confirms the campaign now reads `state:"PAUSED"`.

Then thread them through the apply CLI **with the one-time flag**:

```
cd engine && uv run python scripts/apply_action.py \
  --sku FX-M8MA-MMSA --action-type pause --delta-spend -9.30 --marketplace CA \
  --entity-type campaigns --entity-id <campaignId-from-FIND-cache> \
  --params '{"state":"PAUSED"}' \
  --dryrun-resp data/<canary_dryrun>.json --apply-resp data/<canary_apply>.json \
  --status-resp data/<canary_status>.json --find-echo data/<canary_find>.json \
  --owned config/owned_asins.toml \
  --confirm-canary
```

- `--confirm-canary` is the **one-time** gate for the **first apply of the phase** (D-09), not
  per-action. The CLI writes the marker `data/phase8_canary_confirmed` only **after** a success;
  once present, every subsequent reversible move auto-applies **without** the flag. Omit the flag
  on the first apply and the result is a `canary_unconfirmed` refusal — by design.
- Verify the canary reconciled: `actions_get` reached **COMPLETED** **and** the FIND echo shows
  `state:"PAUSED"`. A disagreement → `find_echo_mismatch`, never recorded as applied.
- **Log the canary** (D-11): append a dated line to `state/decisions.md` and a note to
  `brain/raw/2026-06-23_stop-the-bleed-batch.md` — what changed, why, expected effect, and the
  `actionId`. No seller UUID in either.

**Do not run STEP 3 until the canary reconciles COMPLETED.**

---

## STEP 3 — BATCH: the standing-approved stop-the-bleed (only after the canary clears)

Under D-01's **standing-approved permissive auto-apply** for reversible actions (no per-action
confirm after the canary), run as **one batch**:

### 3a. Pause the remaining whole campaigns (D-03 / D-05)

For the other dead-SKU campaigns (every campaign across the 4 SKUs not already paused by the
canary): pause the **WHOLE campaign**, not just keywords/targets. Whole-campaign pause is the
cleanest fully-reversible stop and leaves **no empty ENABLED shell** that re-accrues spend (D-05).
Each pause runs the full spine via `apply_action.py` (`--action-type pause`,
`--params '{"state":"PAUSED"}'`, `--delta-spend <=0`), identity from the FIND cache — **no
`--confirm-canary`** (marker already set).

### 3b. Exact-match negative-keyword harvest (D-04)

Per campaign, harvest the wasted search terms as **exact-match negatives only**:

- **Exact by default.** `targetDetails.keywordTarget.matchType:"EXACT"`, `negative:true`.
  **NO phrase, NO broad** negatives in this batch.
- **keep-positive allowlist:** `baklava gift box` is **NEVER negated** — skip it on every
  campaign, no exception.
- **"watch-don't-negate" terms → BID-DOWN, not negated.** A term that is borderline (some signal,
  not pure waste) is lowered via `AMAZON_ADS_TARGETS_UPDATE` (`--action-type bid_down`,
  `--params '{"bid":<new_lower_bid>}'` on its `targetId`), **never** added as a negative.
- Each negative runs the spine via `apply_action.py` (`--action-type negative`, `--entity-type
  targets`, attached at **ad-group** level via `adGroupId` per the SCHEMA), identity from FIND.

Run 3a + 3b as one batch. Each move STILL logs (D-11 — autonomy ≠ silence): a `decisions.md`
line + a `brain/raw/2026-06-23_stop-the-bleed-batch.md` note with the `actionId`, no seller UUID.

**Idempotency is automatic.** The ledger (`data/actions_ledger.jsonl`) no-ops a re-run: two
moves are "the same" when the content hash over {entity type + entity ID + action type +
normalized params} matches a COMPLETED entry; an in-flight `actionId` **resumes at poll**, never
re-fires `actions_start` (D-10). Re-running this whole runbook re-pauses nothing — every move
short-circuits.

---

## STEP 4 — RECONCILE: via `actions_get` COMPLETED + a `*_FIND` echo, NEVER an export

Confirm **every** pause and negative the same way (WRITE-05):

1. `actions_get(actionId)` reached a terminal **COMPLETED** (not `FAILED` — there is no `FAILED`;
   `CANCELED` is one L). In-flight = `PENDING`/`IN_PROGRESS`/`WAITING_EXTERNAL_PROCESSING`; keep
   polling. (`classify_poll.py` owns the verdict.)
2. A `*_FIND` **echo** of the changed entity confirms it: pause → campaign `state:"PAUSED"`;
   negative → the target exists with `negative:true` + the matching `keywordTarget`; bid-down →
   the FIND echoes bid as `{ "bid": 0.49, "currencyCode": "CAD" }`, so read **`.bid.bid`** and
   confirm it equals the new lower bid.

**NEVER reconcile via a next-day DataDoe export.** The analytics tables lag up to ~24h, so an
export cannot confirm a just-applied write (WRITE-05, `datadoe-query` SKILL line 187–189).
The FIND echo is the confirmation; the export is not.

---

## STEP 5 — STOP for Rami's spot-check (human verify — Task 3 of plan 08-04)

Do **not** auto-advance. Surface for Rami:
- The 4 dead-SKU campaigns are **paused** in Amazon Campaign Manager (~$279/mo, ~43% spend off).
- `baklava gift box` was **never negated**; healthy MAINTAIN-tier SKUs untouched.
- Every move reconciled (COMPLETED + FIND echo) and logged with its `actionId`.
- `data/actions_ledger.jsonl` has one COMPLETED record per applied move; re-running any move is a
  no-op.
- No seller UUID appears in `decisions.md`, the brain note, or `logs/external-calls.jsonl`.

---

## Pinned payload schemas (08-SCHEMA-PIN — the source of truth; never fabricate)

**Envelope (all types):** `actions_start` needs `type`, `sellerOrVendorId` (the UUID — sent in
the live MCP payload **only**, never to disk), `details`, `dryRun`. A clean validate returns
top-level `status:"VALIDATED"` + nested `validation:{valid:true, issues:[]}`.

**1. Pause a campaign — `AMAZON_ADS_CAMPAIGNS_UPDATE`**
```json
{ "campaigns": [ { "campaignId": "<id>", "state": "PAUSED" } ] }
```
Send ONLY the mutable fields (`campaignId` + `state`). **Do NOT echo `adProduct`** — the live
validator rejects it on `CAMPAIGNS_UPDATE`. Normalized ledger params: `{ "state": "PAUSED" }`.

**2. Add an exact-match negative — `AMAZON_ADS_TARGETS_ADD`**
```json
{ "targets": [ {
  "campaignId": "<id>", "adGroupId": "<id>",
  "adProduct": "SPONSORED_PRODUCTS",
  "state": "ENABLED", "negative": true,
  "targetType": "KEYWORD",
  "targetDetails": { "keywordTarget": { "keyword": "<text>", "matchType": "EXACT" } }
} ] }
```
`negative:true` is what makes it a negative (there is **no** `NEGATIVE_EXACT` literal). `matchType`
lives nested under `keywordTarget`. `state:"ENABLED"` is REQUIRED on ADD. Attach at **ad-group**
level (`adGroupId`). `adProduct` IS allowed on ADD. Ledger params:
`{ "keyword":"<text>", "matchType":"EXACT", "negative":true }`.

**3. Bid-down a target — `AMAZON_ADS_TARGETS_UPDATE`**
```json
{ "targets": [ { "targetId": "<id>", "bid": 0.25 } ] }
```
Send ONLY `targetId` + `bid` (a flat number; `exclusiveMinimum:0`). Read the FIND echo's nested
`.bid.bid`, write a bare number. Ledger params: `{ "bid": <new_bid> }`.

---

## Guardrails recap (every move, every time)
1. **Org-enable cleared** (STEP 0) — a 412 = not enabled; surface, never retry.
2. **Identity from `*_FIND` + cache** — never `sku_catalog.toml`; a cache miss is refused.
3. **`dryRun:true` validates first** — proceed only on VALIDATED/valid/no-issues.
4. **Canary first** — one pause with `--confirm-canary`, reconciled COMPLETED, before the batch.
5. **Exact-only negatives** — `baklava gift box` never negated; watch-don't-negate → bid-down.
6. **Reconcile via COMPLETED + FIND echo** — never via a DataDoe export.
7. **Log every move** (D-11) — `decisions.md` + `brain/raw/` with the `actionId`; standing-approved
   ≠ silent.
8. **Idempotent** — the ledger no-ops a re-run (D-10); in-flight resumes at poll.
9. **No seller UUID on disk** — only inside the live MCP payload (CLAUDE.md hard rule 5).
