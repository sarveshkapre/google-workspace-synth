# PLAN

## Goal
Ship a local-first synthetic Google Workspace API (Docs/Drive/Sheets) with permissions and sharing so teams can test integrations and demos without real Google accounts.

## Stack
- Flask for a clean REST API.
- SQLite (via `sqlite3`) for a simple embedded datastore.
- Ruff + Mypy + Pytest for quality gates.

## Architecture
- `gwsynth.main`: Flask app setup and startup hooks.
- `gwsynth.models`: deprecated placeholder (kept for compatibility).
- `gwsynth.api`: API routes and request/response schemas.
- `gwsynth.seed`: CLI to generate deterministic demo orgs.
- SQLite file at `GWSYNTH_DB_PATH` (default `./data/gwsynth.db`).

## MVP checklist
- [ ] CRUD users, groups, and group membership
- [ ] Create/list Drive items (folder/doc/sheet)
- [ ] Update doc text and sheet cell map
- [ ] Permission model: user/group/anyone + role
- [ ] Share links API with tokens
- [ ] Search endpoint (name/content)
- [ ] Seeder CLI
- [ ] Tests + CI `make check`

## Risks
- Data model may expand over time (keep migrations simple).
- Large seeds may be slow on SQLite; keep defaults modest.
- No auth: document clearly that this is for local dev only.

## Non-goals
- Real Google API compatibility.
- Multi-tenant auth or billing.
- Real-time collaboration.
