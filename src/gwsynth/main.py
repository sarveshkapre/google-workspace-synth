from __future__ import annotations

from flask import Flask

from .api import register_routes
from .config import (
    max_request_bytes,
    rate_limit_burst,
    rate_limit_enabled,
    rate_limit_requests_per_minute,
)
from .db import init_db
from .rate_limit import RateLimitConfig, install_rate_limiter


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = max_request_bytes()
    init_db()
    install_rate_limiter(
        app,
        RateLimitConfig(
            enabled=rate_limit_enabled(),
            requests_per_minute=rate_limit_requests_per_minute(),
            burst=rate_limit_burst(),
        ),
    )
    register_routes(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
