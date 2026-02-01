from __future__ import annotations

from flask import Flask

from .api import register_routes
from .db import init_db


def create_app() -> Flask:
    app = Flask(__name__)
    init_db()
    register_routes(app)
    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
