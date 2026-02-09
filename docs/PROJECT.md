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
- `GWSYNTH_RATE_LIMIT_ENABLED` (default: `true`) - basic in-memory per-IP rate limiter
- `GWSYNTH_RATE_LIMIT_RPM` (default: `600`) - requests per minute
- `GWSYNTH_RATE_LIMIT_BURST` (default: `60`) - burst capacity
- `GWSYNTH_API_KEY` (optional) - require `Authorization: Bearer ...` or `X-API-Key: ...` (except `/health`)

## Next 3 improvements
1. Add snapshot compression and/or streaming export for very large demo datasets.
2. Add integration smoke coverage for real Workspace `apply`/`destroy` workflows (mocked; no network).
3. Add API surface documentation (OpenAPI + minimal local docs page).
