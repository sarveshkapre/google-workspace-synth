# ROADMAP

## Next
- Add integration smoke coverage for real Workspace `apply`/`destroy` flows (mocked; no network).
- Add richer snapshot compatibility guarantees (nullable/optional fill policy + explicit migration notes).
- Add a small "demo guide" page (examples + curl snippets + recommended seed profiles).

## Done
- Snapshot export/import for deterministic demo resets.
- Snapshot v2 metadata + schema checks; selective snapshot table export/import.
- Snapshot streaming + gzip export for large datasets (API + CLI).
- Basic rate limiting and request size caps (local-safe defaults).
- Per-item activity timeline.
- Pagination + cursor support for large datasets.
- Basic audit log for changes.
- Mocked smoke coverage for `gwsynth.real plan` (no network).
- API surface documentation: OpenAPI spec + local `/docs` page.
