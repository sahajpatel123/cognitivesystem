"""
Phase 17 Step 2: Schema Validation Tests

Tests for DecisionDelta schema and validator with 2-strikes rule.
"""

from backend.app.deepthink.schema import (
    PatchOp,
    DecisionDelta,
    is_allowed_path,
    is_forbidden_path,
    get_path_spec,
    DecisionAction,
    ALLOWED_PATCH_PATHS,
    MAX_ANSWER_CHARS,
    MAX_RATIONALE_CHARS,
    MAX_CLARIFY_QUESTION_CHARS,
    MAX_ALTERNATIVE_CHARS,
    MAX_ALTERNATIVES_COUNT,
)
from backend.app.deepthink.validator import validate_delta, ValidationResult


class TestSchemaAllowlist:
    """Test path allowlist and forbidden patterns."""
    
    def test_allowed_paths_are_recognized(self):
        """Allowed paths return True."""
        for path in ALLOWED_PATCH_PATHS:
            assert is_allowed_path(path), f"Path {path} should be allowed"
    
    def test_unknown_path_not_allowed(self):
        """Unknown paths return False."""
        assert not is_allowed_path("unknown.path")
        assert not is_allowed_path("decision.unknown")
        assert not is_allowed_path("entitlement.tier")
    
    def test_forbidden_patterns_detected(self):
        """Forbidden patterns are detected."""
        forbidden_paths = [
            "entitlement.cap",
            "tier.max",
            "routing.pass_count",
            "breaker.threshold",
            "budget.total",
            "safety.policy",
            "security.token",
            "header.auth",
            "cookie.session",
        ]
        for path in forbidden_paths:
            assert is_forbidden_path(path), f"Path {path} should be forbidden"
    
    def test_allowed_paths_not_forbidden(self):
        """Allowed paths don't match forbidden patterns."""
        for path in ALLOWED_PATCH_PATHS:
            assert not is_forbidden_path(path), f"Allowed path {path} should not be forbidden"


class TestValidDelta:
    """Test that valid deltas pass validation."""
    
    def test_valid_action_patch(self):
        """Valid action patch passes."""
        delta = [PatchOp(op="set", path="decision.action", value="ANSWER")]
        result = validate_delta(delta, current_strikes=0)
        
        assert result.ok
        assert len(result.errors) == 0
        assert result.strikes_added == 0
        assert result.total_strikes == 0
        assert result.stop_reason is None
        assert not result.downgrade
    
    def test_valid_answer_patch(self):
        """Valid answer patch passes."""
        delta = [PatchOp(op="set", path="decision.answer", value="This is a valid answer.")]
        result = validate_delta(delta, current_strikes=0)
        
        assert result.ok
        assert result.strikes_added == 0
    
    def test_valid_multiple_patches(self):
        """Multiple valid patches pass."""
        delta = [
            PatchOp(op="set", path="decision.action", value="ANSWER"),
            PatchOp(op="set", path="decision.answer", value="Valid answer text."),
            PatchOp(op="set", path="decision.rationale", value="Valid rationale."),
        ]
        result = validate_delta(delta, current_strikes=0)
        
        assert result.ok
        assert result.strikes_added == 0


class TestInvalidPath:
    """Test that invalid paths fail validation."""
    
    def test_unknown_path_fails(self):
        """Unknown path fails validation."""
        delta = [PatchOp(op="set", path="unknown.path", value="test")]
        result = validate_delta(delta, current_strikes=0)
        
        assert not result.ok
        assert result.strikes_added == 1
        assert result.total_strikes == 1
        assert any("not in allowlist" in e for e in result.errors)
    
    def test_forbidden_path_fails(self):
        """Forbidden path pattern fails."""
        delta = [PatchOp(op="set", path="entitlement.cap", value=5)]
        result = validate_delta(delta, current_strikes=0)
        
        assert not result.ok
        assert result.strikes_added == 1
        assert any("forbidden pattern" in e or "not in allowlist" in e for e in result.errors)


