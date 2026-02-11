from __future__ import annotations

import secrets

from flask import Flask, Response, jsonify, request


def install_api_key_auth(app: Flask, api_key: str | None) -> None:
    if not api_key:
        return

    # Routes that stay accessible for demo ergonomics even when an API key is set.
    allow_paths = {"/", "/health", "/docs", "/openapi.json", "/stats"}

    @app.before_request
    def _require_api_key() -> Response | None:
        if request.path in allow_paths or request.path.startswith("/docs-assets/"):
            return None

        provided = request.headers.get("X-API-Key")
        if not provided:
            auth = request.headers.get("Authorization", "")
            if auth.lower().startswith("bearer "):
                provided = auth[7:].strip()

        if not provided or not secrets.compare_digest(provided, api_key):
            response = jsonify({"error": "Unauthorized"})
            response.status_code = 401
            response.headers["WWW-Authenticate"] = "Bearer"
            return response

        return None
