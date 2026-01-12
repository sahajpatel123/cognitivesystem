# Deterministic Reference MCI

This document describes the deterministic, executable reference wiring of the
Minimal Correct Implementation (MCI).

## 1. Definition of Determinism

In this system, "deterministic" means:

- The same input `session_id` and `text` produce the same final reply.
- The reasoning backend returns the same internal trace for identical prompts.
- The expression backend renders the same text from the same ExpressionPlan.

Determinism applies to the structure of the pipeline, not to answer quality.

## 2. Deterministic Components

The following components are deterministic:

- Request handling (`mci_backend/app/main.py`)
  - Given the same payload, it follows the same execution path.
- Reasoning backend (`mci_backend/app/reasoning_runtime.py`)
  - `call_reasoning_backend(prompt)` computes a hash-based trace that is
    stable for a given prompt.
- Expression backend (`mci_backend/app/expression.py`)
  - `render_reply(plan)` joins plan segments in a fixed order.
- Memory updates (`mci_backend/app/memory.py`)
  - Given the same inputs, clamped updates and storage behavior are
    deterministic.

## 3. Exclusions

Determinism in this reference does not cover:

- Answer usefulness or correctness.
- Any notion of intelligence or understanding.
- Performance, latency, or cost.
- User experience or client behavior.

The reference wiring is intended only to make the MCI pipeline executable and
repeatable.

## 4. Verifying Determinism Manually

To verify determinism:

1. Run the reference entry point multiple times with the same arguments:

   ```bash
   python -m mci_backend.run_reference test_session "example text"
   ```

2. Confirm that the printed reply is identical across runs.

3. Change the input text or session_id and observe that the reply changes
   consistently for the new input.

This procedure demonstrates that the system behaves in a stable, repeatable
way for identical inputs.
