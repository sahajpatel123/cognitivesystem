# Phase 16 — Step 4: Model Routing Policy (LOCK)

Status: IN EFFECT ✅ (2026-01-23)

## Purpose
- Provide a deterministic, tier-gated routing policy for /api/chat.
- Prevent hidden upgrades: never escalate capability beyond what tier/mode allows.
- Enforce bounded, ordered fallbacks and deterministic downgrades when breakers/budgets are tight.

## Non-goals
- No cognition or prompt changes.
- No provider SDK coupling inside the policy.
- No probabilistic or time-based routing.

## Inputs
- tier: FREE | PRO | MAX
- requested_mode: DEFAULT | THINKING | RESEARCH (optional; from JSON "mode" or header "X-Mode"; defaults to DEFAULT)
- breaker_open (bool), budget_tight (bool)
- est_input_tokens (optional, for context only)

## Allowed modes by tier (matrix)
- FREE: DEFAULT only
- PRO: DEFAULT, THINKING
- MAX: DEFAULT, THINKING, RESEARCH

## Downgrade ladder
- Mode: RESEARCH → THINKING → DEFAULT (no escalation)
- Model class: STRONG → BALANCED → FAST (no escalation)
- Triggered when:
  - Requested mode not allowed by tier
  - breaker_open is True
  - budget_tight is True

## Primary selection
- Capability: CHAT
- Model class: STRONG for RESEARCH, BALANCED for THINKING/DEFAULT (after downgrades)
- Constraints: uses existing validated caps from settings (no increases)

## Fallback chain (ordered, deterministic)
1) Lower model_class (e.g., BALANCED → FAST) with same mode.
2) Lower mode via ladder, then lower model_class again.
Never higher than the primary; chain is stable.

## Determinism & logging
- No randomness or clock-based choices.
- Logs include: tier, requested_mode, effective_mode, primary model_class, fallback_count, request_id (if available).
- No user_text logging.

## Failure behavior
- If budgets/breakers block, higher layers return existing failure types (e.g., BUDGET_EXCEEDED, PROVIDER_UNAVAILABLE); policy never escalates capability.
- If request caps exceeded, upstream cost checks respond (429/503) per Step 3.

## Verification checklist
- python3 -m compileall backend mci_backend
- python3 -c "import backend.app.main; print('OK backend.app.main import')"
- python3 -c "from backend.app.observability.request_id import get_request_id; print(callable(get_request_id))"
- bash -n scripts/smoke_api_chat.sh scripts/promotion_gate.sh scripts/cost_gate_chat.sh
- curl -s -i -H "Content-Type: application/json" -d '{"user_text":"hi"}' $BASE/api/chat → 200
- curl -s -i $BASE/auth/whoami → 200

## Invalidation triggers
- Any route selection using randomness/time.
- Any import of provider SDKs inside policy.
- Any logging of user_text.
- Any silent escalation of mode or model class beyond tier.
