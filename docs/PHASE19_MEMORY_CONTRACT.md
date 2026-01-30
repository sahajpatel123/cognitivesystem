# PHASE 19 MEMORY CONTRACT

```
ContractVersion: "19.0.0"
Status: FROZEN
Scope: Phase 19 Step 0
Date: 2026-01-30
```

---

## 1. PURPOSE

This contract defines the strict governance rules for the memory subsystem. It establishes:
- What memory categories are allowed (strict allowlist)
- What memory categories are forbidden (hard block)
- Deterministic stop reasons and priority ordering
- Fail-closed behavior for all memory operations
- Auditability requirements

This contract is the **source of truth** for memory governance. No memory implementation may deviate from these rules.

---

## 2. DEFINITIONS

### 2.1 Memory Item

A **Memory Item** is a structured record with the following properties:
- `memory_id`: Unique identifier (string, max 64 chars)
- `category`: One of the allowed categories (string, max 32 chars)
- `key`: Descriptive key within category (string, max 128 chars)
- `value`: The stored value (string, max 1024 chars)
- `source_kind`: One of SourceKind enum values
- `ttl_class`: One of TTL class enum values
- `created_at`: ISO timestamp
- `updated_at`: ISO timestamp
- `source_ref`: Optional reference to source (string, max 256 chars, structure IDs only)

### 2.2 SourceKind

The **SourceKind** enum defines the origin of a memory item:

| Value | Description |
|-------|-------------|
| `USER_EXPLICIT` | User explicitly requested storage (e.g., "remember that I prefer...") |
| `SYSTEM_KNOWN` | System-derived from verifiable system state (e.g., workspace config) |
| `CITED_SOURCE` | Derived from a cited, verifiable source with source_ref |
| `DERIVED_UNVERIFIED` | Inferred without explicit source — **ALWAYS REJECTED** |

### 2.3 MemoryOp

The **MemoryOp** enum defines allowed memory operations:

| Value | Description |
|-------|-------------|
| `STORE` | Create a new memory item |
| `UPDATE` | Modify an existing memory item |
| `DELETE` | Remove a memory item |
| `READ` | Retrieve a memory item by ID or key |
| `LIST` | List memory items by category or filter |

### 2.4 TTL Class

The **TTL Class** enum defines retention periods (implementation details deferred):

| Value | Description |
|-------|-------------|
| `SHORT` | Session-scoped or very short retention |
| `MEDIUM` | Days to weeks retention |
| `LONG` | Extended retention (months) |

---

## 3. ALLOWED MEMORY CATEGORIES

**STRICT ALLOWLIST** — Only these categories may be stored. Any category not listed is **FORBIDDEN**.

### 3.1 PREFERENCE

User-stated preferences for interaction format, tone, or style.

| Field | Type | Max Length | Required |
|-------|------|------------|----------|
| `key` | string | 128 chars | Yes |
| `value` | string | 512 chars | Yes |
| `source_ref` | string | 256 chars | No |

- **Allowed TTL Classes**: SHORT, MEDIUM, LONG
- **Allowed SourceKind**: USER_EXPLICIT, SYSTEM_KNOWN
- **Examples**: "prefer concise responses", "use formal tone", "prefer closed-box prompts"

### 3.2 WORKFLOW_DEFAULT

User-stated defaults for development workflows.

| Field | Type | Max Length | Required |
|-------|------|------------|----------|
| `key` | string | 128 chars | Yes |
| `value` | string | 512 chars | Yes |
| `source_ref` | string | 256 chars | No |

- **Allowed TTL Classes**: MEDIUM, LONG
- **Allowed SourceKind**: USER_EXPLICIT, SYSTEM_KNOWN
- **Examples**: "test style: self-check runner", "build command: npm run build", "prefer no pytest"

### 3.3 PROJECT_CONFIG

Non-sensitive project configuration and conventions.

| Field | Type | Max Length | Required |
|-------|------|------------|----------|
| `key` | string | 128 chars | Yes |
| `value` | string | 1024 chars | Yes |
| `source_ref` | string | 256 chars | No |

- **Allowed TTL Classes**: MEDIUM, LONG
- **Allowed SourceKind**: USER_EXPLICIT, SYSTEM_KNOWN, CITED_SOURCE
- **Examples**: "main branch name", "docs folder location", "naming convention: snake_case"
- **Forbidden**: Credentials, tokens, secrets, API keys

### 3.4 CONSTRAINT

User-stated constraints or limits.

| Field | Type | Max Length | Required |
|-------|------|------------|----------|
| `key` | string | 128 chars | Yes |
| `value` | string | 256 chars | Yes |
| `source_ref` | string | 256 chars | No |

