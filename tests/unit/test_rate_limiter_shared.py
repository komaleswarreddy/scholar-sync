"""GRD-06 shared RateLimiter singleton unit tests."""

from __future__ import annotations

import pytest

from packages.core.memory.rate_limiter import get_rate_limiter, reset_rate_limiter_for_tests


@pytest.fixture(autouse=True)
def _reset_limiter():
    reset_rate_limiter_for_tests()
    yield
    reset_rate_limiter_for_tests()


def test_singleton_same_instance():
    a = get_rate_limiter(max_requests_per_minute=5, debounce_seconds=0)
    b = get_rate_limiter()
    assert a is b


def test_accumulates_requests_per_user():
    limiter = get_rate_limiter(max_requests_per_minute=3, debounce_seconds=0, max_requests_per_hour=100)
    for i in range(3):
        check = limiter.check_rate_limit("user_a", f"query-{i}")
        assert check["allowed"] is True, check
    blocked = limiter.check_rate_limit("user_a", "query-overflow")
    assert blocked["allowed"] is False
    assert blocked["reason"] == "rate_limit_minute"
    assert blocked.get("retry_after", 0) > 0


def test_per_user_isolation():
    limiter = get_rate_limiter(max_requests_per_minute=2, debounce_seconds=0, max_requests_per_hour=100)
    limiter.check_rate_limit("user_x", "q1")
    limiter.check_rate_limit("user_x", "q2")
    blocked_x = limiter.check_rate_limit("user_x", "q3")
    assert blocked_x["allowed"] is False

    allowed_y = limiter.check_rate_limit("user_y", "q1")
    assert allowed_y["allowed"] is True
