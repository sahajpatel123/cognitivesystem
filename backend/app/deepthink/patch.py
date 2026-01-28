"""
Phase 17 Step 2: DecisionDelta Patch Applier

Applies validated deltas to decision state with strict guardrails.
"""

from typing import Any, Dict
from copy import deepcopy

from backend.app.deepthink.schema import (
    PatchOp,
    DecisionDelta,
    is_allowed_path,
    is_forbidden_path,
    get_path_spec,
)


class PatchError(Exception):
    """Raised when patch application fails guardrails."""
    pass


def apply_delta(state: Dict[str, Any], delta: DecisionDelta) -> Dict[str, Any]:
    """
    Apply a validated DecisionDelta to a decision state.
    
    Args:
        state: Original decision state (dict)
        delta: List of PatchOp to apply
    
    Returns:
        New state with patches applied (original state unchanged)
    
    Raises:
        PatchError: If any guardrail is violated
    
    Guardrails:
        - Only 'set' operations allowed
        - Only allowlisted paths
        - No forbidden paths
        - Type and bounds checked
        - Deterministic application order (sorted by path)
    """
    # Deep copy to avoid mutating original
    new_state = deepcopy(state)
    
    # Sort ops by path for deterministic ordering
    sorted_ops = sorted(delta, key=lambda op: op.path)
    
    for op in sorted_ops:
        # Guardrail: op type
        if op.op != "set":
            raise PatchError(f"Only 'set' operation allowed, got: {op.op}")
        
        # Guardrail: allowlist
        if not is_allowed_path(op.path):
            raise PatchError(f"Path '{op.path}' not in allowlist")
        
        # Guardrail: forbidden patterns
        if is_forbidden_path(op.path):
            raise PatchError(f"Path '{op.path}' matches forbidden pattern")
        
        # Guardrail: validate value against spec
        spec = get_path_spec(op.path)
        if spec:
            _validate_value_for_apply(op.path, op.value, spec)
        
        # Apply the patch
        _set_nested_value(new_state, op.path, op.value)
    
    return new_state


def _set_nested_value(state: Dict[str, Any], path: str, value: Any) -> None:
    """
    Set a nested value in state dict using dot-notation path.
    
    Example: path="decision.action" sets state["decision"]["action"] = value
    """
    parts = path.split(".")
    current = state
    
    # Navigate to parent
    for part in parts[:-1]:
        if part not in current:
            current[part] = {}
        current = current[part]
    
    # Set the final value
    current[parts[-1]] = value


def _validate_value_for_apply(path: str, value: Any, spec: dict) -> None:
    """
    Validate value at apply-time (defensive check).
    
    Raises PatchError if validation fails.
    """
    value_type = spec.get("type")
    
    # Handle None for optional fields
    if value is None:
        if not spec.get("optional", False):
            raise PatchError(f"Path '{path}' is not optional, cannot set to None")
        return
    
    # Type-specific validation
    if value_type == "enum":
        if not isinstance(value, str):
            raise PatchError(f"Path '{path}' requires string value for enum")
        if value not in spec.get("enum_values", set()):
            allowed = sorted(spec.get("enum_values", set()))
            raise PatchError(f"Value '{value}' not in allowed enum values {allowed} for path '{path}'")
    
    elif value_type == "string":
        if not isinstance(value, str):
            raise PatchError(f"Path '{path}' requires string value")
        max_len = spec.get("max_length")
        if max_len and len(value) > max_len:
            raise PatchError(f"Value length {len(value)} exceeds max {max_len} for path '{path}'")
    
    elif value_type == "list":
        if not isinstance(value, list):
            raise PatchError(f"Path '{path}' requires list value")
        
        max_items = spec.get("max_items")
        if max_items and len(value) > max_items:
            raise PatchError(f"List length {len(value)} exceeds max {max_items} for path '{path}'")
        
        item_type = spec.get("item_type")
        max_item_length = spec.get("max_item_length")
        
        for idx, item in enumerate(value):
            if item_type == "string":
                if not isinstance(item, str):
                    raise PatchError(f"List item [{idx}] must be string for path '{path}'")
                if max_item_length and len(item) > max_item_length:
                    raise PatchError(f"List item [{idx}] length {len(item)} exceeds max {max_item_length} for path '{path}'")
    
    else:
        raise PatchError(f"Unknown type '{value_type}' in spec for path '{path}'")
