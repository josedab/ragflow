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

"""Unit tests for API rate limiting utilities."""

import time
from unittest.mock import MagicMock, patch, PropertyMock
import pytest

from api.utils.rate_limiter import (
    RateLimiter,
    rate_limit,
    rate_limit_by_user,
    rate_limit_by_tenant,
    rate_limit_by_ip,
    get_rate_limit_key_for_user,
    get_rate_limit_key_for_tenant,
    get_rate_limit_key_for_ip,
)
from common.constants import RetCode


class TestRateLimiter:
    """Test cases for the RateLimiter class."""

    def test_is_allowed_when_under_limit(self):
        """Test that requests are allowed when under the limit."""
        # Create a mock Redis connection
        mock_redis = MagicMock()
        mock_redis.is_alive.return_value = True

        # Mock pipeline to return count of 5 (under limit of 10)
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [None, 5, None, None]
        mock_redis.REDIS.pipeline.return_value = mock_pipeline

        limiter = RateLimiter()
        limiter.redis = mock_redis

        is_allowed, info = limiter.is_allowed("test_key", limit=10, window_seconds=60)

        assert is_allowed is True
        assert info["limit"] == 10
        assert info["remaining"] >= 0

    def test_is_allowed_when_at_limit(self):
        """Test that requests are denied when at the limit."""
        mock_redis = MagicMock()
        mock_redis.is_alive.return_value = True

        # Mock pipeline to return count of 10 (at limit of 10)
        mock_pipeline = MagicMock()
        mock_pipeline.execute.return_value = [None, 10, None, None]
        mock_redis.REDIS.pipeline.return_value = mock_pipeline

        limiter = RateLimiter()
        limiter.redis = mock_redis

        is_allowed, info = limiter.is_allowed("test_key", limit=10, window_seconds=60)

        assert is_allowed is False
        assert info["remaining"] == 0

    def test_is_allowed_when_redis_unavailable(self):
        """Test that requests are allowed when Redis is unavailable."""
        mock_redis = MagicMock()
        mock_redis.is_alive.return_value = False

        limiter = RateLimiter()
        limiter.redis = mock_redis

        is_allowed, info = limiter.is_allowed("test_key", limit=10, window_seconds=60)

        # Should allow request when Redis is down
        assert is_allowed is True

    def test_is_allowed_on_redis_error(self):
        """Test that requests are allowed on Redis errors."""
        mock_redis = MagicMock()
        mock_redis.is_alive.return_value = True
        mock_redis.REDIS.pipeline.side_effect = Exception("Redis connection error")

        limiter = RateLimiter()
        limiter.redis = mock_redis

        is_allowed, info = limiter.is_allowed("test_key", limit=10, window_seconds=60)

        # Should allow request on error
        assert is_allowed is True

    def test_get_current_count(self):
        """Test getting current request count."""
        mock_redis = MagicMock()
        mock_redis.is_alive.return_value = True
        mock_redis.zcount.return_value = 5

        limiter = RateLimiter()
        limiter.redis = mock_redis

        count = limiter.get_current_count("test_key", window_seconds=60)

        assert count == 5

    def test_get_current_count_when_redis_unavailable(self):
        """Test that count returns 0 when Redis is unavailable."""
        mock_redis = MagicMock()
        mock_redis.is_alive.return_value = False

        limiter = RateLimiter()
        limiter.redis = mock_redis

        count = limiter.get_current_count("test_key", window_seconds=60)

        assert count == 0


class TestRateLimitKeyFunctions:
    """Test cases for rate limit key generation functions."""

    @patch('api.utils.rate_limiter.current_user')
    @patch('api.utils.rate_limiter.request')
    def test_get_rate_limit_key_for_user_authenticated(self, mock_request, mock_current_user):
        """Test key generation for authenticated user."""
        mock_current_user.id = "user123"

        key = get_rate_limit_key_for_user()

        assert key == "ratelimit:user:user123"

    @patch('api.utils.rate_limiter.current_user')
    @patch('api.utils.rate_limiter.request')
    def test_get_rate_limit_key_for_user_unauthenticated(self, mock_request, mock_current_user):
        """Test key generation for unauthenticated user falls back to IP."""
        mock_current_user.id = None
        mock_request.remote_addr = "192.168.1.1"

        key = get_rate_limit_key_for_user()

        assert key == "ratelimit:ip:192.168.1.1"

    @patch('api.utils.rate_limiter.current_user')
    @patch('api.utils.rate_limiter.request')
    def test_get_rate_limit_key_for_tenant(self, mock_request, mock_current_user):
        """Test key generation for tenant."""
        mock_current_user.tenant_id = "tenant456"

        key = get_rate_limit_key_for_tenant()

        assert key == "ratelimit:tenant:tenant456"

    @patch('api.utils.rate_limiter.request')
    def test_get_rate_limit_key_for_ip(self, mock_request):
        """Test key generation for IP address."""
        mock_request.remote_addr = "10.0.0.1"

        key = get_rate_limit_key_for_ip()

        assert key == "ratelimit:ip:10.0.0.1"


