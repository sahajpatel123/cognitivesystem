# Audit Checklist

This checklist supports periodic audits of continuous compliance. It uses yes/no questions. If any answer is "No", drift must be logged. The checklist does not include remediation steps.

## 1. Cognition Integrity

1.1 Has the cognition code hash been compared to the certified hash?
- [ ] Yes
- [ ] No

1.2 Does the current cognition code hash match the certified hash?
- [ ] Yes
- [ ] No

1.3 Have there been any code changes that modify reasoning logic, expression logic, planner behavior, hypothesis handling, or memory handling since the last audit?
- [ ] Yes
- [ ] No

1.4 If "Yes" to 1.3, were these changes authorized through a higher-order governance process?
- [ ] Yes
- [ ] No

## 2. Prompt Integrity

2.1 Have prompt hashes for the Reasoning LLM and Expression LLM been compared to the certified hashes?
- [ ] Yes
- [ ] No

2.2 Do the current prompt hashes match the certified hashes?
- [ ] Yes
- [ ] No

2.3 Have any prompt contents, structures, or examples been changed since the last audit?
- [ ] Yes
- [ ] No

2.4 If "Yes" to 2.3, were these changes authorized through a higher-order governance process?
- [ ] Yes
- [ ] No

## 3. Memory and Hypothesis Integrity

3.1 Do memory key patterns still follow the documented session-only design?
- [ ] Yes
- [ ] No

3.2 Do memory entries still use TTL-bound storage as documented?
- [ ] Yes
- [ ] No

3.3 Has any cross-session identity or profiling behavior been observed or implemented?
- [ ] Yes
- [ ] No

3.4 Do hypotheses remain session-local, non-deleting, and clamped as described in the Cognitive Contract?
- [ ] Yes
- [ ] No

## 4. Governance Adherence

4.1 Is the Governance Charter still in effect and unmodified in substance?
- [ ] Yes
- [ ] No

4.2 Have any roles been allowed to approve cognitive changes outside the Governance Charter?
- [ ] Yes
- [ ] No

4.3 Have all proposals for cognitive changes been logged in the Governance Pressure Log?
- [ ] Yes
- [ ] No

4.4 Have any logged cognitive change proposals later been implemented without higher-order governance approval?
- [ ] Yes
- [ ] No

## 5. Incident Behavior

5.1 Have incident postmortems been reviewed for the audit period?
- [ ] Yes
- [ ] No

5.2 During incidents, were any prompts, planner behavior, reasoning logic, hypotheses, or memory rules modified?
- [ ] Yes
- [ ] No

5.3 If "Yes" to 5.2, were these changes authorized through a higher-order governance process?
- [ ] Yes
- [ ] No

## 6. Drift Logging Instruction

If any answer above is "No" where "Yes" is required for conformance, or "Yes" where "No" indicates a violation:

- Log the drift in the appropriate record (for example, Governance Pressure Log or a separate drift record).
- Do **not** perform fixes as part of this checklist.
- Escalate according to the Governance Charter.
