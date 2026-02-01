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

## Next 3 improvements
1. Add export/import for synthetic org snapshots.
2. Add basic rate limiting and request size caps.
3. Add per-item activity timeline.
