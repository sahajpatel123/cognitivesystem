"""
Phase 18 Step 7: Research Telemetry (Structure-Only, No User Text)

Deterministic, fail-closed telemetry builder and signature computation.
"""

import hashlib
import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


FORBIDDEN_KEYS = {
    "user_text",
    "prompt",
    "message",
    "content",
    "rendered_text",
    "snippet",
    "snippets",
    "excerpt",
    "excerpts",
    "answer",
    "rationale",
    "clarify_question",
    "alternatives",
    "claims",
    "claim_text",
    "citation_text",
    "title",
    "tool_output",
    "query",
}

GRADE_KEYS = ["A", "B", "C", "D", "E", "UNKNOWN"]

MAX_DOMAIN_LENGTH = 80
MAX_DOMAINS = 20
MAX_ENV_LEN = 16
MAX_REASON_LEN = 64
MAX_VERSION_LEN = 32


@dataclass(frozen=True)
class ResearchTelemetryEvent:
    """Structure-only telemetry event."""
    research_signature: str
    tool_calls_count: int
    domains_used: List[str]
    grade_histogram: Dict[str, int]
    citation_coverage: Dict[str, Any]
    stop_reason: Optional[str]
    validator_failures: int
    downgrade_reason: Optional[str]
    env_mode: Optional[str] = None
    versions: Optional[Dict[str, str]] = None
    sandbox_caps: Optional[Dict[str, int]] = None
    counters: Optional[Dict[str, int]] = None


def _bound_string(value: Optional[str], max_len: int) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    return value[:max_len]


def _safe_int(value: Any) -> int:
    try:
        value_int = int(value)
        return value_int if value_int >= 0 else 0
    except Exception:
        return 0


def sanitize_event(event: Any) -> Any:
    """
    Recursively drop forbidden keys from dicts.
    
    Args:
        event: Event structure
    
    Returns:
        Sanitized structure with forbidden keys removed
    """
    if isinstance(event, dict):
        sanitized = {}
        for key, value in event.items():
            if key in FORBIDDEN_KEYS:
                continue
            sanitized_value = sanitize_event(value)
            sanitized[key] = sanitized_value
        return sanitized
    
    if isinstance(event, list):
        return [sanitize_event(item) for item in event]
    
    return event


def _collect_keys(event: Any, keys: set) -> None:
    if isinstance(event, dict):
        for key, value in event.items():
            keys.add(key)
            _collect_keys(value, keys)
    elif isinstance(event, list):
        for item in event:
            _collect_keys(item, keys)


def assert_no_text_leakage(event: dict, sentinels: List[str]) -> None:
    """
    Assert that no sentinel strings or forbidden keys appear in serialized event.
    
    Args:
        event: Telemetry event
        sentinels: List of sentinel strings
    """
    event_json = json.dumps(event, sort_keys=True, ensure_ascii=True)
    
    for sentinel in sentinels:
        assert sentinel not in event_json
    
    keys = set()
    _collect_keys(event, keys)
    
    for forbidden in FORBIDDEN_KEYS:
        assert forbidden not in keys


def normalize_domains(domains: List[str]) -> List[str]:
    """
    Normalize domains: lowercase, strip www., dedupe, sort, bound length.
    """
    normalized = []
    for domain in domains or []:
        if domain is None:
            continue
        domain = str(domain).strip().lower()
        if domain.startswith("www."):
            domain = domain[4:]
        if not domain:
            continue
        domain = domain[:MAX_DOMAIN_LENGTH]
        normalized.append(domain)
    
    unique = sorted(set(normalized))
    return unique[:MAX_DOMAINS]


def normalize_grade_histogram(histogram: Optional[Dict[str, Any]]) -> Dict[str, int]:
    """Ensure histogram has all keys and non-negative ints."""
    result = {key: 0 for key in GRADE_KEYS}
    if histogram:
        for key, value in histogram.items():
            if key in result:
                result[key] = _safe_int(value)
    return result


