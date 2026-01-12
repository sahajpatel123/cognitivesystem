from __future__ import annotations

"""Deterministic reasoning backend for MCI.

This module provides a reference-only backend for `call_reasoning_model`.
It is deterministic: the same prompt always produces the same output.

There are no external calls, no randomness, and no configuration.
"""

import hashlib


def call_reasoning_backend(prompt: str) -> str:
    """Return a deterministic reasoning trace for a given prompt.

    Implementation: compute a SHA256 hash of the prompt and embed it in a
    simple textual trace. This is sufficient to exercise the pipeline and
    remains stable for identical prompts.
    """
    h = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
    return f"DETERMINISTIC_REASONING_TRACE hash={h}"
