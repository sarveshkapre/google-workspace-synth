# PROJECT_MEMORY

Structured, append-only memory for decisions and outcomes.

## Entry Template
- Date:
- Decision:
- Why:
- Evidence:
- Commit:
- Confidence:
- Trust Label: (measured | inferred | speculative)
- Follow-ups:

## Entries
- Date: 2026-02-09
- Decision: Snapshot export/import upgraded to v2 with metadata + schema checks; added `tables=...` filtering and `mode=replace_tables`.
- Why: Large demo datasets and schema evolution require clearer compatibility guarantees and selective restore workflows.
- Evidence: `src/gwsynth/snapshot.py`, `src/gwsynth/api.py`, `tests/test_api.py`, `README.md`, `docs/CHANGELOG.md`, `CHANGELOG.md`; local `make check` pass.
- Commit: d5e0892
- Confidence: High
- Trust Label: measured
- Follow-ups: Consider adding snapshot compression and/or streaming export for very large datasets.

- Date: 2026-02-09
- Decision: Drive appProperties query builder now escapes quotes/backslashes and is deterministic.
- Why: Prevent broken Drive queries when run names/paths include quotes; deterministic queries simplify debugging and testability.
- Evidence: `src/gwsynth/real/google_drive.py`, `tests/test_real_drive_props.py`; local `pytest` pass.
- Commit: cd398a5
- Confidence: High
- Trust Label: measured
- Follow-ups: Validate escape semantics against Drive query edge-cases (newlines/unicode) if encountered in real tenants.

- Date: 2026-02-09
- Decision: Added a mocked `gwsynth.real plan` smoke test and removed `datetime.utcnow()` usage.
- Why: Keep the real-tenant CLI testable without external creds; avoid future runtime warnings/behavior changes on newer Python.
- Evidence: `tests/test_real_cli_plan_smoke.py`, `src/gwsynth/real/cli.py`; local `pytest` pass.
- Commit: 95303c4
- Confidence: Medium-High
- Trust Label: measured
- Follow-ups: Expand smoke coverage to `apply --yes` in a fully mocked mode (no network), or factor dependency injection for clients.

- Date: 2026-02-09
- Decision: Snapshot export now supports streaming compact JSON and gzip compression (API `GET /snapshot?gzip=1` and snapshot CLI `.gz` / `--gzip` / `--compact`).
- Why: Large demo datasets were memory- and transfer-heavy with full in-memory JSON materialization.
- Evidence: `src/gwsynth/snapshot.py`, `src/gwsynth/api.py`, `tests/test_api.py::test_snapshot_gzip_stream`, `tests/test_snapshot_cli.py`; local `make check` pass.
- Commit: 3a58b58
- Confidence: High
- Trust Label: measured
- Follow-ups: Consider adding ETag/If-None-Match for repeated snapshot downloads in demo loops.

- Date: 2026-02-09
- Decision: Added OpenAPI spec (`GET /openapi.json`) and local Swagger UI docs page (`GET /docs`); docs/spec are accessible even when API key auth is enabled.
- Why: Interactive API docs and a machine-readable contract are baseline DX for local API tools and reduce integration friction.
- Evidence: `src/gwsynth/openapi.py`, `src/gwsynth/api.py`, `src/gwsynth/auth.py`, `tests/test_api.py::test_openapi_and_docs_endpoints`; local `make check` pass.
- Commit: ccfc64e
- Confidence: Medium-High
- Trust Label: measured
- Follow-ups: Expand schema detail in the spec for list responses (paged vs unpaged) and item subresources.

- Date: 2026-02-09
- Decision: Default `python -m gwsynth.main` to non-debug; add `GWSYNTH_DEBUG`, `GWSYNTH_HOST`, and `GWSYNTH_PORT`/`PORT` plus `make smoke`.
- Why: Docker/dev-server defaults should be safer and easier to validate; debug/reloader should be opt-in.
- Evidence: `src/gwsynth/main.py`, `Makefile`, `scripts/smoke.py`, `make smoke` output (`smoke ok`).
- Commit: fa367c1
- Confidence: High
- Trust Label: measured
- Follow-ups: If needed for hosting, add structured logging and a production WSGI server option (gunicorn) behind a separate entrypoint.