def normalize_citation_coverage(coverage: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Normalize citation coverage with deterministic ratio."""
    if coverage is None:
        coverage = {}
    
    claims_total = _safe_int(coverage.get("claims_total", 0))
    claims_required = _safe_int(coverage.get("claims_required", 0))
    claims_required_covered = _safe_int(coverage.get("claims_required_covered", 0))
    
    claims_required_uncovered = max(0, claims_required - claims_required_covered)
    claims_total = max(claims_total, claims_required)
    
    if claims_required > 0:
        coverage_ratio = round(claims_required_covered / claims_required, 3)
    else:
        coverage_ratio = 0.0
    
    return {
        "claims_total": claims_total,
        "claims_required": claims_required,
        "claims_required_covered": claims_required_covered,
        "claims_required_uncovered": claims_required_uncovered,
        "coverage_ratio_required": float(coverage_ratio),
    }


def normalize_versions(versions: Optional[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    if not versions:
        return None
    
    sanitized = {}
    for key, value in versions.items():
        key_str = _bound_string(key, MAX_VERSION_LEN)
        val_str = _bound_string(value, MAX_VERSION_LEN)
        if key_str and val_str:
            sanitized[key_str] = val_str
    
    return sanitized or None


def normalize_caps(caps: Optional[Dict[str, Any]]) -> Optional[Dict[str, int]]:
    if not caps:
        return None
    
    sanitized = {}
    for key, value in caps.items():
        key_str = _bound_string(key, MAX_VERSION_LEN)
        if not key_str:
            continue
        sanitized[key_str] = _safe_int(value)
    
    return sanitized or None


def normalize_counters(counters: Optional[Dict[str, Any]]) -> Optional[Dict[str, int]]:
    if not counters:
        return None
    
    sanitized = {}
    for key, value in counters.items():
        key_str = _bound_string(key, MAX_VERSION_LEN)
        if not key_str:
            continue
        sanitized[key_str] = _safe_int(value)
    
    return sanitized or None


def compute_research_signature(structure_pack: Dict[str, Any]) -> str:
    """
    Compute deterministic research signature from structure-only pack.
    
    Args:
        structure_pack: Structure-only dict (no raw text)
    
    Returns:
        SHA256 hex string
    """
    sanitized_pack = sanitize_event(structure_pack)
    canonical = json.dumps(sanitized_pack, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    hash_digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    return hash_digest


def build_research_telemetry_event(
    *,
    env_mode: Optional[str],
    tool_calls_count: int,
    domains_used: List[str],
    grade_histogram: Optional[Dict[str, Any]],
    citation_coverage: Optional[Dict[str, Any]],
    stop_reason: Optional[str],
    validator_failures: int = 0,
    downgrade_reason: Optional[str] = None,
    sandbox_caps: Optional[Dict[str, Any]] = None,
    versions: Optional[Dict[str, Any]] = None,
    counters: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Build structure-only research telemetry event.
    """
    env_mode_bounded = _bound_string(env_mode, MAX_ENV_LEN)
    stop_reason_bounded = _bound_string(stop_reason, MAX_REASON_LEN)
    downgrade_bounded = _bound_string(downgrade_reason, MAX_REASON_LEN)
    
    normalized_domains = normalize_domains(domains_used)
    normalized_histogram = normalize_grade_histogram(grade_histogram)
    normalized_coverage = normalize_citation_coverage(citation_coverage)
    normalized_versions = normalize_versions(versions)
    normalized_caps = normalize_caps(sandbox_caps)
    normalized_counters = normalize_counters(counters)
    
    structure_pack = {
        "tool_calls_count": _safe_int(tool_calls_count),
        "domains_used": normalized_domains,
        "grade_histogram": normalized_histogram,
        "citation_coverage": normalized_coverage,
        "stop_reason": stop_reason_bounded,
        "validator_failures": _safe_int(validator_failures),
        "downgrade_reason": downgrade_bounded,
        "env_mode": env_mode_bounded,
        "versions": normalized_versions,
        "sandbox_caps": normalized_caps,
        "counters": normalized_counters,
    }
    
    structure_pack = sanitize_event(structure_pack)
    
    research_signature = compute_research_signature(structure_pack)
    
    event = ResearchTelemetryEvent(
        research_signature=research_signature,
        tool_calls_count=structure_pack["tool_calls_count"],
        domains_used=structure_pack["domains_used"],
        grade_histogram=structure_pack["grade_histogram"],
        citation_coverage=structure_pack["citation_coverage"],
        stop_reason=structure_pack["stop_reason"],
        validator_failures=structure_pack["validator_failures"],
        downgrade_reason=structure_pack["downgrade_reason"],
        env_mode=structure_pack.get("env_mode"),
        versions=structure_pack.get("versions"),
        sandbox_caps=structure_pack.get("sandbox_caps"),
        counters=structure_pack.get("counters"),
    )
    
    event_dict = asdict(event)
    return sanitize_event(event_dict)
