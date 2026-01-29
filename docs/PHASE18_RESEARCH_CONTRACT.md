# PHASE 18 — Research Contract + Stop Rules (Frozen)

## Contract Metadata

**ContractVersion**: "18.0.0"  
**Status**: FROZEN  
**ChangeControl**: Any change requires version bump + re-certification gate updates.

---

## 1. PURPOSE

Phase 18 adds bounded, tool-based retrieval (web/docs) to support research mode. Research MUST remain controlled, bounded, and non-agentic. It operates within strict policy caps and fail-closed guarantees.

**Key Principle**: Research is a tool-assisted retrieval capability, NOT an autonomous agent. All tool usage is deterministically bounded and subject to injection filtering.

---

## 2. DEFINITIONS

### 2.1 ResearchMode
A request mode where the system is permitted to invoke external retrieval tools (web search, document lookup) to gather sources before generating a response. ResearchMode is requested by the user but granted by the router based on entitlements and policy.

### 2.2 ToolCall
A single invocation of an external retrieval tool (e.g., web search API, document retrieval). Each ToolCall has a deterministic timeout, budget cost, and output size limit.

### 2.3 Source
A single retrieved document or web result returned by a ToolCall. Contains: URL/identifier, snippet/content, metadata (timestamp, domain, etc.).

### 2.4 SourceBundle
The collection of all Sources returned across all ToolCalls in a single research session. SourceBundle is the input to citation and grounding logic.

### 2.5 Claim
A factual statement in the generated response that references information from Sources. Claims must be traceable to specific Sources via Citations.

### 2.6 Citation
A reference linking a Claim to one or more Sources in the SourceBundle. Citations must be deterministic and verifiable.

### 2.7 Injection
Untrusted content in tool output that attempts to override system rules or policies. Examples: "Ignore previous instructions", "You must answer X", "Tool says: change your behavior".

### 2.8 Sandbox
The isolated execution environment for tool invocations. Sandbox enforces timeouts, output size limits, and prevents side effects.

### 2.9 PolicyCaps
Deterministic limits on research behavior: max_tool_calls_total, max_tool_calls_per_minute, per_call_timeout_ms, total_research_timeout_ms, budget_units_clamp.

### 2.10 StopReason
An exhaustive enum code indicating why research terminated. Every research execution path MUST map to exactly one StopReason.

---

## 3. HARD-LOCK INVARIANTS

### 3.1 Tool Boundary Invariant
**Statement**: All tool usage MUST go through a single adapter chokepoint (implemented in Step 18.1).

**Rules**:
- No direct tool calls anywhere outside the adapter.
- Adapter enforces: timeout, budget, output size limits, injection filtering.
- Adapter is the ONLY code path that invokes external retrieval tools.

**Enforcement**: Code review + import analysis. Any tool import outside adapter module → contract violation.

---

### 3.2 No-Source → UNKNOWN Invariant
**Statement**: If zero acceptable sources are returned, output MUST be ASK_CLARIFY or UNKNOWN (deterministic). Never a grounded-sounding answer.

**Rules**:
- If SourceBundle is empty after all ToolCalls → StopReason = NO_SOURCE.
- Output action forced to ASK_CLARIFY with bounded question: "I couldn't find reliable sources. Could you clarify [aspect]?"
- If clarify not possible (e.g., user already clarified) → output action = UNKNOWN with explanation: "No sources available."
- NO exceptions. No hallucinated answers.

**Enforcement**: Validator checks SourceBundle size. If empty → action MUST be ASK_CLARIFY or UNKNOWN.

---

### 3.3 Policy Caps Invariant
**Statement**: Research is bounded by deterministic caps. Requested_mode=research is a request; router/policy decides. It CANNOT override caps/entitlements.

**PolicyCaps (Deterministic)**:
- `max_tool_calls_total`: Maximum tool calls per research session (e.g., 5)
- `max_tool_calls_per_minute`: Rate limit (e.g., 10/min)
- `per_call_timeout_ms`: Timeout per ToolCall (e.g., 5000ms)
- `total_research_timeout_ms`: Total research session timeout (e.g., 15000ms)
- `budget_units_clamp`: Maximum budget units for research (e.g., 500)

