# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration
- GitHub Actions run triage (`gh run list`, `gh run view`)

## Candidate Features To Do
- [ ] P1: Real-tenant CLI safety: add fully mocked smoke coverage for `gwsynth.real apply --yes` and `gwsynth.real destroy --yes` (content-only + all) with zero network calls (Score: impact high, effort medium, risk low, confidence high).
- [ ] P2: Add `GET /` landing page (allowlisted when `GWSYNTH_API_KEY` is set) linking to `/docs`, `/openapi.json`, `/health`, `/stats`, and showing auth hint + key env var names (Score: impact medium, effort low, risk low, confidence high).
- [ ] P2: Snapshot compatibility policy: document allowed schema evolution + explicit migration notes per snapshot version; add `docs/SNAPSHOTS.md` and link from `README.md` (Score: impact medium, effort low, risk low, confidence high).
- [ ] P2: Demo guide: add `docs/DEMO_GUIDE.md` (seed profiles + curl snippets + typical flows), including a snapshot reset loop pattern (Score: impact medium, effort low, risk low, confidence medium-high).
- [ ] P3: Swagger UI auth ergonomics: support providing API key to the interactive docs UI when `GWSYNTH_API_KEY` is set (Score: impact low-medium, effort medium, risk low, confidence medium).
- [ ] P3: Rate limit proxy awareness: optional trust-proxy mode (use `X-Forwarded-For`) with tests and clear docs (Score: impact low-medium, effort medium, risk medium, confidence medium).

## Implemented
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

## Notes
- This file is maintained by the autonomous clone loop.
- Verification evidence for this cycle:
  - `make check` (pass)
  - `make smoke` (pass)