- Date: 2026-02-09
- Decision: Bounded market scan: OpenAPI-first local mock servers emphasize interactive docs and request validation as baseline UX.
- Why: Helps prioritize emulator UX (docs/spec, validation, repeatable seeds/snapshots) without copying competitor assets.
- Evidence: WireMock OpenAPI docs (https://wiremock.org/docs/openapi/), Prism repo (https://github.com/stoplightio/prism), Mockoon repo (https://github.com/mockoon/mockoon).
- Commit: N/A
- Confidence: Medium
- Trust Label: untrusted
- Follow-ups: Revisit parity expectations quarterly (docs UX, schema validation, export/import ergonomics).

- Date: 2026-02-09
- Decision: Updated CodeQL GitHub Action from v3 to v4.
- Why: CodeQL Action v3 has an announced deprecation timeline; bumping early avoids a future CI outage.
- Evidence: `.github/workflows/codeql.yml`; GitHub Actions run `main ci` passed after change.
- Commit: 709d333
- Confidence: High
- Trust Label: measured
- Follow-ups: None.

- Date: 2026-02-09
- Decision: Added fully mocked smoke coverage for `gwsynth.real apply --yes` and `gwsynth.real destroy --yes` (content-only + all).
- Why: Keep the "real tenant" CLI testable without external creds and reduce regression risk for high-impact flows.
- Evidence: `tests/test_real_cli_apply_destroy_smoke.py`; local `make check` pass.
- Commit: b3b5b32
- Confidence: High
- Trust Label: measured
- Follow-ups: Consider adding a small dependency-injection seam so the CLI can run "mock mode" without monkeypatching.

- Date: 2026-02-09
- Decision: Added `GET /` landing page and allowlisted `/` + `/stats` when `GWSYNTH_API_KEY` is set.
- Why: Improve first-run UX and avoid confusing `401` at the base URL during safer demo setups.
- Evidence: `src/gwsynth/api.py`, `src/gwsynth/auth.py`, `tests/test_api.py`; local `make check` pass.
- Commit: 0d78e4d
- Confidence: High
- Trust Label: measured
- Follow-ups: If API key auth is commonly enabled, consider letting Swagger UI send the key (without storing it).

- Date: 2026-02-09
- Decision: Added snapshot compatibility policy + demo guide docs and linked them from the README.
- Why: Reduce user friction for demos, resets, and schema evolution by making the "happy path" explicit.
- Evidence: `docs/SNAPSHOTS.md`, `docs/DEMO_GUIDE.md`, `README.md`.
- Commit: f52ce76
- Confidence: High
- Trust Label: measured
- Follow-ups: None.

- Date: 2026-02-09
- Decision: Recorded verification evidence for this cycle.
- Why: Keep maintenance work auditable and reproducible.
- Evidence: `make check` (pass), `make smoke` (pass).
- Commit: f52ce76
- Confidence: High
- Trust Label: measured
- Follow-ups: None.

- Date: 2026-02-09
- Decision: Aligned docs with API key allowlist behavior (include `/` and `/stats`).
- Why: Prevent confusion when `GWSYNTH_API_KEY` is enabled and users rely on docs for "what needs auth".
- Evidence: `README.md`, `docs/PROJECT.md`, `docs/SECURITY.md`; local `make check` pass.
- Commit: 7a7f8a9
- Confidence: High
- Trust Label: measured
- Follow-ups: None.

- Date: 2026-02-09
- Decision: Verified CI for the latest `main` commits after pushes.
- Why: Catch regressions early and keep `main` production-ready.
- Evidence: GitHub Actions runs for commit `7a7f8a9` succeeded (`ci`, `codeql`, `gitleaks`); local `make check` pass.
- Commit: 7a7f8a9
- Confidence: High
- Trust Label: measured
- Follow-ups: None.

- Date: 2026-02-09
- Decision: Added OpenAPI `securitySchemes` + global `security` and enabled Swagger UI auth persistence (`persistAuthorization`); `/health` and `/stats` explicitly opt out of auth in-spec via `security: []`.
- Why: Interactive docs are baseline DX; without declared auth schemes, Swagger UI doesn't expose the correct "Authorize" controls and auth is annoying to re-enter during demos.
- Evidence: `src/gwsynth/openapi.py`, `src/gwsynth/api.py`, `tests/test_api.py::test_openapi_and_docs_endpoints`; local `make check` pass.
- Commit: c95498e
- Confidence: High
- Trust Label: measured
- Follow-ups: Consider vendoring Swagger UI assets to remove CDN dependency for offline demos.

- Date: 2026-02-09
- Decision: Rate limiting now returns `Retry-After` on `429` and tests assert rate limit headers on throttled responses.
- Why: Clients need clear backoff guidance; `Retry-After` reduces thundering-herd retry behavior and improves debuggability.
- Evidence: `src/gwsynth/rate_limit.py`, `tests/test_api.py::test_rate_limiting`; local `make check` pass.
- Commit: 98ac98f
- Confidence: High
- Trust Label: measured
- Follow-ups: If we add proxy-aware parsing (RFC 7239 `Forwarded`), ensure spoofing remains impossible when `GWSYNTH_TRUST_PROXY` is off.

- Date: 2026-02-10
- Decision: `POST /snapshot` accepts gzip-compressed JSON (`Content-Encoding: gzip`) with a separate decompressed-size cap (`GWSYNTH_SNAPSHOT_MAX_DECOMPRESSED_BYTES`); `GET /snapshot` uses ETag/If-None-Match to short-circuit repeated exports; oversized bodies return a JSON `413` with an actionable hint.
- Why: Large demo reset loops are a core workflow; gzip import avoids raising the global request-size cap and ETag reduces repeated export overhead.
- Evidence: `src/gwsynth/api.py`, `src/gwsynth/config.py`, `src/gwsynth/main.py`, `src/gwsynth/openapi.py`, `tests/test_api.py`, `docs/DEMO_GUIDE.md`; local `make check` + `make smoke` pass.
- Commit: a8788ec
- Confidence: High
- Trust Label: measured
- Follow-ups: If snapshot ETag collisions or mtime resolution issues show up, consider a lightweight DB change token (not full snapshot hashing).

- Date: 2026-02-10
- Decision: Added composite SQLite indexes to support cursor pagination ordering (`created_at`, `id`) for core list routes.
- Why: Large seeded demo orgs should stay fast under cursor pagination; composite indexes reduce sort cost and improve filtered pagination (items by parent/owner, group members by group, activities by item).
- Evidence: `src/gwsynth/db.py`; local `make check` pass.
- Commit: 5bd5621
- Confidence: Medium-High
- Trust Label: measured
- Follow-ups: If any endpoint becomes a hotspot, run `EXPLAIN QUERY PLAN` for typical seed sizes and tune indexes accordingly.

- Date: 2026-02-10
- Decision: Recorded verification evidence for this maintenance session.
- Why: Keep changes auditable and reproducible.
- Evidence: `make check` (pass), `make smoke` (pass).
- Commit: N/A
- Confidence: High
- Trust Label: measured
- Follow-ups: None.

- Date: 2026-02-09
- Decision: Recorded verification evidence for this maintenance session.
- Why: Keep changes auditable and reproducible.
- Evidence: `make check` (pass), `make smoke` (pass).
- Commit: N/A
- Confidence: High
- Trust Label: measured
- Follow-ups: None.

## Recent Decisions (2026-02-11)
- Date: 2026-02-11
- Decision: Hardened list/search query param validation so malformed `limit`, `cursor`, and filter values return `400` JSON errors.
- Why: Unhandled `ValueError` in several GET routes would otherwise bubble to `500` in production mode.
- Evidence: `src/gwsynth/api.py`, `tests/test_api.py::test_invalid_query_params_return_400`.
- Commit: 52c8cdc
- Confidence: High
- Trust Label: trusted
- Follow-ups: Add pagination contract tests for every paginated route.

- Date: 2026-02-11
- Decision: Removed paginated group-members N+1 lookups with a joined cursor query.
- Why: Large groups caused avoidable per-member user queries.
- Evidence: `src/gwsynth/api.py`, `tests/test_api.py::test_group_members_listing_and_idempotent_add`.
- Commit: 52c8cdc
- Confidence: High
- Trust Label: trusted
- Follow-ups: Add query-plan guardrails for high-cardinality list routes.

- Date: 2026-02-11
- Decision: Added trusted proxy client IP parsing for `Forwarded` and `X-Real-IP` (with existing `X-Forwarded-For`) when `GWSYNTH_TRUST_PROXY=1`.
- Why: Reverse-proxy deployments commonly emit different header conventions.
- Evidence: `src/gwsynth/rate_limit.py`, `tests/test_api.py::test_rate_limiting_prefers_forwarded_header_when_trust_proxy_enabled`, `tests/test_api.py::test_rate_limiting_uses_x_real_ip_as_proxy_fallback`.
- Commit: 52c8cdc
- Confidence: Medium-High
- Trust Label: trusted
- Follow-ups: Document explicit proxy-chain assumptions if multi-hop proxying is introduced.

- Date: 2026-02-11
- Decision: Added offline Swagger UI docs mode (`cdn`/`local`/`auto`) with vendored asset serving and helper script.
- Why: Airgapped/demo environments should not depend on external CDNs.
- Evidence: `src/gwsynth/config.py`, `src/gwsynth/api.py`, `src/gwsynth/auth.py`, `scripts/vendor_swagger_ui.py`, `tests/test_api.py::test_docs_local_mode_uses_vendored_assets`.
- Commit: 52c8cdc
- Confidence: High
- Trust Label: trusted
- Follow-ups: Add smoke coverage for local docs mode in `scripts/smoke.py`.

- Date: 2026-02-11
- Decision: Expanded OpenAPI schemas for high-traffic list/resource responses.
- Why: SDK/demo consumers need stronger contracts than generic `object`/`array` placeholders.
- Evidence: `src/gwsynth/openapi.py`, `tests/test_api.py::test_openapi_and_docs_endpoints`.
- Commit: 52c8cdc
- Confidence: High
- Trust Label: trusted
- Follow-ups: Add explicit `429` response schema + rate-limit headers in OpenAPI.

- Date: 2026-02-11
- Decision: Bounded market scan reaffirmed baseline expectations: OpenAPI-driven mocks emphasize validation/import workflows and docs can be self-hosted.
- Why: Prioritization input for parity features without copying proprietary assets/code.
- Evidence: Stoplight Prism (`https://stoplight.io/open-source/prism`), Mockoon OpenAPI compatibility (`https://mockoon.com/docs/latest/openapi/openapi-specification-compatibility/`), Swagger UI installation/config docs (`https://swagger.io/docs/open-source-tools/swagger-ui/usage/installation/`, `https://swagger.io/docs/open-source-tools/swagger-ui/usage/configuration/`), WireMock OpenAPI validation (`https://docs.wiremock.io/openAPI/openapi-validation`).
- Commit: N/A
- Confidence: Medium
- Trust Label: untrusted
- Follow-ups: Re-run scan quarterly for parity drift.

## Mistakes And Fixes (2026-02-11)
- Root Cause: The `/docs` HTML switched to an f-string and unescaped JS object braces triggered a Python `NameError` (`url`).
- Fix: Escaped JS braces (`{{ ... }}`) inside the f-string.
- Prevention Rule: For f-string HTML/JS templates, immediately run endpoint tests that render the page (`/docs`) before merging.
- Evidence: `tests/test_api.py` failures and subsequent pass in local pytest run.

## Verification Evidence (2026-02-11)
- `gh issue list --state open --limit 50 --json number,title,author,labels,url` -> `[]` (pass; no owner/bot issues to action).
- `gh run list --limit 20 --json ...` (pre-change baseline) -> no failing completed runs (pass).
- `PYTHONPATH=src ./.venv/bin/pytest tests/test_api.py -q` -> `28 passed` (pass).
- `make check` -> Ruff/Mypy/Pytest/compileall all pass (`43 passed`).
- `make smoke` -> `smoke ok` (pass).