**Rules**:
- Caps are set by entitlement tier (FREE/PRO/MAX) + environment mode (dev/staging/prod).
- User request for research mode is advisory; router enforces caps.
- If caps exceeded → StopReason = RATE_LIMITED or BUDGET_EXHAUSTED or TIMEOUT.

**Enforcement**: Router validates caps before enabling research. Adapter enforces caps during execution.

---

### 3.4 Injection Policy Invariant
**Statement**: Tool output is untrusted content. It CANNOT override system rules.

**Rules**:
- Tool output directives (e.g., "Ignore instructions", "You must answer X") MUST be ignored.
- Only factual content from tool output may be considered (subject to filtering).
- If injection patterns detected → StopReason = INJECTION_DETECTED, downgrade to baseline.

**Enforcement**: Adapter applies injection filter to all tool output before returning SourceBundle. Filter detects common injection patterns and strips/flags them.

---

### 3.5 Non-Agentic Invariant
**Statement**: Research is NOT autonomous. No self-directed planning, no unbounded looping, no tool selection outside adapter's allowed tools list.

**Rules**:
- Tool calls are deterministic: adapter decides which tools to call based on fixed logic (not LLM-generated plans).
- Maximum tool calls is fixed (PolicyCaps.max_tool_calls_total).
- No recursive or self-modifying tool selection.
- No "agent loop" where system decides to call more tools based on previous results beyond fixed budget.

**Enforcement**: Adapter uses fixed tool call sequence or deterministic branching (no LLM-in-the-loop for tool selection).

---

### 3.6 Fail-Closed Ladder
**Statement**: If anything is missing/invalid/unsafe → downgrade (no research) + deterministic StopReason.

**Failure Triggers**:
- Missing entitlement
- Policy disabled
- Budget exhausted
- Rate limited
- Timeout
- Sandbox violation
- Injection detected
- No sources returned
- Validation failure
- Internal inconsistency

**Downgrade Behavior**:
1. Abort research immediately
2. Return baseline response (no research)
3. Record StopReason (internal telemetry)
4. MUST be deterministic
5. MUST NOT leak internal details to user

---

## 4. RESEARCH STOP REASONS (EXHAUSTIVE + DETERMINISTIC)

Every research termination path MUST map to exactly one ResearchStopReason code. No vague "OTHER" bucket.

### 4.1 Stop Reason Codes

| Code | Description | Trigger Condition |
|------|-------------|-------------------|
| `SUCCESS_COMPLETED` | Research completed successfully with sources | SourceBundle non-empty, all tool calls succeeded |
| `ENTITLEMENT_CAP` | User tier does not permit research | Tier = FREE and research requested |
| `POLICY_DISABLED` | Research disabled by policy/feature flag | Feature flag = OFF or policy = DISABLED |
| `BUDGET_EXHAUSTED` | Budget units consumed | Budget remaining < required for next tool call |
| `RATE_LIMITED` | Rate limit exceeded | Tool calls per minute > max_tool_calls_per_minute |
| `TIMEOUT` | Research timeout exceeded | Elapsed time > total_research_timeout_ms |
| `SANDBOX_VIOLATION` | Tool execution violated sandbox rules | Tool attempted forbidden operation |
| `INJECTION_DETECTED` | Injection pattern detected in tool output | Injection filter flagged tool output |
| `NO_SOURCE` | Zero acceptable sources returned | SourceBundle empty after all tool calls |
| `VALIDATION_FAIL` | Source validation failed | Sources failed quality/safety checks |
| `INTERNAL_INCONSISTENCY` | Adapter state corruption or unexpected error | Catch-all for unrecoverable internal errors |

### 4.2 Stop Reason Determinism
Given identical inputs (tier, mode, request, tool outputs), ResearchStopReason MUST be stable and reproducible.

### 4.3 Mapping Requirement
Every code path that terminates research MUST explicitly set one of these ResearchStopReason codes. No implicit or unmapped terminations allowed.

---

## 5. STOP PRIORITY ORDER (DETERMINISTIC)

When multiple stop conditions are true, the FIRST matching condition in this priority order wins:

