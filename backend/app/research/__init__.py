"""
Phase 18 Research: Sandbox, Rate Limiting, Credibility, Citations, and Injection Defense

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
from backend.app.research.citations import (
    CitationRef,
    make_citation_ref,
    normalize_url,
    extract_domain,
)
from backend.app.research.claim_binder import (
    Claim,
    BinderOutput,
    bind_claims_and_citations,
    extract_claims,
)
from backend.app.research.injection_defense import (
    InjectionFlag,
    SanitizerConfig,
    SanitizerEvent,
    SanitizerResult,
    sanitize_tool_output,
    INJECTION_MODEL_VERSION,
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
    "CitationRef",
    "make_citation_ref",
    "normalize_url",
    "extract_domain",
    "Claim",
    "BinderOutput",
    "bind_claims_and_citations",
    "extract_claims",
    "InjectionFlag",
    "SanitizerConfig",
    "SanitizerEvent",
    "SanitizerResult",
    "sanitize_tool_output",
    "INJECTION_MODEL_VERSION",
]
