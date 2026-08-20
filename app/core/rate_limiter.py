"""
app/core/rate_limiter.py

SEC-008: Centralized rate limiter instance using slowapi.

Rate limits are enforced by client IP address. Limits are defined per-route
in the route handlers using the @limiter.limit() decorator.

Default limits:
- Read endpoints (GET): 120 requests per minute
- Write/execute endpoints (POST): 30 requests per minute
- High-risk endpoints (execution trigger, dependency install): 10 per minute
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Shared limiter instance — imported in main.py and individual routes
limiter = Limiter(key_func=get_remote_address, default_limits=["120/minute"])