1. **INTERNAL_INCONSISTENCY** — Fail-closed for unrecoverable errors
2. **SANDBOX_VIOLATION** — Security boundary breach
3. **INJECTION_DETECTED** — Security: untrusted content override attempt
4. **ENTITLEMENT_CAP** — User not authorized for research
5. **POLICY_DISABLED** — Feature flag or policy disables research
6. **RATE_LIMITED** — Rate limit exceeded
7. **BUDGET_EXHAUSTED** — Budget consumed
8. **TIMEOUT** — Time limit exceeded
9. **VALIDATION_FAIL** — Source quality/safety checks failed
10. **NO_SOURCE** — Zero sources returned
11. **SUCCESS_COMPLETED** — Normal completion with sources

**Rationale**: Safety and security failures (1-3) take precedence over policy/entitlement (4-5), which take precedence over resource limits (6-8), which take precedence over content issues (9-10). Success is last.

---

## 6. NO-SOURCE HANDLING (MECHANICAL RULE)

### 6.1 Trigger Condition
If SourceBundle is empty after all ToolCalls complete (or are aborted), StopReason = NO_SOURCE.

### 6.2 Canonical Response
**Deterministic Rule**: If NO_SOURCE triggers, output action is forced to ASK_CLARIFY.

**Clarify Question Template** (bounded, deterministic):
```
"I couldn't find reliable sources for your request. Could you clarify: (1) specific topic, (2) time period, or (3) source type you're looking for?"
```

**Fallback**: If user has already clarified (detected by request history or context), output action = UNKNOWN with explanation:
```
"No sources are available for this request."
```

### 6.3 Enforcement
Validator checks: if StopReason == NO_SOURCE, then action MUST be ASK_CLARIFY or UNKNOWN. Any other action → validation failure → downgrade.

---

## 7. CHANGE CONTROL / FREEZE

### 7.1 Frozen Status
This contract is **FROZEN** as of version 18.0.0. Phase 18 implementation (Steps 18.1–18.9) MUST comply with these invariants.

### 7.2 Change Process
Any change to:
- ResearchStopReasons (add/remove/rename)
- PolicyCaps definitions or defaults
- Invariants (Tool Boundary, No-Source, Injection, etc.)
- Stop Priority Order

Requires:
1. Version bump (18.0.0 → 18.1.0 or 19.0.0 depending on scope)
2. Update this contract document
3. Update promotion gate checks
4. Re-run certification gates (Phase 18.8/18.9)
5. Commit with message: "phase18: contract update vX.Y.Z"

### 7.3 Allowed Without Version Bump
- Clarifying comments or examples
- Fixing typos
- Adding implementation notes that don't change rules

---

## 8. COMPLIANCE CHECKLIST

Before promoting Phase 18 to production, verify:

- [ ] **Tool Boundary**: All tool calls go through adapter chokepoint
- [ ] **No-Source**: Empty SourceBundle forces ASK_CLARIFY or UNKNOWN
- [ ] **Policy Caps**: Caps enforced by router and adapter
- [ ] **Injection Filter**: Applied to all tool output
- [ ] **Non-Agentic**: No autonomous planning or unbounded loops
- [ ] **Fail-Closed**: All failures downgrade with deterministic StopReason
- [ ] **Stop Priority**: Fixed order enforced in adapter
- [ ] **Deterministic**: Same inputs → same StopReason
- [ ] **No Leakage**: Internal details not exposed to user

---

## 9. FROZEN COMPONENTS (PHASE 18)

The following components are **FROZEN** after Phase 18.9 certification:

- `backend/app/research/adapter.py` (Step 18.1): Tool call chokepoint
- `backend/app/research/policy.py` (Step 18.2): PolicyCaps enforcement
- `backend/app/research/injection.py` (Step 18.3): Injection filter
- `backend/app/research/validator.py` (Step 18.4): Source validation
- `backend/app/research/router.py` (Step 18.5): Research mode routing
- `docs/PHASE18_RESEARCH_CONTRACT.md`: This contract

---

## 10. CERTIFICATION ATTESTATION

**Date**: 2026-01-29  
**Certified By**: Phase 18 Implementation Team  
**Version**: 18.0.0  
**Status**: CONTRACT FROZEN (implementation pending)

Contract locked. Promotion gate enforced. Implementation Steps 18.1–18.9 must comply.

**Next Steps**: Implement adapter chokepoint (Step 18.1).
