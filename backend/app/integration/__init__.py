"""
Phase 18 Step 9: Integration Package

Policy-gated research wiring for DeepThink + Research pipeline.
"""

from backend.app.integration.research_wiring import (
    ResearchPolicyDecision,
    ResearchOutcome,
    run_policy_gated_research,
    ALLOWED_STOP_REASONS,
)
from backend.app.research.sandbox import SandboxCaps, SandboxState, create_sandbox_state

__all__ = [
    "ResearchPolicyDecision",
    "ResearchOutcome",
    "run_policy_gated_research",
    "ALLOWED_STOP_REASONS",
    "SandboxCaps",
    "SandboxState",
    "create_sandbox_state",
]
