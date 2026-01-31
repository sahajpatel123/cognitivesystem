#!/usr/bin/env python3
"""
Phase 20 Step 7: Region Modes Tests

Self-contained test runner for compliance region modes with deterministic
capability clamping and fail-closed behavior.
"""

import sys
import os
import json
import random
from typing import Dict, Any, List

# Add backend to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from backend.app.governance.regions import (
    RegionMode, TelemetryLevel, RegionReasonCode,
    ResolvedRegionCaps, parse_region_mode, canonicalize_domain,
    clamp_tools, clamp_telemetry, resolve_region_caps,
    assert_no_text_leakage
)
from backend.app.governance.tenant import TenantConfig, PlanTier, FeatureFlag, ToolKind, ResolvedTenantCaps


# ============================================================================
# TEST CONSTANTS
# ============================================================================

# Sentinel string for leakage testing
SENTINEL = "SENSITIVE_USER_TEXT_123"
SENTINEL_2 = "SECRET_REGION_456"
SENTINEL_3 = "PRIVATE_DOMAIN_789"

SENTINEL_STRINGS = [SENTINEL, SENTINEL_2, SENTINEL_3]


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def assert_equal(actual, expected, msg=""):
    """Assert equality with descriptive error."""
    if actual != expected:
        raise AssertionError(f"Expected {expected}, got {actual}. {msg}")


def assert_true(condition, msg=""):
    """Assert condition is true."""
    if not condition:
        raise AssertionError(f"Expected True, got False. {msg}")


def assert_false(condition, msg=""):
    """Assert condition is false."""
    if condition:
        raise AssertionError(f"Expected False, got True. {msg}")


def assert_in(item, container, msg=""):
    """Assert item is in container."""
    if item not in container:
        raise AssertionError(f"Expected {item} in {container}. {msg}")


def assert_not_in(item, container, msg=""):
    """Assert item is not in container."""
    if item in container:
        raise AssertionError(f"Expected {item} not in {container}. {msg}")


def check_no_sentinel_leakage(data: Any, context: str = ""):
    """Check that no sentinel strings appear in serialized data."""
    serialized = json.dumps(data) if not isinstance(data, str) else data
    for sentinel in SENTINEL_STRINGS:
        if sentinel in serialized:
            raise AssertionError(f"Sentinel string '{sentinel}' found in {context}: {serialized}")


def create_test_tenant_caps(tools: List[ToolKind] = None, export_allowed: bool = True) -> ResolvedTenantCaps:
    """Create test tenant capabilities."""
    if tools is None:
        tools = [ToolKind.WEB, ToolKind.DOCS]
    
    from backend.app.governance.tenant import TTLClassLabel
    
    return ResolvedTenantCaps(
        tenant_id="test-tenant",
        plan=PlanTier.ENTERPRISE,
        research_allowed=True,
        allowed_tools=tuple(tools),
        deepthink_max_passes=3,
        memory_ttl_cap=TTLClassLabel.TTL_1H,
        memory_max_facts_per_request=100,
        export_allowed=export_allowed,
        stop_reasons=(),
        clamp_notes=()
    )


# ============================================================================
# TEST GROUPS
# ============================================================================

def test_unknown_region_strict():
    """Test A: Unknown region → STRICT (fail-closed)."""
    print("Test A: Unknown region → STRICT")
    
    tenant_caps = create_test_tenant_caps()
    
    # Test unknown string region
    resolved = resolve_region_caps(tenant_caps, "MARS")
    
    assert_equal(resolved.region_mode, RegionMode.STRICT, "Unknown region should map to STRICT")
    assert_in(RegionReasonCode.REGION_UNKNOWN_FAIL_CLOSED.value, resolved.clamp_notes, 
             "Should have REGION_UNKNOWN_FAIL_CLOSED in clamp notes")
    
    # STRICT should be most restrictive
    assert_equal(resolved.effective_allowed_tools, [], "STRICT should allow no tools")
    assert_equal(resolved.telemetry_level_cap, TelemetryLevel.OFF, "STRICT should have OFF telemetry")
    assert_false(resolved.export_allowed, "STRICT should deny export")
    assert_equal(resolved.allowed_domains, [], "STRICT should allow no domains")
    
    print("✓ Test A: Unknown region → STRICT")


