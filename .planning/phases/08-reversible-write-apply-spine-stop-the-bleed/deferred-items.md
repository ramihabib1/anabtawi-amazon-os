# Phase 08 — Deferred Items

Out-of-scope discoveries logged during execution (NOT fixed — see GSD SCOPE BOUNDARY rule).

## 08-02 (executor)

- **`engine/tests/test_env.py::test_seller_id_in_env_not_code` fails in the isolated worktree.**
  - **Cause:** the test asserts `AMAZON_CA_SELLER_ID` is loaded from the gitignored `.env`
    (Plan 01-01 Task 2 contract). The worktree has no `.env` (gitignored — never copied into
    a fresh worktree), so the env var is unset and the assertion fails.
  - **Why out of scope:** unrelated to Plan 08-02's modules (test_env.py imports no `habibos`
    code — it is a pure env/secret-hygiene assertion). The failure is purely a worktree
    environment-config gap, not a regression from this plan's changes.
  - **Why NOT auto-fixed:** materializing the seller UUID into the worktree to satisfy the
    test would violate CLAUDE.md hard rule 5 (secrets live only in the gitignored `.env`).
  - **Resolution:** passes in the primary checkout where `.env` exists; no action needed in
    the worktree. The full suite is otherwise green (44 passed, 5 skipped, this 1 env-gap).
