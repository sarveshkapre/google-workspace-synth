# CHANGELOG

## Unreleased
- Add snapshot export/import (`GET /snapshot`, `POST /snapshot?mode=replace`) plus CLI (`python -m gwsynth.snapshot`).
- Add default HTTP request body size cap via `GWSYNTH_MAX_REQUEST_BYTES`.
- Add basic in-memory rate limiting via `GWSYNTH_RATE_LIMIT_*`.
- Add per-item activity timeline (`GET /items/<item_id>/activity`).
- Add optional cursor pagination (`limit`, `cursor`, `next_cursor`) on list endpoints.

## v0.1.0 - 2026-02-01
- Initial MVP: Flask API, SQLite storage, seeder CLI, CI, and docs.
