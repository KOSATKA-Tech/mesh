import os

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# Global rate limiter using remote address as key.
# default_limits applies to all routes globally.
enabled = os.getenv("KOSATKA_RATE_LIMIT_ENABLED", "true").lower() == "true"
limiter = Limiter(key_func=get_remote_address, default_limits=["60 per minute"] if enabled else [])


def setup_rate_limiting(app):
    """Register rate limiter and its error handler with the FastAPI app."""
    if not enabled:
        return

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
