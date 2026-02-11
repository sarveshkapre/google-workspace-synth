# SECURITY

## Supported versions
This project is pre-1.0. Security fixes land on `main`.

## Reporting
Please open a GitHub issue with steps to reproduce. Avoid sharing real secrets.

## Threat model notes
- No auth by default: this server is for local development only.
- Inputs are validated, size-limited, and rate-limited in code.
- SQLite file is local; protect it with filesystem permissions.
- If you run this behind a reverse proxy, do not trust client IP headers unless the proxy is trusted.
  Use `GWSYNTH_TRUST_PROXY=true` only when the app is exclusively reachable via that proxy.
  When enabled, the rate limiter uses `Forwarded` (RFC 7239), then `X-Forwarded-For`, then `X-Real-IP`.

## Optional API key
If you set `GWSYNTH_API_KEY`, all endpoints except `/`, `/health`, `/docs`, `/openapi.json`, and `/stats` require either:
- `Authorization: Bearer <key>`
- `X-API-Key: <key>`
