# UPDATE

## 2026-02-01

### Shipped
- Snapshot export/import for deterministic demo resets:
  - API: `GET /snapshot`, `POST /snapshot?mode=replace`
  - CLI: `PYTHONPATH=src ./.venv/bin/python -m gwsynth.snapshot export|import`
- Default HTTP request size cap via `GWSYNTH_MAX_REQUEST_BYTES` (default: `2000000`).

### Verify
```bash
make check
```

### PR
If `gh` is installed and authenticated:
```bash
git checkout -b feat/snapshots
git push -u origin feat/snapshots
gh pr create --title "Add snapshot export/import" --body "Adds /snapshot endpoints + snapshot CLI, plus configurable request size cap."
```

