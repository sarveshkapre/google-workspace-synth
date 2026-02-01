# CHANGELOG

This file mirrors `docs/CHANGELOG.md` (kept in sync for repo-root discoverability).

## Unreleased
- Add snapshot export/import (`GET /snapshot`, `POST /snapshot?mode=replace`) plus CLI (`python -m gwsynth.snapshot`).
- Add default HTTP request body size cap via `GWSYNTH_MAX_REQUEST_BYTES`.

## v0.1.0 - 2026-02-01
- Initial MVP: Flask API, SQLite storage, seeder CLI, CI, and docs.

