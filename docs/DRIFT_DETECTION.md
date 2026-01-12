# Drift Detection

This document defines how drift from the Certified System is detected. It describes automated and human signals. It does not define how to fix drift.

## 1. Automated Drift Signals

Automated checks can detect differences between the current system and the Certified System.

### 1.1 Cognition Code Hash Comparison

- Compute a hash of all code that implements cognition:
  - Reasoning logic.
  - Expression logic.
  - Planner behavior.
  - Hypothesis handling.
  - Memory handling.
- Compare this hash to the last certified hash.
- Any difference is a potential drift signal.

### 1.2 Prompt Hash Comparison

- Compute hashes of all prompts used by the Reasoning LLM and Expression LLM.
- Compare these hashes to the certified prompt hashes.
- Any difference is a potential drift signal.

### 1.3 Planner Structure Enumeration Comparison

- Enumerate planner structures and allowed sections.
- Compare the set of structures to the certified version.
- Any addition, removal, or modification is a potential drift signal.

### 1.4 Memory Key Pattern Verification

- Verify that memory keys follow the documented session-only patterns.
- Ensure that keys include session identifiers and follow TTL rules.
- Any deviation from the expected patterns is a potential drift signal.

### 1.5 Forbidden Key and Pattern Scans

- Scan for keys or patterns that indicate:
  - Cross-session identity.
  - Long-term profiles.
  - Personalization based on past sessions.
- Discovery of such keys or patterns is a cognitive drift signal.

## 2. Human-Required Drift Signals

Some forms of drift require human judgment.

### 2.1 Documentation vs Code Review

- Periodically review code and prompts against:
  - `docs/COGNITIVE_CONTRACT.md`
  - `docs/GOVERNANCE_CHARTER.md`
- Confirm that implementation matches documentation.
- Any mismatch is documentation drift.

### 2.2 Governance Pressure Review

- Review entries in `docs/GOVERNANCE_PRESSURE_LOG.md`.
- Check whether any rejected cognitive change was later implemented.
- Any such case is cognitive drift.

### 2.3 Incident Postmortem Scan

- For each incident postmortem, verify:
  - No cognitive changes were made as part of the response.
- If cognitive changes were made, this is cognitive drift.

## 3. Drift Classification Levels

Drift is classified into four levels.

### 3.1 NO DRIFT

- All automated checks match certified values.
- Documentation and implementation align.
- No unauthorized cognitive changes are detected.

### 3.2 DOCUMENTATION DRIFT

- Implementation and prompts match the Certified System.
- Documentation is out of date or incomplete.
- The behavior of the system still conforms to the Cognitive Contract and Governance Charter.

### 3.3 DELIVERY DRIFT (Allowed)

- Differences exist in delivery or infrastructure configuration only.
- Cognition, prompts, planner behavior, hypotheses, and memory semantics are unchanged.
- The drift is within the scope of allowed delivery changes.

### 3.4 COGNITIVE DRIFT (Blocking Signal)

- Any unauthorized change to:
  - Cognition code.
  - Prompts.
  - Planner definitions.
  - Hypothesis rules or behavior.
  - Memory semantics or identity behavior.
- Any implementation of previously rejected cognitive changes.

Cognitive drift is a blocking signal. It indicates that the running system is no longer the Certified System and requires governance escalation.

## 4. Scope of Drift Detection

- Drift detection does not apply fixes.
- Drift detection does not change code, prompts, or configuration.
- Drift detection produces signals for governance review and audit.
