from __future__ import annotations

from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class UserMessage(BaseModel):
    id: str
    text: str
    timestamp: int


class Intent(BaseModel):
    type: Literal[
        "question",
        "elaboration",
        "example_request",
        "self_explanation",
        "meta_request",
    ]
    topic_guess: Optional[str] = None
    goal_guess: Optional[str] = None
    confidence: float = 0.0


class CognitiveStyle(BaseModel):
    abstraction_level: Literal["high", "medium", "low"]
    formality: Literal["casual", "neutral", "formal"]
    preferred_analogies: Literal["code_first", "real_world_first", "mixed"]
    overrides: Optional[dict] = None


class Hypothesis(BaseModel):
    id: str
    claim: str
    support_score: float = 0.0
    refute_score: float = 0.0
    last_updated: int


class HypothesisDelta(BaseModel):
    id: str
    claim: str
    support_score_delta: float = 0.0
    refute_score_delta: float = 0.0
    justification: str


class ReasoningStep(BaseModel):
    id: str
    description: str
    related_hypotheses: List[str] = Field(default_factory=list)
    status: Literal["proposed", "tested", "refuted", "supported"] = "proposed"


class ReasoningTrace(BaseModel):
    steps: List[ReasoningStep]
    summary: str


class IntermediateAnswer(BaseModel):
    goals: List[str]
    key_points: List[str]
    assumptions_and_uncertainties: List[dict] = Field(default_factory=list)
    checks_for_understanding: List[str] = Field(default_factory=list)


class ReasoningOutput(BaseModel):
    reasoning_trace: ReasoningTrace
    updated_hypotheses: List[HypothesisDelta]
    intermediate_answer: IntermediateAnswer


class SessionSummary(BaseModel):
    active_goal: Optional[str] = None
    cognitive_patterns: dict = Field(default_factory=dict)


class ExpressionPlan(BaseModel):
    target_tone: Literal["casual", "neutral", "formal"]
    structure: List[
        Literal["ack", "reframe", "concept", "example", "check_understanding"]
    ]
    analogy_style: Literal["code_first", "real_world_first", "mixed"]
    constraints: dict = Field(default_factory=dict)
    emphasis: List[str] = Field(default_factory=list)


class RenderedMessage(BaseModel):
    text: str


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    message: str
