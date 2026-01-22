from __future__ import annotations

from backend.app.config import get_settings


def cost_global_daily_tokens() -> int:
    return max(0, int(get_settings().cost_global_daily_tokens))


def cost_ip_window_seconds() -> int:
    return max(1, int(get_settings().cost_ip_window_seconds))


def cost_ip_window_tokens() -> int:
    return max(0, int(get_settings().cost_ip_window_tokens))


def cost_actor_daily_tokens() -> int:
    return max(0, int(get_settings().cost_actor_daily_tokens))


def cost_request_max_tokens() -> int:
    return max(1, int(get_settings().cost_request_max_tokens))


def cost_request_max_output_tokens() -> int:
    return max(1, int(get_settings().cost_request_max_output_tokens))


def cost_breaker_fail_threshold() -> int:
    return max(1, int(get_settings().cost_breaker_fail_threshold))


def cost_breaker_window_seconds() -> int:
    return max(1, int(get_settings().cost_breaker_window_seconds))


def cost_breaker_cooldown_seconds() -> int:
    return max(1, int(get_settings().cost_breaker_cooldown_seconds))


def cost_events_ring_size() -> int:
    return max(1, int(get_settings().cost_events_ring_size))
