import pathlib
import sys

import pytest

# Ensure repository root on path for imports
ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.mci_backend.control_plan import ClosureState, QuestionClass, RefusalCategory
from backend.mci_backend.model_output_schema import (
    AnswerJSON,
    AskOneQuestionJSON,
    CloseJSON,
    ModelOutputParseError,
    ModelOutputSchemaViolation,
    RefusalJSON,
    parse_model_json,
    validate_answer_payload,
    validate_ask_payload,
    validate_close_payload,
    validate_refusal_payload,
)
from backend.mci_backend.orchestration_question_compression import QuestionPriorityReason


def test_parse_model_json_accepts_object():
    raw = '{"answer_text": "ok"}'
    parsed = parse_model_json(raw)
    assert parsed["answer_text"] == "ok"


def test_parse_model_json_rejects_non_json():
    with pytest.raises(ModelOutputParseError):
        parse_model_json("not-json")


def test_parse_model_json_rejects_markdown_fence():
    with pytest.raises(ModelOutputParseError):
        parse_model_json("```json\n{\"a\":1}\n```")


def test_answer_schema_accepts_valid():
    payload = {"answer_text": "hello", "assumptions": ["a"], "unknowns": ["u"]}
    obj = validate_answer_payload(payload)
    assert isinstance(obj, AnswerJSON)


def test_answer_schema_rejects_extra_key():
    with pytest.raises(ModelOutputSchemaViolation):
        validate_answer_payload({"answer_text": "hi", "extra": "nope"})


def test_answer_schema_rejects_overlong():
    with pytest.raises(ModelOutputSchemaViolation):
        validate_answer_payload({"answer_text": "x" * 6001})


def test_ask_schema_accepts_valid():
    payload = {
        "question": "What is your goal?",
        "question_class": QuestionClass.INFORMATIONAL,
        "priority_reason": QuestionPriorityReason.UNKNOWN_CONTEXT,
    }
    obj = validate_ask_payload(payload)
    assert isinstance(obj, AskOneQuestionJSON)


def test_ask_schema_rejects_multi_question():
    payload = {
        "question": "What is your goal? And what is your budget?",
        "question_class": QuestionClass.INFORMATIONAL,
        "priority_reason": QuestionPriorityReason.UNKNOWN_CONTEXT,
    }
    with pytest.raises(ModelOutputSchemaViolation):
        validate_ask_payload(payload)


def test_ask_schema_rejects_extra_keys():
    payload = {
        "question": "What is your goal?",
        "question_class": QuestionClass.INFORMATIONAL,
        "priority_reason": QuestionPriorityReason.UNKNOWN_CONTEXT,
        "extra": "nope",
    }
    with pytest.raises(ModelOutputSchemaViolation):
        validate_ask_payload(payload)


def test_refusal_schema_accepts_valid():
    payload = {
        "refusal_category": RefusalCategory.RISK_REFUSAL,
        "refusal_text": "Cannot comply for safety reasons.",
    }
    obj = validate_refusal_payload(payload)
    assert isinstance(obj, RefusalJSON)


def test_refusal_schema_rejects_policy_language():
    payload = {
        "refusal_category": RefusalCategory.RISK_REFUSAL,
        "refusal_text": "As an AI model I cannot comply.",
    }
    with pytest.raises(ModelOutputSchemaViolation):
        validate_refusal_payload(payload)


def test_close_schema_accepts_valid():
    payload = {"closure_state": ClosureState.CLOSING, "closure_text": "Closing now."}
    obj = validate_close_payload(payload)
    assert isinstance(obj, CloseJSON)


def test_close_schema_rejects_question():
    payload = {"closure_state": ClosureState.CLOSING, "closure_text": "Are you there?"}
    with pytest.raises(ModelOutputSchemaViolation):
        validate_close_payload(payload)


def test_parse_model_json_rejects_array():
    with pytest.raises(ModelOutputParseError):
        parse_model_json('["not", "object"]')
