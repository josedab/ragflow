#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

"""
Rate limiting utilities for API endpoints.

Implements token bucket rate limiting using Redis sorted sets for
sliding window tracking.
"""

import logging
import time
from functools import wraps
from typing import Callable, Optional

from flask import request, jsonify
from flask_login import current_user

from common.constants import RetCode
from common import settings
from rag.utils.redis_conn import REDIS_CONN


# Load rate limit configuration
def get_rate_limit_config():
    """Load rate limit configuration from settings."""
    try:
        config = settings.get_base_config("rate_limits", {})
        return config
    except Exception as e:
        logging.warning(f"Failed to load rate_limits config: {e}")
        return {}


RATE_LIMIT_CONFIG = get_rate_limit_config()


class RateLimiter:
    """
    Token bucket rate limiter using Redis sorted sets.

    Uses sliding window algorithm where each request is recorded
    with its timestamp as the score. Old entries are removed and
    remaining count is checked against the limit.
    """

    def __init__(self):
        self.redis = REDIS_CONN

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> tuple[bool, dict]:
        """
        Check if a request is allowed under the rate limit.

        Args:
            key: Unique identifier for the rate limit bucket
            limit: Maximum number of requests allowed in the window
            window_seconds: Time window in seconds

        Returns:
            Tuple of (is_allowed, info_dict) where info_dict contains
            rate limit headers information
        """
        if not self.redis.is_alive():
            # If Redis is unavailable, allow the request but log warning
            logging.warning("Redis unavailable for rate limiting, allowing request")
            return True, {"limit": limit, "remaining": limit, "reset": 0}

        now = time.time()
        window_start = now - window_seconds

        try:
            # Use pipeline for atomic operations
            pipe = self.redis.REDIS.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count current entries in the window
            pipe.zcard(key)

            # Add new entry with current timestamp
            pipe.zadd(key, {f"{now}:{id(request)}": now})

            # Set expiry on the key
            pipe.expire(key, window_seconds + 1)

            results = pipe.execute()
            current_count = results[1]

            # Calculate remaining requests
            remaining = max(0, limit - current_count - 1)
            reset_time = int(now + window_seconds)

            info = {
                "limit": limit,
                "remaining": remaining,
                "reset": reset_time,
                "window": window_seconds
            }

            is_allowed = current_count < limit

            if not is_allowed:
                # Remove the entry we just added since request is denied
                pipe = self.redis.REDIS.pipeline()
                pipe.zrem(key, f"{now}:{id(request)}")
                pipe.execute()
                logging.info(f"Rate limit exceeded for key: {key}, count: {current_count}, limit: {limit}")

            return is_allowed, info

        except Exception as e:
            logging.error(f"Rate limiter error for key {key}: {e}")
            # On error, allow the request to avoid blocking legitimate traffic
            return True, {"limit": limit, "remaining": limit, "reset": 0}

    def get_current_count(self, key: str, window_seconds: int) -> int:
        """Get the current request count for a key within the window."""
        if not self.redis.is_alive():
            return 0

        now = time.time()
        window_start = now - window_seconds

        try:
            return self.redis.zcount(key, window_start, now) or 0
        except Exception as e:
            logging.error(f"Error getting rate limit count: {e}")
            return 0


# Global rate limiter instance
_rate_limiter = RateLimiter()


def get_rate_limit_key_for_user() -> str:
    """Get rate limit key based on current user."""
    if hasattr(current_user, 'id') and current_user.id:
        return f"ratelimit:user:{current_user.id}"
    return f"ratelimit:ip:{request.remote_addr}"


def get_rate_limit_key_for_tenant() -> str:
    """Get rate limit key based on current user's tenant."""
    if hasattr(current_user, 'tenant_id') and current_user.tenant_id:
        return f"ratelimit:tenant:{current_user.tenant_id}"
    return get_rate_limit_key_for_user()


def get_rate_limit_key_for_ip() -> str:
    """Get rate limit key based on IP address."""
    return f"ratelimit:ip:{request.remote_addr}"