class TestInvalidOp:
    """Test that invalid operations fail validation."""
    
    def test_unknown_op_fails(self):
        """Unknown operation fails."""
        # Note: PatchOp constructor will raise ValueError for invalid op
        # So we test via validator's handling of malformed data
        delta = [PatchOp(op="set", path="decision.action", value="ANSWER")]
        # Manually create invalid op for testing
        invalid_op = object.__new__(PatchOp)
        object.__setattr__(invalid_op, "op", "add")
        object.__setattr__(invalid_op, "path", "decision.action")
        object.__setattr__(invalid_op, "value", "ANSWER")
        
        delta_with_invalid = [invalid_op]
        result = validate_delta(delta_with_invalid, current_strikes=0)
        
        assert not result.ok
        assert result.strikes_added == 1


class TestEnumValidation:
    """Test enum value validation."""
    
    def test_invalid_action_enum_fails(self):
        """Invalid action enum value fails."""
        delta = [PatchOp(op="set", path="decision.action", value="INVALID_ACTION")]
        result = validate_delta(delta, current_strikes=0)
        
        assert not result.ok
        assert result.strikes_added == 1
        assert any("not in allowed enum values" in e for e in result.errors)
    
    def test_valid_action_enum_passes(self):
        """Valid action enum values pass."""
        for action in DecisionAction:
            delta = [PatchOp(op="set", path="decision.action", value=action.value)]
            result = validate_delta(delta, current_strikes=0)
            assert result.ok, f"Action {action.value} should be valid"


class TestTextBounds:
    """Test text length bounds validation."""
    
    def test_overlong_answer_fails(self):
        """Answer exceeding max length fails."""
        long_text = "x" * (MAX_ANSWER_CHARS + 1)
        delta = [PatchOp(op="set", path="decision.answer", value=long_text)]
        result = validate_delta(delta, current_strikes=0)
        
        assert not result.ok
        assert result.strikes_added == 1
        assert any("exceeds max" in e for e in result.errors)
    
    def test_max_length_answer_passes(self):
        """Answer at max length passes."""
        text = "x" * MAX_ANSWER_CHARS
        delta = [PatchOp(op="set", path="decision.answer", value=text)]
        result = validate_delta(delta, current_strikes=0)
        
        assert result.ok
    
    def test_overlong_rationale_fails(self):
        """Rationale exceeding max length fails."""
        long_text = "x" * (MAX_RATIONALE_CHARS + 1)
        delta = [PatchOp(op="set", path="decision.rationale", value=long_text)]
        result = validate_delta(delta, current_strikes=0)
        
        assert not result.ok
        assert result.strikes_added == 1
    
    def test_overlong_clarify_question_fails(self):
        """Clarify question exceeding max length fails."""
        long_text = "x" * (MAX_CLARIFY_QUESTION_CHARS + 1)
        delta = [PatchOp(op="set", path="decision.clarify_question", value=long_text)]
        result = validate_delta(delta, current_strikes=0)
        
        assert not result.ok
        assert result.strikes_added == 1


class TestListBounds:
    """Test list bounds validation."""
    
    def test_too_many_alternatives_fails(self):
        """Too many alternatives fails."""
        alternatives = ["alt1", "alt2", "alt3", "alt4"]  # MAX is 3
        delta = [PatchOp(op="set", path="decision.alternatives", value=alternatives)]
        result = validate_delta(delta, current_strikes=0)
        
        assert not result.ok
        assert result.strikes_added == 1
        assert any("exceeds max" in e for e in result.errors)
    
    def test_max_alternatives_passes(self):
        """Max alternatives count passes."""
        alternatives = ["alt1", "alt2", "alt3"]
        delta = [PatchOp(op="set", path="decision.alternatives", value=alternatives)]
        result = validate_delta(delta, current_strikes=0)
        
        assert result.ok
    
    def test_overlong_alternative_item_fails(self):
        """Alternative item exceeding max length fails."""
        long_alt = "x" * (MAX_ALTERNATIVE_CHARS + 1)
        alternatives = [long_alt]
        delta = [PatchOp(op="set", path="decision.alternatives", value=alternatives)]
        result = validate_delta(delta, current_strikes=0)
        
        assert not result.ok
        assert result.strikes_added == 1


