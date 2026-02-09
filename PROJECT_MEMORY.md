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
