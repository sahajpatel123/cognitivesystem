# Governance Scenario Drills

This document provides practice scenarios to help staff apply cognitive governance under realistic pressure.

Success in these drills is not measured by fixing problems. Success is measured by not breaking the Cognitive Contract.

## Scenario 1: Executive Demands Faster Responses During an Outage

- **Situation**
  - A latency incident is affecting a key region. An executive asks the team to "do whatever it takes" to make responses faster.
- **Common wrong responses**
  - Proposing to skip the Reasoning LLM for some requests.
  - Suggesting prompt changes to make outputs shorter and faster.
- **Correct governance response**
  - Apply delivery-layer mitigations only (scaling, throttling, load shedding).
  - Reject any suggestion to modify cognition.
- **Who has authority**
  - Incident Commander for delivery actions.
  - Cognitive Owner for governance decisions.
- **What must be logged**
  - The executive request.
  - The rejected cognitive proposals.
  - The delivery actions taken.

## Scenario 2: Cost Alarm Triggers Finance Escalation

- **Situation**
  - Cost monitoring shows a significant increase during peak hours. Finance escalates and asks for immediate cost reduction.
- **Common wrong responses**
  - Reducing reasoning complexity in prompts.
  - Switching to a cheaper model with different behavior.
- **Correct governance response**
  - Adjust rollout scope, rate limits, or infrastructure within governance rules.
  - Reject cognitive changes aimed at reducing cost.
- **Who has authority**
  - Delivery Owner and Product Owner for rollout and capacity decisions.
  - Cognitive Owner for governance boundaries.
- **What must be logged**
  - The cost alarm and escalation.
  - Any rejected cognitive change proposals.
  - The non-cognitive actions taken.

## Scenario 3: Product Manager Requests Personalization

- **Situation**
  - A product manager requests personalization based on user history to improve engagement.
- **Common wrong responses**
  - Proposing cross-session memory to store user preferences.
  - Suggesting identity-based tuning of cognition.
- **Correct governance response**
  - Explain that cross-session memory and user profiling are forbidden.
  - Consider allowed UX-level improvements that do not break session-only rules.
- **Who has authority**
  - Product Owner for non-cognitive UX changes.
  - Cognitive Owner for enforcement of memory and identity rules.
- **What must be logged**
  - The personalization request.
  - The decision to reject cognitive changes.

## Scenario 4: Engineer Proposes "Minor" Prompt Cleanup

- **Situation**
  - An engineer proposes to "standardize" and "clean up" prompt wording to make it more consistent.
- **Common wrong responses**
  - Treating the change as a simple refactor and approving it.
- **Correct governance response**
  - Classify the change as a cognitive change.
  - Block the change under normal operations and refer to the Governance Charter.
- **Who has authority**
  - No role may approve this as a routine change.
  - Any reconsideration requires a higher-order governance process.
- **What must be logged**
  - The proposal and reasoning.
  - The decision to block the change.

## Scenario 5: Suggestion to Add a Fast Path for Simple Questions

- **Situation**
  - An engineer suggests adding a fast path for "simple" queries that bypasses full reasoning to improve responsiveness.
- **Common wrong responses**
  - Implementing the fast path as an optimization.
- **Correct governance response**
  - Recognize this as a cognition shortcut and a contract-threatening change.
  - Reject the proposal.
- **Who has authority**
  - Cognitive Owner to enforce the Cognitive Contract.
  - Delivery Owner to pursue allowed delivery optimizations instead.
- **What must be logged**
  - The suggestion.
  - Its classification as a contract-threatening change.
  - The rejection decision.

In all scenarios, success means preserving the Cognitive Contract and Governance Charter, even when this leads to slower service, reduced functionality, or higher short-term cost.
