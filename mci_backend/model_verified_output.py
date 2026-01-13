"""Phase 12 — Step 5: Verified output dataclasses (bounded, deterministic)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class VerifiedAnswer:
    text: str


@dataclass(frozen=True)
class VerifiedAsk:
    question: str
    question_class: str
    priority_reason: str


@dataclass(frozen=True)
class VerifiedRefusal:
    text: str
    refusal_category: str


@dataclass(frozen=True)
class VerifiedClose:
    text: str
    closure_state: str


__all__ = [
    "VerifiedAnswer",
    "VerifiedAsk",
    "VerifiedRefusal",
    "VerifiedClose",
]