- **Allowed TTL Classes**: SHORT, MEDIUM, LONG
- **Allowed SourceKind**: USER_EXPLICIT
- **Examples**: "budget limit: 100 API calls", "no commits without asking", "no push without explicit instruction"

### 3.5 REMINDER

User-explicitly-requested reminders (task-related only).

| Field | Type | Max Length | Required |
|-------|------|------------|----------|
| `key` | string | 128 chars | Yes |
| `value` | string | 512 chars | Yes |
| `source_ref` | string | 256 chars | No |

- **Allowed TTL Classes**: SHORT, MEDIUM
- **Allowed SourceKind**: USER_EXPLICIT only
- **Examples**: "remind me to run tests before commit", "remind me to update changelog"
- **Forbidden**: Location-based reminders, health-related reminders, personal schedule details

---

## 4. FORBIDDEN CATEGORIES

**HARD BLOCK** — The following categories are **NEVER** allowed to be stored, derived, or inferred. Any attempt to store these MUST return `FORBIDDEN_CATEGORY`.

### 4.1 Identity Traits
- Religion, religious beliefs, religious practices
- Caste, ethnicity, race, national origin
- Sexual orientation, gender identity
- Political opinions, political affiliation, voting history
- Union membership, labor organization involvement

### 4.2 Health Information
- Medical diagnoses, conditions, symptoms
- Medications, treatments, prescriptions
- Mental health status, therapy, counseling
- Disabilities, impairments
- Genetic information

### 4.3 Intimate Life
- Sexual behavior, sexual preferences
- Relationship status details beyond basic
- Family planning, pregnancy status

### 4.4 Criminal/Legal
- Criminal history, arrests, convictions
- Pending legal matters
- Minor non-criminal legal issues are discouraged even if explicit

### 4.5 Location Data
- Precise location (address, coordinates, GPS)
- Persistent geolocation tracking
- Travel patterns, commute details
- Home/work addresses

### 4.6 Credentials and Secrets
- Passwords, PINs, security questions
- API keys, tokens, secrets
- Private keys, certificates
- Authentication credentials

