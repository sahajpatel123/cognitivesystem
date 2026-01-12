from __future__ import annotations

"""Minimal data structures for MCI.

This module defines only the structures required by the Cognitive Contract.
No logic, helpers, or defaults beyond necessity.
"""

from dataclasses import dataclass, field
from typing import List


# Cognitive Contract: external user input + session identifier.
@dataclass
class UserMessage:
    session_id: str
    text: str


# Cognitive Contract: internal, session-local hypotheses.
@dataclass
class Hypothesis:
    key: str
    value: float


@dataclass
class HypothesisSet:
    session_id: str
    hypotheses: List[Hypothesis] = field(default_factory=list)
    ttl_seconds: int = 900  # Required: TTL-bound memory. Value is fixed here.


# Cognitive Contract: the only bridge from reasoning to expression.
@dataclass
class ExpressionPlan:
    segments: List[str]


# Internal reasoning output, never exposed outside the backend pipeline.
@dataclass
class ReasoningOutput:
    internal_trace: str
    proposed_hypotheses: HypothesisSet
    plan: ExpressionPlan


# Final user-visible reply.
@dataclass
class AssistantReply:
    text: str
