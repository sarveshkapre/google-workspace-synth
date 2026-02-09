from __future__ import annotations

import gzip
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path


def _free_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])
    finally:
        sock.close()


def _http_get(url: str, *, timeout_s: float = 2.0) -> tuple[int, dict[str, str], bytes]:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        headers = {k: v for k, v in resp.headers.items()}
        body = resp.read()
        return int(resp.status), headers, body


def main() -> int:
    port = _free_port()
    base = f"http://127.0.0.1:{port}"

    with tempfile.TemporaryDirectory(prefix="gwsynth-smoke-") as td:
        db_path = str(Path(td) / "gwsynth.db")
        env = os.environ.copy()
        env.update(
            {
                "GWSYNTH_DB_PATH": db_path,
                "GWSYNTH_HOST": "127.0.0.1",
                "GWSYNTH_PORT": str(port),
                "GWSYNTH_DEBUG": "0",
                "GWSYNTH_RATE_LIMIT_ENABLED": "0",
            }
        )

        proc = subprocess.Popen(
            [sys.executable, "-m", "gwsynth.main"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        try:
            deadline = time.time() + 8.0
            last_err: str | None = None
            while time.time() < deadline:
                try:
                    status, _, _ = _http_get(f"{base}/health", timeout_s=0.5)
                    if status == 200:
                        break
                except Exception as exc:  # noqa: BLE001 - smoke script; keep it simple
                    last_err = str(exc)
                    time.sleep(0.1)
            else:
                output = proc.stdout.read() if proc.stdout else ""
                raise SystemExit(
                    f"server did not become healthy within timeout (last_err={last_err})\n{output}"
                )

            status, _, body = _http_get(f"{base}/openapi.json")
            if status != 200:
                raise SystemExit(f"/openapi.json returned {status}")
            spec = json.loads(body.decode("utf-8"))
            if not isinstance(spec, dict) or "openapi" not in spec:
                raise SystemExit("openapi spec did not look like a JSON object")

            status, headers, body = _http_get(f"{base}/snapshot?gzip=1&tables=users,items")
            if status != 200:
                raise SystemExit(f"/snapshot?gzip=1 returned {status}")
            if headers.get("Content-Encoding") != "gzip":
                raise SystemExit("expected gzip Content-Encoding for snapshot")
            snap = json.loads(gzip.decompress(body).decode("utf-8"))
            if snap.get("snapshot_version") != 2:
                raise SystemExit(f"unexpected snapshot_version: {snap.get('snapshot_version')}")

            print("smoke ok")
            return 0
        finally:
            try:
                proc.send_signal(signal.SIGTERM)
            except Exception:
                pass
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
