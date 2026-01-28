"""
Phase 17 Step 8: Observability + Replay Signature (NO USER TEXT)

Safe telemetry with zero user text leakage. Decision signature is deterministic
and based only on structural metadata, never raw text content.

Non-agentic, deterministic, privacy-preserving.
"""

from typing import Dict, Any, List, Optional
import hashlib
import json


# Forbidden keys that contain user/assistant text (must be redacted)
FORBIDDEN_TEXT_KEYS = {
    "user_text",
    "prompt",
    "message",
    "content",
    "rendered_text",
    "answer",
    "rationale",
    "clarify_question",
    "alternatives",
    "request_text",
    "user_input",
    "assistant_output",
}


def compute_decision_signature(
    stable_inputs: Dict[str, Any],
    pass_plan: List[str],
    deltas: List[Any],
    meta: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Compute deterministic decision signature with NO user text.
    
    Args:
        stable_inputs: Safe non-text inputs (tier, mode, flags, budgets, timeouts)
        pass_plan: List of pass type strings
        deltas: List of PatchOp objects (will extract structure only)
        meta: Optional metadata (validator_failures, stop_reason)
    
    Returns:
        SHA256 hex digest (64 chars)
    
    Guarantees:
        - Deterministic: same inputs -> same signature
        - Privacy-preserving: no user text included
        - Structural only: includes op/path/value_type/length, not content
    """
    # Build signature data with safe fields only
    sig_data = {
        "stable_inputs": _sanitize_stable_inputs(stable_inputs),
        "pass_plan": pass_plan,
        "deltas_structure": _encode_deltas_structure(deltas),
    }
    
    # Add safe meta fields if provided
    if meta:
        if "validator_failures" in meta:
            sig_data["validator_failures"] = meta["validator_failures"]
        if "stop_reason" in meta:
            sig_data["stop_reason"] = meta["stop_reason"]
    
    # Canonical JSON serialization
    sig_json = json.dumps(sig_data, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    sig_hash = hashlib.sha256(sig_json.encode('utf-8')).hexdigest()
    
    return sig_hash


def build_telemetry_event(
    pass_count: int,
    stop_reason: str,
    validator_failures: int,
    downgraded: bool,
    decision_signature: str,
    pass_summaries: Optional[List[Any]] = None,
    final_action: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build safe telemetry event with NO user text.
    
    Args:
        pass_count: Number of passes executed
        stop_reason: Stop reason code (enum)
        validator_failures: Count of validation failures
        downgraded: Whether execution was downgraded
        decision_signature: Computed decision signature
        pass_summaries: Optional list of pass summaries (will sanitize)
        final_action: Optional final action enum (ANSWER/ASK_CLARIFY/REFUSE/FALLBACK)
    
    Returns:
        JSON-serializable dict with safe fields only
    
    Guarantees:
        - No user text included
        - Only primitives, lists, dicts
        - JSON-serializable
    """
    event = {
        "pass_count": pass_count,
        "stop_reason": stop_reason,
        "validator_failures": validator_failures,
        "downgraded": downgraded,
        "decision_signature": decision_signature,
    }
    
    # Add final action if provided (enum only)
    if final_action:
        event["final_action"] = final_action
    
    # Add safe pass summaries if provided
    if pass_summaries:
        event["pass_summaries"] = _sanitize_pass_summaries(pass_summaries)
    
    return event


def _sanitize_stable_inputs(stable_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize stable inputs to remove any text fields.
    
    Keeps only safe non-text fields like tier, mode, flags, budgets, timeouts.
    """
    safe_inputs = {}
    
    # Allowlist of safe keys
    safe_keys = {
        "env_mode",
        "entitlement_tier",
        "deepthink_enabled",
        "breaker_tripped",
        "abuse_blocked",
        "total_budget_units",
        "total_timeout_ms",
        "requested_mode",
    }
    
    for key, value in stable_inputs.items():
        # Skip forbidden text keys
        if key in FORBIDDEN_TEXT_KEYS:
            continue
        
        # Include safe keys
        if key in safe_keys:
            # Ensure value is not a string containing user text
            if isinstance(value, (int, float, bool)):
                safe_inputs[key] = value
            elif isinstance(value, str) and len(value) < 50:
                # Short strings (enums/modes) are ok
                safe_inputs[key] = value
    
    return safe_inputs


def _encode_deltas_structure(deltas: List[Any]) -> List[Dict[str, Any]]:
    """
    Encode deltas as structure-only (no text content).
    
    For each PatchOp:
    - Include op type and path
    - For value: include type and metadata (length/count) but NOT content
    """
    encoded = []
    
    for delta in deltas:
        # Extract op and path
        if hasattr(delta, 'op'):
            op = delta.op
        else:
            op = delta.get('op', 'unknown')
        
        if hasattr(delta, 'path'):
            path = delta.path
        else:
            path = delta.get('path', 'unknown')
        
        if hasattr(delta, 'value'):
            value = delta.value
        else:
            value = delta.get('value')
        
        # Encode value as metadata only
        value_meta = _encode_value_metadata(value)
        
        encoded.append({
            "op": op,
            "path": path,
            "value_meta": value_meta,
        })
    
    return encoded


def _encode_value_metadata(value: Any) -> Dict[str, Any]:
    """
    Encode value as metadata (type, length, count) but NOT content.
    
    This ensures no user text leaks into the signature.
    """
    if value is None:
        return {"type": "null"}
    
    elif isinstance(value, str):
        return {"type": "str", "len": len(value)}
    
    elif isinstance(value, list):
        if all(isinstance(item, str) for item in value):
            # List of strings: include count and lengths (capped at 3)
            lens = [len(item) for item in value[:3]]
            return {"type": "list_str", "count": len(value), "lens": lens}
        else:
            return {"type": "list", "count": len(value)}
    
    elif isinstance(value, bool):
        return {"type": "bool", "value": value}
    
    elif isinstance(value, (int, float)):
        return {"type": "number", "value": value}
    
    elif isinstance(value, dict):
        # Dict: include sorted keys (capped at 5) but not values
        keys = sorted(value.keys())[:5]
        return {"type": "dict", "keys": keys}
    
    else:
        return {"type": str(type(value).__name__)}


def _sanitize_pass_summaries(pass_summaries: List[Any]) -> List[Dict[str, Any]]:
    """
    Sanitize pass summaries to remove text fields.
    
    Keeps only safe metadata: pass_type, executed, validation_ok, cost, duration, strikes.
    """
    safe_summaries = []
    
    for summary in pass_summaries:
        safe_summary = {}
        
        # Extract safe fields
        if hasattr(summary, 'pass_type'):
            safe_summary["pass_type"] = summary.pass_type
        elif isinstance(summary, dict) and "pass_type" in summary:
            safe_summary["pass_type"] = summary["pass_type"]
        
        # Safe boolean/int fields
        safe_fields = [
            "executed",
            "validation_ok",
            "patch_applied",
            "cost_units",
            "duration_ms",
            "strikes_added",
        ]
        
        for field in safe_fields:
            if hasattr(summary, field):
                value = getattr(summary, field)
                if isinstance(value, (bool, int, float)):
                    safe_summary[field] = value
            elif isinstance(summary, dict) and field in summary:
                value = summary[field]
                if isinstance(value, (bool, int, float)):
                    safe_summary[field] = value
        
        # Do NOT include error field (may contain text)
        
        safe_summaries.append(safe_summary)
    
    return safe_summaries


def sanitize_summary_for_logging(summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a summary dict for safe logging (no user text).
    
    Removes any keys that might contain user/assistant text.
    """
    safe_summary = {}
    
    for key, value in summary.items():
        # Skip forbidden text keys
        if key in FORBIDDEN_TEXT_KEYS:
            continue
        
        # Include safe primitives
        if isinstance(value, (int, float, bool, type(None))):
            safe_summary[key] = value
        elif isinstance(value, str) and len(value) < 100:
            # Short strings (codes/enums) are ok
            safe_summary[key] = value
        elif isinstance(value, list):
            # Sanitize list items
            safe_list = []
            for item in value:
                if isinstance(item, (int, float, bool)):
                    safe_list.append(item)
                elif isinstance(item, dict):
                    safe_list.append(sanitize_summary_for_logging(item))
            safe_summary[key] = safe_list
        elif isinstance(value, dict):
            # Recursively sanitize nested dicts
            safe_summary[key] = sanitize_summary_for_logging(value)
    
    return safe_summary
