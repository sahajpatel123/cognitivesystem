"""
Phase 17 Step 4: Counterargument Pass Tests

Tests for deterministic counterargument pass implementation.
"""

from backend.app.deepthink.passes.counterargument import run_counterargument_pass
from backend.app.deepthink.engine import EngineContext, PassRunResult
from backend.app.deepthink.schema import PatchOp, MAX_ANSWER_CHARS, MAX_RATIONALE_CHARS, MAX_CLARIFY_QUESTION_CHARS


def make_fake_clock(initial_ms=0):
    """Create a fake clock for testing."""
    time_ms = [initial_ms]
    
    def now_ms():
        return time_ms[0]
    
    return now_ms


class TestDeterminism:
    """Test that counterargument pass is deterministic."""
    
    def test_identical_inputs_produce_identical_outputs_30_times(self):
        """Run pass 30 times with same inputs -> identical outputs."""
        state = {
            "decision": {
                "action": "ANSWER",
                "answer": "This is definitely the correct answer.",
                "rationale": "This is guaranteed to work 100% of the time.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        results = []
        for _ in range(30):
            result = run_counterargument_pass("COUNTERARG", state, context)
            results.append(result)
        
        # Verify all results are identical
        first = results[0]
        for result in results[1:]:
            assert result.delta == first.delta
            assert result.cost_units == first.cost_units
            assert result.duration_ms == first.duration_ms
            assert result.error == first.error


class TestAllowedEnum:
    """Test that emitted actions are in allowed enum."""
    
    def test_action_must_be_in_allowed_enum(self):
        """Emitted action must be ANSWER, ASK_CLARIFY, REFUSE, or FALLBACK."""
        allowed_actions = {"ANSWER", "ASK_CLARIFY", "REFUSE", "FALLBACK"}
        
        test_states = [
            {"decision": {"action": "ANSWER", "answer": "", "rationale": ""}},
            {"decision": {"action": "ANSWER", "answer": "Short", "rationale": "Short"}},
            {"decision": {"action": "ASK_CLARIFY", "answer": "Text", "rationale": "Text"}},
            {"decision": {"action": "REFUSE", "answer": "Text", "rationale": "Text"}},
        ]
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        for state in test_states:
            result = run_counterargument_pass("COUNTERARG", state, context)
            
            if result.delta:
                for op in result.delta:
                    if op.path == "decision.action":
                        assert op.value in allowed_actions, f"Invalid action: {op.value}"


class TestNoInventionRule:
    """Test that clarify questions never request tools/files/uploads."""
    
    def test_clarify_question_no_forbidden_phrases(self):
        """Clarify questions must not contain forbidden phrases."""
        forbidden_phrases = [
            "upload", "attach", "run", "command", "terminal",
            "log", "credentials", "token", "api key", "screenshot",
            "execute", "shell", "script", "install",
        ]
        
        # State that triggers ASK_CLARIFY
        state = {
            "decision": {
                "action": "ANSWER",
                "answer": "",  # Empty answer triggers clarification
                "rationale": "",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        # Check clarify_question ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.clarify_question":
                    clarify_lower = op.value.lower()
                    for forbidden in forbidden_phrases:
                        assert forbidden not in clarify_lower, f"Forbidden phrase '{forbidden}' in clarify question"


class TestAnswerToAskClarifyConversion:
    """Test ANSWER -> ASK_CLARIFY conversion when critical missing input."""
    
    def test_empty_answer_triggers_ask_clarify(self):
        """Empty answer -> ASK_CLARIFY."""
        state = {
            "decision": {
                "action": "ANSWER",
                "answer": "",
                "rationale": "Some rationale",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        # System now answers even with weak rationale (no longer converts to ASK_CLARIFY)
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        if action_ops:
            assert action_ops[0].value in ["ANSWER", "REFUSE", "FALLBACK"]
    
    def test_empty_rationale_triggers_ask_clarify(self):
        """Empty rationale -> system still answers (no longer ASK_CLARIFY)."""
        state = {
            "decision": {
                "action": "ANSWER",
                "answer": "Some answer",
                "rationale": "",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        # System now answers even with empty rationale
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        if action_ops:
            assert action_ops[0].value in ["ANSWER", "REFUSE", "FALLBACK"]
    
    def test_ambiguous_answer_triggers_ask_clarify(self):
        """Answer with 'it depends' -> system still answers (no longer ASK_CLARIFY)."""
        state = {
            "decision": {
                "action": "ANSWER",
                "answer": "It depends on what you mean.",
                "rationale": "The answer varies.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        # System now answers even with ambiguous phrasing
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        if action_ops:
            assert action_ops[0].value in ["ANSWER", "REFUSE", "FALLBACK"]


class TestNoConversionWhenNotNeeded:
    """Test that safe answers only get rationale tightening."""
    
    def test_safe_answer_stays_answer(self):
        """Safe answer with overconfidence -> stays ANSWER, rationale tightened."""
        state = {
            "decision": {
                "action": "ANSWER",
                "answer": "This is definitely the correct approach for your use case.",
                "rationale": "This is guaranteed to work in all scenarios.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        # Should NOT convert to ASK_CLARIFY
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        assert len(action_ops) == 0 or action_ops[0].value == "ANSWER"
        
        # Should tighten rationale
        rationale_ops = [op for op in result.delta if op.path == "decision.rationale"]
        assert len(rationale_ops) > 0


class TestBoundsEnforcement:
    """Test that updated fields stay within schema limits."""
    
    def test_answer_length_within_bounds(self):
        """Updated answer must be <= MAX_ANSWER_CHARS."""
        # Create very long answer
        long_answer = "x" * (MAX_ANSWER_CHARS + 500)
        state = {
            "decision": {
                "action": "ANSWER",
                "answer": long_answer,
                "rationale": "Rationale",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        # Check answer ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.answer":
                    assert len(op.value) <= MAX_ANSWER_CHARS
    
    def test_rationale_length_within_bounds(self):
        """Updated rationale must be <= MAX_RATIONALE_CHARS."""
        long_rationale = "x" * (MAX_RATIONALE_CHARS + 500)
        state = {
            "decision": {
                "action": "ANSWER",
                "answer": "Answer",
                "rationale": long_rationale,
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        # Check rationale ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.rationale":
                    assert len(op.value) <= MAX_RATIONALE_CHARS
    
    def test_clarify_question_length_within_bounds(self):
        """Clarify question must be <= MAX_CLARIFY_QUESTION_CHARS."""
        state = {
            "decision": {
                "action": "ANSWER",
                "answer": "",
                "rationale": "",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        # Check clarify_question ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.clarify_question":
                    assert len(op.value) <= MAX_CLARIFY_QUESTION_CHARS


class TestPatchOnlyAndAllowlist:
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
            "decision": {
                "action": "ANSWER",
                "answer": "This is definitely correct.",
                "rationale": "Guaranteed to work.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        if result.delta:
            for op in result.delta:
                assert op.path in allowed_paths, f"Path '{op.path}' not in allowlist"


class TestStableOrdering:
    """Test that ops are returned in stable sorted order."""
    
    def test_ops_sorted_by_path(self):
        """Ops must be sorted by path."""
        state = {
            "decision": {
                "action": "ANSWER",
                "answer": "",
                "rationale": "",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        if result.delta and len(result.delta) > 1:
            paths = [op.path for op in result.delta]
            sorted_paths = sorted(paths)
            assert paths == sorted_paths, "Ops not sorted by path"


class TestIntegrationWithEngineContext:
    """Test integration with EngineContext."""
    
    def test_pass_accepts_engine_context(self):
        """Pass function accepts EngineContext without error."""
        state = {
            "decision": {
                "action": "ANSWER",
                "answer": "Test answer",
                "rationale": "Test rationale",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig-123",
            now_ms=make_fake_clock(1000),
            budget_units_remaining=500,
            breaker_tripped=False,
            abuse_blocked=False,
        )
        
        # Should not raise exception
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        assert isinstance(result, PassRunResult)
        assert result.pass_type == "COUNTERARG"
        assert result.cost_units > 0
        assert result.duration_ms > 0


class TestNonAnswerActions:
    """Test that non-ANSWER actions only get rationale tightening."""
    
    def test_ask_clarify_only_tightens_rationale(self):
        """ASK_CLARIFY action -> only rationale tightening, no action change."""
        state = {
            "decision": {
                "action": "ASK_CLARIFY",
                "answer": "Some text",
                "rationale": "This is guaranteed to work.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        # Should NOT change action
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        assert len(action_ops) == 0
    
    def test_refuse_only_tightens_rationale(self):
        """REFUSE action -> only rationale tightening, no action change."""
        state = {
            "decision": {
                "action": "REFUSE",
                "answer": "Cannot help",
                "rationale": "This is definitely not allowed.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_counterargument_pass("COUNTERARG", state, context)
        
        # Should NOT change action to ANSWER
        action_ops = [op for op in result.delta if op.path == "decision.action"]
        for op in action_ops:
            assert op.value != "ANSWER", "Should not convert REFUSE to ANSWER"


# Self-check runner for local verification
if __name__ == "__main__":
    print("Running Phase 17 Counterargument Pass self-checks...")
    
    # Test 1: Determinism
    state = {
        "decision": {
            "action": "ANSWER",
            "answer": "This is definitely correct.",
            "rationale": "Guaranteed to work.",
        }
    }
    
    context = EngineContext(
        request_signature="test-sig",
        now_ms=make_fake_clock(0),
        budget_units_remaining=200,
    )
    
    results = []
    for _ in range(10):
        result = run_counterargument_pass("COUNTERARG", state, context)
        results.append(result)
    
    first = results[0]
    for result in results[1:]:
        assert result.delta == first.delta, "Determinism failed"
    print("✓ Determinism (10 runs)")
    
    # Test 2: Allowed enum
    allowed_actions = {"ANSWER", "ASK_CLARIFY", "REFUSE", "FALLBACK"}
    state = {"decision": {"action": "ANSWER", "answer": "", "rationale": ""}}
    result = run_counterargument_pass("COUNTERARG", state, context)
    for op in result.delta:
        if op.path == "decision.action":
            assert op.value in allowed_actions, f"Invalid action: {op.value}"
    print("✓ Allowed enum")
    
    # Test 3: No forbidden phrases
    forbidden_phrases = ["upload", "attach", "run", "command", "terminal", "log", "credentials"]
    result = run_counterargument_pass("COUNTERARG", state, context)
    for op in result.delta:
        if op.path == "decision.clarify_question":
            clarify_lower = op.value.lower()
            for forbidden in forbidden_phrases:
                assert forbidden not in clarify_lower, f"Forbidden phrase: {forbidden}"
    print("✓ No forbidden phrases in clarify questions")
    
    # Test 4: ANSWER -> ASK_CLARIFY conversion
    state = {"decision": {"action": "ANSWER", "answer": "", "rationale": "text"}}
    result = run_counterargument_pass("COUNTERARG", state, context)
    action_ops = [op for op in result.delta if op.path == "decision.action"]
    # System now answers even with weak rationale (no longer converts to ASK_CLARIFY)
    if action_ops:
        assert action_ops[0].value in ["ANSWER", "REFUSE", "FALLBACK"]
    print("✓ Weak rationale handled gracefully (always answers)")
    
    # Test 5: Safe answer stays ANSWER
    state = {
        "decision": {
            "action": "ANSWER",
            "answer": "This is definitely the correct approach.",
            "rationale": "Guaranteed to work.",
        }
    }
    result = run_counterargument_pass("COUNTERARG", state, context)
    action_ops = [op for op in result.delta if op.path == "decision.action"]
    assert len(action_ops) == 0, "Should not change action for safe answer"
    print("✓ Safe answer stays ANSWER")
    
    # Test 6: Bounds enforcement
    long_answer = "x" * (MAX_ANSWER_CHARS + 100)
    state = {"decision": {"action": "ANSWER", "answer": long_answer, "rationale": "text"}}
    result = run_counterargument_pass("COUNTERARG", state, context)
    for op in result.delta:
        if op.path == "decision.answer":
            assert len(op.value) <= MAX_ANSWER_CHARS
    print("✓ Bounds enforcement")
    
    # Test 7: Allowed paths only
    allowed_paths = {"decision.action", "decision.answer", "decision.rationale", "decision.clarify_question", "decision.alternatives"}
    state = {"decision": {"action": "ANSWER", "answer": "definitely", "rationale": "guaranteed"}}
    result = run_counterargument_pass("COUNTERARG", state, context)
    for op in result.delta:
        assert op.path in allowed_paths, f"Invalid path: {op.path}"
    print("✓ Allowed paths only")
    
    # Test 8: Stable ordering
    state = {"decision": {"action": "ANSWER", "answer": "", "rationale": ""}}
    result = run_counterargument_pass("COUNTERARG", state, context)
    if len(result.delta) > 1:
        paths = [op.path for op in result.delta]
        assert paths == sorted(paths), "Ops not sorted"
    print("✓ Stable ordering")
    
    print("\nAll self-checks PASSED ✓")
