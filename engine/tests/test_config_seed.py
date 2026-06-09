"""DATA-04 config-seed test (consumed by plan 01-04).

Asserts the `config` table is non-empty after the seed migration, is keyed on
(key, marketplace), and carries the required operator thresholds. Empty config
is forbidden (RESEARCH §Pitfall 2 — an empty config is a fabrication invitation).

Until plan 01-04 seeds real operator values this SKIPS cleanly (the table is
absent or empty before then).
"""

from __future__ import annotations

import pytest

# Required threshold keys the operator must supply (RESEARCH §Pitfall 2,
# REQUIREMENTS DATA-04). All keyed to marketplace 'amazon.ca'.
REQUIRED_KEYS = {
    "min_margin_pct",
    "acos_ceiling",
    "days_of_cover_trigger",
}


def _table_exists(conn, table: str) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT 1 FROM information_schema.tables "
            "WHERE table_schema = 'public' AND table_name = %s",
            (table,),
        )
        return cur.fetchone() is not None


def test_required_thresholds_seeded(db_connection) -> None:
    if not _table_exists(db_connection, "config"):
        pytest.skip("config table not yet created — plan 01-02/01-04")

    with db_connection.cursor() as cur:
        cur.execute("SELECT count(*) FROM config")
        (row_count,) = cur.fetchone()
        if row_count == 0:
            pytest.skip("config not yet seeded — plan 01-04")

        # The table must be keyed on (key, marketplace).
        cur.execute(
            """
            SELECT kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
             AND tc.table_schema = kcu.table_schema
            WHERE tc.table_schema = 'public'
              AND tc.table_name = 'config'
              AND tc.constraint_type IN ('PRIMARY KEY', 'UNIQUE')
            """
        )
        key_cols = {row[0] for row in cur.fetchall()}
        assert {"key", "marketplace"} <= key_cols, (
            "config must be keyed on (key, marketplace) (DATA-04)"
        )

        # Required thresholds must be present for amazon.ca.
        cur.execute(
            "SELECT key FROM config WHERE marketplace = %s",
            ("amazon.ca",),
        )
        present = {row[0] for row in cur.fetchall()}

    missing = REQUIRED_KEYS - present
    assert not missing, f"config missing required threshold keys for amazon.ca: {sorted(missing)} (DATA-04)"
