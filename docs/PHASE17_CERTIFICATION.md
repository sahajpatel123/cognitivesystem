# Phase 17 Certification — Deep Thinking (Frozen)

## Certification Version

**PHASE17_CERT_VERSION = "17.9.0"**

This document certifies that Phase 17 Deep Thinking implementation satisfies all contract invariants and passes all evaluation gates. Phase 17 is now **FROZEN** — any changes to routing caps, StopReasons, signature computation, validator strike logic, or telemetry structure require recertification.

---

## 1. INVARIANTS (ENFORCED)

### 1.1 Non-Agentic Invariant
**Statement**: Deep thinking performs ONLY in-request computation. No tool usage, external calls, file writes, or side effects outside DecisionDelta production.

**Enforcement Locations**:
- `backend/app/deepthink/passes/*.py`: All pass implementations are pure functions with no external calls
- `backend/app/deepthink/engine.py`: Engine orchestration uses only injected dependencies (clock, runner)
- Contract: §3.1

**Verification**: All passes are deterministic functions that accept state + context and return PassRunResult with delta only.

---

### 1.2 State Mutation Invariant
**Statement**: Deep thinking can ONLY modify DecisionDelta-allowed paths defined in schema.

**Enforcement Locations**:
- `backend/app/deepthink/schema.py`: ALLOWED_PATCH_PATHS defines exhaustive allowlist
  - `decision.action`
  - `decision.answer`
  - `decision.rationale`
  - `decision.clarify_question`
  - `decision.alternatives`
- `backend/app/deepthink/validator.py`: Validates every patch op against allowlist
- `backend/app/deepthink/patch.py`: Rejects patches to non-allowed paths
- Contract: §3.2

**Verification**: Validator rejects any patch with path not in ALLOWED_PATCH_PATHS. Patch applier enforces same constraint.

---

### 1.3 Fail-Closed Ladder
**Statement**: On ANY failure, system downgrades to baseline state. No partial application of invalid deltas.

**Enforcement Locations**:
- `backend/app/deepthink/engine.py`: 
  - `_downgrade_output()` returns initial_state on failure
  - Two-strikes validator logic (validator_strikes >= 2) triggers downgrade
  - All exception handlers return downgrade output
- Contract: §3.3, §6

**Verification**: Engine returns initial_state (baseline) on:
- Validation failure (2 strikes)
- Budget exhausted
- Timeout
- Breaker tripped
- Entitlement cap
- Abuse blocked
- Internal inconsistency

---

### 1.4 StopReasons Exhaustive + Deterministic
**Statement**: Every termination path maps to exactly one StopReason code from contract. No "OTHER" or unmapped terminations.

**Enforcement Locations**:
- `backend/app/deepthink/router.py`: StopReason enum with exhaustive codes
- `backend/app/deepthink/engine.py`: STOP_PRIORITY_ORDER defines deterministic priority
- Contract: §5

**Contract StopReason Codes**:
1. `SUCCESS_COMPLETED`
2. `BUDGET_EXHAUSTED`
3. `PASS_LIMIT_REACHED`
4. `TIMEOUT`
5. `BREAKER_TRIPPED`
6. `ENTITLEMENT_CAP`
7. `ABUSE`
8. `VALIDATION_FAIL`
9. `INTERNAL_INCONSISTENCY`

**Verification**: All engine termination paths explicitly set one of these codes. Stop priority order is fixed and deterministic.

---

### 1.5 Deterministic Replay Guarantee
**Statement**: Identical inputs (tier, mode, budget, timeout, breaker, abuse) + identical pass_plan + identical pass outputs → identical final state + identical meta.

**Enforcement Locations**:
- `backend/app/deepthink/router.py`: Deterministic plan generation (no randomness, no wall clock)
- `backend/app/deepthink/engine.py`: Deterministic orchestration with injected clock
- All passes: Deterministic scoring and delta generation
- Contract: §3.4

**Verification**: Replay tests run engine N times with identical inputs and assert all outputs match exactly.

---

### 1.6 Telemetry Signature Has NO User Text
**Statement**: Decision signature is computed from structural metadata only (stable_inputs + pass_plan + deltas structure). NO raw user text or assistant text included.

**Enforcement Locations**:
- `backend/app/deepthink/telemetry.py`:
  - `compute_decision_signature()`: Encodes deltas as structure (op/path/type/length) not content
  - `_encode_value_metadata()`: Strings encoded as `{"type":"str","len":N}` not content
  - FORBIDDEN_TEXT_KEYS: Blocks user_text, answer, rationale, clarify_question, etc.
- `backend/app/deepthink/engine.py`: Uses telemetry module for signature computation
- Contract: Implicit in §7 (telemetry must not leak user data)

**Verification**: Sentinel strings injected into deltas do NOT appear in signature or telemetry event JSON.

---

## 2. EVALUATION GATES

### Gate A: Deterministic Replay Gate
**Purpose**: Prove that identical inputs produce identical outputs across all engine components.

**Test File**: `backend/tests/test_phase17_eval_gates.py::TestDeterministicReplayGate`