class TestRateLimitDecorator:
    """Test cases for the rate_limit decorator."""

    @patch('api.utils.rate_limiter._rate_limiter')
    @patch('api.utils.rate_limiter.current_user')
    @patch('api.utils.rate_limiter.request')
    def test_decorator_allows_request_under_limit(self, mock_request, mock_current_user, mock_limiter):
        """Test that decorator allows requests under limit."""
        mock_current_user.id = "user123"
        mock_current_user.is_authenticated = True
        mock_limiter.is_allowed.return_value = (True, {"limit": 100, "remaining": 99, "reset": int(time.time()) + 60})

        @rate_limit(limit=100, window=60)
        def test_endpoint():
            return "success"

        result = test_endpoint()

        assert result == "success"

    @patch('api.utils.rate_limiter._rate_limiter')
    @patch('api.utils.rate_limiter.current_user')
    @patch('api.utils.rate_limiter.request')
    def test_decorator_blocks_request_over_limit(self, mock_request, mock_current_user, mock_limiter):
        """Test that decorator blocks requests over limit."""
        mock_current_user.id = "user123"
        mock_current_user.is_authenticated = True
        mock_limiter.is_allowed.return_value = (False, {"limit": 100, "remaining": 0, "reset": int(time.time()) + 60, "window": 60})

        @rate_limit(limit=100, window=60)
        def test_endpoint():
            return "success"

        with patch('api.utils.rate_limiter.jsonify') as mock_jsonify:
            mock_response = MagicMock()
            mock_response.headers = {}
            mock_jsonify.return_value = mock_response

            result = test_endpoint()

            # Verify jsonify was called with rate limit error
            mock_jsonify.assert_called_once()
            call_args = mock_jsonify.call_args[0][0]
            assert call_args["code"] == RetCode.RATE_LIMIT_EXCEEDED

    @patch('api.utils.rate_limiter._rate_limiter')
    @patch('api.utils.rate_limiter.current_user')
    @patch('api.utils.rate_limiter.request')
    def test_decorator_with_custom_key_func(self, mock_request, mock_current_user, mock_limiter):
        """Test decorator with custom key function."""
        mock_limiter.is_allowed.return_value = (True, {"limit": 10, "remaining": 9, "reset": int(time.time()) + 60})

        custom_key = "custom:key"

        @rate_limit(limit=10, window=60, key_func=lambda: custom_key)
        def test_endpoint():
            return "success"

        result = test_endpoint()

        # Verify the custom key was used
        call_args = mock_limiter.is_allowed.call_args
        assert custom_key in call_args[0][0]


class TestConvenienceDecorators:
    """Test cases for convenience decorator functions."""

    def test_rate_limit_by_user_returns_decorator(self):
        """Test that rate_limit_by_user returns a decorator."""
        decorator = rate_limit_by_user(limit=100, window=60)
        assert callable(decorator)

    def test_rate_limit_by_tenant_returns_decorator(self):
        """Test that rate_limit_by_tenant returns a decorator."""
        decorator = rate_limit_by_tenant(limit=100, window=60)
        assert callable(decorator)

    def test_rate_limit_by_ip_returns_decorator(self):
        """Test that rate_limit_by_ip returns a decorator."""
        decorator = rate_limit_by_ip(limit=100, window=60)
        assert callable(decorator)


class TestRetCodeConstant:
    """Test that RATE_LIMIT_EXCEEDED constant exists."""

    def test_rate_limit_exceeded_constant(self):
        """Test that RetCode.RATE_LIMIT_EXCEEDED is defined correctly."""
        assert hasattr(RetCode, 'RATE_LIMIT_EXCEEDED')
        assert RetCode.RATE_LIMIT_EXCEEDED == 429
