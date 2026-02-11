# ROADMAP

## Next
- Request-id correlation (`X-Request-Id`) in responses and errors for easier debugging.
- Rate-limit docs parity: specify `429` headers and examples in OpenAPI.
- DB query-plan guardrails for hot list endpoints on large seeded datasets.

## Done
- Query-param validation hardening: list/search routes now return `400` (not `500`) for invalid
  `limit`, `cursor`, and filter values.
- Group members pagination no longer performs N+1 user lookups; paginated reads are now joined.
- Proxy-aware rate limiting now supports trusted `Forwarded` and `X-Real-IP` in addition to
  `X-Forwarded-For` when `GWSYNTH_TRUST_PROXY=1`.
- Swagger UI offline mode: optional local/vendored docs assets with CDN fallback (`GWSYNTH_SWAGGER_UI_MODE`).
- OpenAPI completeness sweep for common list routes (`/users`, `/groups`, `/items`, permissions,
  share-links, comments, activity, search).
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
