# PROJECT

## Commands

```bash
make setup
make dev
make seed
make smoke
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
- `GWSYNTH_API_KEY` (optional) - require `Authorization: Bearer ...` or `X-API-Key: ...` (except `/`, `/health`, `/docs`, `/openapi.json`, `/stats`)
- `GWSYNTH_DEBUG` (default: `false`) - enables Flask debug/reloader when running `python -m gwsynth.main`
- `GWSYNTH_HOST` (default: `0.0.0.0`) - bind host for `python -m gwsynth.main`
- `GWSYNTH_PORT` or `PORT` (default: `8000`) - bind port for `python -m gwsynth.main`

## Next 3 improvements
1. Add richer snapshot compatibility guarantees (nullable/optional fill policy + explicit migration notes).
2. Add fully mocked smoke coverage for real Workspace `apply --yes` / `destroy` workflows (no network).
3. Add a small "demo guide" page (examples + curl snippets + recommended seed profiles).
