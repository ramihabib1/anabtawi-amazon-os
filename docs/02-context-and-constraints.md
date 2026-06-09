# Context & Constraints

## The business
Habib Distribution imports and distributes Anabtawi Sweets into Canada — ~30 SKUs on **Amazon.ca** (FBA), with a **US FBA expansion** underway. Operated solo on the technical/analytical side; finance and sales/marketing are handled by family.

## Runtime
Built around the **Hermes Mac desktop app** (public preview) — the workspace I work in day to day. Not a server deployment. See CLAUDE.md "Runtime" for the scheduling implication.

## Connected systems (all already authenticated)
- **DataDoe MCP** — the single Amazon data source. SQL-style exports over Seller Central **and** the attached Amazon Ads connection. Seller entity resolved via `sellers_and_vendors_list`; store the amazon.ca UUID in `.env` as `AMAZON_CA_SELLER_ID`.
- **Supabase** — Postgres + pgvector; numeric source of truth and the decision ledger.
- **Gmail / Drive / Calendar** — supplier comms, compliance docs, scheduling.
- **Tavily** — web research (competitor/keyword context for listings).

> NOT available: Agent Central. Everything PPC, listing, and profit related comes from DataDoe (see 04). What we forgo: granular FBA long-term storage fees and native repeat-purchase / Subscribe & Save — minor, and partially reconstructable from DataDoe.

## Why the guardrails are this strict
A prior third party took **unauthorized PPC actions** and produced **fabricated reporting**. The architecture makes oversight *structural*: the data tools physically cannot write, and any action that could move money is a human-approved, logged proposal. PPC and listing edits — the highest priority *and* the prior abuse vector — are recommend-then-approve, never autonomous. Do not propose patterns that bypass this.

## Decisions already locked
- Runtime is the **Hermes Mac desktop app**.
- **Highest priority: PPC management, then listing optimization.**
- One resident agent with skills — not a fleet.
- Two memory stores: Supabase = numeric truth; `~/.hermes/` = procedural memory + skills + persona (SOUL.md).
- Manual execution of writes through early milestones; a gated write-MCP is a later, separate decision.
- Learn-before-build: prove each piece read-only before anything can act.

## Operating principles
- Numbers-first, terse. Flag risk explicitly.
- Never invent thresholds — read them from Supabase `config`.
- Prefer DataDoe's premium "Profit by SKU & Date" for margin/ACOS/TACOS over hand-rolled math.
