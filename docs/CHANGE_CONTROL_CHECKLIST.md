# Change Control Checklist

This checklist is mandatory for any change that might affect cognition. It is intended for authors and reviewers of changes.

## 1. Scope of This Checklist

You must apply this checklist to any change that touches any of the following:

- Prompts used by the Reasoning LLM or Expression LLM.
- Planner code or configuration.
- Reasoning logic.
- Expression logic.
- Hypothesis handling.
- Memory handling.

If you are unsure whether a change touches cognition, assume that it does and apply this checklist.

## 2. Mandatory Questions for Authors

Before submitting a change, the author must answer these questions:

1. Does this change modify any prompt content, structure, or intent?
2. Does this change modify how the planner structures responses?
3. Does this change modify how reasoning is performed or how conclusions are derived?
4. Does this change modify how expression renders user-facing text from internal plans?
5. Does this change modify how hypotheses are created, updated, clamped, or stored?
6. Does this change modify how memory is stored, retrieved, or scoped?
7. Does this change introduce or use any cross-session information?
8. Does this change introduce any personalization based on past sessions?

If the answer to any question is "yes" or "not sure", the change is a cognitive change and must not proceed under normal operations.

## 3. Questions Reviewers MUST Ask Before Approving

Reviewers must ask and answer the following questions explicitly:

1. Does this change alter prompts in any way, including wording, examples, or structure?
2. Does this change alter planner behavior, including the number or type of sections produced?
3. Does this change alter how reasoning is carried out or which information is considered?
4. Does this change alter how expression is constrained by reasoning outputs?
5. Does this change alter hypothesis rules, including non-deletion and clamping?
6. Does this change alter memory rules, including TTL, session-only scope, or identity?
7. Does this change introduce any new path that bypasses or shortens cognition?
8. Could this change be seen as a contract-threatening change under the Governance Charter?

If any answer is "yes" or "not sure", the reviewer must block the change.

## 4. Examples of Disguised Cognitive Changes

These examples illustrate changes that may appear to be infrastructure or UX-only but actually touch cognition and must be treated as cognitive changes.

- "Clean up" prompts for readability.
- "Standardize" wording across different prompts.
- Add a new flag to skip reasoning for certain request types.
- Change memory keys to persist beyond session TTL.
- Add a fallback path that uses a different model or prompt when latency is high.
- Move logic that decides what to say from backend code into a different service without changing behavior on paper.

If a change affects what conclusions are drawn, what is remembered, or how responses are constrained, it is a cognitive change.

## 5. Final Attestation

Every change that passes review must include the following attestation from the author and at least one reviewer:

> "I confirm this change does not alter cognition. It does not change prompts, planner behavior, reasoning logic, expression constraints, hypothesis rules, memory rules, or introduce any new cognitive paths."

If this attestation cannot be truthfully made, the change must be blocked and escalated according to the Governance Charter.
