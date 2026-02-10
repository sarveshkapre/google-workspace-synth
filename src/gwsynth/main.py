from __future__ import annotations

import os
from typing import Any

from flask import Flask, jsonify
from werkzeug.exceptions import RequestEntityTooLarge

from .api import register_routes
from .auth import install_api_key_auth
from .config import (
    api_key,
    max_request_bytes,
    rate_limit_burst,
    rate_limit_enabled,
    rate_limit_requests_per_minute,
    trust_proxy,
)
from .db import init_db
from .rate_limit import RateLimitConfig, install_rate_limiter


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = max_request_bytes()

    @app.errorhandler(RequestEntityTooLarge)
    def handle_request_too_large(exc: RequestEntityTooLarge) -> tuple[Any, int]:
        # Flask raises this before route handlers run; return JSON with an actionable hint.
        return (
            jsonify(
                {
                    "error": "Request entity too large",
                    "hint": (
                        "Raise GWSYNTH_MAX_REQUEST_BYTES. For large snapshots, use "
                        "Content-Encoding: gzip on POST /snapshot."
                    ),
                }
            ),
            413,
        )

    init_db()
    install_api_key_auth(app, api_key())
    install_rate_limiter(
        app,
        RateLimitConfig(
            enabled=rate_limit_enabled(),
            requests_per_minute=rate_limit_requests_per_minute(),
            burst=rate_limit_burst(),
            trust_proxy=trust_proxy(),
        ),
    )
    register_routes(app)
    return app


app = create_app()


if __name__ == "__main__":
    debug = os.environ.get("GWSYNTH_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}
    host = os.environ.get("GWSYNTH_HOST", "0.0.0.0")
    port_raw = os.environ.get("GWSYNTH_PORT") or os.environ.get("PORT") or "8000"
    try:
        port = int(port_raw)
    except ValueError:
        port = 8000

    # Default to non-debug for safer Docker/demo usage. `make dev` enables debug explicitly.
    app.run(host=host, port=port, debug=debug)
