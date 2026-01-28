# PHASE17 DEEP THINKING CONTRACT

## Purpose
This document freezes the constitutional rules for Phase 17 "Deep Thinking" multi-pass refinement. All future implementation steps (router, engine, passes, schema, telemetry, eval) MUST comply with these invariants. Any deviation invalidates Phase 17 certification.

## Scope
Phase 17 adds bounded multi-pass refinement to the cognition engine. It does NOT add agency, tools, retrieval, or memory expansion. Deep thinking remains purely in-request computation with deterministic orchestration.

---

## 1. DEFINITIONS

### 1.1 Deep Thinking Engine
A bounded multi-pass refinement system that produces 2–5 passes maximum. Each pass refines a baseline decision through structured delta application. The engine operates deterministically within a single request lifecycle.

### 1.2 Pass
A single refinement iteration that:
- Receives immutable DecisionState as input
- Produces DecisionDelta as output (patch-only)
- Operates within allocated timeout slice
- Cannot perform side effects or external calls

### 1.3 Pass Plan
An ordered list of passes (length 2–5) determined by the router before execution begins. The plan is immutable once set and must complete or fail-closed.

### 1.4 DecisionState
The baseline output structure produced by the existing single-pass cognition path. Treated as immutable input to deep thinking. Contains:
- Rendered text
- Action type
- Failure metadata (if any)
- Quality/safety scores
- Token counts

### 1.5 DecisionDelta
A patch-only output structure that specifies changes to DecisionState. Contains ONLY allowed field modifications. Until Step 17.3 defines the full schema, the baseline allowed fields are:
- `rendered_text` (refinement only)
- `quality_score` (adjustment only)
- `reasoning_trace` (additive only, internal telemetry)

**Strict Rule**: If a delta touches a non-allowed field → validation failure → fail-closed downgrade to baseline.

### 1.6 Deterministic Orchestration
The router and engine must produce identical pass plans and stop reasons for identical inputs (tier, mode, request context). No influence from:
- Wall clock time
- Randomness or sampling
- Network state
- External systems
- Unbounded recursion

---

## 2. NON-GOALS (EXPLICIT EXCLUSIONS)

Deep thinking is NOT:
- **An agent**: No tool usage, no file writes, no external API calls
- **Autonomous**: No self-directed workflows or goal-seeking
- **Memory-enabled**: No expansion of context beyond request (Phase 19 territory)
- **Retrieval-enabled**: No document search or knowledge base access (Phase 18 territory)
- **Browsing-enabled**: No web access or dynamic data fetching
- **Side-effect producing**: No state mutations outside DecisionDelta allowed fields

---

## 3. HARD-LOCKED INVARIANTS

### 3.1 Non-Agentic Invariant
Deep thinking performs:
- ✅ In-request computation only
- ✅ Structured delta production
- ✅ Deterministic refinement

Deep thinking MUST NOT perform:
- ❌ Tool usage
- ❌ External calls
- ❌ File writes
- ❌ Side effects outside producing DecisionDelta

**Enforcement**: Any attempt to import or call tools/retrieval/memory modules → validation failure → fail-closed downgrade.

### 3.2 State Mutation Invariant
Deep thinking can ONLY modify DecisionDelta-allowed fields (defined in §1.5).

**Rules**:
- DecisionState is immutable input
- Only validated deltas may be applied
- If delta touches non-allowed field → validation failure → fail-closed downgrade
- Engine must reject deltas that violate schema

**Baseline Allowed Fields** (until Step 17.3 extends):
- `rendered_text` (string refinement)
- `quality_score` (numeric adjustment)
- `reasoning_trace` (array append, internal only)

### 3.3 Fail-Closed Ladder
If ANY failure occurs, the system MUST downgrade to baseline single-pass behavior.

**Failure triggers**:
- Schema validation failure
- Validator threshold breach
- Timeout exceeded
- Breaker tripped
- Entitlement cap reached
- Abuse score threshold
- Internal inconsistency
- Delta application error

**Downgrade behavior**:
1. Discard all unapplied deltas
2. Return baseline DecisionState (existing safe output)
3. Record stop_reason + downgrade_reason (internal telemetry)
4. Must be deterministic
5. Must NOT leak internal details to user

### 3.4 Determinism Rules
**Router determinism**:
- Pass count (2–5) determined by: tier (Free/Pro/Max), runtime clamps, requested deep mode, environment mode
- Tie-breaking rules must be stable and documented

**Prohibited influences**:
- Wall clock time (except for timeout enforcement)
- Random sampling or non-deterministic selection
- Network latency or external system state
- Unbounded recursion or dynamic expansion

**Requirement**: Given identical inputs (tier, mode, request), router MUST produce identical pass plan.

---

## 4. PASS BUDGET AND STOP RULES

### 4.1 Pass Count Constraints
- **Minimum**: 2 passes
- **Maximum**: 5 passes
- **Never**: More than 5 passes under any circumstance

### 4.2 Timeout Allocation
Each pass receives an explicit timeout slice (implementation in Step 17.2). Total deep thinking time must not exceed request budget.

### 4.3 Early Stop Conditions
Engine may stop before completing all planned passes if:
- Budget exhausted (time or tokens)
- Breaker tripped
- Entitlement cap reached
- Abuse threshold exceeded
- Validation failure
- Internal inconsistency detected

---

## 5. STOP REASON ENUM (EXHAUSTIVE)

Every termination path MUST map to exactly one StopReason code. No vague "OTHER" bucket.

### 5.1 Stop Reason Codes

