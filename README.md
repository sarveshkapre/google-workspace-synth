# Google Workspace Synth

Synthetic Google Workspace (Docs/Drive/Sheets) with permissions and sharing APIs. Runs locally with a seeded demo org so you can test workflows, demos, and integrations without real Google accounts.

## What it does
- Creates synthetic users, groups, and Drive items (folders, docs, sheets)
- Stores doc text and sheet cells in SQLite
- Models permissions (user/group/anyone) and share links
- Exposes a clean REST API for local development
- Provides a CLI seeder for repeatable demo data

## Important note
This server ships with no authentication and is intended for local development or demo use only.

## Quickstart

```bash
make setup
make dev
```

Then open:
- Health: http://localhost:8000/health

Seed a demo org:

```bash
make seed
```

## API highlights
- `POST /users`, `GET /users`
- `POST /groups`, `POST /groups/{group_id}/members`
- `POST /items` (folder/doc/sheet)
- `GET /items/{item_id}`
- `PUT /items/{item_id}/content`
- `POST /items/{item_id}/permissions`
- `POST /items/{item_id}/share-links`
- `GET /search?q=...`

## Docker

```bash
docker build -t google-workspace-synth .
docker run -p 8000:8000 google-workspace-synth
```

## Project docs
See `docs/` for architecture, security notes, and workflows.

## License
MIT
