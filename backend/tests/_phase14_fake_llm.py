from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator, Optional


@dataclass
class FakeRendered:
    text: str


class Phase14FakeLLM:
    """Deterministic, side-effect-free fake LLM for Phase 14 adversarial tests."""

    def __init__(self, responses: Iterator[Callable[[], str]] | Iterator[str]):
        # Normalize responses to callables for laziness and to allow exception raising
        self._iter = iter(responses)

    def call_expression_model(self, *args, **kwargs):
        next_item = next(self._iter)
        if callable(next_item):
            result = next_item()
        else:
            result = next_item
        return FakeRendered(text=result)


class Phase14TimeoutLLM(Phase14FakeLLM):
    def __init__(self):
        super().__init__([self._raise_timeout])

    def _raise_timeout(self) -> str:  # pragma: no cover - intentional exception
        raise TimeoutError("simulated timeout")


class Phase14ErrorLLM(Phase14FakeLLM):
    def __init__(self, message: str):
        super().__init__([self._raise(message)])

    def _raise(self, message: str) -> Callable[[], str]:  # pragma: no cover - intentional exception
        def _inner():
            raise RuntimeError(message)

        return _inner
