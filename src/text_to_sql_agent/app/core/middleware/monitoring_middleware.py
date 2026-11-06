"""
Lightweight in-process request metrics, exposed at GET /metrics-summary as
JSON for now. Swap the `_counters` dict for a prometheus_client Counter/
Histogram (or OTel Meter) when Prometheus/App Insights metrics are wired
up - the middleware hook point doesn't need to change.
"""
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

_counters: dict[str, int] = defaultdict(int)
_latency_ms_total: dict[str, float] = defaultdict(float)


class MonitoringMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        key = f"{request.method} {request.url.path}"
        _counters[key] += 1
        _latency_ms_total[key] += duration_ms

        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"
        return response


def get_metrics_summary() -> dict:
    return {
        route: {
            "count": count,
            "avg_latency_ms": round(_latency_ms_total[route] / count, 2),
        }
        for route, count in _counters.items()
    }
