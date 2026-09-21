import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from apps.backend.core.observability import REGISTRY

logger = logging.getLogger("workwell.request")


class RequestObservabilityMiddleware(BaseHTTPMiddleware):
    """Assigns a request id, times the request, and emits one structured log
    line per request. The route *template* is used as the metric label, not
    the raw path, so employee ids in URLs never become metric cardinality
    (or leak into a metrics endpoint that is not consent-gated)."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id

        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration = time.perf_counter() - start
            route = request.scope.get("route")
            path_template = getattr(route, "path", request.url.path)

            labels = {"method": request.method, "path": path_template}
            REGISTRY.observe("workwell_http_request_duration_seconds", duration, labels)
            REGISTRY.increment(
                "workwell_http_requests_total", {**labels, "status": str(status_code)}
            )

            logger.info(
                "request",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": path_template,
                    "status_code": status_code,
                    "duration_ms": round(duration * 1000, 2),
                },
            )
