# Governance Charter

This document defines governance for the cognitive system. It specifies what is frozen, what may change, and who has authority to approve changes.

## 1. Scope

- This charter applies to all components that implement or affect:
  - The Cognitive Contract.
  - WHAT vs HOW separation.
  - Hypothesis rules.
  - Memory rules.
  - Planner behavior.
  - Expression constraints.
- UI, infrastructure capacity, and non-cognitive observability are covered only insofar as they must not violate the Cognitive Contract.

## 2. Frozen vs Mutable Surfaces

### 2.1 Permanently Frozen

The following surfaces are cognitively frozen and may not be changed under normal operations:

- Reasoning logic.
- Expression constraints.
- Planner semantics.
- Hypothesis rules.
- Memory rules.
- Prompt structure and intent.

Any modification to these surfaces is a cognitive change and requires a separate, higher-order governance process outside this charter.

### 2.2 Conditionally Mutable

The following surfaces may change if they do not alter cognition:

- Infrastructure (instance types, node counts, regions, networking).
- Rate limits (API throttling, concurrency caps, quotas).
- Deployment topology (replicas, regions, blue/green, canary, without cognitive variation).
- Caching of final responses only (exact-match caching of user-visible outputs).
- Observability (metrics, logs, traces, dashboards) that do not change cognitive behavior.

### 2.3 Never Allowed

The following are categorically forbidden:

- Cross-session memory.
- User profiling.
- Modes or levels that change cognitive behavior.
- Cognition shortcuts (skipping or bypassing reasoning).
- Prompt tuning for UX, style, or cost that alters cognition.

## 3. Roles and Decision Authority

### 3.1 Cognitive Owner

- May approve:
  - Clarifications of documentation that describe the existing Cognitive Contract.
  - Non-functional internal naming or organization changes that do not alter behavior.
- May not approve:
  - Any change to prompts, reasoning logic, planner semantics, hypothesis rules, or memory rules.
  - Any experimentation with alternative cognitive configurations.
- Requires escalation for:
  - Any proposal classified as cognitive change or contract-threatening change.
  - Any stakeholder or incident-driven request to modify cognition.

### 3.2 Delivery Owner

- May approve:
  - Delivery changes such as infrastructure scaling, rate limits, deployment strategies, and caching of final responses only.
  - Observability enhancements at the delivery and infrastructure layers.
- May not approve:
  - Any modification to cognitive components or prompts.
  - Any change that bypasses or conditionally skips cognitive steps.
- Requires escalation for:
  - Any change that might indirectly affect cognition (for example, aggressive caching or selective routing that changes behavior).
  - Any incident response proposal that suggests altering cognition.

### 3.3 Product Owner

- May approve:
  - Rollout scope decisions within the certified cognitive configuration.
  - Frontend UX flows that consume the existing API contract without changing cognition.
- May not approve:
  - Any cognitive, prompt, planner, hypothesis, or memory changes, regardless of business motivation.
  - Any experiments that involve different cognitive behaviors or prompt sets.
- Requires escalation for:
  - Requests for customized cognition for segments or user groups.
  - Proposals that trade off cognitive constraints for engagement or revenue.

### 3.4 Incident Commander

- May approve:
  - Emergency delivery-layer actions such as traffic shedding, scaling, disabling non-essential features above cognition, and read-only modes.
- May not approve:
  - Any change to prompts, cognitive stages, or memory and hypothesis rules during incidents.
  - Any "temporary" cognitive changes as an incident workaround.
- Requires escalation for:
  - Any emergency request that implies or requires cognitive modification.

## 4. Incident Rule

- Cognition may never be modified during incidents.
- All incident responses must remain within delivery and infrastructure surfaces.
- Any proposal to modify cognition during an incident must be rejected and logged as governance pressure.
