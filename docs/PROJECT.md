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

## Next 3 improvements
1. Add request-id correlation (`X-Request-Id`) to responses/error payloads for easier troubleshooting.
2. Add API pagination contract tests that assert `400` behavior across all paginated routes.
3. Add OpenAPI docs for `429` responses and rate-limit headers (`Retry-After`, `X-RateLimit-*`).
