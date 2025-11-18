# RFC-0007: API Rate Limiting

**Status:** Draft
**Author:** Analysis Team
**Created:** November 18, 2025
**Effort:** 2-3 days
**Priority:** P2 (Quick Win)

## Summary

Add rate limiting to API endpoints to prevent abuse, ensure fair usage, and protect infrastructure from overload.

## Motivation

Currently no rate limiting exists:
1. **No abuse protection**: Single user can overwhelm system
2. **No fair usage**: One tenant can starve others
3. **No DDoS protection**: Easy to overload
4. **No cost control**: LLM calls can be expensive

## Detailed Design

### Rate Limiter

```python
# api/utils/rate_limiter.py
from functools import wraps
import time

class RateLimiter:
    """Token bucket rate limiter using Redis"""

    def __init__(self, redis_conn):
        self.redis = redis_conn

    def is_allowed(self, key, limit, window_seconds):
        """Check if request is allowed"""
        now = time.time()
        window_start = now - window_seconds

        pipe = self.redis.pipeline()
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current entries
        pipe.zcard(key)
        # Add new entry
        pipe.zadd(key, {str(now): now})
        # Set expiry
        pipe.expire(key, window_seconds)

        results = pipe.execute()
        current_count = results[1]

        return current_count < limit

def rate_limit(limit=100, window=60, key_func=None):
    """Decorator for rate limiting"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get rate limit key
            if key_func:
                key = key_func()
            else:
                key = f"ratelimit:{request.remote_addr}"

            limiter = RateLimiter(REDIS_CONN)
            if not limiter.is_allowed(key, limit, window):
                return get_json_result(
                    code=429,
                    message=f"Rate limit exceeded. Max {limit} requests per {window}s"
                )

            return func(*args, **kwargs)
        return wrapper
    return decorator
```

### Usage

```python
# api/apps/dialog_app.py

# Per-user limit
@manager.route('/completion', methods=['POST'])
@login_required
@rate_limit(limit=60, window=60, key_func=lambda: f"user:{current_user.id}")
def completion():
    # ... existing code

# Per-tenant limit for expensive operations
@manager.route('/run', methods=['POST'])
@login_required
@rate_limit(limit=10, window=60, key_func=lambda: f"tenant:{current_user.tenant_id}")
def run_agent():
    # ... existing code

# Global limit for anonymous endpoints
@manager.route('/health', methods=['GET'])
@rate_limit(limit=1000, window=60)
def health_check():
    # ... existing code
```

### Configuration

```yaml
# docker/service_conf.yaml.template
rate_limits:
  default:
    limit: 100
    window: 60
  llm_completion:
    limit: 60
    window: 60
  document_upload:
    limit: 20
    window: 60
  search:
    limit: 200
    window: 60
```

## Implementation Plan

### Day 1
1. Implement `RateLimiter` class
2. Create decorator
3. Add to high-risk endpoints (completion, upload)

### Day 2
1. Add to remaining endpoints
2. Add configuration support
3. Add 429 response handling in frontend

### Day 3
1. Add monitoring for rate limit hits
2. Documentation
3. Testing

## Success Criteria

- [ ] All public endpoints have rate limits
- [ ] Rate limits configurable per endpoint
- [ ] 429 responses handled in frontend
- [ ] Monitoring for rate limit events

## Stakeholder Approvals

- [ ] Security Lead
- [ ] Backend Lead
