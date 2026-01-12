# Compliance Runbook

This runbook describes how continuous compliance and drift detection (STEP O) are operated. It does not modify cognition or CI behavior.

## 1. Audit Schedule

Compliance audits are run at defined times:

- **Regular audits**
  - For example: monthly.
- **Pre-scale audits**
  - Before moving to a higher rollout tier.
- **Post-incident audits**
  - After major incidents affecting the cognitive system.

The exact schedule is defined by operations policy but must include all three categories.

## 2. Roles Responsible

- **Compliance Auditor (role)**
  - Runs the audit using this runbook and the Audit Checklist.
  - Prepares the Compliance Report.
- **Cognitive Owner (role)**
  - Reviews findings related to cognition and governance.
- **Delivery Owner (role)**
  - Reviews findings related to delivery and infrastructure drift.
- **Product Owner (role)**
  - Reviews findings related to governance pressure and rollout scope.

## 3. Audit Procedure

1. **Collect current state**
   - Retrieve current cognition code hash.
   - Retrieve current prompt hashes.
   - Verify planner structures and memory key patterns.
2. **Run automated drift checks**
   - Code and prompt hash comparisons.
   - Planner structure enumeration.
   - Memory key pattern and forbidden pattern scans.
3. **Run human checks**
   - Review documentation vs code and prompts.
   - Review Governance Pressure Log entries.
   - Review incident postmortems for the audit period.
4. **Complete the Audit Checklist**
   - Answer all yes/no questions in `AUDIT_CHECKLIST.md`.
5. **Prepare the Compliance Report**
   - Use `COMPLIANCE_REPORT_TEMPLATE.md`.
   - Record drift classification for each surface.
   - Record governance pressure and incident summaries.

## 4. Handling Detected Drift

When drift is detected:

- **Documentation drift**
  - Record the mismatch and notify relevant roles.
- **Delivery drift (allowed)**
  - Record the drift and confirm that cognition is unchanged.
- **Cognitive drift (blocking signal)**
  - Record the drift and escalate according to the Governance Charter.

In all cases:

- Do not modify cognition as part of the audit.
- Do not apply fixes during the compliance procedure.
- Use the Governance Charter to determine next steps.

## 5. Interaction with CI

- CI can compute and record hashes and run automated drift checks.
- CI can surface drift signals as warnings or reports.
- CI does not automatically block deployments based solely on this runbook.

Decisions to block or allow deployments remain with the governance roles defined in the Governance Charter.