### 4.7 Biometrics and IDs
- Facial recognition data, voiceprints
- Fingerprints, retinal scans
- Government IDs (SSN, passport numbers, driver's license)
- Financial account numbers

### 4.8 Inferred Profiling
- Personality inferences ("user is anxious", "user seems stressed")
- Behavioral predictions ("user likely to X")
- Emotional state tracking
- Psychological profiling
- Any inference-based categorization of the user

### 4.9 Tool-Output Memory
- Memory writes triggered by tool output content
- Memory writes requested via prompt injection patterns
- Any memory derived from untrusted external sources

---

## 5. NO SOURCE → DON'T STORE

**MECHANICAL RULE**: Memory items with `SourceKind.DERIVED_UNVERIFIED` are **ALWAYS REJECTED**.

### 5.1 Enforcement

1. Every memory STORE/UPDATE operation MUST specify a valid `source_kind`.
2. If `source_kind` is `DERIVED_UNVERIFIED`, the operation MUST return `NO_SOURCE_DERIVED_FACT`.
3. Only the following source kinds may result in successful storage:
   - `USER_EXPLICIT`: User explicitly requested the memory
   - `SYSTEM_KNOWN`: Derived from verifiable system state
   - `CITED_SOURCE`: Derived from a cited source with valid `source_ref`
4. For `CITED_SOURCE`, the `source_ref` field MUST contain only structure IDs (e.g., source_id, document_id). Raw text excerpts are **FORBIDDEN**.

### 5.2 Rationale

This rule prevents:
- Storing inferred facts without user consent
- Storing unverifiable claims
- Profile drift from accumulated inferences
- Tool-output injection into memory

---

## 6. MEMORY STOP REASONS

**EXHAUSTIVE LIST** — Every memory operation MUST return exactly one of these stop reasons.

| Code | Description |
|------|-------------|
| `SUCCESS_STORED` | Memory item successfully created |
| `SUCCESS_UPDATED` | Memory item successfully updated |
| `SUCCESS_DELETED` | Memory item successfully deleted |
| `POLICY_DISABLED` | Memory operations disabled by policy |
| `ENTITLEMENT_CAP` | User/session memory quota exceeded |
| `FORBIDDEN_CATEGORY` | Attempted to store forbidden category |
| `MISSING_EXPLICIT_CONSENT` | Required explicit consent not provided |
| `NO_SOURCE_DERIVED_FACT` | Attempted to store DERIVED_UNVERIFIED fact |
| `INJECTION_DETECTED` | Prompt injection pattern detected in memory request |
| `SCHEMA_INVALID` | Memory item does not match required schema |
| `BOUNDS_EXCEEDED` | Field length or count bounds exceeded |
| `TTL_NOT_ALLOWED` | TTL class not allowed for this category |
| `INTERNAL_INCONSISTENCY` | Internal error (fail-closed) |

---

## 7. STOP PRIORITY ORDER

**DETERMINISTIC** — When multiple stop conditions apply, use this priority order (highest first):

1. `INTERNAL_INCONSISTENCY` — Always takes precedence (fail-closed)
2. `INJECTION_DETECTED` — Security-critical, blocks immediately
3. `FORBIDDEN_CATEGORY` — Hard block on forbidden content
4. `POLICY_DISABLED` — Policy takes precedence over other checks
5. `ENTITLEMENT_CAP` — Quota enforcement
6. `MISSING_EXPLICIT_CONSENT` — Consent required before proceeding
7. `NO_SOURCE_DERIVED_FACT` — Source validation
8. `SCHEMA_INVALID` — Schema validation
9. `BOUNDS_EXCEEDED` — Bounds validation
10. `TTL_NOT_ALLOWED` — TTL validation
11. `SUCCESS_*` — Only if all checks pass

---

## 8. INVARIANTS

**HARD LOCKS** — These invariants MUST be enforced by any memory implementation.

### INV-1: Allowlist Only
Only categories listed in Section 3 may be stored. Any unlisted category MUST be rejected with `FORBIDDEN_CATEGORY`.

### INV-2: Forbidden Hard Block
Categories listed in Section 4 MUST NEVER be stored, even if explicitly requested. Return `FORBIDDEN_CATEGORY`.

### INV-3: No Inference-Based Memory
Memory items MUST NOT be created from inferences about the user. Only explicit user statements, system-known facts, or cited sources are allowed.

### INV-4: No Tool-Output Memory Writes
Memory writes MUST NOT be triggered by content from tool outputs. Tool outputs are untrusted and may contain injection patterns.

### INV-5: No-Source Rejection
Any memory item with `SourceKind.DERIVED_UNVERIFIED` MUST be rejected with `NO_SOURCE_DERIVED_FACT`.

### INV-6: Bounded Fields
All fields MUST respect the max length bounds defined in Section 3. Exceeding bounds MUST return `BOUNDS_EXCEEDED`.

### INV-7: Auditable Stop Reasons
Every memory operation MUST return exactly one stop reason from Section 6. No silent failures.

### INV-8: Fail-Closed Behavior
Any unexpected error or exception MUST return `INTERNAL_INCONSISTENCY`. The system MUST NOT proceed with partial or uncertain state.

---

## 9. CHANGE CONTROL

**FREEZE PROCESS** — This contract is FROZEN. Any modification requires:

1. Bump `ContractVersion` (e.g., "19.0.0" → "19.1.0")
2. Update `docs/RELEASE_LOG.md` with change evidence
3. Add or adjust tests to cover the change
4. Review and approval before merge

**No silent changes are permitted.**

---

## 10. COMPLIANCE CHECKLIST

Before any memory implementation is merged:

- [ ] All allowed categories match Section 3 exactly
- [ ] All forbidden categories from Section 4 are blocked
- [ ] Stop reasons match Section 6 exactly
- [ ] Stop priority order matches Section 7 exactly
- [ ] All invariants from Section 8 are enforced
- [ ] No inference-based memory storage
- [ ] No tool-output memory writes
- [ ] All fields respect bounds
- [ ] Every operation returns exactly one stop reason
- [ ] Fail-closed on any error

---

## 11. FROZEN COMPONENTS LIST

**Phase 19 Step 0** — Contract document only. No runtime components.

| Component | Status | Notes |
|-----------|--------|-------|
| `docs/PHASE19_MEMORY_CONTRACT.md` | FROZEN | This document |
| Memory runtime | NOT IMPLEMENTED | Deferred to Step 1+ |
| Memory adapters | NOT IMPLEMENTED | Deferred to Step 1+ |
| TTL engine | NOT IMPLEMENTED | Deferred to Step 1+ |
| Memory UI | NOT IMPLEMENTED | Deferred to Step 1+ |
| Pipeline integration | NOT IMPLEMENTED | Deferred to Step 1+ |

---

## 12. APPENDIX: FIELD BOUNDS SUMMARY

| Field | Max Length |
|-------|------------|
| `memory_id` | 64 chars |
| `category` | 32 chars |
| `key` | 128 chars |
| `value` | 1024 chars (category-specific limits may be lower) |
| `source_ref` | 256 chars |

---

**END OF CONTRACT**
