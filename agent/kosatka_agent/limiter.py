from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

# Global rate limiter using remote address as key.
# Agents typically receive fewer API requests (mostly from Master),
# but let's keep a reasonable limit.
limiter = Limiter(key_func=get_remote_address, default_limits=["60 per minute"])


def setup_rate_limiting(app):
    """Register rate limiter and its error handler with the FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
