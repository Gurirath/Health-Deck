"""In-memory rate limiting subsystem for Health Deck (Single-Instance).

Provides thread-safe sliding-window rate limiting for critical public endpoints
(auth login, triage creation, audio transcription, and file upload) without
requiring external infrastructure dependencies (like Redis).

Can be swapped for a distributed Redis-backed limiter in multi-instance deployments.
"""

import os
import time
import threading
from collections import defaultdict
from typing import Dict, List, Optional
from fastapi import HTTPException, Request, status


# Global thread-safe state
_lock = threading.Lock()
_access_history: Dict[str, List[float]] = defaultdict(list)
_last_prune = time.time()
PRUNE_INTERVAL_SECONDS = 300  # prune stale entries every 5 minutes


def is_rate_limiting_enabled() -> bool:
    """Return True if rate limiting is enabled via environment."""
    val = os.environ.get("HEALTHDECK_RATE_LIMIT_ENABLED", "true").strip().lower()
    return val not in ("false", "0", "no", "off")


def get_client_ip(request: Request) -> str:
    """Safely extract client IP address from request.
    
    If behind a trusted reverse proxy (HEALTHDECK_BEHIND_PROXY=true or production default):
    Parses X-Forwarded-For from the right based on HEALTHDECK_TRUSTED_PROXY_COUNT to prevent
    client-side IP spoofing attacks.
    If not behind a proxy (e.g. local dev / direct exposure), ignores X-Forwarded-For to prevent
    untrusted clients from spoofing their IP, falling back to request.client.host.
    """
    from core import config

    if config.is_behind_proxy():
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded and forwarded.strip():
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                proxy_count = config.get_trusted_proxy_count()
                idx = -min(proxy_count, len(parts))
                return parts[idx]
        real_ip = request.headers.get("x-real-ip")
        if real_ip and real_ip.strip():
            return real_ip.strip()

    if request.client and request.client.host:
        return request.client.host
    return "unknown_client"


def prune_stale_records(now: float, window_seconds: float = 300.0):
    """Remove entries older than window_seconds to prevent memory bloat."""
    global _last_prune
    if now - _last_prune < PRUNE_INTERVAL_SECONDS:
        return
    _last_prune = now
    stale_keys = []
    for key, timestamps in _access_history.items():
        _access_history[key] = [t for t in timestamps if now - t < window_seconds]
        if not _access_history[key]:
            stale_keys.append(key)
    for key in stale_keys:
        _access_history.pop(key, None)


def reset_rate_limits():
    """Clear all rate limit histories (used for testing and maintenance)."""
    with _lock:
        _access_history.clear()


def check_rate_limit(
    request: Request,
    scope: str,
    default_max_requests: int,
    window_seconds: int = 60,
):
    """Evaluate sliding-window rate limit for the current client request.
    
    Raises HTTP 429 Too Many Requests if the limit is exceeded.
    Includes standard 'Retry-After' response header.
    """
    if not is_rate_limiting_enabled():
        return

    # Allow environment variable override for the limit: HEALTHDECK_LIMIT_<SCOPE>
    env_override = os.environ.get(f"HEALTHDECK_LIMIT_{scope.upper()}")
    max_requests = default_max_requests
    if env_override and env_override.strip().isdigit():
        max_requests = int(env_override.strip())

    client_ip = get_client_ip(request)
    key = f"{scope}:{client_ip}"
    now = time.time()

    with _lock:
        prune_stale_records(now, window_seconds=float(window_seconds * 2))
        history = _access_history[key]
        # Retain only timestamps within the sliding window
        window_start = now - window_seconds
        active_timestamps = [t for t in history if t > window_start]
        _access_history[key] = active_timestamps

        if len(active_timestamps) >= max_requests:
            oldest_active = active_timestamps[0]
            retry_after = max(1, int(oldest_active + window_seconds - now) + 1)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )

        _access_history[key].append(now)


def rate_limit(scope: str, max_requests: int, window_seconds: int = 60):
    """FastAPI dependency for declarative endpoint rate limiting."""
    def dependency(request: Request):
        check_rate_limit(
            request=request,
            scope=scope,
            default_max_requests=max_requests,
            window_seconds=window_seconds,
        )
    return dependency
