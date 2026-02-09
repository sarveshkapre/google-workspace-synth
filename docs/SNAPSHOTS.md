# Snapshots

Snapshots are a portable JSON export/import format for resetting a seeded demo org quickly.

## API and CLI
- API export: `GET /snapshot` (supports `tables=...` and `gzip=1`)
- API import: `POST /snapshot?mode=replace` or `POST /snapshot?mode=replace_tables&tables=...`
- CLI: `python -m gwsynth.snapshot export|import` (supports `--tables`, `--gzip`, `--compact`)

## Versions
Current snapshot version is `2`. Supported import versions: `1` and `2`.

### v1 (legacy)
v1 snapshots are accepted for import. v1 payloads typically contain only:
- `snapshot_version`
- `tables` (object: table name -> list of rows)

### v2 (current)
v2 adds metadata and schema hints:
- `app_version`
- `exported_at` (UTC ISO timestamp)
- `exported_tables` (ordered list)
- `schema` (per-table column lists)

Schema metadata is optional at import time (v1 snapshots will not include it).

## Compatibility Policy
Snapshot import is intentionally strict to keep resets safe and predictable.

- Unknown columns in rows are rejected.
  - This prevents silently accepting typos or unexpected schema drift.
- Missing columns are handled as follows:
  - If the DB column is nullable, missing values import as `null`.
  - If the DB column is `NOT NULL` and has a SQLite default, missing values import as that default.
  - If the DB column is `NOT NULL` and has no default, import fails with a clear error.
- Foreign keys are enforced during import.
  - If `mode=replace_tables` omits dependent tables, SQLite cascades may delete dependent rows.

Practical rule for future schema changes:
- Prefer adding new columns as nullable (or with a default), never `NOT NULL` without a default.

## Migration Notes
- v1 -> v2: added export metadata and optional schema hints; table row formats are unchanged.

