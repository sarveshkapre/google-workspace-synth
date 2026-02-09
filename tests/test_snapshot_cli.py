from __future__ import annotations

from uuid import uuid4


def test_snapshot_cli_export_import_gzip(tmp_path, monkeypatch):
    db1 = tmp_path / "db1.db"
    db2 = tmp_path / "db2.db"
    snap = tmp_path / "snapshot.json.gz"

    monkeypatch.setenv("GWSYNTH_DB_PATH", str(db1))
    from gwsynth.db import get_connection, init_db
    from gwsynth.snapshot import main as snapshot_main

    init_db()
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO users (id, email, display_name, created_at) VALUES (?, ?, ?, ?)",
            (str(uuid4()), "zipcli@example.com", "Zip CLI", "2026-01-01T00:00:00Z"),
        )

    snapshot_main(["export", "--out", str(snap)])

    monkeypatch.setenv("GWSYNTH_DB_PATH", str(db2))
    init_db()
    snapshot_main(["import", "--in", str(snap), "--mode", "replace"])

    with get_connection() as conn:
        row = conn.execute(
            "SELECT email FROM users WHERE email = ?",
            ("zipcli@example.com",),
        ).fetchone()
        assert row is not None
