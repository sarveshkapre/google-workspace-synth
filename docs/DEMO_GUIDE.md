# Demo Guide

This guide is a quick, repeatable way to spin up a realistic demo org, exercise key flows, and reset
state between runs.

## Start + Seed

```bash
make setup
make dev
make seed
```

If you want a more enterprise-style org, use the seed CLI:

```bash
PYTHONPATH=src ./.venv/bin/python -m gwsynth.seed \
  --company-name "Northwind Labs" \
  --domain "northwind.test" \
  --shared-drives 3 \
  --personal-docs 3 \
  --personal-sheets 2 \
  --history-days 120
```

## Typical API Flow (Curl)

```bash
BASE=http://localhost:8000

# Create a user
USER_ID=$(curl -s -X POST "$BASE/users" \
  -H 'content-type: application/json' \
  -d '{"email":"demo@example.com","display_name":"Demo User"}' | jq -r .id)

# Create a group
GROUP_ID=$(curl -s -X POST "$BASE/groups" \
  -H 'content-type: application/json' \
  -d '{"name":"Team","description":"Core team"}' | jq -r .id)

# Add membership (idempotent)
curl -s -X POST "$BASE/groups/$GROUP_ID/members" \
  -H 'content-type: application/json' \
  -d "{\"user_id\":\"$USER_ID\"}" >/dev/null

# Create a folder + doc
FOLDER_ID=$(curl -s -X POST "$BASE/items" \
  -H 'content-type: application/json' \
  -d "{\"name\":\"Root\",\"item_type\":\"folder\",\"owner_user_id\":\"$USER_ID\"}" | jq -r .id)

DOC_ID=$(curl -s -X POST "$BASE/items" \
  -H 'content-type: application/json' \
  -d "{\"name\":\"Spec\",\"item_type\":\"doc\",\"parent_id\":\"$FOLDER_ID\",\"owner_user_id\":\"$USER_ID\",\"content_text\":\"Hello\"}" | jq -r .id)

# Share with the group
curl -s -X POST "$BASE/items/$DOC_ID/permissions" \
  -H 'content-type: application/json' \
  -d "{\"principal_type\":\"group\",\"principal_id\":\"$GROUP_ID\",\"role\":\"viewer\"}" >/dev/null

# Create a share link
curl -s -X POST "$BASE/items/$DOC_ID/share-links" \
  -H 'content-type: application/json' \
  -d '{"role":"viewer"}' | jq .

# Search (name + content)
curl -s "$BASE/search?q=Spec" | jq .
```

Note: this guide uses `jq` for convenience.

## Snapshot Reset Loop (Fast Demos)

One good workflow is:
1. Seed once.
2. Export a snapshot.
3. Before every demo run, import the same snapshot to reset the world instantly.

```bash
BASE=http://localhost:8000

# After seeding:
curl -s "$BASE/snapshot?gzip=1" > snapshot.json.gz

# Before each demo run:
curl -s -X POST "$BASE/snapshot?mode=replace" \
  -H 'content-type: application/json' \
  -H 'content-encoding: gzip' \
  --data-binary @snapshot.json.gz | jq .
```

## Optional API Key (Safer Demos)

If you want to avoid accidental access during a screen share:

```bash
export GWSYNTH_API_KEY=dev-secret
make dev
```

Then use one of:
- `X-API-Key: dev-secret`
- `Authorization: Bearer dev-secret`

The docs/spec stay accessible at `/`, `/docs`, `/openapi.json`, `/health`, and `/stats`.
