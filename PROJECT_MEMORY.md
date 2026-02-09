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

- Date: 2026-02-09
- Decision: Recorded verification evidence for this maintenance session.
- Why: Keep changes auditable and reproducible.
- Evidence: `make check` (pass), `make smoke` (pass).
- Commit: N/A
- Confidence: High
- Trust Label: measured
- Follow-ups: None.
