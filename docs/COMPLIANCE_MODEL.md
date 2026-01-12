# Compliance Model

This document defines what is being verified by continuous compliance and why. It does not change the system; it only describes what must remain unchanged.

## 1. Certified System Definition

The "Certified System" is the cognitive system as described and constrained by the following documents:

- `docs/COGNITIVE_CONTRACT.md`
- `docs/GOVERNANCE_CHARTER.md`
- `docs/DECISIONS/STEP_J_CERTIFICATION.md`
- `docs/DECISIONS/STEP_L_SCALE_GOVERNANCE.md`
- `docs/GOVERNANCE_PRESSURE_LOG.md`

The Certified System is defined by:

- The Cognitive Contract, including:
  - WHAT vs HOW separation.
  - Two-LLM architecture (Reasoning LLM and Expression LLM).
  - Planner role as structure-only.
  - Hypothesis rules (session-local, non-deleting, clamped).
  - Memory rules (TTL-bound, session-only, no identity).
  - Expression constraints and prohibitions.
- The Governance Charter, including:
  - Frozen vs mutable surfaces.
  - Roles and decision authority.
  - Incident rule that cognition may not be modified.
- The decisions recorded in STEP J and STEP L.
- The recorded governance pressure events.

Compliance verifies that the running system matches this Certified System.

## 2. Compliance Surfaces

Continuous compliance checks the following surfaces for conformance:

1. **Cognition code**
   - Code implementing reasoning, expression, planner behavior, hypotheses, and memory.
   - Must remain consistent with the Cognitive Contract.

2. **Prompts**
   - Text and structure of prompts used by the Reasoning LLM and Expression LLM.
   - Must remain consistent with the Cognitive Contract and Governance Charter.

3. **Planner definitions**
   - Structures and rules used to define expression plans.
   - Must remain structure-only and aligned with the contract.

4. **Hypothesis rules**
   - Implementation of session-local, non-deleting, clamped hypotheses.
   - Must conform to the documented semantics.

5. **Memory semantics**
   - Implementation of TTL-bound, session-only, no-identity memory.
   - Must conform to the documented semantics and must not introduce cross-session identity.

6. **Governance documents**
   - Cognitive Contract.
   - Governance Charter.
   - Decisions and logs.
   - Must remain synchronized with the actual behavior of the system.

## 3. Scope of Compliance

- Compliance checks **conformance only**.
- Compliance does **not** evaluate:
  - Quality of answers.
  - Performance or latency.
  - Cost or efficiency.
  - UX experience or satisfaction.

Compliance determines whether the running system is the same certified system, not whether it is good, fast, or cheap.

## 4. Purpose of Compliance

The purpose of continuous compliance is to:

- Detect any drift between implementation and the Certified System.
- Ensure that cognitive behavior remains within the boundaries defined by existing documents.
- Provide evidence that governance is being followed over time.
- Support audits and reviews without changing cognition.
