# ROADMAP

## Next
- Swagger UI offline mode: optionally vendor Swagger UI assets to avoid CDN dependency for airgapped demos.
- Proxy-aware rate limiting: when `GWSYNTH_TRUST_PROXY=1`, optionally parse RFC 7239 `Forwarded` and/or `X-Real-IP`.
- OpenAPI completeness sweep: add schemas for currently underspecified responses.

## Done
- Snapshot export/import for deterministic demo resets.
- Snapshot v2 metadata + schema checks; selective snapshot table export/import.
- Snapshot streaming + gzip export for large datasets (API + CLI).
- Snapshot import supports `Content-Encoding: gzip` with a decompressed-size cap for large demo reset loops.
- Snapshot `ETag` / `If-None-Match` caching for faster repeated exports.
- Basic rate limiting and request size caps (local-safe defaults).
- Per-item activity timeline.
- Pagination + cursor support for large datasets.
- Composite indexes for cursor pagination (`created_at`, `id`) on large seeds.
- Basic audit log for changes.
- Mocked smoke coverage for `gwsynth.real plan` (no network).
- API surface documentation: OpenAPI spec + local `/docs` page.