def rate_limit(
    limit: int = 100,
    window: int = 60,
    key_func: Optional[Callable[[], str]] = None,
    config_key: Optional[str] = None
):
    """
    Decorator for rate limiting API endpoints.

    Args:
        limit: Maximum number of requests allowed in the window (default: 100)
        window: Time window in seconds (default: 60)
        key_func: Function that returns the rate limit key. If None,
                  uses IP-based limiting for unauthenticated requests
                  or user-based limiting for authenticated requests.
        config_key: Optional key to look up limits in configuration.
                    If provided, overrides limit and window with config values.

    Example usage:
        @rate_limit(limit=60, window=60)
        def my_endpoint():
            ...

        @rate_limit(key_func=lambda: f"user:{current_user.id}")
        def user_specific_endpoint():
            ...

        @rate_limit(config_key="llm_completion")
        def completion():
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get configured limits if config_key provided
            effective_limit = limit
            effective_window = window

            if config_key and config_key in RATE_LIMIT_CONFIG:
                config = RATE_LIMIT_CONFIG[config_key]
                effective_limit = config.get("limit", limit)
                effective_window = config.get("window", window)
            elif "default" in RATE_LIMIT_CONFIG:
                config = RATE_LIMIT_CONFIG["default"]
                effective_limit = config.get("limit", limit)
                effective_window = config.get("window", window)

            # Get rate limit key
            if key_func:
                try:
                    key = key_func()
                except Exception as e:
                    logging.error(f"Error getting rate limit key: {e}")
                    key = get_rate_limit_key_for_ip()
            else:
                # Default key based on authentication status
                if hasattr(current_user, 'id') and current_user.is_authenticated:
                    key = get_rate_limit_key_for_user()
                else:
                    key = get_rate_limit_key_for_ip()

            # Add endpoint to key for per-endpoint limiting
            endpoint_name = func.__name__
            full_key = f"{key}:{endpoint_name}"

            # Check rate limit
            is_allowed, info = _rate_limiter.is_allowed(
                full_key,
                effective_limit,
                effective_window
            )

            if not is_allowed:
                response = jsonify({
                    "code": RetCode.RATE_LIMIT_EXCEEDED,
                    "message": f"Rate limit exceeded. Maximum {effective_limit} requests per {effective_window} seconds.",
                    "data": {
                        "retry_after": info.get("reset", 0) - int(time.time()),
                        "limit": info.get("limit"),
                        "window": info.get("window")
                    }
                })
                response.status_code = 429
                # Add rate limit headers
                response.headers["X-RateLimit-Limit"] = str(info.get("limit", effective_limit))
                response.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
                response.headers["X-RateLimit-Reset"] = str(info.get("reset", 0))
                response.headers["Retry-After"] = str(max(1, info.get("reset", 0) - int(time.time())))
                return response

            # Call the actual function
            result = func(*args, **kwargs)

            # Add rate limit headers to successful responses
            if hasattr(result, 'headers'):
                result.headers["X-RateLimit-Limit"] = str(info.get("limit", effective_limit))
                result.headers["X-RateLimit-Remaining"] = str(info.get("remaining", 0))
                result.headers["X-RateLimit-Reset"] = str(info.get("reset", 0))

            return result
        return wrapper
    return decorator


def rate_limit_by_user(limit: int = 100, window: int = 60, config_key: Optional[str] = None):
    """
    Convenience decorator for per-user rate limiting.

    Args:
        limit: Maximum requests per user in the window
        window: Time window in seconds
        config_key: Optional configuration key
    """
    return rate_limit(
        limit=limit,
        window=window,
        key_func=get_rate_limit_key_for_user,
        config_key=config_key
    )


def rate_limit_by_tenant(limit: int = 100, window: int = 60, config_key: Optional[str] = None):
    """
    Convenience decorator for per-tenant rate limiting.

    Args:
        limit: Maximum requests per tenant in the window
        window: Time window in seconds
        config_key: Optional configuration key
    """
    return rate_limit(
        limit=limit,
        window=window,
        key_func=get_rate_limit_key_for_tenant,
        config_key=config_key
    )


def rate_limit_by_ip(limit: int = 100, window: int = 60, config_key: Optional[str] = None):
    """
    Convenience decorator for IP-based rate limiting.

    Args:
        limit: Maximum requests per IP in the window
        window: Time window in seconds
        config_key: Optional configuration key
    """
    return rate_limit(
        limit=limit,
        window=window,
        key_func=get_rate_limit_key_for_ip,
        config_key=config_key
    )
