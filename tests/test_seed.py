from __future__ import annotations

import sqlite3

from gwsynth.seed import seed_database


def test_seed_enterprise_profile(tmp_path, monkeypatch):
    db_path = tmp_path / "seed.db"
    monkeypatch.setenv("GWSYNTH_DB_PATH", str(db_path))

    seed_database(
        users=3,
        groups=2,
        folders=2,
        docs=2,
        sheets=2,
        seed=123,
        shared_drives=2,
        personal_drives=True,
        personal_docs=1,
        personal_sheets=1,
        company_name="Acme Labs",
        domain="acme.test",
        profile="engineering",
        history_days=30,
    )

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        users = conn.execute("SELECT email FROM users").fetchall()
        assert all(row["email"].endswith("@acme.test") for row in users)

        roots = conn.execute(
            "SELECT id FROM items WHERE parent_id IS NULL"
        ).fetchall()
        assert len(roots) == 5

        activities = conn.execute("SELECT COUNT(*) AS c FROM activities").fetchone()
        assert activities["c"] > 0
    finally:
        conn.close()
