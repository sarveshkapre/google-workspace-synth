# AGENTS

## Purpose
This repo is a local-first synthetic Google Workspace API (Docs/Drive/Sheets) with permissions and sharing. Keep changes small, documented, and fully tested via `make check`.

## Commands
- `make setup` - create venv and install deps
- `make dev` - run API server with auto-reload
- `make seed` - generate demo org data
- `make test` - run unit/integration tests
- `make lint` - ruff lint
- `make typecheck` - mypy
- `make build` - compile sources
- `make check` - lint + typecheck + test + build

## Conventions
- Keep APIs backward compatible when possible.
- Validate inputs; never trust client values.
- Add tests for new endpoints and bug fixes.
- Update `docs/CHANGELOG.md` for user-facing changes.