def test_none_empty_region_strict():
    """Test B: None/"" region → STRICT."""
    print("Test B: None/empty region → STRICT")
    
    tenant_caps = create_test_tenant_caps()
    
    # Test None region
    resolved_none = resolve_region_caps(tenant_caps, None)
    assert_equal(resolved_none.region_mode, RegionMode.STRICT, "None region should map to STRICT")
    assert_in(RegionReasonCode.REGION_UNKNOWN_FAIL_CLOSED.value, resolved_none.clamp_notes, 
             "Should have REGION_UNKNOWN_FAIL_CLOSED for None")
    
    # Test empty string region
    resolved_empty = resolve_region_caps(tenant_caps, "")
    assert_equal(resolved_empty.region_mode, RegionMode.STRICT, "Empty region should map to STRICT")
    assert_in(RegionReasonCode.REGION_UNKNOWN_FAIL_CLOSED.value, resolved_empty.clamp_notes, 
             "Should have REGION_UNKNOWN_FAIL_CLOSED for empty")
    
    # Test invalid type
    resolved_invalid = resolve_region_caps(tenant_caps, 123)
    assert_equal(resolved_invalid.region_mode, RegionMode.STRICT, "Invalid type should map to STRICT")
    assert_in(RegionReasonCode.REGION_INVALID_FAIL_CLOSED.value, resolved_invalid.clamp_notes, 
             "Should have REGION_INVALID_FAIL_CLOSED for invalid type")
    
    print("✓ Test B: None/empty region → STRICT")


def test_requested_flags_cannot_override():
    """Test C: Requested flags cannot override region caps."""
    print("Test C: Requested flags cannot override region caps")
    
    tenant_caps = create_test_tenant_caps()
    
    # EU region caps telemetry to MINIMAL, request DEBUG
    request_hints = {"telemetry_level": "DEBUG"}
    resolved = resolve_region_caps(tenant_caps, "EU", request_hints)
    
    assert_equal(resolved.region_mode, RegionMode.EU, "Should resolve to EU")
    assert_equal(resolved.telemetry_level_cap, TelemetryLevel.MINIMAL, 
                "Should be clamped to EU cap (MINIMAL), not requested DEBUG")
    assert_in(RegionReasonCode.TELEMETRY_CLAMPED_BY_REGION.value, resolved.clamp_notes,
             "Should have telemetry clamping note")
    
    # Test with STRICT region (most restrictive)
    resolved_strict = resolve_region_caps(tenant_caps, "STRICT", request_hints)
    assert_equal(resolved_strict.telemetry_level_cap, TelemetryLevel.OFF, 
                "STRICT should override any request to OFF")
    
    print("✓ Test C: Requested flags cannot override region caps")


def test_region_cannot_expand_tenant_caps():
    """Test D: Region cannot expand tenant caps."""
    print("Test D: Region cannot expand tenant caps")
    
    # Create tenant with no tools
    tenant_no_tools = create_test_tenant_caps(tools=[])
    
    # US region allows WEB and DOCS, but tenant allows none
    resolved = resolve_region_caps(tenant_no_tools, "US")
    
    assert_equal(resolved.effective_allowed_tools, [], 
                "Region cannot expand tenant tools (tenant has none)")
    
    # Create tenant with only DOCS
    tenant_docs_only = create_test_tenant_caps(tools=[ToolKind.DOCS])
    
    # STRICT region allows no tools, tenant allows DOCS
    resolved_strict = resolve_region_caps(tenant_docs_only, "STRICT")
    
    assert_equal(resolved_strict.effective_allowed_tools, [], 
                "STRICT region should deny all tools even if tenant allows")
    assert_in(RegionReasonCode.TOOLS_CLAMPED_BY_REGION.value, resolved_strict.clamp_notes,
             "Should have tools clamping note")
    
    print("✓ Test D: Region cannot expand tenant caps")


def test_export_clamping():
    """Test E: Export clamping."""
    print("Test E: Export clamping")
    
    # Tenant allows export, EU region denies
    tenant_export = create_test_tenant_caps(export_allowed=True)
    resolved_eu = resolve_region_caps(tenant_export, "EU")
    
    assert_false(resolved_eu.export_allowed, "EU should deny export even if tenant allows")
    assert_in(RegionReasonCode.EXPORT_DENIED_BY_REGION.value, resolved_eu.clamp_notes,
             "Should have export denial note")
    
    # Tenant allows export, US region allows
    resolved_us = resolve_region_caps(tenant_export, "US")
    assert_true(resolved_us.export_allowed, "US should allow export when tenant allows")
    
    # Tenant denies export, US region allows - should still be denied
    tenant_no_export = create_test_tenant_caps(export_allowed=False)
    resolved_us_no_tenant = resolve_region_caps(tenant_no_export, "US")
    assert_false(resolved_us_no_tenant.export_allowed, 
                "Should be denied when tenant denies, even if region allows")
    
    print("✓ Test E: Export clamping")


