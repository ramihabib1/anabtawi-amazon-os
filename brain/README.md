# The Brain  (markdown-first, Obsidian-compatible)

The system's memory. Two layers, the Karpathy raw → wiki pattern:

- `raw/` — append-only inbox. Everything the system observes or decides goes here, timestamped
  and never edited: daily briefings (`raw/daily/`), anomaly events, audit notes, research
  dumps, and every decision. Cheap to write, never deleted.
- `wiki/` — the compiled, deduplicated, linked knowledge. Generated from `raw/` by the weekly
  compaction task. This is what agents read first.
  - `wiki/index.md` — map of content / entry point.
  - `wiki/skus/<SKU>.md` — a living profile per SKU (velocity, margin, lead time, ad behaviour,
    known listing issues, history of what worked).
  - `wiki/playbooks/<topic>.md` — operating knowledge that has proven out and graduated from
    one-off notes into standing guidance.
  - `wiki/customers.md`, `wiki/competitors.md` — voice-of-customer and competitive intel.

## Rules
- Agents **read `wiki/` first** for context, **append to `raw/`** as they learn. They do not
  edit `wiki/` directly — only the compaction task does.
- It's plain markdown. Point Obsidian at this folder for the human view (graph, backlinks,
  mobile). The agents read the same files and don't care that Obsidian exists.
- Keep it a folder of notes. No plugins/Bases/Dataview required — don't let the vault become
  the project.
- When `raw/` ever grows into thousands of unstructured docs and "find every past situation
  like X" becomes a repeated need, layer pgvector (already in Supabase) **under** `raw/` for
  semantic search. Not before.
