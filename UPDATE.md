# UPDATE

## 2026-02-01

### Shipped
- Snapshot export/import for deterministic demo resets:
  - API: `GET /snapshot`, `POST /snapshot?mode=replace`
  - CLI: `PYTHONPATH=src ./.venv/bin/python -m gwsynth.snapshot export|import`
- Default HTTP request size cap via `GWSYNTH_MAX_REQUEST_BYTES` (default: `2000000`).
- Basic in-memory per-IP rate limiting via `GWSYNTH_RATE_LIMIT_*`.
- Per-item activity timeline via `GET /items/<item_id>/activity`.

### Verify
```bash
make check
```

### Notes
- Working directly on `main` (no PR workflow).
