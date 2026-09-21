import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from apps.backend.core.config import get_settings
from apps.backend.core.redis_client import get_redis

# Auth endpoints get a tighter budget than the rest of the API: they are the
# ones worth brute-forcing.
DEFAULT_LIMIT_PER_MINUTE = 120
AUTH_LIMIT_PER_MINUTE = 10
AUTH_PATHS = ("/auth/login",)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
        )
        # The API serves JSON, never HTML, so a maximally restrictive CSP is
        # safe here and blunts any reflected-content mistake.
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'")
        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Fixed-window rate limiting backed by Redis so the budget is shared
    across API replicas rather than per-process.

    Fails open: if Redis is unavailable the request is allowed through. A
    wellness tool that locks employees out because a cache is down is worse
    than one that briefly loses rate limiting, and the limiter is defence in
    depth rather than the only control.
    """

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/metrics"):
            return await call_next(request)

        identity = self._identity(request)
        limit = AUTH_LIMIT_PER_MINUTE if request.url.path in AUTH_PATHS else DEFAULT_LIMIT_PER_MINUTE
        window = int(time.time() // 60)
        key = f"ratelimit:{identity}:{request.url.path}:{window}"

        try:
            redis = get_redis()
            count = redis.incr(key)
            if count == 1:
                redis.expire(key, 90)
        except Exception:
            return await call_next(request)

        if count > limit:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded. Try again shortly."},
                headers={"Retry-After": "60"},
            )

        return await call_next(request)

    @staticmethod
    def _identity(request: Request) -> str:
        # Bucket by token when present so one noisy client cannot exhaust the
        # budget for everyone behind the same NAT/proxy address.
        auth = request.headers.get("Authorization")
        if auth:
            return f"token:{hash(auth) & 0xFFFFFFFF}"
        client = request.client
        return f"ip:{client.host if client else 'unknown'}"


def rate_limiting_enabled() -> bool:
    return not get_settings().is_test
