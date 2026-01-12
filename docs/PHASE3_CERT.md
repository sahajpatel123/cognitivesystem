# Phase 3 Certification — Model Integration (Steps 0–6)

_Date: 2026-01-07_

## Scope Statement
Phase 3 covers model integration for the research-grade cognitive system. This phase guarantees that every large-language-model invocation is performed exclusively through the certified adapter path, guarded by stateless enforcement logic. The enforcement layer validates inputs and outputs against the contractual schemas, classifies violations deterministically, and fails closed whenever constraints are not met. These guarantees hold provided that upstream components supply schema-conformant objects and that downstream consumers respect the rendered output contract. Phase 3 does **not** guarantee answer quality, user-facing UX, performance characteristics, or resilience to external provider outages beyond typed failure surfacing.

## Locked Components (Do Not Modify Without Re-Certification)
1. **`LLMClient` adapter path (`backend/app/llm_client.py`)**  
   The reasoning and expression model entry points, their call ordering, and the `_post` transport wrapper are now frozen. Any change that alters call sequencing, payload shaping, retry behavior, or logging must reopen Phase 3.
2. **Enforcement module (`backend/app/enforcement.py`)**  
   Adapter input schemas, violation classes, pre-call character/latency limits, output validators, and semantic guards are contractual. Changing thresholds, error typing, or guard logic invalidates certification.
3. **Typed failure propagation**  
   The use of `EnforcementError`/`EnforcementFailure` objects as the only way to surface violations is locked. Consumers must continue to receive these typed failures with the documented classes.
4. **Service integration (`backend/app/service.py`)**  
   Invocation order (reasoning → belief update → expression) and the boundary checks around expression output are fixed. No component may call models outside the adapter.
5. **Tested adapter schemas (`backend/app/schemas.py`)**  
   Structures used by adapters (e.g., `ReasoningOutput`, `RenderedMessage`, `ExpressionPlan`) are now contractual. Field additions, removals, or type changes require re-opening Phase 3.

## Contractual Interfaces
- **Adapter Inputs**  
  `ReasoningAdapterInput` and `ExpressionAdapterInput` forbid extra fields and require the exact schema documented in `enforcement.py`. These are now stable integration contracts for upstream callers.
- **Adapter Outputs**  
  Reasoning returns `ReasoningOutput`; expression returns `RenderedMessage`. Downstream code must continue to treat these as the sole artifacts that may leave the adapter boundary.
- **Violation Types**  
  `ViolationClass` enumerations (`STRUCTURAL_VIOLATION`, `SCHEMA_MISMATCH`, `SEMANTIC_CONTRACT_VIOLATION`, `BOUNDARY_VIOLATION`, `EXECUTION_CONSTRAINT_VIOLATION`, `EXTERNAL_DEPENDENCY_FAILURE`) are canonical. Consumers must not expect additional classes without re-certification.
- **Invocation Boundary**  
  Only `LLMClient.call_reasoning_model` and `.call_expression_model` may reach external models. Any new caller must depend on these interfaces rather than invoking transports directly.

## Certification Conditions & Invalidation Triggers
Certification remains valid only if:
- No retries, backoffs, or alternate transports are introduced.  
- Enforcement guards run before and after every model call without bypass.  
- Payload schemas, token/character/latency limits, and semantic filters remain unchanged.  
- No component caches, rewrites, or partially uses model outputs when violations occur.  

Certification is invalidated immediately if any of the following occur:
1. Addition of retries, fallbacks, or recovery paths around LLM calls.  
2. Direct HTTP calls to models that skip the adapter/enforcement stack.  
3. Changes to violation class definitions or their severities.  
4. Modifications to adapter schemas, enforcement thresholds, or semantic guard patterns.  
5. Introduction of stateful memory/learning tied to model outcomes.  
6. Alteration of the deterministic call order (reasoning before expression).  
Any such change requires re-running Phase 3 Steps 3–5 at minimum.

## Known & Accepted Limitations
- The system intentionally lacks retries, performance tuning, or degradation strategies; any provider error surfaces as a typed failure.  
- No guarantees are provided for latency, throughput, or cost.  
- Reasoning/expression quality is outside Phase 3 scope; only structural correctness is enforced.  
- User-facing UX constraints, paraphrasing, and pedagogy remain unaddressed.  
- Enforcement assumes honest upstream schema usage; malicious mutation outside adapters is out-of-scope.

## Phase 3 Closure Marker
> **Phase 3 (Model Integration) is hereby declared COMPLETE and FROZEN as of 2026-01-07.**  
> Any modification to the components or contracts listed above constitutes a certification-breaking change and requires reopening Phase 3.

_No runtime logic was altered while producing this certification._
