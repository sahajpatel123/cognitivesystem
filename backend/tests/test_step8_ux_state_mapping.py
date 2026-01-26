from backend.app.chat_contract import ChatAction, ChatResponse, FailureType
from backend.app.ux.state import UXState, decide_ux_state


def test_ask_clarify_maps_to_needs_input():
    state = decide_ux_state(status_code=200, action=ChatAction.ASK_CLARIFY.value, failure_type=None)
    assert state == UXState.NEEDS_INPUT


def test_answer_ok_maps_to_ok():
    state = decide_ux_state(status_code=200, action=ChatAction.ANSWER.value, failure_type=None)
    assert state == UXState.OK


def test_415_maps_to_needs_input():
    state = decide_ux_state(status_code=415, action=None, failure_type=None)
    assert state == UXState.NEEDS_INPUT


def test_422_maps_to_needs_input():
    state = decide_ux_state(status_code=422, action=None, failure_type=None)
    assert state == UXState.NEEDS_INPUT


def test_429_maps_to_rate_limited():
    state = decide_ux_state(status_code=429, action=None, failure_type=None)
    assert state == UXState.RATE_LIMITED


def test_503_provider_unavailable_maps_to_degraded():
    state = decide_ux_state(
        status_code=503,
        action=None,
        failure_type=FailureType.PROVIDER_UNAVAILABLE.value,
        failure_reason="temporarily unavailable",
    )
    assert state == UXState.DEGRADED


def test_budget_or_quota_maps_to_quota_exceeded():
    state_ft = decide_ux_state(status_code=429, action=None, failure_type=FailureType.BUDGET_EXCEEDED.value)
    state_reason = decide_ux_state(status_code=500, action=None, failure_type=None, failure_reason="quota reached")
    assert state_ft == UXState.QUOTA_EXCEEDED
    assert state_reason == UXState.QUOTA_EXCEEDED


def test_abuse_blocked_maps_to_blocked():
    state = decide_ux_state(status_code=403, action=None, failure_type=FailureType.ABUSE_BLOCKED.value)
    assert state == UXState.BLOCKED


def test_500_default_maps_to_error():
    state = decide_ux_state(status_code=500, action=None, failure_type=None)
    assert state == UXState.ERROR
