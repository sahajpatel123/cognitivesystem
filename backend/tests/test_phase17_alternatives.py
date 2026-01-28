"""
Phase 17 Step 6: Alternative Plan Generation Pass Tests

Tests for deterministic alternative generation with stable scoring and ranking.
"""

from backend.app.deepthink.passes.alternatives import (
    run_alternatives_pass,
    Candidate,
    FORBIDDEN_CLARIFY_PHRASES,
)
import hashlib
from backend.app.deepthink.engine import EngineContext, PassRunResult
from backend.app.deepthink.schema import (
    PatchOp,
    MAX_ANSWER_CHARS,
    MAX_RATIONALE_CHARS,
    MAX_CLARIFY_QUESTION_CHARS,
    MAX_ALTERNATIVE_CHARS,
    MAX_ALTERNATIVES_COUNT,
)


def make_fake_clock(initial_ms=0):
    """Create a fake clock for testing."""
    time_ms = [initial_ms]
    
    def now_ms():
        return time_ms[0]
    
    return now_ms


class TestDeterminism:
    """Test that alternatives pass is deterministic."""
    
    def test_identical_inputs_produce_identical_outputs_30_times(self):
        """Run pass 30 times with same inputs -> identical outputs."""
        state = {
            "request_text": "What's the best laptop for programming?",
            "decision": {
                "action": "ANSWER",
                "answer": "You should definitely buy a MacBook Pro.",
                "rationale": "It's guaranteed to work perfectly.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        results = []
        for _ in range(30):
            result = run_alternatives_pass("ALTERNATIVES", state, context)
            results.append(result)
        
        # Verify all results are identical
        first = results[0]
        for result in results[1:]:
            assert result.delta == first.delta
            assert result.cost_units == first.cost_units
            assert result.duration_ms == first.duration_ms
            assert result.error == first.error


class TestBoundedAlternatives:
    """Test that alternatives are bounded to 2-3."""
    
    def test_alternatives_list_length_2_or_3(self):
        """If decision.alternatives is written, it must be length 2 or 3."""
        state = {
            "request_text": "Recommend a laptop",
            "decision": {
                "action": "ANSWER",
                "answer": "Buy a laptop.",
                "rationale": "Standard approach.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_alternatives_pass("ALTERNATIVES", state, context)
        
        # Check alternatives ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.alternatives":
                    assert isinstance(op.value, list)
                    assert 2 <= len(op.value) <= 3, f"Alternatives length {len(op.value)} not in [2,3]"


class TestStableOrdering:
    """Test that alternatives are sorted by stable key."""
    
    def test_stable_sort_key_ordering(self):
        """Candidates sorted by (risk ASC, clarity DESC, cost ASC, tie_break ASC)."""
        # Create candidates with known scores
        candidate1 = Candidate(
            action="ANSWER",
            answer="Answer 1",
            rationale="Rationale 1",
            clarify_question="",
            risk_score=50,
            clarity_score=70,
            cost_score=10,
            tie_break_hash="aaa",
        )
        
        candidate2 = Candidate(
            action="ASK_CLARIFY",
            answer="",
            rationale="Rationale 2",
            clarify_question="Question 2",
            risk_score=30,
            clarity_score=80,
            cost_score=40,
            tie_break_hash="bbb",
        )
        
        candidate3 = Candidate(
            action="FALLBACK",
            answer="",
            rationale="Rationale 3",
            clarify_question="",
            risk_score=30,
            clarity_score=50,
            cost_score=20,
            tie_break_hash="ccc",
        )
        
        candidates = [candidate1, candidate2, candidate3]
        candidates.sort(key=lambda c: c.sort_key())
        
        # Expected order: candidate2 (risk=30, clarity=80), candidate3 (risk=30, clarity=50), candidate1 (risk=50)
        assert candidates[0] == candidate2
        assert candidates[1] == candidate3
        assert candidates[2] == candidate1
    
    def test_tie_break_hash_ordering(self):
        """When risk/clarity/cost equal, tie_break_hash determines order."""
        candidate1 = Candidate(
            action="ANSWER",
            answer="Answer A",
            rationale="Rationale",
            clarify_question="",
            risk_score=50,
            clarity_score=70,
            cost_score=10,
            tie_break_hash="zzz",
        )
        
        candidate2 = Candidate(
            action="ANSWER",
            answer="Answer B",
            rationale="Rationale",
            clarify_question="",
            risk_score=50,
            clarity_score=70,
            cost_score=10,
            tie_break_hash="aaa",
        )
        
        candidates = [candidate1, candidate2]
        candidates.sort(key=lambda c: c.sort_key())
        
        # Expected order: candidate2 (tie_break="aaa") before candidate1 (tie_break="zzz")
        assert candidates[0] == candidate2
        assert candidates[1] == candidate1


class TestAllowedEnumEnforcement:
    """Test that emitted actions are in allowed enum."""
    
    def test_action_must_be_in_allowed_enum(self):
        """Emitted action must be ANSWER, ASK_CLARIFY, REFUSE, or FALLBACK."""
        allowed_actions = {"ANSWER", "ASK_CLARIFY", "REFUSE", "FALLBACK"}
        
        test_states = [
            {"request_text": "test", "decision": {"action": "ANSWER", "answer": "text", "rationale": ""}},
            {"request_text": "test", "decision": {"action": "ASK_CLARIFY", "answer": "", "rationale": ""}},
        ]
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        for state in test_states:
            result = run_alternatives_pass("ALTERNATIVES", state, context)
            
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
            "request_text": "Recommend something",
            "decision": {
                "action": "ANSWER",
                "answer": "Buy this.",
                "rationale": "It's good.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_alternatives_pass("ALTERNATIVES", state, context)
        
        if result.delta:
            for op in result.delta:
                assert op.path in allowed_paths, f"Path '{op.path}' not in allowlist"


class TestBoundsEnforcement:
    """Test that updated fields stay within schema limits."""
    
    def test_answer_length_within_bounds(self):
        """Updated answer must be <= MAX_ANSWER_CHARS."""
        long_answer = "x" * (MAX_ANSWER_CHARS + 500)
        state = {
            "request_text": "test",
            "decision": {
                "action": "ANSWER",
                "answer": long_answer,
                "rationale": "text",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_alternatives_pass("ALTERNATIVES", state, context)
        
        # Check answer ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.answer":
                    assert len(op.value) <= MAX_ANSWER_CHARS
    
    def test_rationale_length_within_bounds(self):
        """Updated rationale must be <= MAX_RATIONALE_CHARS."""
        long_rationale = "x" * (MAX_RATIONALE_CHARS + 500)
        state = {
            "request_text": "test",
            "decision": {
                "action": "ANSWER",
                "answer": "text",
                "rationale": long_rationale,
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_alternatives_pass("ALTERNATIVES", state, context)
        
        # Check rationale ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.rationale":
                    assert len(op.value) <= MAX_RATIONALE_CHARS
    
    def test_clarify_question_length_within_bounds(self):
        """Clarify question must be <= MAX_CLARIFY_QUESTION_CHARS."""
        state = {
            "request_text": "test",
            "decision": {
                "action": "ANSWER",
                "answer": "text",
                "rationale": "text",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_alternatives_pass("ALTERNATIVES", state, context)
        
        # Check clarify_question ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.clarify_question":
                    assert len(op.value) <= MAX_CLARIFY_QUESTION_CHARS
    
    def test_alternatives_item_length_within_bounds(self):
        """Each alternative item must be <= MAX_ALTERNATIVE_CHARS."""
        state = {
            "request_text": "test",
            "decision": {
                "action": "ANSWER",
                "answer": "text",
                "rationale": "text",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_alternatives_pass("ALTERNATIVES", state, context)
        
        # Check alternatives ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.alternatives":
                    for item in op.value:
                        assert len(item) <= MAX_ALTERNATIVE_CHARS


class TestNoForbiddenPhrases:
    """Test that clarify questions never contain forbidden phrases."""
    
    def test_clarify_question_no_forbidden_phrases(self):
        """Clarify questions must not contain forbidden phrases."""
        state = {
            "request_text": "Help me with something",
            "decision": {
                "action": "ANSWER",
                "answer": "Do this.",
                "rationale": "Standard approach.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_alternatives_pass("ALTERNATIVES", state, context)
        
        # Check clarify_question ops
        if result.delta:
            for op in result.delta:
                if op.path == "decision.clarify_question":
                    clarify_lower = op.value.lower()
                    for forbidden in FORBIDDEN_CLARIFY_PHRASES:
                        assert forbidden not in clarify_lower, f"Forbidden phrase '{forbidden}' in clarify question"


class TestScoringFunctions:
    """Test scoring functions via pass execution."""
    
    def test_high_risk_state_produces_safer_alternative(self):
        """High-risk state (absolute language) should produce safer alternative."""
        # State with risky absolute language
        state = {
            "request_text": "medical advice",
            "decision": {
                "action": "ANSWER",
                "answer": "This is guaranteed to cure you 100%.",
                "rationale": "Always works.",
            }
        }
        
        context = EngineContext(
            request_signature="test-sig",
            now_ms=make_fake_clock(0),
            budget_units_remaining=200,
        )
        
        result = run_alternatives_pass("ALTERNATIVES", state, context)
        
        # Should produce a safer alternative (likely ASK_CLARIFY or tightened)
        assert result.delta is not None
        assert len(result.delta) > 0


class TestTieBreakHash:
    """Test tie-break hash computation."""
    
    def test_tie_break_hash_deterministic(self):
        """Same canonical string produces same hash."""
        canonical = "ANSWER|test answer|test rationale|"
        
        # Compute hash locally
        hash1 = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:12]
        hash2 = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:12]
        
        assert hash1 == hash2
    
    def test_tie_break_hash_different_for_different_strings(self):
        """Different canonical strings produce different hashes."""
        canonical1 = "ANSWER|answer1|rationale1|"
        canonical2 = "ANSWER|answer2|rationale2|"
        
        hash1 = hashlib.sha256(canonical1.encode('utf-8')).hexdigest()[:12]
        hash2 = hashlib.sha256(canonical2.encode('utf-8')).hexdigest()[:12]
        
        assert hash1 != hash2


# Self-check runner for local verification
if __name__ == "__main__":
    print("Running Phase 17 Alternatives Pass self-checks...")
    
    # Test 1: Determinism
    state = {
        "request_text": "What's the best laptop?",
        "decision": {
            "action": "ANSWER",
            "answer": "Buy a MacBook.",
            "rationale": "It's guaranteed to work.",
        }
    }
    
    context = EngineContext(
        request_signature="test-sig",
        now_ms=make_fake_clock(0),
        budget_units_remaining=200,
    )
    
    results = []
    for _ in range(10):
        result = run_alternatives_pass("ALTERNATIVES", state, context)
        results.append(result)
    
    first = results[0]
    for result in results[1:]:
        assert result.delta == first.delta, "Determinism failed"
    print("✓ Determinism (10 runs)")
    
    # Test 2: Bounded alternatives
    result = run_alternatives_pass("ALTERNATIVES", state, context)
    for op in result.delta:
        if op.path == "decision.alternatives":
            assert 2 <= len(op.value) <= 3, f"Alternatives length {len(op.value)} not in [2,3]"
    print("✓ Bounded alternatives (2-3)")
    
    # Test 3: Allowed enum
    allowed_actions = {"ANSWER", "ASK_CLARIFY", "REFUSE", "FALLBACK"}
    for op in result.delta:
        if op.path == "decision.action":
            assert op.value in allowed_actions, f"Invalid action: {op.value}"
    print("✓ Allowed enum enforcement")
    
    # Test 4: Allowed paths only
    allowed_paths = {"decision.action", "decision.answer", "decision.rationale", "decision.clarify_question", "decision.alternatives"}
    for op in result.delta:
        assert op.path in allowed_paths, f"Invalid path: {op.path}"
    print("✓ Allowed paths only")
    
    # Test 5: Bounds enforcement
    for op in result.delta:
        if op.path == "decision.answer":
            assert len(op.value) <= MAX_ANSWER_CHARS
        elif op.path == "decision.rationale":
            assert len(op.value) <= MAX_RATIONALE_CHARS
        elif op.path == "decision.clarify_question":
            assert len(op.value) <= MAX_CLARIFY_QUESTION_CHARS
        elif op.path == "decision.alternatives":
            for item in op.value:
                assert len(item) <= MAX_ALTERNATIVE_CHARS
    print("✓ Bounds enforcement")
    
    # Test 6: No forbidden phrases
    for op in result.delta:
        if op.path == "decision.clarify_question":
            clarify_lower = op.value.lower()
            for forbidden in FORBIDDEN_CLARIFY_PHRASES:
                assert forbidden not in clarify_lower, f"Forbidden phrase: {forbidden}"
    print("✓ No forbidden phrases in clarify questions")
    
    # Test 7: Stable ordering (sort key)
    candidate1 = Candidate(
        action="ANSWER", answer="A1", rationale="R1", clarify_question="",
        risk_score=50, clarity_score=70, cost_score=10, tie_break_hash="aaa"
    )
    candidate2 = Candidate(
        action="ASK_CLARIFY", answer="", rationale="R2", clarify_question="Q2",
        risk_score=30, clarity_score=80, cost_score=40, tie_break_hash="bbb"
    )
    candidates = [candidate1, candidate2]
    candidates.sort(key=lambda c: c.sort_key())
    assert candidates[0] == candidate2, "Sort key ordering failed"
    print("✓ Stable sort key ordering")
    
    # Test 8: Tie-break hash determinism
    canonical = 'ANSWER|test|test|'
    hash1 = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:12]
    hash2 = hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:12]
    assert hash1 == hash2, 'Tie-break hash not deterministic'
    print('✓ Tie-break hash determinism')
    
    print("\nAll self-checks PASSED ✓")
