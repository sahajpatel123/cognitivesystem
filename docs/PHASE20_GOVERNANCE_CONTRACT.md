# PHASE 20 — GOVERNANCE CONTRACT
ContractVersion: "20.0.0"
Status: FROZEN

## PURPOSE
Define "enterprise governance" invariants + stop rules, frozen for promotion gating.

## GOVERNANCE INVARIANTS

- **Audit**: Append-only event log for all governance operations, structure-only telemetry, always-on recording including failures, deterministic event ordering, no user text leakage
- **Export**: Deterministic data extraction with bounded output size, automatic redaction of sensitive content, consistent formatting across requests, fail-closed on policy violations
- **Retention**: Explicit policy-driven data lifecycle management, deterministic pruning based on configurable TTL rules, auditable retention events with timestamps and reason codes
- **Admin Controls**: Capability-based authorization system, policy-gated operations with no mode overrides, fail-closed on invalid permissions, structured audit trail for all admin actions

## STOP REASONS (EXHAUSTIVE)

1. **OK** - Operation completed successfully
   - Trigger: All checks passed, operation executed without errors
   - Deterministic handling: Return success with operation results
   - User-visible: Yes

2. **POLICY_DISABLED** - Governance policy is disabled or not configured
   - Trigger: Required governance policy not found or explicitly disabled
   - Deterministic handling: Immediate rejection, no operation attempted
   - User-visible: Yes

3. **NOT_AUTHORIZED** - User lacks required permissions for operation
   - Trigger: Authorization check failed against capability matrix
   - Deterministic handling: Access denied, log security event
   - User-visible: Yes

4. **SCOPE_INVALID** - Operation scope exceeds allowed boundaries
   - Trigger: Request scope validation failed against policy limits
   - Deterministic handling: Reject request, return scope constraints
   - User-visible: Yes

5. **REQUEST_INVALID** - Malformed or invalid request parameters
   - Trigger: Input validation failed, required fields missing, format errors
   - Deterministic handling: Return validation errors, no processing
   - User-visible: Yes

6. **RATE_LIMITED** - Request rate exceeds configured limits
   - Trigger: Rate limiter threshold exceeded for user/operation type
   - Deterministic handling: Reject with retry-after guidance
   - User-visible: Yes

7. **BUDGET_EXHAUSTED** - Resource budget limits exceeded
   - Trigger: Operation would exceed allocated resource quotas
   - Deterministic handling: Reject with budget status information
   - User-visible: Yes

8. **RETENTION_POLICY_VIOLATION** - Operation violates data retention rules
   - Trigger: Requested data outside retention window or policy conflict
   - Deterministic handling: Block operation, return policy requirements
   - User-visible: Yes

9. **EXPORT_DENIED** - Data export blocked by policy or classification
   - Trigger: Export request conflicts with data classification or policy
   - Deterministic handling: Deny export, log security event
   - User-visible: Yes

10. **DATA_NOT_FOUND** - Requested data does not exist or is inaccessible
    - Trigger: Query returned no results or data has been purged
    - Deterministic handling: Return empty result set with metadata
    - User-visible: Yes

11. **INTERNAL_INCONSISTENCY** - System error or unexpected failure
    - Trigger: Unhandled exceptions, system state corruption, infrastructure failure
    - Deterministic handling: Fail-closed, log error, return generic failure
    - User-visible: No (generic error message only)

## FAIL-CLOSED LADDER (PRIORITY ORDER)

1. **Contract/policy disabled** - Check if governance contract is active and policies are enabled
2. **Authorization** - Verify user permissions and capability grants for requested operation
3. **Scope validation** - Validate operation scope against policy boundaries and constraints
4. **Input bounds** - Check request parameters, payload size, format compliance
5. **Rate/budget** - Enforce rate limits and resource budget constraints
6. **Retention/export policy violations** - Apply data lifecycle and export policies
7. **Execution failures** - Handle runtime errors and system failures → INTERNAL_INCONSISTENCY

## VERSIONING & CHANGE CONTROL

- Any change to this file REQUIRES ContractVersion bump following semantic versioning (20.x.y)
- Any change REQUIRES an entry in docs/RELEASE_LOG.md under "Phase 20 — Step 0 Evidence"
- The promotion gate enforces:
  - File presence check with fail-closed behavior
  - Required headings and fields validation
  - ContractVersion format compliance (20.x.y pattern)
  - Content change detection using tracked SHA256 hash
  - Release evidence verification for version bumps
- Hash tracking: docs/PHASE20_GOVERNANCE_CONTRACT.hash contains SHA256 of current content
- Modified without version bump → automatic promotion gate failure

## NO CONTENT LEAKAGE

Governance artifacts must be structure-only with no raw user messages, quotes, excerpts, or sensitive data. All telemetry, audit logs, and export data must use sanitized structure-only representations. User identifiers may be included but no user-generated content or system responses containing user data.
