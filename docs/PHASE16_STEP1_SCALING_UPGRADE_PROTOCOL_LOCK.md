# Phase 16 Step 1 — Scaling & Upgrade Protocol (LOCK)

## Title + Purpose
Locks the scaling and upgrade protocol for Phase 16 to ensure reliability, performance, abuse-resilience, and cost control without altering cognition or the Phase 15 production trust contract.

## Carry-Forward Locks (Phases 1–14 + Phase 15)
- No cognition logic changes; governed pipeline and contracts stay intact.
- No personalization or memory learning tables; no long-term chat retention.
- No raw prompt/user_text logging; observability is passive only.
- No silent degradation; degradations must be explicit and surfaced.
- Storage boundaries remain minimal and bounded (sessions, quotas, rate_limits, invocation_logs only).
- Phase 15 certification (docs/PHASE15_CERTIFICATION.md) remains the baseline.

## Definitions
- Scaling (Phase 16): improving four axes without altering cognition:
  - Reliability: consistent availability and correctness of governed endpoints.
  - Performance: latency and throughput improvements within existing semantics.
  - Abuse-resilience: sustaining WAF/plan/rate protections under load.
  - Cost-bounded operation: predictable spend via ceilings and controls.
- Upgrade: any deployable change to infra, configs, policies, or code paths that does not modify cognition.
- Release Drill: rehearsed validation covering health, auth, chat, WAF/policy enforcement, and rollback readiness.

## Environments & Topology
- Environments: local/dev, staging, production.
- Parity: staging and production must match WAF rules, plan guard policies, identity/authn flows, DB schema, and observability fields. Allowed differences: secrets/keys, domains, capacity caps.
- Domains/hosting: Vercel frontend, Railway backend, Supabase Postgres; HTTPS termination at platform edge; API base routed to backend domain.
- ASCII topology:
```
[Client] --HTTPS--> [Vercel Frontend] --HTTPS--> [Railway FastAPI] --TLS--> [Supabase Postgres]
                                  |-- passive logs/metrics (no prompts)
```

## SLO / SLI Targets (LOCKED NUMBERS)
| SLO | Target | Notes |
| --- | --- | --- |
| Availability (monthly) | <fill>% | Measured via health + /api/chat success |
| /api/chat p50 latency | <fill> ms | Measured from logs/metrics |
| /api/chat p95 latency | <fill> ms | Measured from logs/metrics |
| /api/chat 5xx error rate | <fill>% | Includes upstream/model errors |
| 429 rate-limit behavior | Predictable + bounded (not zero) | Must remain deterministic |
| Budget cap policy | Daily: <fill>; Monthly: <fill> | Token/spend ceilings |

- SLO measurement source: passive logs with request_id, hashed_subject, waf_decision, plan_decision, latency_ms.
- No silent degradation: any breach or intentional downgrade must be explicit, logged, and operator-visible.

## Upgrade Classification & Evidence Protocol
- Class A: safe/reversible, no behavior change. Tests: smokes; evidence: contract consistency; rollout: standard or quick canary optional.
- Class B: policy/limit adjustments (non-cognitive). Tests: smokes + staging drill subset; evidence: policy diff + limits validated; rollout: canary/flagged, staged promotion.
- Class C: cognition/personalization/raw-content logging — forbidden in Phase 16.
- All changes declare class, impacted surfaces, evidence, and rollback plan before merge.

## Rollout & Rollback Rules
- Canary: required for Class B; percentage or internal-only first segment.
- Kill switch: required for changes affecting traffic or cost (flags or config toggles).
- Rollback triggers: SLO breach thresholds or cost overrun at <fill> percentage beyond targets; any rise in 5xx beyond <fill>% absolute.
- Rollback procedure: use prior deploy artifact; follow drills in docs/PHASE15_STEP8_RELEASE_DRILLS.md and scripts/release_drills.sh.
- Post-rollback review: capture cause, evidence, and prevent recurrence before reattempt.
- Production promotion model (Option B): production advances only by fast-forwarding `release` from staging-tested `main` commits with evidence; no direct prod deploys.

## Cost & Capacity Guardrails
- Token/request caps enforced (Step 4), requests/day caps enforced, WAF enforced (Step 5), observability passive (Step 6).
- No unbounded concurrency; scaling changes must declare limits.
- No background jobs processing user content unless bounded, documented, and policy-approved.
- New compute features must declare spend ceiling + measurement method (<fill>), and must default to off/flagged.
- “Coming Soon” features stay off and non-routable until explicitly unlocked.

## Data & Retention Constraints
- Allowed tables only: sessions, quotas, rate_limits, invocation_logs (sanitized metadata).
- Retention limits remain as Phase 15; no expansion without new certification.
- No raw prompt/user_text storage; no personalization or embeddings from chats.

## Evidence Checklist (Release-Ready Gate)
- /health OK
- /db/health OK
- /auth/whoami OK
- /api/chat happy path 200 (governed response)
- /api/chat wrong content-type 415
- /api/chat burst test returns some 429 (no 500s)
- Logs contain request_id, hashed_subject, waf_decision, plan_decision; no user_text in logs
- Reference scripts: scripts/release_drills.sh, scripts/certify_phase15.sh (use safe payload “hi”)

## Invalidation Triggers
- Any cognition change or prompt/schema/routing change.
- Any raw prompt/user_text logging or storage.
- Any new persistence beyond allowed boundaries.
- Silent degradation or bypassing WAF/plan/auth gates.
- Observability feeding back into decisions.

## Acceptance Criteria (for Step 1)
- Document includes classification, allowed/forbidden, rollout/rollback, evidence, SLO placeholders, and invalidation triggers.
- Placeholders are explicit (<fill>) and limited to user-specified values.
- Status footer present.

## Status Footer
- Phase 16 Step 1 Status: COMPLETE ✅ (LOCKED)
