# Role Accountability Matrix

This document defines what different roles are allowed to say about the system, what they are forbidden to imply, and how violations are handled.

## 1. Reference

All roles are bound by:

- `docs/LAUNCH_NARRATIVE.md`
- `docs/ANTI-ANTHROPOMORPHISM_GUIDE.md`
- `docs/DEMO_AND_SALES_BOUNDARIES.md`
- `docs/LAUNCH_RISK_CHECKLIST.md`

Seniority does not grant exceptions.

## 2. Sales

- **Allowed to say**
  - Capabilities and limitations as described in `LAUNCH_NARRATIVE.md`.
  - Demo-safe explanations from `DEMO_AND_SALES_BOUNDARIES.md`.
- **Forbidden to imply**
  - Memory across sessions.
  - Learning from individual customers.
  - Per-customer tuning of how the system behaves.
  - Future cognitive customization for specific deals.
- **Violation handling**
  - Violations are logged as drift incidents.
  - Repeated violations trigger mandatory retraining and may restrict who may represent the product.

## 3. Marketing

- **Allowed to say**
  - System description and limitations from `LAUNCH_NARRATIVE.md`.
  - Non-anthropomorphic benefits, such as clarity and structure.
- **Forbidden to imply**
  - That the system is a person, teammate, or agent.
  - That it adapts to or remembers individual users.
  - That future versions will add learning or personalization, unless separately authorized.
- **Violation handling**
  - Violations are logged and materials are withdrawn.
  - Repeated violations require pre-approval of all marketing copy for a defined period.

## 4. Product

- **Allowed to say**
  - Current capabilities and constraints based on existing documents.
  - How the product is used, not how cognition is or will be changed.
- **Forbidden to imply**
  - That cognition will change to meet roadmap or customer requests.
  - That personalization or long-term memory is planned.
- **Violation handling**
  - Violations are logged.
  - Repeated violations are escalated to governance for review of communication responsibilities.

## 5. Executives

- **Allowed to say**
  - High-level description from `LAUNCH_NARRATIVE.md`.
  - Directional statements that do not contradict existing constraints.
- **Forbidden to imply**
  - That the system will be personalized, will learn individuals, or will have identity.
  - That exceptions can be made for key customers.
  - That internal rules can be relaxed for growth.
- **Violation handling**
  - Executive statements are subject to the same drift incident process.
  - Repeated violations require direct governance review and may trigger additional approvals for external appearances.

## 6. Customer Success

- **Allowed to say**
  - Clarifications of limitations from `LAUNCH_NARRATIVE.md`.
  - Demo-safe answers from `DEMO_AND_SALES_BOUNDARIES.md`.
- **Forbidden to imply**
  - That the system will "learn the customer" over time.
  - That additional use will cause the system to adapt or remember.
- **Violation handling**
  - Violations are logged and may require updated support macros and retraining.

## 7. Incident Commanders

- **Allowed to say**
  - Operational status and impact.
  - Neutral explanations that do not discuss internal cognition.
- **Forbidden to imply**
  - That the system will change how it works because of incidents.
  - That emergency changes to how it behaves are possible.
- **Violation handling**
  - Any such statements are logged as drift incidents and reviewed in post-incident analysis.

## 8. Logging of Violations

- All violations, regardless of role, are logged in a central record.
- Logs include:
  - Date and context.
  - Role and team involved.
  - Content of the violation.
- Logs are used for audits and for adjusting oversight as needed.
