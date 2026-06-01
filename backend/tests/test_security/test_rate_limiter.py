import asyncio
import pytest
from fastapi import HTTPException

from app.core.rate_limiter import RateLimiter


@pytest.mark.asyncio
async def test_allows_requests_under_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        await limiter.check("ip1")  # must not raise


@pytest.mark.asyncio
async def test_blocks_on_exceeding_limit():
    limiter = RateLimiter(max_requests=3, window_seconds=60)
    for _ in range(3):
        await limiter.check("ip1")
    with pytest.raises(HTTPException) as exc_info:
        await limiter.check("ip1")
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_exponential_backoff_increases():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    await limiter.check("ip2")
    with pytest.raises(HTTPException):
        await limiter.check("ip2")
    # violation_count should now be 1
    assert limiter._state["ip2"].violation_count == 1
    # blocked_until should be set
    assert limiter._state["ip2"].blocked_until > 0


@pytest.mark.asyncio
async def test_reset_clears_state():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    await limiter.check("ip3")
    limiter.reset("ip3")
    # After reset, should allow again
    await limiter.check("ip3")  # must not raise


@pytest.mark.asyncio
async def test_different_keys_are_independent():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    await limiter.check("ip4")
    with pytest.raises(HTTPException):
        await limiter.check("ip4")
    # Different IP should not be affected
    await limiter.check("ip5")  # must not raise


@pytest.mark.asyncio
async def test_retry_after_header_present():
    limiter = RateLimiter(max_requests=1, window_seconds=60)
    await limiter.check("ip6")
    with pytest.raises(HTTPException) as exc_info:
        await limiter.check("ip6")
    assert "Retry-After" in exc_info.value.headers
