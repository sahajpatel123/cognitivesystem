"""
Phase 18 Research: Sandbox, Rate Limiting, and Credibility Grading

Deterministic, fail-closed components for research mode.
"""

from backend.app.research.ratelimit import (
    RateLimitConfig,
    RateLimiterState,
    check_and_consume,
)
from backend.app.research.sandbox import (
    SandboxCaps,
    SandboxState,
    SandboxResult,
    run_sandboxed_call,
)
from backend.app.research.credibility import (
    CredibilityReport,
    GradedSource,
    grade_sources,
    CREDIBILITY_MODEL_VERSION,
)

__all__ = [
    "RateLimitConfig",
    "RateLimiterState",
    "check_and_consume",
    "SandboxCaps",
    "SandboxState",
    "SandboxResult",
    "run_sandboxed_call",
    "CredibilityReport",
    "GradedSource",
    "grade_sources",
    "CREDIBILITY_MODEL_VERSION",
]
