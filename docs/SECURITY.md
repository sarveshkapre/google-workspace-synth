# SECURITY

## Supported versions
This project is pre-1.0. Security fixes land on `main`.

## Reporting
Please open a GitHub issue with steps to reproduce. Avoid sharing real secrets.

## Threat model notes
- No auth by default: this server is for local development only.
- Inputs are validated, size-limited, and rate-limited in code.
- SQLite file is local; protect it with filesystem permissions.

## Optional API key
If you set `GWSYNTH_API_KEY`, all endpoints except `/health`, `/docs`, and `/openapi.json` require either:
- `Authorization: Bearer <key>`
- `X-API-Key: <key>`
