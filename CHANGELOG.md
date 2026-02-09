# CHANGELOG

This file mirrors `docs/CHANGELOG.md` (kept in sync for repo-root discoverability).

## Unreleased
- Add `GET /groups/<group_id>/members` endpoint with cursor pagination support.
- Harden item creation/update validation by enforcing item-type-specific content fields.
- Enforce permission principal invariants (`anyone` must omit `principal_id`; `user/group` require it).
- Return `404` on item-scoped permissions/share-links/comments list/delete routes when item is missing.
- Enforce unique group memberships via DB uniqueness on `(group_id, user_id)`.
- Add snapshot export/import (`GET /snapshot`, `POST /snapshot?mode=replace`) plus CLI (`python -m gwsynth.snapshot`).
- Snapshot v2 metadata + schema checks; add `tables=...` filtering and `mode=replace_tables` for partial restores.
- Add streaming + gzip snapshot export for large demo datasets (`GET /snapshot?gzip=1`; snapshot CLI `.gz` + `--gzip`).
- Add default HTTP request body size cap via `GWSYNTH_MAX_REQUEST_BYTES`.
- Add basic in-memory rate limiting via `GWSYNTH_RATE_LIMIT_*`.
- Add per-item activity timeline (`GET /items/<item_id>/activity`).
- Add optional cursor pagination (`limit`, `cursor`, `next_cursor`) on list endpoints.
- Add item filtering on `GET /items` (`parent_id`, `owner_user_id`, `item_type`).
- Add optional API key auth via `GWSYNTH_API_KEY`.
- Add OpenAPI spec endpoint (`GET /openapi.json`) and local Swagger UI docs page (`GET /docs`).
- Default `python -m gwsynth.main` to non-debug; add `GWSYNTH_DEBUG`, `GWSYNTH_HOST`, `GWSYNTH_PORT`/`PORT`.
- Add `make smoke` local verification target.

## v0.1.0 - 2026-02-01
- Initial MVP: Flask API, SQLite storage, seeder CLI, CI, and docs.
