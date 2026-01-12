# Operational Enforcement Playbook

This playbook defines how STEP Q launch and communication rules are enforced in daily operations. It does not change cognition or product behavior.

All sections below are mandatory. There are no optional parts.

## 1. Reference Documents

Operational enforcement relies on the following documents:

- `docs/LAUNCH_NARRATIVE.md`
- `docs/ANTI-ANTHROPOMORPHISM_GUIDE.md`
- `docs/DEMO_AND_SALES_BOUNDARIES.md`
- `docs/LAUNCH_RISK_CHECKLIST.md`

These documents define what may and may not be said about the system externally.

## 2. Language Review Gates

Language review gates are required before any external material is used.

### 2.1 Scope

Language review is required for:

- Public website copy.
- Product marketing pages.
- Sales decks and one-pagers.
- Demo scripts.
- Press releases and blog posts.
- Conference talk abstracts and slide decks.

### 2.2 Process

1. The author submits materials to a designated Language Reviewer.
2. The Language Reviewer checks all text against:
   - `LAUNCH_NARRATIVE.md` (overall framing).
   - `ANTI-ANTHROPOMORPHISM_GUIDE.md` (forbidden vs approved phrases).
   - `DEMO_AND_SALES_BOUNDARIES.md` (for any demo-related content).
3. The Language Reviewer completes `LAUNCH_RISK_CHECKLIST.md` for the material.
4. If any checklist item fails, the material is rejected.
5. Only materials that pass all checks may be used externally.

### 2.3 Enforcement

- No material may be published or used in external settings without a recorded Language Review.
- Missing or bypassed review is treated as a violation and logged.

## 3. Pre-Demo and Pre-Talk Certification

Any live demo or talk that shows or describes the system must pass certification.

### 3.1 Required Actions

Before the event:

1. Presenter submits:
   - Demo script or outline.
   - Slides, if any.
2. A Language Reviewer verifies that:
   - All statements are consistent with `LAUNCH_NARRATIVE.md`.
   - No anthropomorphic language is used, per `ANTI-ANTHROPOMORPHISM_GUIDE.md`.
   - All demo claims comply with `DEMO_AND_SALES_BOUNDARIES.md`.
3. Reviewer signs off on a short certification note:
   - Event name.
   - Date.
   - Materials reviewed.
   - Outcome: approved or rejected.

### 3.2 Blocking Condition

- If certification is not completed, the demo or talk does not proceed.
- If a presenter uses uncertified materials, it is a violation and must be logged.

## 4. Sales and Customer Success Call Guardrails

Sales and Customer Success calls must obey communication boundaries.

### 4.1 Pre-Call Briefing

- Sales and Customer Success teams must:
  - Read `LAUNCH_NARRATIVE.md` and `DEMO_AND_SALES_BOUNDARIES.md` during onboarding.
  - Review them at least once per quarter.

### 4.2 Call Rules

During calls:

- Representatives must not:
  - Promise memory across sessions.
  - Promise learning from individual users.
  - Promise personalization or adaptation.
  - Suggest that cognition will be customized for specific accounts.
- If asked about such capabilities, they must answer according to `DEMO_AND_SALES_BOUNDARIES.md`.

### 4.3 Call Sampling

- A sample of recorded calls (where recording is permitted) must be reviewed each month by a Compliance Reviewer.
- The reviewer checks for:
  - Violations of anti-anthropomorphism rules.
  - Misstatements about memory, learning, or personalization.
- Detected violations trigger drift incident handling.

## 5. Incident Communications Lockdown

During technical incidents, all external communications about the system are subject to lockdown.

### 5.1 Scope

- Status pages.
- Email updates to customers.
- Social media posts.
- Support macros and canned responses.

### 5.2 Process

1. Incident Commander designates a Communications Owner.
2. Communications Owner drafts all external statements about the incident.
3. A Language Reviewer checks for:
   - No claims that the system is "learning from the incident".
   - No anthropomorphic language.
   - No promises to change how the system thinks.
4. Only reviewed statements may be sent.

### 5.3 Blocking Condition

- If no reviewer is available, communications must limit themselves to neutral operational status (for example, "service available/unavailable") and must not discuss system behavior.

## 6. Marketing Copy Escalation Rules

Marketing initiatives that reference intelligence, learning, or personalization require explicit escalation.

### 6.1 Trigger

- Any proposal that uses language about:
  - learning,
  - adapting,
  - remembering,
  - understanding users,
  - or intelligence growth.

### 6.2 Actions

1. Proposal is immediately escalated to:
   - Language Reviewer.
   - Product Owner.
2. Proposal is evaluated solely for compliance with `LAUNCH_NARRATIVE.md` and `ANTI-ANTHROPOMORPHISM_GUIDE.md`.
3. If any part conflicts, the proposal is rejected.

### 6.3 Enforcement

- Approval cannot be granted informally.
- Any unapproved marketing copy that reaches public channels is treated as a drift incident.
