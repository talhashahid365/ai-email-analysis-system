"""Request ID tracking and security headers middleware."""
import time
import uuid
import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

# ContextVars are defined in logging_config so the entire app shares one source of truth.
# Importing here (not defining) avoids circular imports.
from app.logging_config import request_id_var, user_id_var  # noqa: F401 (re-exported for legacy imports)

log = logging.getLogger('mailnexa.request')


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Attach a unique X-Request-ID to every request and response.

    The ID is also set in ContextVar so all log lines include it.
    """

    async def dispatch(self, request: Request, call_next):
        req_id = str(uuid.uuid4())[:12]
        request_id_var.set(req_id)
        request.state.request_id = req_id

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000, 1)

        response.headers['X-Request-ID'] = req_id

        # Skip logging for health checks to reduce noise
        if request.url.path not in ('/api/health', '/api/health/live'):
            log.info(
                'request',
                extra={
                    'req_id': req_id,
                    'method': request.method,
                    'path': request.url.path,
                    'status': response.status_code,
                    'duration_ms': duration_ms,
                },
            )
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add OWASP-recommended security headers to every response."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Legacy XSS filter (belt-and-suspenders)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Limit referrer leakage
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Disable browser features we don't need
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=()"
        )
        # HSTS — only on HTTPS
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        # API responses should not be cached by shared proxies
        if request.url.path.startswith("/api"):
            if "Cache-Control" not in response.headers:
                response.headers["Cache-Control"] = "private, no-store"

        return response
