# ROADMAP

## Next
- Add snapshot compression and/or streaming export for very large demo datasets.
- Add integration smoke coverage for real Workspace `apply`/`destroy` flows (mocked; no network).
- Add API surface documentation (OpenAPI + minimal local docs page).

## Done
- Snapshot export/import for deterministic demo resets.
- Snapshot v2 metadata + schema checks; selective snapshot table export/import.
- Basic rate limiting and request size caps (local-safe defaults).
- Per-item activity timeline.
- Pagination + cursor support for large datasets.
- Basic audit log for changes.
- Mocked smoke coverage for `gwsynth.real plan` (no network).
