from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

DEFAULT_BASE_URL = "https://unpkg.com/swagger-ui-dist@5"
ASSETS = ("swagger-ui.css", "swagger-ui-bundle.js")


def _download(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=30) as resp:
        return resp.read()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Download Swagger UI assets for offline /docs usage."
    )
    parser.add_argument(
        "--out",
        default="data/swagger-ui",
        help="Destination directory for vendored assets.",
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help="Swagger UI base URL (defaults to unpkg swagger-ui-dist@5).",
    )
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_url = args.base_url.rstrip("/")

    for asset in ASSETS:
        url = f"{base_url}/{asset}"
        payload = _download(url)
        out_path = out_dir / asset
        out_path.write_bytes(payload)
        print(f"downloaded {url} -> {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
