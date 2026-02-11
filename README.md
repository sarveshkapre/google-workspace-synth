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
- API docs (Swagger UI): http://localhost:8000/docs
- OpenAPI spec: http://localhost:8000/openapi.json

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
- `GWSYNTH_SNAPSHOT_MAX_DECOMPRESSED_BYTES` (default: `50000000`) - max decompressed bytes for `POST /snapshot` when using `Content-Encoding: gzip`
- `GWSYNTH_RATE_LIMIT_ENABLED` (default: `true`) - basic in-memory per-IP rate limiter
- `GWSYNTH_RATE_LIMIT_RPM` (default: `600`) - requests per minute
- `GWSYNTH_RATE_LIMIT_BURST` (default: `60`) - burst capacity
- `GWSYNTH_TRUST_PROXY` (default: `false`) - if `true`, trust proxy IP headers (`Forwarded`, `X-Forwarded-For`, `X-Real-IP`) for rate limiting; only enable behind a trusted reverse proxy
- `GWSYNTH_SWAGGER_UI_MODE` (default: `cdn`) - docs asset source: `cdn`, `local`, or `auto`
- `GWSYNTH_SWAGGER_UI_LOCAL_DIR` (default: `./data/swagger-ui`) - local directory for vendored Swagger UI assets
- `GWSYNTH_SWAGGER_UI_CDN_BASE_URL` (default: `https://unpkg.com/swagger-ui-dist@5`) - CDN base when docs mode resolves to CDN
- `GWSYNTH_API_KEY` (optional) - require `Authorization: Bearer ...` or `X-API-Key: ...` (except `/`, `/health`, `/docs`, `/openapi.json`, `/stats`)
- `GWSYNTH_DEBUG` (default: `false`) - enables Flask debug/reloader when running `python -m gwsynth.main`
- `GWSYNTH_HOST` (default: `0.0.0.0`) - bind host for `python -m gwsynth.main`
- `GWSYNTH_PORT` or `PORT` (default: `8000`) - bind port for `python -m gwsynth.main`

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

## Offline API docs (airgapped demos)
Vendor Swagger UI assets once:

```bash
PYTHONPATH=src ./.venv/bin/python scripts/vendor_swagger_ui.py --out data/swagger-ui
```

Then run with local docs assets:

```bash
GWSYNTH_SWAGGER_UI_MODE=local make dev
```

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

Export only selected tables (useful for large datasets):

```bash
curl -s "http://localhost:8000/snapshot?tables=users,items" > snapshot.json
```

Export a gzip-compressed snapshot (recommended for very large datasets):

```bash
curl -s "http://localhost:8000/snapshot?gzip=1" > snapshot.json.gz
python -c "import gzip,sys; sys.stdout.buffer.write(gzip.decompress(open('snapshot.json.gz','rb').read()))" > snapshot.json
```

Import (replaces current DB contents):

```bash
curl -s -X POST "http://localhost:8000/snapshot?mode=replace" \\
  -H "content-type: application/json" \\
  --data-binary @snapshot.json
```

Import a gzip-compressed snapshot directly (recommended for large snapshots):

```bash
curl -s -X POST "http://localhost:8000/snapshot?mode=replace" \\
  -H "content-type: application/json" \\
  -H "content-encoding: gzip" \\
  --data-binary @snapshot.json.gz
```

Import only selected tables:

```bash
curl -s -X POST "http://localhost:8000/snapshot?mode=replace_tables&tables=users,items" \\
  -H "content-type: application/json" \\
  --data-binary @snapshot.json
```

Or export/import directly from the SQLite DB:

```bash
PYTHONPATH=src ./.venv/bin/python -m gwsynth.snapshot export --out snapshot.json
PYTHONPATH=src ./.venv/bin/python -m gwsynth.snapshot export --out subset.json --tables users,items
PYTHONPATH=src ./.venv/bin/python -m gwsynth.snapshot export --out snapshot.json.gz
PYTHONPATH=src ./.venv/bin/python -m gwsynth.snapshot export --out snapshot.compact.json.gz --compact
PYTHONPATH=src ./.venv/bin/python -m gwsynth.snapshot import --in snapshot.json --mode replace
PYTHONPATH=src ./.venv/bin/python -m gwsynth.snapshot import --in subset.json --mode replace_tables --tables users,items
PYTHONPATH=src ./.venv/bin/python -m gwsynth.snapshot import --in snapshot.json.gz --mode replace
```

## Docker

```bash
docker build -t google-workspace-synth .
docker run -p 8000:8000 google-workspace-synth
```

## Project docs
- `docs/PROJECT.md` - commands, environment, and the short "next improvements" list
- `docs/DEMO_GUIDE.md` - seed profiles + curl flows + snapshot reset loop
- `docs/SNAPSHOTS.md` - snapshot format, compatibility policy, and migration notes
- `docs/SECURITY.md` - threat model notes and optional API key auth
- `docs/ROADMAP.md` - upcoming work

## License
MIT
