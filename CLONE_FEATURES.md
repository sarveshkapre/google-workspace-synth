# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration
- GitHub Actions run triage (`gh run list`, `gh run view`)

## Candidate Features To Do
- [ ] P1 (selected): Return `400` (not `500`) for invalid `limit`, `cursor`, and filter query params across list/search endpoints. (Score: impact high, effort low, strategic fit high, differentiation low, risk low, confidence high)
- [ ] P1 (selected): Group members pagination performance: replace paginated N+1 member-user lookups with a joined, cursor-paginated query (keep response shape). (Score: impact medium-high, effort medium, strategic fit high, differentiation low, risk low, confidence high)
- [ ] P1 (selected): Proxy-aware rate limiting: when `GWSYNTH_TRUST_PROXY=1`, parse RFC 7239 `Forwarded` and `X-Real-IP` with safe precedence and tests. (Score: impact medium, effort medium, strategic fit high, differentiation low, risk low-medium, confidence medium-high)
- [ ] P2 (selected): Swagger UI offline mode: support local vendored assets with CDN fallback for airgapped demos. (Score: impact medium, effort medium, strategic fit medium-high, differentiation low, risk low, confidence medium-high)
- [ ] P2 (selected): OpenAPI completeness sweep for high-traffic endpoints (`/users`, `/groups`, `/items`, permissions/share-links/comments lists). (Score: impact medium, effort medium-high, strategic fit medium-high, differentiation low, risk low, confidence medium)
- [ ] P2: Add request-id correlation (`X-Request-Id`) to responses and error payloads for easier debugging in demos. (Score: impact medium, effort medium, strategic fit medium, differentiation low, risk low, confidence medium)
- [ ] P2: Add lightweight DB query-plan regression checks for hot list routes (`EXPLAIN QUERY PLAN`) on seeded data sizes. (Score: impact medium, effort medium, strategic fit medium, differentiation low-medium, risk low, confidence medium)
- [ ] P2: Add `GET /version` endpoint exposing app version + schema/snapshot compatibility info for tooling. (Score: impact low-medium, effort low, strategic fit medium, differentiation low, risk low, confidence high)
- [ ] P2: Improve `/stats` with optional per-item-type counts (`folder/doc/sheet`) and top-level metadata for seed diagnostics. (Score: impact low-medium, effort low-medium, strategic fit medium, differentiation low, risk low, confidence high)
- [ ] P3: Add API pagination contract tests for invalid/malformed cursors on every paginated route. (Score: impact medium, effort medium, strategic fit medium, differentiation low, risk low, confidence high)
- [ ] P3: Add explicit schema for `429` in OpenAPI with `Retry-After` + rate-limit headers documentation. (Score: impact low-medium, effort low, strategic fit medium, differentiation low, risk low, confidence high)
- [ ] P3: Add optional strict email normalization/validation in seeder and `POST /users` (RFC-lite, pragmatic). (Score: impact low-medium, effort medium, strategic fit low-medium, differentiation low, risk medium, confidence medium)
- [ ] P3: Reduce API module size by extracting shared row serializers and repeated list-route patterns. (Score: impact low-medium, effort medium-high, strategic fit medium, differentiation low, risk medium, confidence medium)
- [ ] P3: Add smoke coverage for docs route in offline mode and API-key-enabled mode together. (Score: impact low-medium, effort low, strategic fit medium, differentiation low, risk low, confidence high)
- [ ] P3: Evaluate optional seed profile for "support org" (tickets, shared docs, incident templates) to broaden demo scenarios. (Score: impact medium, effort medium-high, strategic fit medium, differentiation medium, risk low-medium, confidence medium)

## Implemented
- [x] 2026-02-11: Query validation hardening: paginated/filterable list routes now return `400` JSON errors for invalid `limit`, `cursor`, or filter values instead of raising uncaught `ValueError` (`500` in production).
  - Evidence: `src/gwsynth/api.py`, `tests/test_api.py::test_invalid_query_params_return_400`.
- [x] 2026-02-11: Group members pagination performance: replaced paginated N+1 user lookups with a joined cursor query.
  - Evidence: `src/gwsynth/api.py`, `tests/test_api.py::test_group_members_listing_and_idempotent_add`.
- [x] 2026-02-11: Trusted proxy rate-limit identity now supports `Forwarded` and `X-Real-IP` (with `X-Forwarded-For` fallback) when `GWSYNTH_TRUST_PROXY=1`.
  - Evidence: `src/gwsynth/rate_limit.py`, `tests/test_api.py::test_rate_limiting_prefers_forwarded_header_when_trust_proxy_enabled`, `tests/test_api.py::test_rate_limiting_uses_x_real_ip_as_proxy_fallback`.