def test_domain_canonicalization():
    """Test F: Domain canonicalization & bounding."""
    print("Test F: Domain canonicalization")
    
    # Test canonicalize_domain function directly
    assert_equal(canonicalize_domain("WWW.Example.COM"), "example.com", 
                "Should canonicalize to lowercase and remove www")
    
    assert_equal(canonicalize_domain("  test.org  "), "test.org", 
                "Should trim whitespace")
    
    # Test rejection of URLs
    assert_equal(canonicalize_domain("https://example.com/path"), None, 
                "Should reject URLs with protocol")
    
    assert_equal(canonicalize_domain("example.com/path?query=1"), None, 
                "Should reject URLs with path/query")
    
    # Test invalid domains
    assert_equal(canonicalize_domain("invalid"), None, 
                "Should reject invalid domain format")
    
    assert_equal(canonicalize_domain(""), None, 
                "Should reject empty string")
    
    # Test sentinel rejection
    assert_equal(canonicalize_domain(f"evil{SENTINEL}.com"), None, 
                "Should reject domains with sentinel patterns")
    
    print("✓ Test F: Domain canonicalization")


def test_sentinel_leakage_gate():
    """Test G: Sentinel leakage gate."""
    print("Test G: Sentinel leakage gate")
    
    tenant_caps = create_test_tenant_caps()
    
    # Test sentinel in region_mode
    resolved_sentinel_region = resolve_region_caps(tenant_caps, SENTINEL)
    
    # Check resolved object contains no sentinels
    resolved_json = json.dumps({
        "region_mode": resolved_sentinel_region.region_mode.value,
        "effective_allowed_tools": resolved_sentinel_region.effective_allowed_tools,
        "telemetry_level_cap": resolved_sentinel_region.telemetry_level_cap.value,
        "export_allowed": resolved_sentinel_region.export_allowed,
        "allowed_domains": resolved_sentinel_region.allowed_domains,
        "clamp_notes": resolved_sentinel_region.clamp_notes,
        "signature": resolved_sentinel_region.signature,
    })
    
    check_no_sentinel_leakage(resolved_json, "resolved region caps JSON")
    
    # Use the helper function
    assert_no_text_leakage(resolved_json, SENTINEL_STRINGS)
    
    # Test with sentinel in request hints
    malicious_hints = {
        "telemetry_level": "DEBUG",
        "user_prompt": SENTINEL_2,  # Should be ignored
        "domain_list": [f"evil{SENTINEL_3}.com"],  # Should be sanitized
    }
    
    resolved_hints = resolve_region_caps(tenant_caps, "US", malicious_hints)
    resolved_hints_json = json.dumps({
        "region_mode": resolved_hints.region_mode.value,
        "effective_allowed_tools": resolved_hints.effective_allowed_tools,
        "telemetry_level_cap": resolved_hints.telemetry_level_cap.value,
        "export_allowed": resolved_hints.export_allowed,
        "allowed_domains": resolved_hints.allowed_domains,
        "clamp_notes": resolved_hints.clamp_notes,
        "signature": resolved_hints.signature,
    })
    
    check_no_sentinel_leakage(resolved_hints_json, "resolved caps with malicious hints")
    
    print("✓ Test G: Sentinel leakage gate")


def test_determinism_replay():
    """Test H: Determinism replay 20x."""
    print("Test H: Determinism replay 20x")
    
    tenant_caps = create_test_tenant_caps()
    
    # Create base request hints with shuffleable order
    base_hints = {
        "telemetry_level": "STANDARD",
        "priority": "high",
        "source": "test",
        "batch_size": 10,
    }
    
    signatures = []
    serialized_caps = []
    
    for i in range(20):
        # Shuffle dict order
        shuffled_hints = {}
        keys = list(base_hints.keys())
        random.seed(i)  # Deterministic shuffle
        random.shuffle(keys)
        for key in keys:
            shuffled_hints[key] = base_hints[key]
        
        resolved = resolve_region_caps(tenant_caps, "IN", shuffled_hints)
        
        signatures.append(resolved.signature)
        serialized_caps.append(json.dumps({
            "region_mode": resolved.region_mode.value,
            "effective_allowed_tools": resolved.effective_allowed_tools,
            "telemetry_level_cap": resolved.telemetry_level_cap.value,
            "export_allowed": resolved.export_allowed,
            "allowed_domains": resolved.allowed_domains,
            "clamp_notes": resolved.clamp_notes,
        }, sort_keys=True))
    
    # All signatures should be identical
    first_signature = signatures[0]
    first_serialized = serialized_caps[0]
    
    for i, (signature, serialized) in enumerate(zip(signatures[1:], serialized_caps[1:]), 1):
        assert_equal(signature, first_signature, f"Signature differs on iteration {i+1}")
        assert_equal(serialized, first_serialized, f"Serialization differs on iteration {i+1}")
    
    print("✓ Test H: Determinism replay 20x")


