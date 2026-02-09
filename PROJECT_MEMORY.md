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

