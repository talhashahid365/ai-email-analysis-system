"""Sliding-window rate limiter.

Uses Redis when REDIS_URL is configured (required for multi-worker/production).
Falls back to in-memory store for local development ONLY.

For production: set REDIS_URL=redis://localhost:6379/0 in your .env file.
"""
import time
import logging
from collections import defaultdict, deque
from typing import Deque, Dict, Optional, Tuple

from fastapi import HTTPException, Request, status

from app.config import settings

log = logging.getLogger("mailnexa.ratelimit")

# ── In-memory fallback (single process only) ──────────────────────────────────
_memory_store: Dict[Tuple[str, str], Deque[float]] = defaultdict(deque)


def reset_rate_limits() -> None:
    """Clear all rate limit counters (used in tests)."""
    _memory_store.clear()


# ── Redis backend (for production / multi-worker) ─────────────────────────────
_redis_client: Optional[object] = None


def _get_redis():
    global _redis_client
    if _redis_client is None and settings.REDIS_URL:
        try:
            import redis
            _redis_client = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
            _redis_client.ping()
            log.info("Rate limiter: using Redis backend (%s)", settings.REDIS_URL)
        except Exception as exc:
            log.warning("Rate limiter: Redis unavailable (%s), falling back to in-memory", exc)
            _redis_client = None
    return _redis_client


def _check_redis(key: str, limit: int, window_seconds: int) -> Tuple[bool, int]:
    """Sliding window check via Redis sorted set. Returns (allowed, retry_after)."""
    r = _get_redis()
    if r is None:
        return True, 0

    now = time.time()
    pipe = r.pipeline()
    pipe.zremrangebyscore(key, 0, now - window_seconds)
    pipe.zcard(key)
    pipe.zadd(key, {str(now): now})
    pipe.expire(key, window_seconds)
    results = pipe.execute()

    count = results[1]  # count BEFORE adding current request
    if count >= limit:
        # Find oldest entry to calculate retry_after
        oldest = r.zrange(key, 0, 0, withscores=True)
        if oldest:
            retry = max(1, int(window_seconds - (now - oldest[0][1])))
        else:
            retry = window_seconds
        r.zrem(key, str(now))  # don't count this blocked request
        return False, retry
    return True, 0


def _check_memory(key: Tuple[str, str], limit: int, window_seconds: int) -> Tuple[bool, int]:
    """Sliding window check in memory. Single-process only."""
    now = time.monotonic()
    q = _memory_store[key]
    while q and now - q[0] > window_seconds:
        q.popleft()
    if len(q) >= limit:
        retry = max(1, int(window_seconds - (now - q[0])))
        return False, retry
    q.append(now)
    return True, 0


def rate_limit(scope: str, per_minute_attr: str, window_seconds: int = 60):
    """FastAPI dependency that enforces a sliding-window rate limit.

    Args:
        scope: Identifier for this limit bucket (e.g. "auth", "ai")
        per_minute_attr: Name of the Settings attribute holding the limit count
        window_seconds: Time window in seconds (default: 60)
    """
    def dependency(request: Request):
        if not settings.RATE_LIMIT_ENABLED:
            return

        limit = getattr(settings, per_minute_attr, 60)
        ident = (request.client.host if request.client else "unknown")

        r = _get_redis()
        if r is not None:
            redis_key = f"rl:{scope}:{ident}"
            allowed, retry = _check_redis(redis_key, limit, window_seconds)
        else:
            if not settings.is_production:
                mem_key = (scope, ident)
                allowed, retry = _check_memory(mem_key, limit, window_seconds)
            else:
                # In production without Redis: fail open with a warning
                log.warning(
                    "Rate limiting is disabled: REDIS_URL not set in production. "
                    "Set REDIS_URL to enable distributed rate limiting."
                )
                return

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down.",
                headers={"Retry-After": str(retry)},
            )

    return dependency


# ── Pre-built limiters for common endpoints ───────────────────────────────────
auth_limiter = rate_limit("auth", "AUTH_RATE_LIMIT_PER_MIN")
ai_limiter = rate_limit("ai", "AI_RATE_LIMIT_PER_MIN")
upload_limiter = rate_limit("upload", "UPLOAD_RATE_LIMIT_PER_MIN")
