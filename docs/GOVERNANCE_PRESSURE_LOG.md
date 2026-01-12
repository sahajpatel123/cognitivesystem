# Governance Pressure Log

This document records governance pressure events: situations where stakeholders, operators, or other parties requested or implied cognitive changes that were not approved.

Logged pressure does not imply approval.

## 1. Logging Template

Each entry must follow this format:

- **ID**: `GP-YYYYMMDD-XX`
- **Phase**: LP1 / LP2 / LP3 / L2 / L3 / L4 / Cross-cutting
- **Tier**: 0 / 1 / 2 / 3 (if applicable)
- **Trigger Event**:
  - Brief description of the event (for example, "Tier 2 evening peak p99 latency above threshold").
- **Stakeholders**:
  - Roles or teams expressing pressure.
- **Requested or Implied Cognitive Change (Rejected)**:
  - Exact description of the requested or implied cognitive modification.
- **Governance Classification**:
  - Delivery change / UX change / Cost change / Cognitive change / Contract-threatening change.
- **Decision**:
  - Description of the decision taken (for example, "Rejected and handled via delivery-layer mitigations only").
- **Evidence Links**:
  - References to metrics, logs, incident reports, or meeting notes.
- **Follow-up (Non-Cognitive)**:
  - Any delivery or operational actions taken that adhered to the Governance Charter.

## 2. Example Entries

### GP-20251231-01

- **Phase**: LP2
- **Tier**: 0
- **Trigger Event**:
  - Sustained p99 latency above the comfort threshold during long-session load.
- **Stakeholders**:
  - Product, Operations.
- **Requested or Implied Cognitive Change (Rejected)**:
  - "Reduce reasoning depth or skip reasoning for simple follow-up questions." 
- **Governance Classification**:
  - Cognitive change.
- **Decision**:
  - Rejected under the Governance Charter. Addressed by adjusting delivery-layer capacity only.
- **Evidence Links**:
  - Latency dashboards and incident report for the period.
- **Follow-up (Non-Cognitive)**:
  - Increased infrastructure capacity and updated alert thresholds.

### GP-20251231-02

- **Phase**: LP3
- **Tier**: 1
- **Trigger Event**:
  - Cost spike associated with induced LLM degradation and retries.
- **Stakeholders**:
  - Finance, Operations.
- **Requested or Implied Cognitive Change (Rejected)**:
  - "Switch to a cheaper prompt configuration with fewer constraints." 
- **Governance Classification**:
  - Contract-threatening change.
- **Decision**:
  - Rejected under the Governance Charter. Delivery-only mitigations considered.
- **Evidence Links**:
  - Cost monitoring reports and incident summary.
- **Follow-up (Non-Cognitive)**:
  - Temporary reduction in test traffic volume and review of rate limits.

### GP-20251231-03

- **Phase**: L4
- **Tier**: 2
- **Trigger Event**:
  - Feedback that some long sessions felt "too tailored" to the user.
- **Stakeholders**:
  - Product, Policy.
- **Requested or Implied Cognitive Change (Rejected)**:
  - "Allow small cross-session personalization to smooth user experience." 
- **Governance Classification**:
  - Contract-threatening change.
- **Decision**:
  - Rejected under the Cognitive Contract and Governance Charter.
- **Evidence Links**:
  - User feedback samples and policy review notes.
- **Follow-up (Non-Cognitive)**:
  - Clarified communication about system behavior and session boundaries.
