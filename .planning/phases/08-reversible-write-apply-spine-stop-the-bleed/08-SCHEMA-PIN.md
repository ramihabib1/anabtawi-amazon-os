# 08-SCHEMA-PIN — Live reversible-action payload schemas (source of truth)

**Captured:** 2026-06-22, live from the DataDoe MCP against ANABTAWI SWEETS CA (Ads connected).
**Method:** `actions_details_schema_get` (read) + `actions_start dryRun:true` round-trips, iterated
until `status:"VALIDATED"`, `validation.valid:true`, `validation.issues:[]`. **No live writes.**
**Provenance:** real IDs sourced from a read-only `AMAZON_ADS_TARGETS_FIND`
(actionId `9c3e7cd0-…`, COMPLETED). Seller UUID stripped from every committed fixture
(CLAUDE.md hard rule 5). These are the field names `build_payload` (Plan 03) and the ledger
normalized-params map (Plan 02) are written against — never fabricate, re-pin if the API changes.

This file is the SINGLE SOURCE OF TRUTH for the three reversible payloads. Fixtures:
`engine/tests/fixtures/actions_start_dryrun_{pause,negative,biddown}.json`.

---

## Top-level envelope (all action types)

`actions_start` request requires: `type`, `sellerOrVendorId` (UUID — **never** committed),
`details`, and `dryRun` (bool). The VALIDATED response shape mirrors `dryrun_validated.json`:
top-level `status:"VALIDATED"` + nested `validation:{valid:true, issues:[]}`. The committed
fixtures keep `request.details` (the pinned payload) but drop `request.sellerOrVendorId`.

---

## 1. PAUSE a campaign — `AMAZON_ADS_CAMPAIGNS_UPDATE`

```json
{ "campaigns": [ { "campaignId": "<id>", "state": "PAUSED" } ] }
```

| Field | Type | Notes |
|-------|------|-------|
| `details.campaigns[]` | array | `minItems:1` |
| `campaignId` | string | the live, FIND-verified campaign id |
| `state` | enum `ENABLED`\|`PAUSED` | send `PAUSED` to pause |

- **Send ONLY mutable fields** (`campaignId` + `state`). 
- **DO NOT echo `adProduct`** — the live request-validator rejects `adProduct` on
  `CAMPAIGNS_UPDATE` ("adProduct is not allowed") even though `actions_details_schema_get`
  lists it as a campaign property. (Confirms `datadoe-query` SKILL line 174.) The pause
  fixture contains **no** `adProduct` key.
- Normalized ledger params: `{ "state": "PAUSED" }` keyed by `campaignId`.

## 2. ADD an exact-match NEGATIVE keyword — `AMAZON_ADS_TARGETS_ADD`

```json
{ "targets": [ {
  "campaignId": "<id>", "adGroupId": "<id>",
  "adProduct": "SPONSORED_PRODUCTS",
  "state": "ENABLED", "negative": true,
  "targetType": "KEYWORD",
  "targetDetails": { "keywordTarget": { "keyword": "<text>", "matchType": "EXACT" } }
} ] }
```

| Field | Type | Notes |
|-------|------|-------|
| `negative` | boolean | **`true` is what makes it a negative.** There is **no** `NEGATIVE_EXACT` literal. |
| `targetType` | string | `"KEYWORD"` |
| `targetDetails.keywordTarget.matchType` | string | **`"EXACT"`** — the match-type literal lives nested under `keywordTarget`, not on the target root |
| `targetDetails.keywordTarget.keyword` | string | the negated keyword text |
| `state` | enum | **REQUIRED on ADD** — validator: "Target add action requires state". Send `"ENABLED"` (the negation is active). |
| `adProduct` | enum | `"SPONSORED_PRODUCTS"` — allowed/included on ADD (unlike UPDATE) |
| `adGroupId` | string | **attachment level = AD_GROUP** (live targets report `targetLevel:"AD_GROUP"`); attach the negative via `adGroupId` |
| `campaignId` | string | included alongside `adGroupId` |

- **Resolves RESEARCH Pitfall 2 / Assumption A2:** match-type literal = `matchType:"EXACT"`
  (under `keywordTarget`); negative is the `negative:true` flag; attachment is **ad-group** level.
- Normalized ledger params: `{ "keyword": "<text>", "matchType": "EXACT", "negative": true }`
  keyed by `adGroupId`.

## 3. BID-DOWN a target/keyword — `AMAZON_ADS_TARGETS_UPDATE`

```json
{ "targets": [ { "targetId": "<id>", "bid": 0.25 } ] }
```

| Field | Type | Notes |
|-------|------|-------|
| `targetId` | string | the live, FIND-verified target/keyword id (`maxLength:128`) |
| `bid` | number | `exclusiveMinimum:0` — the **new, lower** bid as a flat number |

- **Send ONLY mutable fields** (`targetId` + `bid`); do not echo `targetType`/`targetDetails`.
- **Note the shape asymmetry:** the write takes a **flat** `bid` number, but a `TARGETS_FIND`
  echoes bid as an object `{ "bid": 0.49, "currencyCode": "CAD" }`. Read the nested `.bid.bid`
  on the FIND echo; write a bare number. (Resolves Assumption A3.)
- Normalized ledger params: `{ "bid": <new_bid> }` keyed by `targetId`.

---

## FIND-echo confirmation keys (for `test_find_echo_mismatch`, Plan 03)

After `actions_get` reaches `COMPLETED`, a `*_FIND` echo confirms the mutation:

| Action | Echo entity | Confirm field | Expected after write |
|--------|-------------|---------------|----------------------|
| pause | campaign | `state` | `"PAUSED"` |
| negative add | target (negative) | target present with `negative:true` + matching `keywordTarget` | exists |
| bid-down | target | `bid.bid` (nested) | `== new_bid` |

A disagreement → `Refusal(code="find_echo_mismatch")`, never recorded as applied.
