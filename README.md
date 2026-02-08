# Google Workspace Synth

Synthetic Google Workspace (Docs/Drive/Sheets) with permissions and sharing APIs. Runs locally with a seeded demo org so you can test workflows, demos, and integrations without real Google accounts.

## What it does
- Creates synthetic users, groups, and Drive items (folders, docs, sheets)
- Stores doc text and sheet cells in SQLite
- Models permissions (user/group/anyone) and share links
- Exposes a clean REST API for local development
- Provides a CLI seeder for repeatable demo data

## Important note
This server is intended for local development or demo use only. It ships with no authentication by
default, but supports an optional API key for safer demos.

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

Enterprise-style seed (multiple shared drives, personal drives, and history):

```bash
PYTHONPATH=src ./.venv/bin/python -m gwsynth.seed \
  --company-name "Northwind Labs" \
  --domain "northwind.test" \
  --shared-drives 3 \
  --personal-docs 3 \
  --personal-sheets 2 \
  --history-days 120
```

## Real Workspace CLI (Drive/Docs)
This repo includes an optional CLI that seeds a real Google Workspace tenant (Drive + Docs)
using Entra as the identity source. It is separate from the local emulator API.

Create a starter blueprint:

```bash
PYTHONPATH=src ./.venv/bin/python -m gwsynth.real init-blueprint --out blueprint.yaml
```

Plan changes:

```bash
PYTHONPATH=src ./.venv/bin/python -m gwsynth.real plan --blueprint blueprint.yaml
```

Apply changes (requires explicit `--yes`):

```bash
PYTHONPATH=src ./.venv/bin/python -m gwsynth.real apply --blueprint blueprint.yaml --yes
```

Required environment variables (see blueprint for full details):
- `ENTRA_TENANT_ID`, `ENTRA_CLIENT_ID`, `ENTRA_CLIENT_SECRET`
- `GOOGLE_SA_JSON`, `GOOGLE_ADMIN_SUBJECT`, `GOOGLE_CUSTOMER_ID`, `GOOGLE_DOMAIN`
- `OPENAI_API_KEY` (optional, for GPT-generated content)

## Environment
- `GWSYNTH_DB_PATH` (default: `./data/gwsynth.db`)
- `GWSYNTH_SEED` (optional integer for deterministic seeding)
- `GWSYNTH_MAX_REQUEST_BYTES` (default: `2000000`) - max HTTP request body size
- `GWSYNTH_RATE_LIMIT_ENABLED` (default: `true`) - basic in-memory per-IP rate limiter
- `GWSYNTH_RATE_LIMIT_RPM` (default: `600`) - requests per minute
- `GWSYNTH_RATE_LIMIT_BURST` (default: `60`) - burst capacity
- `GWSYNTH_API_KEY` (optional) - require `Authorization: Bearer ...` or `X-API-Key: ...` (except `/health`)

## Seeder profiles
The seeder can model a fictional enterprise org with multiple shared drives, personal drives, and a
history timeline. Key flags:
- `--profile` (`engineering` or `default`) controls shared drive + group naming.
- `--company-name` and `--domain` align user emails and drive names to a fictional company.
- `--shared-drives` creates multiple shared drive roots.
- `--personal-drives` / `--no-personal-drives` toggles per-user My Drives.
- `--personal-docs` / `--personal-sheets` set per-user document counts.
- `--history-days` controls how far back synthetic activity timestamps go.

## API highlights
- `POST /users`, `GET /users`
- `POST /groups`, `POST /groups/{group_id}/members`
- `GET /groups/{group_id}/members`
- `POST /items` (folder/doc/sheet)
- `GET /items/{item_id}`
- `PUT /items/{item_id}/content`
- `POST /items/{item_id}/permissions`
- `POST /items/{item_id}/share-links`
- `GET /items/{item_id}/activity` (simple audit/activity timeline)
- `GET /snapshot`, `POST /snapshot` (export/import seeded demo org snapshots)
- `GET /search?q=...`

## Pagination
Most list endpoints support optional cursor pagination via:
- `?limit=...` (1–200)
- `?cursor=...` (from `next_cursor`)

When `limit` is provided, responses include `next_cursor` when there is another page.

## Filtering
- `GET /items` supports `parent_id`, `owner_user_id`, and `item_type` (folder/doc/sheet), and these compose with pagination.

## Snapshots (export/import)

Export a full org snapshot via API:

```bash
curl -s http://localhost:8000/snapshot > snapshot.json
```

Import (replaces current DB contents):

```bash
curl -s -X POST "http://localhost:8000/snapshot?mode=replace" \\
  -H "content-type: application/json" \\
  --data-binary @snapshot.json
```

Or export/import directly from the SQLite DB:

```bash
PYTHONPATH=src ./.venv/bin/python -m gwsynth.snapshot export --out snapshot.json
PYTHONPATH=src ./.venv/bin/python -m gwsynth.snapshot import --in snapshot.json --mode replace
```

## Docker

```bash
docker build -t google-workspace-synth .
docker run -p 8000:8000 google-workspace-synth
```

## Project docs
See `docs/` for architecture, security notes, and workflows.

## License
MIT
