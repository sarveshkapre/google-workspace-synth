# PLAN

## Pitch
Local-first synthetic Google Workspace (Docs/Drive/Sheets) API with permissions + sharing so teams can test integrations and run demos without real Google accounts.

## Features
- REST API for users, groups, group membership, Drive-like items (folders/docs/sheets), permissions, share links, comments, and search.
- SQLite-backed storage (single file) for easy local dev and repeatable demos.
- Deterministic seeding CLI for generating a demo org.
- Quality gates via `ruff`, `mypy`, and `pytest` (`make check`).

## Top Risks / Unknowns
- No authentication (intentionally): must remain clearly documented as local-only.
- Schema evolution: keep migrations simple and snapshot formats versioned.
- Large seeds / large snapshots: SQLite performance and request-size limits need clear defaults and escape hatches.

## Commands
```bash
make setup
make dev
make seed
make test
make lint
make typecheck
make build
make check
```

See `docs/PROJECT.md` for environment variables and workflow notes.

## Shipped
- 2026-02-01: v0.1.0 initial MVP scaffold.
- 2026-02-01: Snapshot export/import (`/snapshot`) + snapshot CLI; configurable HTTP request size cap; basic rate limiting; per-item activity timeline.

## Next
- Pagination + cursor support for large datasets.
- Improve snapshot portability/versioning.