- [x] 2026-02-11: Swagger UI offline mode: added docs asset modes (`cdn`/`local`/`auto`), local docs asset serving route, auth allowlist for docs assets, and vendoring helper script.
  - Evidence: `src/gwsynth/config.py`, `src/gwsynth/api.py`, `src/gwsynth/auth.py`, `scripts/vendor_swagger_ui.py`, `tests/test_api.py::test_docs_local_mode_uses_vendored_assets`, `tests/test_api.py::test_docs_local_mode_missing_assets_returns_503`, `tests/test_api.py::test_api_key_auth_allows_docs_assets`.
- [x] 2026-02-11: OpenAPI completeness sweep for high-traffic list endpoints and core resources (`users/groups/items/permissions/share-links/comments/activity/search`).
  - Evidence: `src/gwsynth/openapi.py`, `tests/test_api.py::test_openapi_and_docs_endpoints`.
- [x] 2026-02-10: Snapshots: `POST /snapshot` now accepts gzip-compressed JSON via `Content-Encoding: gzip` with a decompressed-size cap; `GET /snapshot` now returns `ETag` and supports `If-None-Match` (`304`). Oversized requests return a JSON `413` with an actionable hint.
  - Evidence: `src/gwsynth/api.py`, `src/gwsynth/config.py`, `src/gwsynth/main.py`, `src/gwsynth/openapi.py`, `tests/test_api.py::test_snapshot_import_accepts_gzip_content_encoding`, `tests/test_api.py::test_snapshot_etag_if_none_match`, `tests/test_api.py::test_request_entity_too_large_is_json`, `README.md`, `docs/DEMO_GUIDE.md`, `docs/SNAPSHOTS.md`.
- [x] 2026-02-10: DB perf: added composite indexes for common cursor pagination orderings (`created_at`, `id`) across core tables (users/groups/items/group_members/activities).
  - Evidence: `src/gwsynth/db.py`; local `make check` pass.
- [x] 2026-02-09: Swagger UI auth ergonomics: added OpenAPI `securitySchemes` + global `security`, marked `/health` + `/stats` as public (`security: []`), and enabled Swagger UI auth persistence (`persistAuthorization`) for smoother interactive docs when `GWSYNTH_API_KEY` is set.
  - Evidence: `src/gwsynth/openapi.py`, `src/gwsynth/api.py`, `tests/test_api.py::test_openapi_and_docs_endpoints`.
- [x] 2026-02-09: Rate limit UX: added `Retry-After` on `429` and asserted rate limit headers on throttled responses.
  - Evidence: `src/gwsynth/rate_limit.py`, `tests/test_api.py::test_rate_limiting`.
- [x] 2026-02-09: Real-tenant CLI safety: added fully mocked smoke coverage for `gwsynth.real apply --yes` and `gwsynth.real destroy --yes` (content-only + all) with zero network calls.
  - Evidence: `tests/test_real_cli_apply_destroy_smoke.py`.
- [x] 2026-02-09: Added `GET /` landing page and allowlisted `/` + `/stats` when `GWSYNTH_API_KEY` is set.
  - Evidence: `src/gwsynth/api.py`, `src/gwsynth/auth.py`, `tests/test_api.py::test_api_key_auth_allows_docs_and_openapi`.
- [x] 2026-02-09: Documented snapshot compatibility policy + migration notes and added a demo guide (seed profiles, curl flows, snapshot reset loop).
  - Evidence: `docs/SNAPSHOTS.md`, `docs/DEMO_GUIDE.md`, `README.md`.
- [x] 2026-02-09: Updated CodeQL GitHub Action from v3 to v4 to avoid the announced v3 deprecation (Dec 2026).
  - Evidence: `.github/workflows/codeql.yml`.
- [x] 2026-02-09: Snapshot large-export path: streaming JSON + gzip support for `GET /snapshot` and snapshot CLI `.gz` / `--gzip` / `--compact`.
  - Evidence: `src/gwsynth/snapshot.py`, `src/gwsynth/api.py`, `tests/test_api.py::test_snapshot_gzip_stream`, `tests/test_snapshot_cli.py`, `README.md`.
- [x] 2026-02-09: API surface docs: `GET /openapi.json` and local Swagger UI docs (`GET /docs`) with auth allowlist for docs/spec.
  - Evidence: `src/gwsynth/openapi.py`, `src/gwsynth/api.py`, `src/gwsynth/auth.py`, `tests/test_api.py::test_openapi_and_docs_endpoints`, `README.md`.
- [x] 2026-02-09: Added `make smoke` and a real local smoke runner; default `python -m gwsynth.main` to non-debug with configurable host/port.
  - Evidence: `Makefile`, `scripts/smoke.py`, `src/gwsynth/main.py`, `README.md`, `docs/PROJECT.md`.
- [x] 2026-02-09: Snapshot v2 metadata + schema checks; added `tables=...` filtering and `mode=replace_tables` (API + CLI).
  - Evidence: `src/gwsynth/snapshot.py`, `src/gwsynth/api.py`, `tests/test_api.py::test_snapshot_tables_filter_and_replace_tables_mode`, `README.md`.
- [x] 2026-02-09: Hardened Google Drive appProperties query building (escape quotes/backslashes; deterministic ordering).
  - Evidence: `src/gwsynth/real/google_drive.py`, `tests/test_real_drive_props.py`.
