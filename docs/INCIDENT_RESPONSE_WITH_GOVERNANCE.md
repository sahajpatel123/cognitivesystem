# Incident Response with Governance

This document defines how incidents are handled without modifying cognition. It applies to all incident types related to the cognitive system.

## 1. Incident Flow Overview

All incidents follow the same high-level flow:

1. **Detection**
   - An alert fires or an issue is reported (latency, errors, cost, outages).
2. **Mitigation**
   - Take delivery-layer actions to stabilize the system.
3. **Communication**
   - Inform stakeholders about the incident and mitigation steps.
4. **Resolution**
   - Restore normal service within governance constraints.
5. **Postmortem**
   - Analyze root causes, validate governance adherence, and record lessons at the delivery level.

At every step, cognition must remain unchanged.

## 2. Incident Types and Rules

### 2.1 Latency Incidents

- **Allowed actions**
  - Scale infrastructure up.
  - Adjust rate limits and throttling.
  - Shed non-critical traffic at the edge.
  - Temporarily reduce non-essential features above the cognitive layer.
- **Forbidden actions**
  - Skipping the Reasoning LLM.
  - Reducing reasoning steps.
  - Editing prompts to make responses shorter or faster.
  - Introducing any cognition shortcut.
- **Mandatory logging**
  - Record start and end time of the incident.
  - Record all changes made to infrastructure and configuration.
  - Record any proposed cognitive changes and their rejection.

### 2.2 Cost Spikes

- **Allowed actions**
  - Right-size infrastructure.
  - Adjust rate limits and quotas.
  - Reduce rollout scope or traffic.
- **Forbidden actions**
  - Changing prompts to reduce tokens.
  - Switching to a cheaper but different cognitive configuration.
  - Modifying reasoning, planner, hypotheses, or memory rules to reduce cost.
- **Mandatory logging**
  - Record cost metrics and thresholds exceeded.
  - Record decisions around rollout scope and rate limits.
  - Record any attempted or requested cognitive changes and their rejection.

### 2.3 LLM Outages

- **Allowed actions**
  - Fail closed with clear user-visible errors.
  - Route to alternative instances of the same certified model and configuration.
- **Forbidden actions**
  - Switching to a different model or prompt that alters cognition.
  - Adding fallback heuristics that bypass cognition.
  - Introducing alternative reasoning paths.
- **Mandatory logging**
  - Record outage duration and impact.
  - Record which endpoints or instances were used.
  - Record all rejected proposals for cognitive workarounds.

### 2.4 Data Store Outages

- **Allowed actions**
  - Fail with appropriate delivery-level error responses.
  - Temporarily degrade features that depend on the data store, without breaching memory rules.
  - Restart or reconfigure the data store.
- **Forbidden actions**
  - Changing memory TTL or semantics during the incident.
  - Introducing cross-session memory or identity as a workaround.
- **Mandatory logging**
  - Record the nature and duration of the outage.
  - Record any state recovery steps taken.
  - Record any proposals to change memory behavior and their rejection.

## 3. Non-Negotiable Cognition Rule

**Cognition MUST NOT be modified during incidents — ever.**

- No prompt changes.
- No planner changes.
- No reasoning logic changes.
- No hypothesis or memory rule changes.
- No temporary or emergency cognitive workarounds.

Any suggestion to modify cognition during an incident must be rejected and logged as governance pressure.

## 4. Incident Commander Read-Aloud Checklist

Before approving any action during an incident, the Incident Commander must read the following aloud to the response team:

1. **Cognition is frozen.**
   - We will not change prompts, planner behavior, reasoning logic, hypotheses, or memory rules.
2. **Only delivery-layer actions are allowed.**
   - We may scale infrastructure, adjust rate limits, shed load, and adjust rollout scope.
3. **No emergency cognitive workarounds.**
   - We will not introduce new cognitive paths, shortcuts, or temporary rules.
4. **All proposed cognitive changes must be rejected and logged.**
   - Any suggestion to change cognition will be recorded as governance pressure.
5. **We accept degraded service over broken governance.**
   - It is better to have reduced or unavailable service than to silently change how the system thinks.

The checklist must be revisited if the incident extends over a long period or if the incident response team changes.
