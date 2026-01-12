# Phase 8 — Step 4: Deployment Integrity & Immutability (Semantic, Governance-Level)

## Scope
- Binds trust and certification to a specific governed artifact.
- Defines immutability and drift invalidation; no runtime/tooling changes.
- Applies to cognition runtime, accountability runtime, audit runtime, enforcement logic, and certified documentation (Phases 1–8).

## Governed Artifact Definition
- Governed artifact includes:
  - Cognition runtime (`mci_backend/app` decision pipeline and adapters).
  - Accountability runtime (`mci_backend/accountability` traces, evidence, attribution, audit replay, external verdict mapping).
  - Enforcement logic and invariants defined through Phases 1–7.
  - Certified documentation for Phases 1–8 (scope, governance, isolation, emergency semantics).
- Anything not explicitly listed is out of scope and not covered by certification.

## Artifact Identity (Conceptual)
- Single, stable identity for the governed artifact; certification attaches to this identity only.
- Trust applies exclusively to the identified artifact; any change yields a different identity.

## Immutability Guarantee
- Governed artifacts must not change post-deployment: no patching, hotfixes, config drift, or environment-based conditional behavior.
- If change is needed, a new artifact must be produced; prior certification does not apply until re-certified.
- No partial or selective updates; immutability is all-or-nothing for governed components.

## Change Classification
- Allowed without recertification: changes outside governed artifact (e.g., UI, infra routing, logging infrastructure) that do not alter governed components or their semantics.
- Forbidden without reopening Phase 8: any modification to governed artifact code, semantics, or certified documentation.
- Invalidating: silent or unauthorized drift of governed artifacts (including config, dependencies, or behavior) instantly voids certification.

## Integrity Verification Semantics (Expectations)
- Integrity is assumed valid only when the governed artifact matches its certified identity and no drift is present.
- If integrity is unverifiable (unknown state, missing provenance), certification is not in effect.
- If integrity is violated (drift detected or inferred), certification is void.
- No runtime hash checks or automation are introduced here; this is a semantic contract.

## Failure Behavior (Fail-Closed)
- On violation or unverifiable integrity:
  - New invocations must be refused.
  - Emergency controls may be invoked per Phase 8 Step 3.
  - No attempt to continue operation under uncertified conditions.
  - Availability is sacrificed to preserve trust and accountability.

## Relationship to Audit & Accountability
- Audit and external audit verdicts apply only to the certified governed artifact.
- Drift invalidates audit trust; external verdicts are artifact-bound.
- Accountability artifacts are never mutated; integrity failure does not permit retroactive change.

## Non-Goals
- No hashing systems, runtime verification, deployment automation, rollback logic, monitoring, metrics, drift detectors, or performance/availability optimizations are added.
- No changes to cognition, accountability, audit semantics, or Phase 7 guarantees.

## Stability & Dependency
- Deployment integrity semantics are STABLE once approved.
- Changes require reopening Phase 8 for re-certification.
- Later phases may depend on these rules but may not alter them without reopening Phase 8.
