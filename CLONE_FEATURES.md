# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration
- GitHub Actions run triage (`gh run list`, `gh run view`)

## Candidate Features To Do
- [ ] P1: Snapshot large-export path: add streaming JSON + gzip support for `GET /snapshot` and `python -m gwsynth.snapshot export` (Score: impact high, effort medium, risk low, confidence high).
- [ ] P1: API surface docs: ship an OpenAPI spec plus `GET /openapi.json` and a minimal local `/docs` page (Score: impact high, effort medium, risk low, confidence medium-high).
- [ ] P2: Real-tenant CLI safety: add fully mocked smoke coverage for `gwsynth.real destroy` and (if feasible) `apply --yes` with no network calls (Score: impact medium, effort medium-high, risk medium, confidence medium).
- [ ] P2: Snapshot compatibility: define a nullable/optional column fill policy and record explicit migration notes per snapshot version (Score: impact medium, effort medium, risk low, confidence medium).
- [ ] P3: Add `make smoke` that starts the API and runs a minimal curl-based verification suite (Score: impact medium, effort low, risk low, confidence high).
- [ ] P3: Snapshot ergonomics: auto-gzip exports when `--out` ends in `.gz`, and document recommended large-export flags (Score: impact medium, effort low, risk low, confidence high).
- [ ] P3: Add `GET /` landing page (or extend `/health`) with links to `/docs`, `/openapi.json`, and key env vars for demo ergonomics (Score: impact low-medium, effort low, risk low, confidence high).

## Implemented
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

## Notes
- This file is maintained by the autonomous clone loop.
- Verification evidence for this cycle:
  - `make check` (pass)
  - Local smoke flow: start API + `curl /health`, `curl /snapshot?tables=users,items` (pass)
