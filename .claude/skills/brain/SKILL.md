---
name: brain
description: The memory protocol for the workspace. Use at the start of any analysis (read wiki for context) and whenever something is learned or decided (append to raw). Defines the raw → wiki compilation that gives the system long-term memory. Reference content — every agent should follow it.
---

# Brain Protocol

The brain lives in `brain/` (see `brain/README.md`). Markdown only, Obsidian-compatible.

## Reading (start of work)
Before analyzing, read the relevant `brain/wiki/` notes for context: the SKU profile in
`wiki/skus/<SKU>.md`, any `wiki/playbooks/` that apply, and `wiki/index.md` for open questions.
This is how you avoid re-deriving what's already known and re-recommending reversed decisions.

## Writing (as you work)
Append — never overwrite — to `brain/raw/`:
- Daily briefings → `brain/raw/daily/{YYYY-MM-DD}.md`.
- A decision or applied change → also append the structured line to `state/decisions.md`.
- An anomaly, a finding, a piece of research, a competitor observation → a timestamped note in
  `brain/raw/{YYYY-MM-DD}-{slug}.md`.
Write concise, factual notes with the SKU/ASIN and the source. Do not edit `wiki/` by hand.

## Compaction (weekly, by the brain-compaction task only)
Read new `raw/` entries since the last run and update `wiki/`:
- Refresh each touched `wiki/skus/<SKU>.md` (latest velocity/margin/lead-time, new known issues,
  what worked or didn't).
- Promote any pattern that has now shown up repeatedly into a `wiki/playbooks/` note.
- Update `customers.md` / `competitors.md` with new themes.
- Update `wiki/index.md`: open questions and a one-line "last compaction" summary.
- Deduplicate. The wiki should shrink relative to raw, not grow unbounded.
Never delete `raw/`. The wiki is the distilled view; raw is the ground truth and audit trail.