class TestTwoStrikesRule:
    """Test exact 2-strikes downgrade behavior."""
    
    def test_first_invalid_delta_one_strike(self):
        """First invalid delta: strikes=1, no downgrade."""
        delta = [PatchOp(op="set", path="unknown.path", value="test")]
        result = validate_delta(delta, current_strikes=0)
        
        assert not result.ok
        assert result.strikes_added == 1
        assert result.total_strikes == 1
        assert result.stop_reason is None
        assert not result.downgrade
    
    def test_second_invalid_delta_two_strikes_downgrade(self):
        """Second invalid delta: strikes=2, VALIDATION_FAIL, downgrade."""
        delta = [PatchOp(op="set", path="unknown.path", value="test")]
        result = validate_delta(delta, current_strikes=1)  # Already 1 strike
        
        assert not result.ok
        assert result.strikes_added == 1
        assert result.total_strikes == 2
        assert result.stop_reason == "VALIDATION_FAIL"
        assert result.downgrade
    
    def test_valid_delta_after_one_strike_no_additional_strike(self):
        """Valid delta after 1 strike: no additional strike."""
        delta = [PatchOp(op="set", path="decision.action", value="ANSWER")]
        result = validate_delta(delta, current_strikes=1)
        
        assert result.ok
        assert result.strikes_added == 0
        assert result.total_strikes == 1
        assert result.stop_reason is None
        assert not result.downgrade
    
    def test_exactly_two_failures_triggers_downgrade(self):
        """Exactly 2 failures trigger downgrade."""
        # First failure
        delta1 = [PatchOp(op="set", path="unknown.path1", value="test")]
        result1 = validate_delta(delta1, current_strikes=0)
        assert result1.total_strikes == 1
        assert not result1.downgrade
        
        # Second failure
        delta2 = [PatchOp(op="set", path="unknown.path2", value="test")]
        result2 = validate_delta(delta2, current_strikes=result1.total_strikes)
        assert result2.total_strikes == 2
        assert result2.downgrade
        assert result2.stop_reason == "VALIDATION_FAIL"


class TestOptionalFields:
    """Test optional field handling."""
    
    def test_none_value_for_optional_field_passes(self):
        """None value for optional field passes."""
        delta = [PatchOp(op="set", path="decision.answer", value=None)]
        result = validate_delta(delta, current_strikes=0)
        
        assert result.ok
        assert result.strikes_added == 0


# Self-check runner for local verification (when pytest not available)
if __name__ == "__main__":
    print("Running Phase 17 Schema Validation self-checks...")
    
    # Test 1: Valid delta
    delta = [PatchOp(op="set", path="decision.action", value="ANSWER")]
    result = validate_delta(delta, current_strikes=0)
    assert result.ok, "Valid delta should pass"
    print("✓ Valid delta passes")
    
    # Test 2: Invalid path
    delta = [PatchOp(op="set", path="unknown.path", value="test")]
    result = validate_delta(delta, current_strikes=0)
    assert not result.ok, "Invalid path should fail"
    assert result.strikes_added == 1, "Should add 1 strike"
    print("✓ Invalid path fails with 1 strike")
    
    # Test 3: 2-strikes downgrade
    delta = [PatchOp(op="set", path="unknown.path", value="test")]
    result = validate_delta(delta, current_strikes=1)
    assert not result.ok, "Second invalid should fail"
    assert result.total_strikes == 2, "Should have 2 strikes"
    assert result.stop_reason == "VALIDATION_FAIL", "Should have VALIDATION_FAIL"
    assert result.downgrade, "Should trigger downgrade"
    print("✓ 2-strikes triggers downgrade")
    
    # Test 4: Text bounds
    long_text = "x" * (MAX_ANSWER_CHARS + 1)
    delta = [PatchOp(op="set", path="decision.answer", value=long_text)]
    result = validate_delta(delta, current_strikes=0)
    assert not result.ok, "Overlong text should fail"
    print("✓ Text bounds enforced")
    
    # Test 5: Enum validation
    delta = [PatchOp(op="set", path="decision.action", value="INVALID_ACTION")]
    result = validate_delta(delta, current_strikes=0)
    assert not result.ok, "Invalid enum should fail"
    print("✓ Enum validation enforced")
    
    print("\nAll self-checks PASSED ✓")
