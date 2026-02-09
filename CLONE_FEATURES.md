# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration
- GitHub Actions run triage (`gh run list`, `gh run view`)

## Candidate Features To Do
- [ ] P2: Swagger UI offline mode: optionally vendor Swagger UI assets to avoid CDN dependency for airgapped demos. (Score: impact medium, effort medium, strategic fit medium, differentiation low, risk low, confidence medium)
- [ ] P2: OpenAPI completeness sweep: add schemas for currently underspecified responses (parity DX improvement). (Score: impact low-medium, effort high, strategic fit medium, differentiation low, risk low, confidence medium)
- [ ] P3: Pagination perf: add composite indexes supporting cursor pagination (`created_at`, `id`) for large seeds. (Score: impact low-medium, effort low, strategic fit medium, differentiation low, risk low, confidence medium)
- [ ] P3: Proxy-aware rate limiting: when `GWSYNTH_TRUST_PROXY=1`, optionally parse RFC 7239 `Forwarded` and/or `X-Real-IP` to align with common reverse proxies. (Score: impact low-medium, effort medium, strategic fit low, differentiation low, risk low-medium, confidence medium)
- [ ] P3: Snapshot caching: add ETag/If-None-Match on `GET /snapshot` to speed repeated demo resets. (Score: impact low-medium, effort medium, strategic fit medium, differentiation low, risk low-medium, confidence medium)

## Implemented
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
- 2026-02-02 Actions failures were GitHub-hosted runner acquisition issues ("job was not acquired by Runner"); latest `main` runs are green.
- Snapshot `mode=replace_tables` intentionally runs with foreign keys enabled: partial restores may cascade-delete dependent rows (safer than leaving DB inconsistent).
- Group membership deduplication needed DB-level enforcement for race safety, not only application-level existence checks.
- API consumer ergonomics improved by returning explicit `404` for missing item scopes instead of silent empty lists.
- Bounded market scan (untrusted): local mock servers commonly treat OpenAPI + interactive docs as baseline DX.
  - WireMock exposes Swagger UI docs at `/__admin/docs` and supports OpenAPI / JSON schema driven APIs: https://wiremock.org/docs/openapi/ and https://wiremock.org/docs/api/
  - Stoplight Prism emphasizes OpenAPI-driven mocking + request validation and dynamic examples: https://github.com/stoplightio/prism
  - Mockoon highlights OpenAPI/Swagger import as a core workflow: https://github.com/mockoon/mockoon
- Bounded market scan (untrusted): interactive docs commonly support persisting auth across refreshes; Swagger UI documents `persistAuthorization` as a config option. (https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration/)
- Bounded market scan (untrusted): Drive/Docs "mock server" repos exist but are typically narrow; a local synthetic org API benefits from strong DX (docs/spec), deterministic fixtures, and safe reset workflows.
  - GoogleDriveMock: https://github.com/nddipiazza/GoogleDriveMock
  - google-drive-mock: https://github.com/pubkey/google-drive-mock
  - googleDocsMock: https://github.com/maxiliarias/googleDocsMock

## Notes
- This file is maintained by the autonomous clone loop.
- Verification evidence for this cycle:
  - `make check` (pass)
  - `make smoke` (pass)
