"""
Phase 17 Step 2: DecisionDelta Validator

Implements 2-strikes validation with fail-closed downgrade.
"""

from dataclasses import dataclass
from typing import List, Optional, Any

from backend.app.deepthink.schema import (
    PatchOp,
    DecisionDelta,
    is_allowed_path,
    is_forbidden_path,
    get_path_spec,
    DecisionAction,
)


@dataclass
class ValidationResult:
    """
    Result of validating a DecisionDelta.
    """
    ok: bool
    errors: List[str]
    strikes_added: int  # 0 or 1
    total_strikes: int
    stop_reason: Optional[str]
    downgrade: bool

    def __post_init__(self) -> None:
        if self.strikes_added not in (0, 1):
            raise ValueError("strikes_added must be 0 or 1")
        if self.total_strikes < 0:
            raise ValueError("total_strikes must be non-negative")


def validate_delta(delta: DecisionDelta, current_strikes: int = 0) -> ValidationResult:
    """
    Validate a DecisionDelta with 2-strikes rule.
    
    Args:
        delta: List of PatchOp to validate
        current_strikes: Current strike count (0, 1, or 2+)
    
    Returns:
        ValidationResult with ok, errors, strikes, stop_reason, downgrade
    
    Rules:
        - First invalid delta: strikes=1, stop_reason=None, downgrade=False
        - Second invalid delta: strikes=2, stop_reason="VALIDATION_FAIL", downgrade=True
    """
    errors: List[str] = []
    
    # Validate delta structure
    if not isinstance(delta, list):
        errors.append("delta must be a list of PatchOp")
    else:
        for i, op in enumerate(delta):
            if not isinstance(op, PatchOp):
                errors.append(f"delta[{i}] is not a PatchOp")
                continue
            
            # Validate op type
            if op.op != "set":
                errors.append(f"delta[{i}]: unknown op '{op.op}', only 'set' is supported")
            
            # Validate path allowlist
            if not is_allowed_path(op.path):
                errors.append(f"delta[{i}]: path '{op.path}' is not in allowlist")
            
            # Defensive check for forbidden patterns
            if is_forbidden_path(op.path):
                errors.append(f"delta[{i}]: path '{op.path}' matches forbidden pattern")
            
            # Validate value against path spec
            if is_allowed_path(op.path):
                spec = get_path_spec(op.path)
                if spec:
                    value_errors = _validate_value(op.path, op.value, spec)
                    errors.extend([f"delta[{i}]: {e}" for e in value_errors])
    
    # Determine result
    ok = len(errors) == 0
    strikes_added = 0 if ok else 1
    total_strikes = current_strikes + strikes_added
    
    # 2-strikes rule
    stop_reason = None
    downgrade = False
    if total_strikes >= 2:
        stop_reason = "VALIDATION_FAIL"
        downgrade = True
    
    # Sort errors for determinism
    errors.sort()
    
    return ValidationResult(
        ok=ok,
        errors=errors,
        strikes_added=strikes_added,
        total_strikes=total_strikes,
        stop_reason=stop_reason,
        downgrade=downgrade,
    )


def _validate_value(path: str, value: Any, spec: dict) -> List[str]:
    """
    Validate a value against its path specification.
    
    Returns list of error messages (empty if valid).
    """
    errors: List[str] = []
    
    value_type = spec.get("type")
    
    # Handle None for optional fields
    if value is None:
        if spec.get("optional", False):
            return []
        else:
            errors.append(f"value is None but path '{path}' is not optional")
            return errors
    
    # Type-specific validation
    if value_type == "enum":
        if not isinstance(value, str):
            errors.append(f"value must be string for enum path '{path}'")
        elif value not in spec.get("enum_values", set()):
            allowed = sorted(spec.get("enum_values", set()))
            errors.append(f"value '{value}' not in allowed enum values: {allowed}")
    
    elif value_type == "string":
        if not isinstance(value, str):
            errors.append(f"value must be string for path '{path}'")
        else:
            max_len = spec.get("max_length")
            if max_len and len(value) > max_len:
                errors.append(f"value length {len(value)} exceeds max {max_len} for path '{path}'")
    
    elif value_type == "list":
        if not isinstance(value, list):
            errors.append(f"value must be list for path '{path}'")
        else:
            max_items = spec.get("max_items")
            if max_items and len(value) > max_items:
                errors.append(f"list length {len(value)} exceeds max {max_items} for path '{path}'")
            
            item_type = spec.get("item_type")
            max_item_length = spec.get("max_item_length")
            
            for idx, item in enumerate(value):
                if item_type == "string":
                    if not isinstance(item, str):
                        errors.append(f"list item [{idx}] must be string for path '{path}'")
                    elif max_item_length and len(item) > max_item_length:
                        errors.append(f"list item [{idx}] length {len(item)} exceeds max {max_item_length} for path '{path}'")
    
    else:
        errors.append(f"unknown type '{value_type}' in spec for path '{path}'")
    
    return errors
