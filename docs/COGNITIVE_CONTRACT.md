# Cognitive Contract

This document defines the cognitive behavior of the system. It is the highest-authority technical specification. All implementation, testing, deployment, and operations must conform to this contract.

## 1. WHAT vs HOW Separation

- **WHAT** is defined by the user’s goals, questions, and constraints as expressed in their messages.
- **HOW** is defined by the system’s internal reasoning and expression process.
- The system controls **HOW**; the user controls **WHAT**.
- The user is never exposed to internal reasoning or hypotheses.

## 2. Two-LLM Architecture

- The system uses two distinct model calls for each response:
  - **Reasoning LLM**
    - Receives user message, prior hypotheses, and cognitive style.
    - Produces an internal reasoning trace, updated hypotheses, and an expression plan.
    - Output is for internal use only and is never exposed directly to the user.
  - **Expression LLM**
    - Receives the expression plan and necessary user-visible context.
    - Produces the final user-facing message.
    - Must not introduce new claims beyond the reasoning trace.
- The Reasoning LLM and Expression LLM are logically separated. Their roles are not merged.

## 3. Planner Role (Structure Only)

- The planner is an internal mechanism that shapes the structure of the system’s response.
- The planner may:
  - Choose sections, ordering, and level of structural scaffolding.
  - Decide which parts of existing knowledge to include or omit, within constraints.
- The planner may not:
  - Introduce new substantive claims.
  - Change the meaning of user goals.
  - Override hypothesis or memory rules.
- The planner is a structure-only component and does not implement domain logic.

## 4. Hypothesis Rules

Hypotheses represent the system’s internal assumptions about the user’s goals, context, and cognitive style within a single session.

- **Session-local**
  - Hypotheses are scoped to a single session.
  - Hypotheses must not be shared or reused across sessions.

- **Non-deleting**
  - Existing hypotheses are never hard-deleted.
  - Updates are applied as deltas that adjust, refine, or weaken existing hypotheses.
  - Historical hypotheses remain part of the internal record for the duration of the session.

- **Clamped**
  - Changes to hypotheses are limited in magnitude per turn.
  - Large shifts must occur gradually over multiple turns.
  - Clamping behavior must be enforced to prevent abrupt re-interpretation of the user.

## 5. Memory Rules

Memory refers to all stored state that persists across requests.

- **TTL-bound**
  - All stored state is subject to a fixed time-to-live.
  - When the TTL expires, the stored state must be discarded.

- **Session-only**
  - Memory keys are scoped to a single session identifier.
  - No stored state may be used to link or relate different sessions.

- **No identity**
  - The system does not construct or maintain user identity across sessions.
  - The system does not build long-term profiles, traits, or histories.
  - Any appearance of identity continuity must arise only from the current session’s messages.

## 6. Expression Constraints

The Expression LLM converts internal plans into user-facing text.

- The Expression LLM must:
  - Follow the structure defined by the planner.
  - Stay within the content supported by the Reasoning LLM’s conclusions.
- The Expression LLM must not:
  - Introduce new factual claims not supported by the reasoning trace.
  - Upgrade modality (for example, from uncertainty to certainty) relative to the reasoning.
  - Soften or remove contract-relevant constraints.

## 7. Prohibitions

The following behaviors are absolutely prohibited by this contract:

- **Chain-of-thought exposure**
  - Internal reasoning traces and hypotheses must never be exposed directly to the user.
  - No API or UI may reveal internal reasoning steps.

- **Cross-session personalization**
  - No personalization or adaptation may rely on information from previous sessions.
  - No long-term user models or profiles may be used.

- **Modes or levels**
  - The system must not implement multiple cognitive modes or levels that change reasoning behavior.
  - There is a single certified cognitive configuration.

- **Cognition shortcuts**
  - The system must not bypass the Reasoning LLM for any request.
  - The system must not provide direct Expression LLM responses without a full reasoning pass.
  - The system must not reduce, skip, or dynamically disable cognitive steps based on latency, cost, or UX pressure.

## 8. Contract Status

- This Cognitive Contract is frozen.
- Any change to this contract is considered a cognitive change and is outside normal engineering scope.
- No implementation, operational practice, or product decision may violate this contract.
