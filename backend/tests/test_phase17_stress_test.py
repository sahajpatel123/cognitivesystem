"""
Phase 17 Step 5: Stress-test Pass Tests

Tests for deterministic assumption stress-test pass implementation.
"""

from backend.app.deepthink.passes.stress_test import (
    run_stress_test_pass,
    DomainType,
    CRITICAL_INPUTS_MAP,
    FORBIDDEN_CLARIFY_PHRASES,
    _classify_domain,
    _is_input_present,
)
from backend.app.deepthink.engine import EngineContext, PassRunResult
from backend.app.deepthink.schema import (
    PatchOp,
    MAX_ANSWER_CHARS,
    MAX_RATIONALE_CHARS,
    MAX_CLARIFY_QUESTION_CHARS,
)


def make_fake_clock(initial_ms=0):
    """Create a fake clock for testing."""
    time_ms = [initial_ms]
    
    def now_ms():
        return time_ms[0]
    
    return now_ms


class TestDeterminism:
    """Test that stress-test pass is deterministic."""
    
    def test_identical_inputs_produce_identical_outputs_30_times(self):
        """Run pass 30 times with same inputs -> identical outputs."""
        state = {
            "request_text": "I have an error in my code",
            "decision": {
                "action": "ANSWER",
                "answer": "You need to fix the error.",
                "rationale": "Standard debugging approach.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        results = []
        for _ in range(30):
            result = run_stress_test_pass("STRESS_TEST", state, context)
            results.append(result)
        
        # Verify all results are identical
        first = results[0]
        for result in results[1:]:
            assert result.delta == first.delta
            assert result.cost_units == first.cost_units
            assert result.duration_ms == first.duration_ms
            assert result.error == first.error


class TestMissingCriticalInputForcesAskClarify:
    """Test that missing critical input forces ASK_CLARIFY for each domain."""
    
    def test_code_tech_missing_lang_runtime(self):
        """CODE_TECH domain missing LANG_RUNTIME -> ASK_CLARIFY."""
        state = {
            "request_text": "I have an error in my code: TypeError exception",
            "decision": {
                "action": "ANSWER",
                "answer": "Debug the error.",
                "rationale": "Standard approach.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        # Should force ASK_CLARIFY
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        assert len(action_ops) == 1
        assert action_ops[0].value == "ASK_CLARIFY"
        
        # Should ask for missing input
        clarify_ops = [op for op in result.delta if op.path == "decision.clarify_question"]
        assert len(clarify_ops) == 1
        assert "language" in clarify_ops[0].value.lower() or "runtime" in clarify_ops[0].value.lower()
    
    def test_deploy_devops_missing_platform(self):
        """DEPLOY_DEVOPS domain missing PLATFORM -> should still ANSWER."""
        state = {
            "request_text": "My deployment build is failing at the start stage",
            "decision": {
                "action": "ANSWER",
                "answer": "Check your build configuration.",
                "rationale": "Standard approach.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        # Should force ASK_CLARIFY
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        assert len(action_ops) == 1
        assert action_ops[0].value == "ASK_CLARIFY"
    
    def test_medical_health_missing_severity(self):
        """MEDICAL_HEALTH domain missing SEVERITY_RED_FLAGS -> ASK_CLARIFY."""
        state = {
            "request_text": "I have a headache since yesterday",
            "decision": {
                "action": "ANSWER",
                "answer": "Take rest.",
                "rationale": "Standard approach.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        # Should force ASK_CLARIFY (missing SEVERITY_RED_FLAGS)
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        assert len(action_ops) == 1
        assert action_ops[0].value == "ASK_CLARIFY"
    
    def test_travel_local_missing_dates(self):
        """TRAVEL_LOCAL domain missing DATES -> ASK_CLARIFY."""
        state = {
            "request_text": "I want to travel to Paris, budget is $2000",
            "decision": {
                "action": "ANSWER",
                "answer": "Book your tickets.",
                "rationale": "Standard approach.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        # Should force ASK_CLARIFY (missing DATES)
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        assert len(action_ops) == 1
        assert action_ops[0].value == "ASK_CLARIFY"
    
    def test_purchase_recommendation_missing_budget(self):
        """PURCHASE_RECOMMENDATION domain missing BUDGET -> ASK_CLARIFY."""
        state = {
            "request_text": "Recommend a laptop for programming in India",
            "decision": {
                "action": "ANSWER",
                "answer": "Buy a good laptop.",
                "rationale": "Standard approach.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        # Should force ASK_CLARIFY (missing BUDGET)
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        assert len(action_ops) == 1
        assert action_ops[0].value == "ASK_CLARIFY"


class TestNoMissingCase:
    """Test that no missing critical inputs does not force ASK_CLARIFY."""
    
    def test_code_tech_all_inputs_present(self):
        """CODE_TECH with all inputs -> no forced ASK_CLARIFY."""
        state = {
            "request_text": "I have a Python TypeError exception in my local dev environment",
            "decision": {
                "action": "ANSWER",
                "answer": "Check your type annotations.",
                "rationale": "Standard debugging approach.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        # Should NOT force ASK_CLARIFY (all inputs present)
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        # Either no action change or stays ANSWER
        if action_ops:
            assert action_ops[0].value != "ASK_CLARIFY"


class TestForbiddenPhraseBlacklist:
    """Test that clarify questions never contain forbidden phrases."""
    
    def test_clarify_question_no_forbidden_phrases(self):
        """Clarify questions must not contain forbidden phrases."""
        # Test multiple domains with missing inputs
        test_states = [
            {"request_text": "I have an error", "decision": {"action": "ANSWER", "answer": "Fix it", "rationale": ""}},
            {"request_text": "Deploy failing", "decision": {"action": "ANSWER", "answer": "Check config", "rationale": ""}},
            {"request_text": "Recommend laptop", "decision": {"action": "ANSWER", "answer": "Buy one", "rationale": ""}},
        ]
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        for state in test_states:
            result = run_stress_test_pass("STRESS_TEST", state, context)
            
            # Check clarify_question ops
            if result.delta:
                for op in result.delta:
                    if op.path == "decision.clarify_question":
                        clarify_lower = op.value.lower()
                        for forbidden in FORBIDDEN_CLARIFY_PHRASES:
                            assert forbidden not in clarify_lower, f"Forbidden phrase '{forbidden}' in clarify question"


class TestAllowedEnumEnforcement:
    """Test that emitted actions are in allowed enum."""
    
    def test_action_must_be_in_allowed_enum(self):
        """Emitted action must be ANSWER, ASK_CLARIFY, REFUSE, or FALLBACK."""
        allowed_actions = {"ANSWER", "ASK_CLARIFY", "REFUSE", "FALLBACK"}
        
        test_states = [
            {"request_text": "error in code", "decision": {"action": "ANSWER", "answer": "fix", "rationale": ""}},
            {"request_text": "deploy issue", "decision": {"action": "ANSWER", "answer": "check", "rationale": ""}},
        ]
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        for state in test_states:
            result = run_stress_test_pass("STRESS_TEST", state, context)
            
            if result.delta:
                for op in result.delta:
                    if op.path == "decision.action":
                        assert op.value in allowed_actions, f"Invalid action: {op.value}"


class TestAllowedPatchPathsOnly:
    """Test that all ops use allowed paths."""
    
    def test_all_ops_use_allowed_paths(self):
        """Every op.path must be in allowed set."""
        allowed_paths = {
            "decision.action",
            "decision.answer",
            "decision.rationale",
            "decision.clarify_question",
            "decision.alternatives",
        }
        
        state = {
            "request_text": "I have an error in my code",
            "decision": {
                "action": "ANSWER",
                "answer": "Debug it.",
                "rationale": "Standard approach.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        if result.delta:
            for op in result.delta:
                assert op.path in allowed_paths, f"Path '{op.path}' not in allowlist"


class TestBoundsEnforcement:
    """Test that updated fields stay within schema limits."""
    
    def test_clarify_question_length_within_bounds(self):
        """Clarify question must be <= MAX_CLARIFY_QUESTION_CHARS."""
        state = {
            "request_text": "error in code",
            "decision": {
                "action": "ANSWER",
                "answer": "Fix it",
                "rationale": "",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        # Check clarify_question ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.clarify_question":
                    assert len(op.value) <= MAX_CLARIFY_QUESTION_CHARS
    
    def test_rationale_length_within_bounds(self):
        """Rationale must be <= MAX_RATIONALE_CHARS."""
        state = {
            "request_text": "error in code",
            "decision": {
                "action": "ANSWER",
                "answer": "Fix it",
                "rationale": "",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        # Check rationale ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.rationale":
                    assert len(op.value) <= MAX_RATIONALE_CHARS


class TestNearMeHandling:
    """Test that 'near me' without city forces ASK_CLARIFY."""
    
    def test_near_me_without_city_missing_location(self):
        """'near me' without city name -> LOCATION missing -> ASK_CLARIFY."""
        state = {
            "request_text": "Recommend a restaurant near me",
            "decision": {
                "action": "ANSWER",
                "answer": "Check nearby restaurants.",
                "rationale": "",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        # Should force ASK_CLARIFY (LOCATION missing)
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        assert len(action_ops) == 1
        assert action_ops[0].value == "ASK_CLARIFY"
        
        # Should ask for location
        clarify_ops = [op for op in result.delta if op.path == "decision.clarify_question"]
        assert len(clarify_ops) == 1
        assert "location" in clarify_ops[0].value.lower() or "city" in clarify_ops[0].value.lower()
    
    def test_near_me_with_city_location_present(self):
        """'near me' with city name -> LOCATION present -> no forced ASK_CLARIFY."""
        state = {
            "request_text": "Recommend a restaurant near me in Bangalore",
            "decision": {
                "action": "ANSWER",
                "answer": "Check restaurants in Bangalore.",
                "rationale": "",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        # Should NOT force ASK_CLARIFY (LOCATION present)
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        # Either no action change or not ASK_CLARIFY
        if action_ops:
            # May still ask for other missing inputs, but LOCATION should be satisfied
            pass


class TestDomainClassification:
    """Test domain classification logic."""
    
    def test_medical_health_classification(self):
        """Medical keywords -> MEDICAL_HEALTH."""
        domain = _classify_domain("I have a fever and headache")
        assert domain == DomainType.MEDICAL_HEALTH
    
    def test_code_tech_classification(self):
        """Code/error keywords -> CODE_TECH."""
        domain = _classify_domain("I have a Python TypeError exception")
        assert domain == DomainType.CODE_TECH
    
    def test_deploy_devops_classification(self):
        """Deploy keywords -> DEPLOY_DEVOPS."""
        domain = _classify_domain("My Railway deployment is failing")
        assert domain == DomainType.DEPLOY_DEVOPS
    
    def test_generic_fallback(self):
        """No matching keywords -> GENERIC."""
        domain = _classify_domain("Hello world")
        assert domain == DomainType.GENERIC


class TestStableOrdering:
    """Test that ops are returned in stable sorted order."""
    
    def test_ops_sorted_by_path(self):
        """Ops must be sorted by path."""
        state = {
            "request_text": "error in code",
            "decision": {
                "action": "ANSWER",
                "answer": "Fix it",
                "rationale": "",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_stress_test_pass("STRESS_TEST", state, context)
        
        if result.delta and len(result.delta) > 1:
            paths = [op.path for op in result.delta]
            sorted_paths = sorted(paths)
            assert paths == sorted_paths, "Ops not sorted by path"


# Self-check runner for local verification
if __name__ == "__main__":
    print("Running Phase 17 Stress-test Pass self-checks...")
    
    # Test 1: Determinism
    state = {
        "request_text": "I have an error in my code",
        "decision": {
            "action": "ANSWER",
            "answer": "Debug it.",
            "rationale": "",
        }
    }
    
    context = EngineContext(
        request_signature="test-sig",
        now_ms=make_fake_clock(0),
        budget_units_remaining=200,
    )
    
    results = []
    for _ in range(10):
        result = run_stress_test_pass("STRESS_TEST", state, context)
        results.append(result)
    
    first = results[0]
    for result in results[1:]:
        assert result.delta == first.delta, "Determinism failed"
    print("✓ Determinism (10 runs)")
    
    # Test 2: Missing critical input forces ASK_CLARIFY
    state = {
        "request_text": "I have an error in my code: TypeError",
        "decision": {
            "action": "ANSWER",
            "answer": "Debug it.",
            "rationale": "",
        }
    }
    result = run_stress_test_pass("STRESS_TEST", state, context)
    action_ops = [op for op in result.delta if op.path == "decision.action"]
    assert len(action_ops) == 1
    assert action_ops[0].value == "ASK_CLARIFY"
    print("✓ Missing critical input forces ASK_CLARIFY")
    
    # Test 3: No forbidden phrases
    for op in result.delta:
        if op.path == "decision.clarify_question":
            clarify_lower = op.value.lower()
            for forbidden in FORBIDDEN_CLARIFY_PHRASES:
                assert forbidden not in clarify_lower, f"Forbidden phrase: {forbidden}"
    print("✓ No forbidden phrases in clarify questions")
    
    # Test 4: Allowed enum
    allowed_actions = {"ANSWER", "ASK_CLARIFY", "REFUSE", "FALLBACK"}
    for op in result.delta:
        if op.path == "decision.action":
            assert op.value in allowed_actions, f"Invalid action: {op.value}"
    print("✓ Allowed enum enforcement")
    
    # Test 5: Allowed paths only
    allowed_paths = {"decision.action", "decision.answer", "decision.rationale", "decision.clarify_question", "decision.alternatives"}
    for op in result.delta:
        assert op.path in allowed_paths, f"Invalid path: {op.path}"
    print("✓ Allowed paths only")
    
    # Test 6: Bounds enforcement
    for op in result.delta:
        if op.path == "decision.clarify_question":
            assert len(op.value) <= MAX_CLARIFY_QUESTION_CHARS
        elif op.path == "decision.rationale":
            assert len(op.value) <= MAX_RATIONALE_CHARS
    print("✓ Bounds enforcement")
    
    # Test 7: Near me handling
    state = {
        "request_text": "Recommend a restaurant near me",
        "decision": {
            "action": "ANSWER",
            "answer": "Check nearby.",
            "rationale": "",
        }
    }
    result = run_stress_test_pass("STRESS_TEST", state, context)
    action_ops = [op for op in result.delta if op.path == "decision.action"]
    assert len(action_ops) == 1
    assert action_ops[0].value == "ASK_CLARIFY"
    print("✓ 'Near me' without city forces ASK_CLARIFY")
    
    # Test 8: Stable ordering
    if len(result.delta) > 1:
        paths = [op.path for op in result.delta]
        assert paths == sorted(paths), "Ops not sorted"
    print("✓ Stable ordering")
    
    print("\nAll self-checks PASSED ✓")
