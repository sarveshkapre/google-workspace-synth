# PROJECT

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

## Environment
- `GWSYNTH_DB_PATH` (default: `./data/gwsynth.db`)
- `GWSYNTH_SEED` (optional integer for deterministic seeding)
- `GWSYNTH_MAX_REQUEST_BYTES` (default: `2000000`) - max HTTP request body size

## Next 3 improvements
1. Add basic rate limiting (local-safe defaults).
2. Add per-item activity timeline.
3. Add pagination + cursor support for large datasets.
