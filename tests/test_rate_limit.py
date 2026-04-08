import pytest

from backend.rate_limit import RateLimiter


def test_rate_limiter_allows_up_to_limit_then_blocks() -> None:
    rl = RateLimiter(max_requests=2, window_seconds=10)
    assert rl.allow("k", now=100.0) is True
    assert rl.allow("k", now=101.0) is True
    assert rl.allow("k", now=102.0) is False


def test_rate_limiter_window_resets() -> None:
    rl = RateLimiter(max_requests=1, window_seconds=10)
    assert rl.allow("k", now=100.0) is True
    assert rl.allow("k", now=105.0) is False
    assert rl.allow("k", now=111.0) is True


def test_rate_limiter_validates_inputs() -> None:
    with pytest.raises(ValueError):
        RateLimiter(max_requests=0, window_seconds=10)
    with pytest.raises(ValueError):
        RateLimiter(max_requests=1, window_seconds=0)

