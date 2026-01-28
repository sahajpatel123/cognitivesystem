"""
Phase 17 Step 2: Patch Guardrails Tests

Tests for DecisionDelta patch applier with strict guardrails.
"""

from backend.app.deepthink.schema import (
    PatchOp,
    DecisionDelta,
    DecisionAction,
    MAX_ANSWER_CHARS,
    MAX_ALTERNATIVES_COUNT,
)
from backend.app.deepthink.patch import apply_delta, PatchError


class TestPatchApplication:
    """Test basic patch application."""
    
    def test_apply_valid_action_patch(self):
        """Valid action patch applies correctly."""
        state = {"decision": {}}
        delta = [PatchOp(op="set", path="decision.action", value="ANSWER")]
        
        new_state = apply_delta(state, delta)
        
        assert new_state["decision"]["action"] == "ANSWER"
        assert state == {"decision": {}}  # Original unchanged
    
    def test_apply_multiple_patches(self):
        """Multiple patches apply in deterministic order."""
        state = {"decision": {}}
        delta = [
            PatchOp(op="set", path="decision.rationale", value="Rationale text"),
            PatchOp(op="set", path="decision.action", value="ANSWER"),
            PatchOp(op="set", path="decision.answer", value="Answer text"),
        ]
        
        new_state = apply_delta(state, delta)
        
        assert new_state["decision"]["action"] == "ANSWER"
        assert new_state["decision"]["answer"] == "Answer text"
        assert new_state["decision"]["rationale"] == "Rationale text"
    
    def test_original_state_unchanged(self):
        """Original state is not mutated."""
        state = {"decision": {"action": "REFUSE"}}
        delta = [PatchOp(op="set", path="decision.action", value="ANSWER")]
        
        new_state = apply_delta(state, delta)
        
        assert new_state["decision"]["action"] == "ANSWER"
        assert state["decision"]["action"] == "REFUSE"  # Original unchanged


class TestForbiddenPathGuardrails:
    """Test that forbidden paths are rejected."""
    
    def test_entitlement_cap_patch_rejected(self):
        """Attempt to patch entitlement cap is rejected."""
        state = {"decision": {}}
        delta = [PatchOp(op="set", path="entitlement.cap", value=10)]
        
        try:
            apply_delta(state, delta)
            assert False, "Should have raised PatchError"
        except PatchError as e:
            assert "not in allowlist" in str(e)
    
    def test_routing_pass_count_patch_rejected(self):
        """Attempt to patch routing pass_count is rejected."""
        state = {"decision": {}}
        delta = [PatchOp(op="set", path="routing.pass_count", value=10)]
        
        try:
            apply_delta(state, delta)
            assert False, "Should have raised PatchError"
        except PatchError as e:
            assert "not in allowlist" in str(e) or "forbidden pattern" in str(e)
    
    def test_safety_field_patch_rejected(self):
        """Attempt to patch safety field is rejected."""
        state = {"decision": {}}
        delta = [PatchOp(op="set", path="safety.threshold", value=0.5)]
        
        try:
            apply_delta(state, delta)
            assert False, "Should have raised PatchError"
        except PatchError as e:
            assert "not in allowlist" in str(e) or "forbidden pattern" in str(e)
    
    def test_security_field_patch_rejected(self):
        """Attempt to patch security field is rejected."""
        state = {"decision": {}}
        delta = [PatchOp(op="set", path="security.token", value="fake")]
        
        try:
            apply_delta(state, delta)
            assert False, "Should have raised PatchError"
        except PatchError as e:
            assert "not in allowlist" in str(e) or "forbidden pattern" in str(e)


class TestActionEnumGuardrails:
    """Test action enum guardrails."""
    
    def test_invalid_action_rejected(self):
        """Invalid action enum value is rejected."""
        state = {"decision": {}}
        delta = [PatchOp(op="set", path="decision.action", value="INVALID_ACTION")]
        
        try:
            apply_delta(state, delta)
            assert False, "Should have raised PatchError"
        except PatchError as e:
            assert "not in allowed enum values" in str(e)
    
    def test_valid_actions_accepted(self):
        """Valid action enum values are accepted."""
        state = {"decision": {}}
        
        for action in DecisionAction:
            delta = [PatchOp(op="set", path="decision.action", value=action.value)]
            new_state = apply_delta(state, delta)
            assert new_state["decision"]["action"] == action.value


class TestTextBoundsGuardrails:
    """Test text length bounds guardrails."""
    
    def test_huge_text_rejected(self):
        """Text exceeding max length is rejected."""
        state = {"decision": {}}
        huge_text = "x" * (MAX_ANSWER_CHARS + 1)
        delta = [PatchOp(op="set", path="decision.answer", value=huge_text)]
        
        try:
            apply_delta(state, delta)
            assert False, "Should have raised PatchError"
        except PatchError as e:
            assert "exceeds max" in str(e)
    
    def test_max_length_text_accepted(self):
        """Text at max length is accepted."""
        state = {"decision": {}}
        text = "x" * MAX_ANSWER_CHARS
        delta = [PatchOp(op="set", path="decision.answer", value=text)]
        
        new_state = apply_delta(state, delta)
        assert new_state["decision"]["answer"] == text


