"""Shared pytest fixtures for the Habib OS truth-store tests.

Wave 0 scaffold (plan 01-01). The Postgres fixtures here are consumed by the
schema/seed integration tests authored as stubs now and turned red->green by
plans 01-02 (schema) and 01-04 (config seed).

Connection policy (RESEARCH §Pattern 4):
  - Migrations / DDL run on the DIRECT (5432) connection: SUPABASE_DB_URL.
  - Short-lived runtime helpers use the POOLED (6543) connection:
    SUPABASE_DB_URL_POOLED.
The schema introspection tests connect on the DIRECT URL so they can see the
result of `alembic upgrade head`.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Repo root = parent of the tests/ directory.
REPO_ROOT = Path(__file__).resolve().parent.parent

# Load the gitignored .env so tests see AMAZON_CA_SELLER_ID / SUPABASE_DB_URL.
load_dotenv(REPO_ROOT / ".env")


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repository root."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def direct_db_url() -> str:
    """The DIRECT (5432) Supabase connection string used for migrations/DDL.

    Skips the consuming test when unset so the suite stays green before the
    live Supabase connection is wired (plan 01-02).
    """
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("SUPABASE_DB_URL (direct connection) not set — wired in plan 01-02")
    return url


@pytest.fixture(scope="session")
def db_connection(direct_db_url: str):
    """A live psycopg connection to the truth store on the DIRECT connection.

    Skips if psycopg is unavailable or the database is unreachable. The schema
    must already exist (`alembic upgrade head`) for the consuming assertions to
    pass — that happens in plan 01-02, so until then the tests skip cleanly.
    """
    psycopg = pytest.importorskip("psycopg")
    try:
        conn = psycopg.connect(direct_db_url, connect_timeout=5)
    except Exception as exc:  # noqa: BLE001 - any connect failure -> skip, not fail
        pytest.skip(f"Cannot reach Supabase Postgres on the direct connection: {exc}")
    try:
        yield conn
    finally:
        conn.close()
