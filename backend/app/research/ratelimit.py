"""
Phase 18 Step 2: Deterministic Rate Limiter

Fixed-window rate limiter with injected time for deterministic behavior.

Contract guarantees:
- Deterministic: same inputs + same time → same outputs
- Fail-closed: invalid config → caller handles stop reason
- No randomness, no wall clock time
"""

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class RateLimitConfig:
    """
    Rate limit configuration.
    
    Attributes:
        max_calls_per_minute: Maximum calls allowed per window
        window_seconds: Window duration in seconds (default 60)
    """
    max_calls_per_minute: int
    window_seconds: int = 60


@dataclass(frozen=True)
class RateLimiterState:
    """
    Rate limiter state (immutable).
    
    Attributes:
        window_start_ms: Start of current window in milliseconds
        calls_in_window: Number of calls made in current window
    """
    window_start_ms: int
    calls_in_window: int


def validate_config(config: RateLimitConfig) -> bool:
    """
    Validate rate limit config.
    
    Returns False if config is invalid (<=0 values).
    Caller is responsible for mapping to appropriate stop reason.
    """
    if config.max_calls_per_minute <= 0:
        return False
    if config.window_seconds <= 0:
        return False
    return True


def check_and_consume(
    state: RateLimiterState,
    config: RateLimitConfig,
    now_ms: int,
) -> Tuple[RateLimiterState, bool]:
    """
    Check if a call is allowed and consume a slot if so.
    
    Deterministic fixed-window rate limiting:
    1. If now_ms >= window_start_ms + window_seconds*1000, reset window
    2. If calls_in_window < max_calls_per_minute, allow and increment
    3. Otherwise, deny (state unchanged)
    
    Args:
        state: Current rate limiter state
        config: Rate limit configuration
        now_ms: Current time in milliseconds (injected for determinism)
    
    Returns:
        Tuple of (new_state, allowed)
        - If allowed: new_state has incremented calls_in_window
        - If denied: new_state is unchanged from input state
    
    Note: Invalid config returns (state, False). Caller maps to stop reason.
    """
    if not validate_config(config):
        return (state, False)
    
    window_duration_ms = config.window_seconds * 1000
    window_end_ms = state.window_start_ms + window_duration_ms
    
    if now_ms >= window_end_ms:
        new_state = RateLimiterState(
            window_start_ms=now_ms,
            calls_in_window=1,
        )
        return (new_state, True)
    
    if state.calls_in_window < config.max_calls_per_minute:
        new_state = RateLimiterState(
            window_start_ms=state.window_start_ms,
            calls_in_window=state.calls_in_window + 1,
        )
        return (new_state, True)
    
    return (state, False)


def create_initial_state(now_ms: int) -> RateLimiterState:
    """
    Create initial rate limiter state.
    
    Args:
        now_ms: Current time in milliseconds
    
    Returns:
        Fresh state with window starting at now_ms, zero calls
    """
    return RateLimiterState(
        window_start_ms=now_ms,
        calls_in_window=0,
    )