| Code | Description | Trigger Condition |
|------|-------------|-------------------|
| `SUCCESS_COMPLETED` | All planned passes completed successfully | Pass plan exhausted, all deltas applied |
| `BUDGET_EXHAUSTED` | Time or token budget consumed | Timeout or token limit reached |
| `PASS_LIMIT_REACHED` | Maximum pass count (5) reached | Pass count = 5, plan incomplete |
| `TIMEOUT` | Individual pass or total request timeout | Timeout enforced by breaker |
| `BREAKER_TRIPPED` | Cost breaker or reliability breaker opened | Breaker state = OPEN |
| `ENTITLEMENT_CAP` | User tier does not permit deep thinking | Tier = Free and deep mode requested |
| `ABUSE` | Abuse score threshold exceeded | Abuse decision = BLOCK |
| `VALIDATION_FAIL` | Delta schema validation failed | Delta touches non-allowed field or invalid structure |
| `INTERNAL_INCONSISTENCY` | Engine state corruption or unexpected error | Catch-all for unrecoverable internal errors |

### 5.2 Stop Reason Determinism
Given identical inputs and execution path, StopReason MUST be stable and reproducible.

### 5.3 Mapping Requirement
Every code path that terminates deep thinking MUST explicitly set one of these StopReason codes. No implicit or unmapped terminations allowed.

---

## 6. FAIL-CLOSED LADDER (STEP-BY-STEP)

The deep thinking execution flow with fail-closed guarantees:

### Step 1: Baseline Production
Produce baseline DecisionState using existing single-pass cognition path. This is the safe fallback output.

### Step 2: Route and Plan
Attempt to determine pass plan (2–5 passes) based on tier, mode, entitlements. If routing fails → return baseline (Step 1 output).

### Step 3: Execute Passes
Run each pass in sequence, producing DecisionDelta outputs. If any pass fails → stop execution, proceed to Step 6.

### Step 4: Validate Deltas
Validate each DecisionDelta against schema and allowed fields. If validation fails → discard delta, proceed to Step 6.

### Step 5: Apply Deltas
Apply validated deltas to baseline DecisionState in order. If application fails → discard remaining deltas, proceed to Step 6.

### Step 6: Downgrade on Failure
If ANY failure occurred in Steps 2–5:
- Discard all unapplied deltas
- Return baseline DecisionState from Step 1
- Record stop_reason and downgrade_reason (internal telemetry)

### Step 7: Telemetry Recording
Record internal metrics (conceptual for now, implemented in Step 17.4):
- `stop_reason` (enum from §5.1)
- `downgrade_reason` (if applicable)
- `passes_completed` (count)
- `passes_planned` (count)
- `deltas_applied` (count)
- `deltas_rejected` (count)

---

## 7. MUTATION BOUNDARIES (STRICT)

### 7.1 Prohibited Mutations
Deep thinking MUST NOT mutate:
- User identity state (subject_type, subject_id)
- Entitlements (plan, tier, caps)
- Memory or context (Phase 19 territory)
- Headers or cookies
- Logging configuration
- External IO or file system
- Database state
- Network requests

### 7.2 Allowed Mutations
Deep thinking MAY ONLY mutate DecisionDelta allowed fields (§1.5):
- `rendered_text` (refinement)
- `quality_score` (adjustment)
- `reasoning_trace` (internal telemetry, additive only)

### 7.3 Enforcement
Any attempt to mutate non-allowed fields → validation failure → fail-closed downgrade.

---

## 8. COMPLIANCE CHECKLIST (FUTURE-PROOF)

Every implementation step (router, engine, passes, telemetry, eval) MUST satisfy:

- [ ] **No agency**: Must not import or call tools/retrieval/memory modules
- [ ] **Delta-only output**: Must only emit DecisionDelta, not full DecisionState
- [ ] **Schema validation**: Must validate all deltas against allowed fields
- [ ] **Deterministic**: Must produce identical results for identical inputs
- [ ] **Fail-closed**: Must downgrade to baseline on any failure
- [ ] **Stop reason mapped**: Must set explicit StopReason code on every termination path
- [ ] **No side effects**: Must not perform external calls, file writes, or state mutations outside allowed fields
- [ ] **Timeout bounded**: Must respect pass timeout slices and total request budget
- [ ] **Pass count clamped**: Must enforce 2–5 pass limit
- [ ] **Immutable input**: Must treat DecisionState as read-only

---

## 9. INVALIDATION TRIGGERS

This contract is invalidated if:
- Deep thinking performs tool usage, external calls, or side effects
- Pass count exceeds 5
- Non-allowed fields are mutated
- Stop reasons become non-deterministic
- Fail-closed ladder is bypassed
- Agency or autonomy is introduced

If invalidated, Phase 17 certification is revoked and all deep thinking features must be disabled until contract compliance is restored.

---

## 10. LOCK STATEMENT

Phase 17 Deep Thinking Contract is frozen as of Step 0. Future steps (17.1–17.5) must implement within these bounds. Any modification to this contract requires explicit Phase 17 re-certification with new evidence.

**Certification authority**: Phase 17 promotion gate must verify this contract exists and all implementation steps comply with checklist (§8).

---

## 11. REFERENCES

- Phase 16 Certification: `docs/PHASE16_CERTIFICATION.md`
- Release Log: `docs/RELEASE_LOG.md`
- Promotion Gate: `scripts/promotion_gate.sh`

---

**Document Version**: 1.0  
**Phase**: 17  
**Step**: 0 (Contract Freeze)  
**Date**: 2026-01-28  
**Status**: LOCKED
