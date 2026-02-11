from __future__ import annotations

import math
import time
from dataclasses import dataclass
from threading import Lock

from flask import Flask, Response, g, jsonify, request


@dataclass
class RateLimitConfig:
    enabled: bool
    requests_per_minute: int
    burst: int
    trust_proxy: bool = False


class _Bucket:
    def __init__(self, capacity: int, refill_per_second: float) -> None:
        self.capacity = capacity
        self.refill_per_second = refill_per_second
        self.tokens = float(capacity)
        self.last_refill = time.monotonic()
        self.last_seen = self.last_refill

    def _refill(self, now: float) -> None:
        elapsed = now - self.last_refill
        if elapsed <= 0:
            return
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_per_second)
        self.last_refill = now

    def consume(self, now: float, amount: float = 1.0) -> bool:
        self._refill(now)
        self.last_seen = now
        if self.tokens >= amount:
            self.tokens -= amount
            return True
        return False

    def remaining(self, now: float) -> int:
        self._refill(now)
        return max(0, int(self.tokens))

    def retry_after_seconds(self, now: float, amount: float = 1.0) -> int:
        """
        Best-effort Retry-After in seconds for token-bucket throttling.

        Uses a ceil so clients don't retry too early.
        """
        self._refill(now)
        if self.tokens >= amount:
            return 0
        if self.refill_per_second <= 0:
            return 60
        needed = (amount - self.tokens) / self.refill_per_second
        return max(1, int(math.ceil(needed)))


class RateLimiter:
    def __init__(self, config: RateLimitConfig) -> None:
        self._config = config
        self._lock = Lock()
        self._buckets: dict[str, _Bucket] = {}
        self._requests_since_prune = 0

    @staticmethod
    def _first_csv_token(value: str) -> str | None:
        for token in value.split(","):
            part = token.strip()
            if part:
                return part
        return None

    @staticmethod
    def _strip_ip_port(value: str) -> str | None:
        text = value.strip().strip('"')
        if not text or text.lower() == "unknown":
            return None

        if text.startswith("["):
            end = text.find("]")
            if end <= 1:
                return None
            return text[1:end]

        if text.count(":") == 1:
            host, maybe_port = text.rsplit(":", 1)
            if maybe_port.isdigit() and host:
                return host
        return text

    @classmethod
    def _forwarded_for(cls, header_value: str) -> str | None:
        for forwarded_entry in header_value.split(","):
            for pair in forwarded_entry.split(";"):
                key, sep, value = pair.partition("=")
                if sep != "=":
                    continue
                if key.strip().lower() != "for":
                    continue
                parsed = cls._strip_ip_port(value)
                if parsed:
                    return parsed
        return None

    def _trusted_proxy_ip(self) -> str | None:
        forwarded = request.headers.get("Forwarded", "")
        if forwarded:
            parsed = self._forwarded_for(forwarded)
            if parsed:
                return parsed

        x_forwarded_for = request.headers.get("X-Forwarded-For", "")
        if x_forwarded_for:
            parsed = self._strip_ip_port(self._first_csv_token(x_forwarded_for) or "")
            if parsed:
                return parsed

        x_real_ip = request.headers.get("X-Real-IP", "")
        if x_real_ip:
            parsed = self._strip_ip_port(x_real_ip)
            if parsed:
                return parsed
        return None

    def _key(self) -> str:
        if self._config.trust_proxy:
            # Only trust proxy headers when the server is exclusively behind a trusted proxy.
            proxy_ip = self._trusted_proxy_ip()
            if proxy_ip:
                return proxy_ip
        return request.remote_addr or "unknown"

    def _get_bucket(self, key: str) -> _Bucket:
        rpm = self._config.requests_per_minute
        burst = self._config.burst
        refill_per_second = rpm / 60.0
        bucket = self._buckets.get(key)
        if bucket is None:
            bucket = _Bucket(capacity=burst, refill_per_second=refill_per_second)
            self._buckets[key] = bucket
        return bucket

    def _prune(self, now: float) -> None:
        self._requests_since_prune += 1
        if self._requests_since_prune < 250:
            return
        self._requests_since_prune = 0
        if len(self._buckets) < 1_000:
            return
        cutoff = now - 60.0 * 10.0
        self._buckets = {k: b for k, b in self._buckets.items() if b.last_seen >= cutoff}

    def check(self) -> Response | None:
        if not self._config.enabled:
            return None

        path = request.path
        if path == "/health":
            return None

        now = time.monotonic()
        with self._lock:
            self._prune(now)
            bucket = self._get_bucket(self._key())
            allowed = bucket.consume(now, 1.0)
            remaining = bucket.remaining(now)
            retry_after = 0 if allowed else bucket.retry_after_seconds(now, 1.0)

        g._gwsynth_rate_limit = {
            "limit": self._config.requests_per_minute,
            "remaining": remaining,
            "retry_after": retry_after,
        }

        if allowed:
            return None

        response_obj = jsonify({"error": "Rate limit exceeded"})
        response_obj.status_code = 429
        return response_obj


def install_rate_limiter(app: Flask, config: RateLimitConfig) -> None:
    limiter = RateLimiter(config)

    @app.before_request
    def _rate_limit() -> Response | None:
        return limiter.check()

    @app.after_request
    def _rate_limit_headers(response: Response) -> Response:
        meta = getattr(g, "_gwsynth_rate_limit", None)
        if isinstance(meta, dict):
            limit = meta.get("limit")
            remaining = meta.get("remaining")
            retry_after = meta.get("retry_after")
            if isinstance(limit, int):
                response.headers["X-RateLimit-Limit"] = str(limit)
            if isinstance(remaining, int):
                response.headers["X-RateLimit-Remaining"] = str(remaining)
            if (
                response.status_code == 429
                and isinstance(retry_after, int)
                and retry_after > 0
            ):
                response.headers["Retry-After"] = str(retry_after)
        return response