- [x] 2026-02-09: Added mocked `gwsynth.real plan` CLI smoke test (no external network calls) and removed `datetime.utcnow()` usage.
  - Evidence: `tests/test_real_cli_plan_smoke.py`, `src/gwsynth/real/cli.py`.
- [x] 2026-02-09: Added repo-root maintainer docs: `AGENTS.md`, `PROJECT_MEMORY.md`, `INCIDENTS.md`.
  - Evidence: `AGENTS.md`, `PROJECT_MEMORY.md`, `INCIDENTS.md`.
- [x] 2026-02-08: Added `GET /groups/<group_id>/members` with optional cursor pagination.
  - Evidence: `src/gwsynth/api.py`, `tests/test_api.py::test_group_members_listing_and_idempotent_add`, `README.md`.
- [x] 2026-02-08: Hardened `POST /items` and sheet content update validation to enforce item-type-specific fields and `sheet_data` shape.
  - Evidence: `src/gwsynth/api.py`, `tests/test_api.py::test_create_item_validates_item_specific_fields`.
- [x] 2026-02-08: Enforced permission invariants for `principal_id` (`anyone` must omit, `user/group` must provide).
  - Evidence: `src/gwsynth/api.py`, `tests/test_api.py::test_permissions_validate_principal_id_rules`.
- [x] 2026-02-08: Standardized `404` behavior for missing items on permissions/share-links/comments list/delete routes.
  - Evidence: `src/gwsynth/api.py`, `tests/test_api.py::test_item_scoped_subresource_routes_return_404_for_missing_item`.
- [x] 2026-02-08: Enforced unique group membership at DB layer and kept add-member behavior idempotent.
  - Evidence: `src/gwsynth/db.py`, `src/gwsynth/api.py`, `tests/test_api.py::test_group_members_listing_and_idempotent_add`.
- [x] 2026-02-08: Refreshed stale docs/checklists and changelog alignment.
  - Evidence: `docs/PLAN.md`, `docs/ROADMAP.md`, `docs/PROJECT.md`, `CHANGELOG.md`, `docs/CHANGELOG.md`.

## Insights
- Invalid query params (`limit`, `cursor`, `item_type`) were a real reliability gap: Flask raised uncaught `ValueError` on several GET routes, which would surface as `500` in production mode.
- For trusted proxy deployments, RFC 7239 `Forwarded` is a better primary signal than legacy `X-Forwarded-For`; keeping `X-Real-IP` as fallback improves compatibility across common reverse proxies.
- 2026-02-02 Actions failures were GitHub-hosted runner acquisition issues ("job was not acquired by Runner"); latest `main` runs are green.
- Snapshot `mode=replace_tables` intentionally runs with foreign keys enabled: partial restores may cascade-delete dependent rows (safer than leaving DB inconsistent).
- Group membership deduplication needed DB-level enforcement for race safety, not only application-level existence checks.
- API consumer ergonomics improved by returning explicit `404` for missing item scopes instead of silent empty lists.
- Bounded market scan (untrusted): OpenAPI-driven mock tools commonly emphasize request/response validation as a baseline, and highlight OpenAPI import/export as a core workflow.
  - Stoplight Prism: https://stoplight.io/open-source/prism
  - WireMock OpenAPI validation docs: https://docs.wiremock.io/openAPI/openapi-validation
  - Mockoon OpenAPI compatibility notes: https://mockoon.com/docs/latest/openapi/openapi-specification-compatibility/
- Bounded market scan (untrusted): Swagger UI explicitly supports self-hosting and config-driven auth persistence, which maps directly to offline-demo DX expectations.
  - Swagger UI installation/self-hosting: https://swagger.io/docs/open-source-tools/swagger-ui/usage/installation/
  - Swagger UI configuration (`persistAuthorization`): https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration/
- Bounded market scan (untrusted): local mock servers commonly treat OpenAPI + interactive docs as baseline DX.
  - WireMock exposes Swagger UI docs at `/__admin/docs` and supports OpenAPI / JSON schema driven APIs: https://wiremock.org/docs/openapi/ and https://wiremock.org/docs/api/
  - Stoplight Prism emphasizes OpenAPI-driven mocking + request validation and dynamic examples: https://github.com/stoplightio/prism
  - Mockoon highlights OpenAPI/Swagger import as a core workflow: https://github.com/mockoon/mockoon
- Bounded market scan (untrusted): Drive/Docs "mock server" repos exist but are typically narrow; a local synthetic org API benefits from strong DX (docs/spec), deterministic fixtures, and safe reset workflows.
  - GoogleDriveMock: https://github.com/nddipiazza/GoogleDriveMock
  - google-drive-mock: https://github.com/pubkey/google-drive-mock
  - googleDocsMock: https://github.com/maxiliarias/googleDocsMock

## Notes
- This file is maintained by the autonomous clone loop.
- Verification evidence for this cycle:
  - `make check` (pass)
  - `make smoke` (pass)
