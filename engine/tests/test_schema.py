"""DATA-01/02/03 schema introspection tests (consumed by plan 01-02).

These assert against the live Supabase truth store AFTER `alembic upgrade head`.
Plan 01-02 authors the migrations; the live push is a blocking-human gate, so
until that lands these tests SKIP cleanly (the db_connection fixture skips when
the DB is unreachable, and each test skips when its target objects are absent).
Once the schema exists they turn red->green automatically.

The constraint/column expectations below are the contract plan 01-02 must
satisfy (RESEARCH §Pattern 2/3, REQUIREMENTS DATA-01/02/03).
"""

from __future__ import annotations

import pytest

# The five truth-store tables (RESEARCH §Recommended Project Structure).
EXPECTED_TABLES = {
    "sku_master",
    "cogs",
    "metric_snapshots",
    "decision_ledger",
    "config",
}


def _table_exists(conn, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s",
            (table,),
        )
        return cur.fetchone() is not None


def _columns(conn, table: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = 'public' AND table_name = %s",
            (table,),
        )
        return {row[0] for row in cur.fetchall()}


def _unique_column_sets(conn, table: str) -> list[set[str]]:
    """Return the column sets covered by UNIQUE / PRIMARY KEY constraints."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tc.constraint_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = 'public'
              AND tc.table_name = %s
              AND tc.constraint_type IN ('UNIQUE', 'PRIMARY KEY')
            """,
            (table,),
        )
        groups: dict[str, set[str]] = {}
        for constraint_name, column_name in cur.fetchall():
            groups.setdefault(constraint_name, set()).add(column_name)
        return list(groups.values())


def test_tables_and_vector_ext(db_connection) -> None:
    """DATA-01: all 5 tables exist and the `vector` extension is enabled."""
    missing = {t for t in EXPECTED_TABLES if not _table_exists(db_connection, t)}
    if missing:
        pytest.skip(f"Schema not yet migrated (missing tables: {sorted(missing)}) — plan 01-02")

    with db_connection.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
        assert cur.fetchone() is not None, "pgvector extension not enabled (DATA-01)"


def test_snapshot_idempotency_key(db_connection) -> None:
    """DATA-02: metric_snapshots unique on the grain key + has provenance cols."""
    if not _table_exists(db_connection, "metric_snapshots"):
        pytest.skip("metric_snapshots not yet created — plan 01-02")

    cols = _columns(db_connection, "metric_snapshots")
    for required in ("marketplace", "seller_sku", "snapshot_date", "captured_at", "datadoe_export_id"):
        assert required in cols, f"metric_snapshots missing column {required!r} (DATA-02)"

    grain = {"marketplace", "seller_sku", "snapshot_date"}
    uniques = _unique_column_sets(db_connection, "metric_snapshots")
    assert any(grain <= u for u in uniques), (
        "metric_snapshots must be UNIQUE on (marketplace, seller_sku, snapshot_date) (DATA-02)"
    )


def test_cogs_scd_fx(db_connection) -> None:
    """DATA-03: cogs has SCD-2 dating + per-row FX, unique on the SCD key."""
    if not _table_exists(db_connection, "cogs"):
        pytest.skip("cogs not yet created — plan 01-02")

    cols = _columns(db_connection, "cogs")
    for required in (
        "marketplace",
        "seller_sku",
        "effective_from",
        "effective_to",
        "unit_cost",
        "cost_currency",
        "fx_rate",
        "fx_as_of",
        "marketplace_currency",
    ):
        assert required in cols, f"cogs missing column {required!r} (DATA-03)"

    scd_key = {"marketplace", "seller_sku", "effective_from"}
    uniques = _unique_column_sets(db_connection, "cogs")
    assert any(scd_key <= u for u in uniques), (
        "cogs must be UNIQUE on (marketplace, seller_sku, effective_from) (DATA-03)"
    )
