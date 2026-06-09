"""habibos — the reusable trust-spine substrate for Habib OS (D-02).

Built in Phase 2 Plan 01 and imported by every later slice (Phases 3-5):
  - result    : typed Answer / Refusal / SkuRow (never None/0 for missing data)
  - thresholds: tomllib reader, missing -> None (caller refuses, never defaults)
  - logging   : structlog one-event-in / one-event-out logged_call wrapper
  - datadoe   : tenacity poll primitive + local artifact loader (agent-MCP seam)
"""

from __future__ import annotations

__version__ = "0.1.0"
