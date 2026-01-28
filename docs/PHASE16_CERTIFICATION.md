# PHASE16 CERTIFICATION (LOCK)

## Scope
This certification covers Phase 16 Steps 1–10. Cognition behavior is unchanged by Steps 6–9 (passive-only / wrappers only).

## Certified Build
- Date: 2026-01-27
- Environment: staging (Railway)
- Version string: 2026.15.1
- Primary endpoints: /health, /db/health, /api/chat

## Evidence Index
- Step5 deterministic wrapper (reliability/quality/safety)
- Step6 observability passive (X-Request-Id + chat.summary)
- Step7 security (headers, abuse throttle, entitlements)
- Step8 UX reliability (X-UX-State + cooldown)
- Step9 release engineering (flags + canary + rollback rules)

## Gates Required to Pass
- scripts/promotion_gate.sh (mode=staging): end-to-end promotion gate smoke + presence checks
- scripts/security_gate.sh (mode=staging): security header + abuse/entitlements verification
- scripts/ux_gate.sh (mode=staging): UX header signaling and cooldown mapping verification
- scripts/canary_check.sh (mode=staging): canary contract verification for /api/chat

## Budget/Cost Control Proof
Cost gate exists to verify breaker/budget policy; breakers/budget fail-closed on overruns.

## Reliability Proof
Deterministic timeouts/retries/chaos hooks exist; failures map to structured failure_type.

## Security Proof
- security headers always-on (HSTS conditional)
- cookie flags hardened on https + non-local
- abuse scoring bounded and deterministic
- entitlements clamp mode/model_class

## UX Proof
- X-UX-State emitted on /api/chat success + error paths
- Retry-After becomes cooldown_seconds capped 1..86400
- frontend renders SystemStatus + cooldown UX (Step 8B)

## Rollback Rules
Rollback triggers:
- promotion gate fail
- security gate fail
- canary_check fail
- increase in 5xx or timeouts
- missing required headers
Rollback action: revert last commit(s), redeploy, re-run gates.

## Invalidation Triggers
Changes to cognition engine, prompt policy, safety/quality gates, auth, routing semantics, or model provider invalidate this certification.

## Lock Statement
Phase 16 is certified. Future phases must not modify Phase 16 contracts without explicit Phase 17+ work and new evidence.