**Pass Criteria**:
- Run engine 20+ times with identical EngineInput
- Assert final_state identical (all fields)
- Assert meta.stop_reason identical
- Assert meta.validator_failures identical
- Assert meta.downgraded identical
- Assert meta.decision_signature identical
- Assert meta.telemetry_event identical (after JSON serialization with sort_keys=True)

**Fail Criteria**: Any output differs across runs.

---

### Gate B: Two-Strikes Downgrade Gate (Exactness)
**Purpose**: Prove that validator downgrade triggers EXACTLY on second validation failure, not before or after.

**Test File**: `backend/tests/test_phase17_eval_gates.py::TestTwoStrikesDowngradeGate`

**Pass Criteria**:
- After first invalid delta: validator_failures == 1, downgraded == False, execution continues
- After second invalid delta: validator_failures == 2, downgraded == True, stop_reason == "VALIDATION_FAIL"
- Engine stops immediately after second failure (no further passes executed)
- Final state is initial_state (baseline)

**Fail Criteria**: Downgrade triggers on first failure, or after third failure, or never.

---

### Gate C: StopReason Contract Gate
**Purpose**: Prove that all StopReasons used in code are members of the contract exhaustive set.

**Test File**: `backend/tests/test_phase17_eval_gates.py::TestStopReasonContractGate`

**Pass Criteria**:
- All StopReasons in router/engine/validator are in contract set
- No "OTHER" or unmapped codes used
- Contract document contains all expected codes

**Fail Criteria**: Code uses StopReason not in contract, or contract is missing expected codes.

---

### Gate D: Telemetry & Summary Safety Gate (No Text Leakage)
**Purpose**: Prove that telemetry and logging never contain raw user text or assistant text.

**Test File**: `backend/tests/test_phase17_eval_gates.py::TestTelemetrySafetyGate`

**Pass Criteria**:
- Sentinel strings (SENSITIVE_USER_TEXT_123, SENSITIVE_ASSISTANT_TEXT_456) injected into deltas
- Sentinels do NOT appear in:
  - meta.decision_signature
  - json.dumps(meta.telemetry_event)
  - sanitized summary output
- Forbidden keys (user_text, answer, rationale, etc.) removed from summaries

**Fail Criteria**: Any sentinel string appears in signature, telemetry event, or summary.

---

## 3. EVIDENCE COMMANDS

### Compilation Check
```bash
python3 -m compileall backend/app/deepthink backend/tests
```
**Expected**: All files compile without syntax errors.

### Eval Gates Execution
```bash
# If pytest available:
python3 -m pytest -v backend/tests/test_phase17_eval_gates.py

# If pytest not available, use self-check runner:
python3 backend/tests/test_phase17_eval_gates.py
```
**Expected**: All gates PASS.

### Certification Freeze Check
```bash
python3 -m pytest -v backend/tests/test_phase17_certification_freeze.py
# OR
python3 backend/tests/test_phase17_certification_freeze.py
```
**Expected**: Certification doc exists, contains version string, gates are present.

---

## 4. CHANGE CONTROL

### Recertification Required For:
1. **Router Changes**: Modifying entitlement caps, pass count limits, or plan generation logic
2. **StopReason Changes**: Adding/removing/renaming StopReason codes
3. **Validator Changes**: Modifying strike threshold (currently 2) or validation rules
4. **Signature Changes**: Modifying decision_signature computation or included fields
5. **Schema Changes**: Adding/removing allowed patch paths or modifying bounds
6. **Telemetry Changes**: Modifying telemetry event structure or adding text fields

### Allowed Without Recertification:
1. **Pass Implementation**: Adding new passes or modifying pass scoring (if deterministic and patch-only)
2. **Documentation**: Clarifying comments, adding examples, fixing typos
3. **Test Expansion**: Adding more test cases to existing gates (if they strengthen verification)
4. **Performance**: Optimizing deterministic code paths without changing behavior

### Recertification Process:
1. Update PHASE17_CERT_VERSION (increment minor or major)
2. Re-run all eval gates and verify PASS
3. Update this document with changes and new evidence
4. Commit with message: "phase17: recertification vX.Y.Z"

---

## 5. FROZEN COMPONENTS

The following components are **FROZEN** as of certification 17.9.0:

- `backend/app/deepthink/router.py`: Pass plan generation, entitlement caps, StopReason enum
- `backend/app/deepthink/engine.py`: Orchestration logic, stop priority order, two-strikes rule
- `backend/app/deepthink/validator.py`: Strike threshold (2), validation rules
- `backend/app/deepthink/schema.py`: ALLOWED_PATCH_PATHS, PATH_SPECS, bounds constants
- `backend/app/deepthink/telemetry.py`: Signature computation, forbidden keys, delta encoding
- `docs/PHASE17_DEEP_THINKING_CONTRACT.md`: Invariants, StopReasons, fail-closed ladder

---

## 6. CERTIFICATION ATTESTATION

**Date**: 2026-01-28  
**Certified By**: Phase 17 Implementation Team  
**Version**: 17.9.0  
**Status**: FROZEN

All invariants enforced. All gates passing. Phase 17 is production-ready for integration.

**Next Steps**: Integration wiring (not part of Phase 17 scope).
