"""Cross-cutting HTTP concerns: request IDs, structured logs, security headers,
rate limiting and Prometheus metrics."""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from collections import OrderedDict

from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

log = logging.getLogger("rotawise.http")

REQUESTS = Counter("rotawise_http_requests_total", "HTTP requests", ["method", "route", "status"])
LATENCY = Histogram(
    "rotawise_http_request_seconds", "HTTP request latency", ["route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)
RATE_LIMITED = Counter("rotawise_rate_limited_total", "Requests rejected by the rate limiter")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update(getattr(record, "extra_fields", {}))
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


class TokenBucket:
    """Per-client token bucket. In-memory, so limits are per instance; put a
    shared limiter (Redis or the API gateway) in front when running several."""

    def __init__(self, rate_per_min: int, burst: int, max_clients: int = 10_000) -> None:
        self.rate = rate_per_min / 60.0
        self.burst = burst
        self.max_clients = max_clients
        self._buckets: OrderedDict[str, tuple[float, float]] = OrderedDict()
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            tokens, last = self._buckets.pop(key, (float(self.burst), now))
            tokens = min(self.burst, tokens + (now - last) * self.rate)
            ok = tokens >= 1.0
            self._buckets[key] = (tokens - 1.0 if ok else tokens, now)
            while len(self._buckets) > self.max_clients:  # bounded memory
                self._buckets.popitem(last=False)
            return ok


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Permissions-Policy": "geolocation=(), camera=(), microphone=()",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https://tile.openstreetmap.org https://gibs.earthdata.nasa.gov; "
        "connect-src 'self' https://tile.openstreetmap.org https://gibs.earthdata.nasa.gov; "
        "worker-src 'self' blob:; frame-ancestors 'none'"
    ),
}


def client_ip(request: Request) -> str:
    # Only trust X-Forwarded-For when explicitly running behind a known proxy.
    if os.environ.get("TRUST_PROXY") == "1":
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class ObservabilityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limiter: TokenBucket) -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        rid = request.headers.get("x-request-id") or uuid.uuid4().hex
        rid = rid[:64]
        path = request.url.path
        exempt = path in ("/api/v1/health", "/api/v1/ready", "/metrics")
        if not exempt and not self.limiter.allow(client_ip(request)):
            RATE_LIMITED.inc()
            resp: Response = JSONResponse({"detail": "Too many requests"}, status_code=429, headers={"Retry-After": "10"})
        else:
            start = time.perf_counter()
            try:
                resp = await call_next(request)
            except Exception:
                log.exception("unhandled error", extra={"extra_fields": {"request_id": rid, "path": path}})
                resp = JSONResponse({"detail": "Internal error", "request_id": rid}, status_code=500)
            elapsed = time.perf_counter() - start
            route = request.scope.get("route")
            route_name = getattr(route, "path", "unmatched")
            LATENCY.labels(route_name).observe(elapsed)
            REQUESTS.labels(request.method, route_name, str(resp.status_code)).inc()
            log.info(
                "request",
                extra={"extra_fields": {
                    "request_id": rid, "method": request.method, "route": route_name,
                    "status": resp.status_code, "ms": round(elapsed * 1000, 1),
                }},
            )
        resp.headers["X-Request-ID"] = rid
        for k, v in SECURITY_HEADERS.items():
            if k == "Content-Security-Policy" and path.startswith("/api/docs"):
                continue  # Swagger UI loads its assets from a CDN
            resp.headers.setdefault(k, v)
        return resp