def test_stable_ordering():
    """Test I: Stable ordering of tools/domains/notes."""
    print("Test I: Stable ordering")
    
    # Create tenant with tools in different order
    tenant_caps_1 = create_test_tenant_caps(tools=[ToolKind.WEB, ToolKind.DOCS])
    tenant_caps_2 = create_test_tenant_caps(tools=[ToolKind.DOCS, ToolKind.WEB])
    
    resolved_1 = resolve_region_caps(tenant_caps_1, "US")
    resolved_2 = resolve_region_caps(tenant_caps_2, "US")
    
    # Tools should be in same order regardless of input order
    assert_equal(resolved_1.effective_allowed_tools, resolved_2.effective_allowed_tools,
                "Tool ordering should be deterministic regardless of input order")
    
    # Tools should be alphabetically sorted
    expected_tools = sorted([ToolKind.WEB.value, ToolKind.DOCS.value])
    assert_equal(resolved_1.effective_allowed_tools, expected_tools,
                "Tools should be alphabetically sorted")
    
    # Clamp notes should be sorted
    # Create a scenario that generates multiple clamp notes
    tenant_export = create_test_tenant_caps(export_allowed=True)
    request_hints = {"telemetry_level": "DEBUG"}
    resolved_multi_clamps = resolve_region_caps(tenant_export, "EU", request_hints)
    
    # Check that clamp notes are sorted
    sorted_notes = sorted(resolved_multi_clamps.clamp_notes)
    assert_equal(resolved_multi_clamps.clamp_notes, sorted_notes,
                "Clamp notes should be sorted")
    
    print("✓ Test I: Stable ordering")


def test_region_mode_mappings():
    """Test J: Region mode capability mappings."""
    print("Test J: Region mode mappings")
    
    tenant_caps = create_test_tenant_caps(tools=[ToolKind.WEB, ToolKind.DOCS], export_allowed=True)
    
    # Test STRICT (most restrictive)
    resolved_strict = resolve_region_caps(tenant_caps, "STRICT")
    assert_equal(resolved_strict.effective_allowed_tools, [], "STRICT should allow no tools")
    assert_equal(resolved_strict.telemetry_level_cap, TelemetryLevel.OFF, "STRICT should have OFF telemetry")
    assert_false(resolved_strict.export_allowed, "STRICT should deny export")
    
    # Test EU (GDPR compliance)
    resolved_eu = resolve_region_caps(tenant_caps, "EU")
    assert_equal(resolved_eu.effective_allowed_tools, ["DOCS"], "EU should allow only DOCS")
    assert_equal(resolved_eu.telemetry_level_cap, TelemetryLevel.MINIMAL, "EU should have MINIMAL telemetry")
    assert_false(resolved_eu.export_allowed, "EU should deny export (GDPR)")
    
    # Test IN (moderate restrictions)
    resolved_in = resolve_region_caps(tenant_caps, "IN")
    expected_in_tools = sorted([ToolKind.WEB.value, ToolKind.DOCS.value])
    assert_equal(resolved_in.effective_allowed_tools, expected_in_tools, "IN should allow WEB and DOCS")
    assert_equal(resolved_in.telemetry_level_cap, TelemetryLevel.STANDARD, "IN should have STANDARD telemetry")
    assert_true(resolved_in.export_allowed, "IN should allow export")
    
    # Test US (least restrictive)
    resolved_us = resolve_region_caps(tenant_caps, "US")
    expected_us_tools = sorted([ToolKind.WEB.value, ToolKind.DOCS.value])
    assert_equal(resolved_us.effective_allowed_tools, expected_us_tools, "US should allow WEB and DOCS")
    assert_equal(resolved_us.telemetry_level_cap, TelemetryLevel.DEBUG, "US should have DEBUG telemetry")
    assert_true(resolved_us.export_allowed, "US should allow export")
    
    print("✓ Test J: Region mode mappings")


# ============================================================================
# TEST RUNNER
# ============================================================================

def run_all() -> bool:
    """Run all tests and return success status."""
    try:
        print("Running Phase 20 Region Modes Tests...")
        print()
        
        test_unknown_region_strict()
        test_none_empty_region_strict()
        test_requested_flags_cannot_override()
        test_region_cannot_expand_tenant_caps()
        test_export_clamping()
        test_domain_canonicalization()
        test_sentinel_leakage_gate()
        test_determinism_replay()
        test_stable_ordering()
        test_region_mode_mappings()
        
        print()
        print("ALL PHASE 20 REGION MODES TESTS PASSED ✓")
        return True
        
    except Exception as e:
        print(f"✗ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all()
    sys.exit(0 if success else 1)
