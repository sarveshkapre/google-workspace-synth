# Clone Feature Tracker

## Context Sources
- README and docs
- TODO/FIXME markers in code
- Test and build failures
- Gaps found during codebase exploration
- GitHub Actions run triage (`gh run list`, `gh run view`)

## Candidate Features To Do
- [ ] P1: Improve snapshot portability/versioning guarantees (schema evolution + compatibility checks).
- [ ] P1: Add selective snapshot export/import modes for large demo datasets.
- [ ] P1: Add real Workspace integration smoke tests using mocked Google/Entra/OpenAI clients.
- [ ] P2: Harden Google Drive appProperties query escaping for run names/paths containing quotes.

## Implemented
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
- Historical failing Actions runs in this cycle were canceled runs on older commits; latest `main` runs are green (`ci`, `codeql`, `gitleaks` on commit `45c25b0`).
- Group membership deduplication needed DB-level enforcement for race safety, not only application-level existence checks.
- API consumer ergonomics improved by returning explicit `404` for missing item scopes instead of silent empty lists.

## Notes
- This file is maintained by the autonomous clone loop.
- Verification evidence for this cycle:
  - `make check` (pass)
  - Local smoke flow: start app + `curl /health`, create user/group, add/list group members (pass)
