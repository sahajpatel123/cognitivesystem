# Steady-State Operation

This document defines what normal operation means after program closure.

## 1. Allowed Activities in Steady State

After closure, the following activities are allowed:

- **Running the system**
  - Operating the deployed system according to existing configurations and contracts.
- **Monitoring**
  - Observing metrics, logs, and user-facing reliability.
- **Compliance Audits**
  - Performing scheduled and event-driven audits as defined in compliance and drift detection documents.
- **Drift Handling**
  - Detecting, recording, and handling communication or governance drift using existing runbooks.

These activities support stable operation without changing how the system thinks or is described.

## 2. Explicitly Disallowed Activities in Steady State

The following activities are not allowed within steady-state operation of this program:

- **Feature Development**
  - Adding new capabilities or user-visible behaviors.
- **Cognitive Tuning**
  - Modifying how the system reasons, plans, or expresses responses.
- **Prompt Changes**
  - Editing, replacing, or extending prompts used by the system.
- **Language Evolution of System Description**
  - Changing the canonical public description of the system beyond what is already defined.
- **Changes to Core Rules**
  - Modifying memory rules, hypothesis rules, or any other cognitive constraints.

These activities are outside the scope of steady-state operation for this program.

## 3. Operation vs Development

- **Operation**
  - Running, monitoring, auditing, and enforcing existing rules.
  - Responding to incidents within the boundaries of current contracts and governance.
- **Development**
  - Creating, changing, or extending system behavior, cognition, or product capabilities.

In this program, only operation is permitted. Development is not permitted.

## 4. Maintenance vs Improvement

- **Maintenance**
  - Keeping existing behavior and descriptions consistent and functional.
  - Addressing issues through enforcement, auditing, and documentation updates that do not alter cognition or claims.
- **Improvement**
  - Changing behavior, performance characteristics, or promises.

In this program, maintenance is allowed; improvement is not.