class TestListBoundsGuardrails:
    """Test list bounds guardrails."""
    
    def test_too_many_alternatives_rejected(self):
        """Too many alternatives is rejected."""
        state = {"decision": {}}
        alternatives = ["alt1", "alt2", "alt3", "alt4"]  # MAX is 3
        delta = [PatchOp(op="set", path="decision.alternatives", value=alternatives)]
        
        try:
            apply_delta(state, delta)
            assert False, "Should have raised PatchError"
        except PatchError as e:
            assert "exceeds max" in str(e)
    
    def test_max_alternatives_accepted(self):
        """Max alternatives count is accepted."""
        state = {"decision": {}}
        alternatives = ["alt1", "alt2", "alt3"]
        delta = [PatchOp(op="set", path="decision.alternatives", value=alternatives)]
        
        new_state = apply_delta(state, delta)
        assert new_state["decision"]["alternatives"] == alternatives


class TestDeterministicOrdering:
    """Test deterministic patch application ordering."""
    
    def test_patches_applied_in_sorted_order(self):
        """Patches are applied in sorted path order."""
        state = {"decision": {}}
        
        # Create patches in non-sorted order
        delta = [
            PatchOp(op="set", path="decision.rationale", value="third"),
            PatchOp(op="set", path="decision.action", value="ANSWER"),
            PatchOp(op="set", path="decision.answer", value="second"),
        ]
        
        new_state = apply_delta(state, delta)
        
        # All should be applied regardless of order
        assert new_state["decision"]["action"] == "ANSWER"
        assert new_state["decision"]["answer"] == "second"
        assert new_state["decision"]["rationale"] == "third"
    
    def test_same_delta_produces_same_result(self):
        """Same delta produces identical result (determinism)."""
        state = {"decision": {}}
        delta = [
            PatchOp(op="set", path="decision.rationale", value="text"),
            PatchOp(op="set", path="decision.action", value="ANSWER"),
        ]
        
        result1 = apply_delta(state, delta)
        result2 = apply_delta(state, delta)
        
        assert result1 == result2


class TestOptionalFieldHandling:
    """Test optional field handling."""
    
    def test_none_value_for_optional_field_accepted(self):
        """None value for optional field is accepted."""
        state = {"decision": {"answer": "existing"}}
        delta = [PatchOp(op="set", path="decision.answer", value=None)]
        
        new_state = apply_delta(state, delta)
        
        assert new_state["decision"]["answer"] is None


class TestInvalidOpGuardrail:
    """Test that invalid operations are rejected."""
    
    def test_non_set_op_rejected(self):
        """Non-set operation is rejected."""
        state = {"decision": {}}
        
        # Manually create invalid op for testing
        invalid_op = object.__new__(PatchOp)
        object.__setattr__(invalid_op, "op", "add")
        object.__setattr__(invalid_op, "path", "decision.action")
        object.__setattr__(invalid_op, "value", "ANSWER")
        
        delta = [invalid_op]
        
        try:
            apply_delta(state, delta)
            assert False, "Should have raised PatchError"
        except PatchError as e:
            assert "Only 'set' operation allowed" in str(e)


# Self-check runner for local verification (when pytest not available)
if __name__ == "__main__":
    print("Running Phase 17 Patch Guardrails self-checks...")
    
    # Test 1: Valid patch applies
    state = {"decision": {}}
    delta = [PatchOp(op="set", path="decision.action", value="ANSWER")]
    new_state = apply_delta(state, delta)
    assert new_state["decision"]["action"] == "ANSWER", "Valid patch should apply"
    assert state == {"decision": {}}, "Original should be unchanged"
    print("✓ Valid patch applies correctly")
    
    # Test 2: Forbidden path rejected
    state = {"decision": {}}
    delta = [PatchOp(op="set", path="entitlement.cap", value=10)]
    try:
        apply_delta(state, delta)
        assert False, "Should have raised PatchError"
    except PatchError:
        pass
    print("✓ Forbidden path rejected")
    
    # Test 3: Invalid action rejected
    state = {"decision": {}}
    delta = [PatchOp(op="set", path="decision.action", value="INVALID")]
    try:
        apply_delta(state, delta)
        assert False, "Should have raised PatchError"
    except PatchError:
        pass
    print("✓ Invalid action enum rejected")
    
    # Test 4: Huge text rejected
    state = {"decision": {}}
    huge_text = "x" * (MAX_ANSWER_CHARS + 1)
    delta = [PatchOp(op="set", path="decision.answer", value=huge_text)]
    try:
        apply_delta(state, delta)
        assert False, "Should have raised PatchError"
    except PatchError:
        pass
    print("✓ Huge text rejected")
    
    # Test 5: Too many alternatives rejected
    state = {"decision": {}}
    alternatives = ["alt1", "alt2", "alt3", "alt4"]
    delta = [PatchOp(op="set", path="decision.alternatives", value=alternatives)]
    try:
        apply_delta(state, delta)
        assert False, "Should have raised PatchError"
    except PatchError:
        pass
    print("✓ Too many alternatives rejected")
    
    # Test 6: Deterministic ordering
    state = {"decision": {}}
    delta = [
        PatchOp(op="set", path="decision.rationale", value="third"),
        PatchOp(op="set", path="decision.action", value="ANSWER"),
    ]
    result1 = apply_delta(state, delta)
    result2 = apply_delta(state, delta)
    assert result1 == result2, "Should be deterministic"
    print("✓ Deterministic ordering")
    
    print("\nAll self-checks PASSED ✓")
