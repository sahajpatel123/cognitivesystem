from __future__ import annotations

from typing import Optional

from fastapi.responses import JSONResponse

from backend.app.auth.identity import IdentityContext
from backend.app.plans.policy import Plan, PlanLimits, get_plan_limits, resolve_plan
from backend.app.plans.quota import check_request_limit, check_token_budget, increment_usage
from backend.app.plans.tokens import estimate_tokens_from_text, estimate_total_tokens


def _error_payload(
    *,
    status_code: int,
    error_code: str,
    message: str,
    plan: Plan,
    limit: int,
    used: int,
    reset_at: Optional[str],
) -> JSONResponse:
    body = {
        "status": "error",
        "error_code": error_code,
        "message": message,
        "plan": plan.value,
        "limit": limit,
        "used": used,
    }
    if reset_at:
        body["reset_at"] = reset_at
    return JSONResponse(status_code=status_code, content=body)


def precheck_plan_and_quotas(user_text: str, identity: IdentityContext) -> tuple[Plan, PlanLimits, Optional[JSONResponse], int, int]:
    """
    Returns (plan, limits, error_response_or_none, input_tokens, budget_estimate_tokens).
    """
    plan = resolve_plan(identity.subject_id)
    limits = get_plan_limits(plan)

    input_tokens = estimate_tokens_from_text(user_text)
    if input_tokens > limits.max_input_tokens:
        return (
            plan,
            limits,
            _error_payload(
                status_code=413,
                error_code="input_too_large",
                message="Input exceeds plan limit.",
                plan=plan,
                limit=limits.max_input_tokens,
                used=input_tokens,
                reset_at=None,
            ),
            input_tokens,
            estimate_total_tokens(input_tokens, limits.max_output_tokens),
        )

    allowed_req, state_req = check_request_limit(identity.subject_type, identity.subject_id, limits.requests_per_day)
    if not allowed_req:
        reset_at = state_req.reset_at.isoformat() if state_req and hasattr(state_req, "reset_at") else None
        used = state_req.requests_count if state_req else limits.requests_per_day
        return (
            plan,
            limits,
            _error_payload(
                status_code=429,
                error_code="requests_limit_exceeded",
                message="Daily request limit exceeded.",
                plan=plan,
                limit=limits.requests_per_day,
                used=used,
                reset_at=reset_at,
            ),
            input_tokens,
            estimate_total_tokens(input_tokens, limits.max_output_tokens),
        )

    budget_estimate = estimate_total_tokens(input_tokens, limits.max_output_tokens)
    allowed_budget, state_budget = check_token_budget(
        identity.subject_type, identity.subject_id, limits.token_budget_per_day, budget_estimate
    )
    if not allowed_budget:
        reset_at = state_budget.reset_at.isoformat() if state_budget and hasattr(state_budget, "reset_at") else None
        used = state_budget.tokens_count if state_budget else limits.token_budget_per_day
        return (
            plan,
            limits,
            _error_payload(
                status_code=429,
                error_code="token_budget_exceeded",
                message="Daily token budget exceeded.",
                plan=plan,
                limit=limits.token_budget_per_day,
                used=used,
                reset_at=reset_at,
            ),
            input_tokens,
            budget_estimate,
        )

    return plan, limits, None, input_tokens, budget_estimate


def post_accounting(identity: IdentityContext, tokens_used: int) -> None:
    try:
        increment_usage(identity.subject_type, identity.subject_id, requests_inc=1, tokens_inc=tokens_used)
    except Exception:
        # best-effort only
        return


__all__ = ["precheck_plan_and_quotas", "post_accounting"]
