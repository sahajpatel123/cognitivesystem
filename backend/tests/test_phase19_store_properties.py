"""
Phase 19 Step 4: Memory Store Properties Tests

Self-check runner for memory store with append-only log and derived view.
CI-grade tests proving determinism, correctness, caps enforcement, and invariants.
"""

import json
import os
import sys
from dataclasses import asdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.app.memory.store import (
    MEMORY_STORE_VERSION,
    EventType,
    StoreCaps,
    MemoryEvent,
    FactAddedEvent,
    FactExpiredEvent,
    FactRevokedEvent,
    ActiveFactMeta,
    CurrentView,
    MemoryEventLogStore,
    MemoryStore,
    recompute_current_view,
    create_event_log_store,
    create_memory_store,
    create_fact_added_event,
    create_fact_expired_event,
    create_fact_revoked_event,
)
from backend.app.memory.schema import (
    MemoryFact,
    MemoryCategory,
    MemoryValueType,
    Provenance,
    ProvenanceType,
)


# ============================================================================
# HELPERS
# ============================================================================

def make_provenance(
    source_type: ProvenanceType = ProvenanceType.USER_EXPLICIT,
    source_id: str = "test_source_123",
    collected_at_ms: int = 1000000,
    citation_ids: list = None,
) -> Provenance:
    """Create a valid provenance for testing."""
    return Provenance(
        source_type=source_type,
        source_id=source_id,
        collected_at_ms=collected_at_ms,
        citation_ids=citation_ids or [],
    )


def make_fact(
    fact_id: str = "fact_001",
    category: MemoryCategory = MemoryCategory.PREFERENCES_CONSTRAINTS,
    key: str = "test_key",
    value_str: str = "test_value",
    confidence: float = 0.8,
    provenance: Provenance = None,
    created_at_ms: int = 1000000,
) -> MemoryFact:
    """Create a valid memory fact for testing."""
    if provenance is None:
        provenance = make_provenance(collected_at_ms=created_at_ms)
    return MemoryFact(
        fact_id=fact_id,
        category=category,
        key=key,
        value_type=MemoryValueType.STR,
        value_str=value_str,
        value_num=None,
        value_bool=None,
        value_list_str=None,
        confidence=confidence,
        provenance=provenance,
        created_at_ms=created_at_ms,
        expires_at_ms=None,
        tags=[],
    )


def view_to_canonical_json(view: CurrentView) -> str:
    """Convert CurrentView to canonical JSON for comparison."""
    # Extract serializable data
    data = {
        "active_fact_ids": sorted(view.active_facts.keys()),
        "dropped_due_to_caps": view.dropped_due_to_caps,
        "total_active": view.total_active,
        "per_category_active": dict(sorted(view.per_category_active.items())),
        "store_version": view.store_version,
        "error_code": view.error_code,
    }
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


# ============================================================================
# GATE 1: Deterministic Recomputation
# ============================================================================

class Gate1_DeterministicRecomputation:
    """Test deterministic recomputation from event log."""
    
    def test_recompute_20_times_identical(self):
        """Recompute 20 times with identical event list -> identical view."""
        scope_id = "test_scope"
        now_ms = 5000000
        caps = StoreCaps(max_facts_total=100, max_facts_per_category=25)
        
        # Build fixed event list
        events = []
        for i in range(5):
            fact = make_fact(
                fact_id=f"fact_{i:03d}",
                key=f"key_{i}",
                confidence=0.5 + i * 0.1,
            )
            event = create_fact_added_event(
                scope_id=scope_id,
                fact=fact,
                created_at_ms=1000000 + i * 1000,
                expires_at_ms=10000000,
            )
            events.append(event)
        
        # Recompute 20 times
        results = []
        for _ in range(20):
            view = recompute_current_view(events, now_ms, caps)
            results.append(view_to_canonical_json(view))
        
        first = results[0]
        for i, r in enumerate(results[1:], 1):
            assert r == first, f"Run {i}: view differs from first run"
    
    def test_different_now_ms_different_view(self):
        """Different now_ms can produce different views (expiry)."""
        scope_id = "test_scope"
        caps = StoreCaps()
        
        fact = make_fact(fact_id="fact_expiry")
        event = create_fact_added_event(
            scope_id=scope_id,
            fact=fact,
            created_at_ms=1000000,
            expires_at_ms=2000000,
        )
        events = [event]
        
        # Before expiry
        view1 = recompute_current_view(events, 1500000, caps)
        # After expiry
        view2 = recompute_current_view(events, 2500000, caps)
        
        assert view1.total_active == 1, "Should be active before expiry"
        assert view2.total_active == 0, "Should be expired after expiry"


# ============================================================================
# GATE 2: Derived View Correctness
# ============================================================================

class Gate2_DerivedViewCorrectness:
    """Test derived view correctness."""
    
    def test_fact_added_produces_active_fact(self):
        """FACT_ADDED produces active fact."""
        scope_id = "test_scope"
        caps = StoreCaps()
        
        fact = make_fact(fact_id="fact_active")
        event = create_fact_added_event(
            scope_id=scope_id,
            fact=fact,
            created_at_ms=1000000,
            expires_at_ms=10000000,
        )
        
        view = recompute_current_view([event], 5000000, caps)
        
        assert "fact_active" in view.active_facts, "Fact should be active"
        assert view.total_active == 1
    
    def test_derived_expiry_removes_fact(self):
        """expires_at_ms <= now_ms removes fact (derived expiry)."""
        scope_id = "test_scope"
        caps = StoreCaps()
        
        fact = make_fact(fact_id="fact_expire")
        event = create_fact_added_event(
            scope_id=scope_id,
            fact=fact,
            created_at_ms=1000000,
            expires_at_ms=2000000,
        )
        
        # now_ms == expires_at_ms (boundary)
        view = recompute_current_view([event], 2000000, caps)
        assert view.total_active == 0, "Fact should be expired at boundary"
        
        # now_ms > expires_at_ms
        view = recompute_current_view([event], 3000000, caps)
        assert view.total_active == 0, "Fact should be expired"
    
    def test_fact_expired_event_dominates(self):
        """FACT_EXPIRED event removes fact even if expires_at_ms in future."""
        scope_id = "test_scope"
        caps = StoreCaps()
        
        fact = make_fact(fact_id="fact_event_expire")
        add_event = create_fact_added_event(
            scope_id=scope_id,
            fact=fact,
            created_at_ms=1000000,
            expires_at_ms=10000000,  # Far future
        )
        expire_event = create_fact_expired_event(
            scope_id=scope_id,
            fact_id="fact_event_expire",
            created_at_ms=2000000,
            observed_at_ms=2000000,
        )
        
        # Without expire event
        view1 = recompute_current_view([add_event], 5000000, caps)
        assert view1.total_active == 1, "Should be active without expire event"
        
        # With expire event
        view2 = recompute_current_view([add_event, expire_event], 5000000, caps)
        assert view2.total_active == 0, "Expire event should dominate"
    
    def test_fact_revoked_removes_fact(self):
        """FACT_REVOKED removes fact (revocation dominates)."""
        scope_id = "test_scope"
        caps = StoreCaps()
        
        fact = make_fact(fact_id="fact_revoke")
        add_event = create_fact_added_event(
            scope_id=scope_id,
            fact=fact,
            created_at_ms=1000000,
            expires_at_ms=10000000,
        )
        revoke_event = create_fact_revoked_event(
            scope_id=scope_id,
            fact_id="fact_revoke",
            created_at_ms=2000000,
            reason_code="USER_REQUEST",
            revoked_at_ms=2000000,
        )
        
        view = recompute_current_view([add_event, revoke_event], 5000000, caps)
        assert view.total_active == 0, "Revoked fact should not be active"
    
    def test_revoke_then_readd(self):
        """Revoked fact can be re-added."""
        scope_id = "test_scope"
        caps = StoreCaps()
        
        fact1 = make_fact(fact_id="fact_readd", value_str="original")
        fact2 = make_fact(fact_id="fact_readd", value_str="updated")
        
        add_event1 = create_fact_added_event(
            scope_id=scope_id,
            fact=fact1,
            created_at_ms=1000000,
            expires_at_ms=10000000,
        )
        revoke_event = create_fact_revoked_event(
            scope_id=scope_id,
            fact_id="fact_readd",
            created_at_ms=2000000,
            reason_code="UPDATE",
            revoked_at_ms=2000000,
        )
        add_event2 = create_fact_added_event(
            scope_id=scope_id,
            fact=fact2,
            created_at_ms=3000000,
            expires_at_ms=10000000,
        )
        
        view = recompute_current_view([add_event1, revoke_event, add_event2], 5000000, caps)
        assert view.total_active == 1, "Re-added fact should be active"
        assert view.active_facts["fact_readd"].fact.value_str == "updated"


# ============================================================================
# GATE 3: Caps Enforcement Deterministic
# ============================================================================

class Gate3_CapsEnforcement:
    """Test caps enforcement is deterministic."""
    
    def test_per_category_cap_deterministic(self):
        """Per-category cap enforced deterministically."""
        scope_id = "test_scope"
        caps = StoreCaps(max_facts_total=100, max_facts_per_category=3)
        
        # Create 5 facts in same category with different confidence
        events = []
        for i in range(5):
            fact = make_fact(
                fact_id=f"cat_fact_{i:03d}",
                category=MemoryCategory.PREFERENCES_CONSTRAINTS,
                key=f"key_{i}",
                confidence=0.5 + i * 0.1,  # 0.5, 0.6, 0.7, 0.8, 0.9
            )
            event = create_fact_added_event(
                scope_id=scope_id,
                fact=fact,
                created_at_ms=1000000 + i * 1000,
                expires_at_ms=10000000,
            )
            events.append(event)
        
        # Recompute multiple times
        results = []
        for _ in range(20):
            view = recompute_current_view(events, 5000000, caps)
            results.append(view_to_canonical_json(view))
        
        # All results should be identical
        first = results[0]
        for i, r in enumerate(results[1:], 1):
            assert r == first, f"Run {i}: caps result differs"
        
        # Verify correct winners (highest confidence kept)
        view = recompute_current_view(events, 5000000, caps)
        assert view.total_active == 3, f"Expected 3 active, got {view.total_active}"
        # Highest confidence facts should be kept (0.9, 0.8, 0.7)
        assert "cat_fact_004" in view.active_facts, "Highest confidence should be kept"
        assert "cat_fact_003" in view.active_facts
        assert "cat_fact_002" in view.active_facts
    
    def test_total_cap_deterministic(self):
        """Total cap enforced deterministically across categories."""
        scope_id = "test_scope"
        caps = StoreCaps(max_facts_total=4, max_facts_per_category=10)
        
        # Create facts across categories
        events = []
        categories = [
            MemoryCategory.PREFERENCES_CONSTRAINTS,
            MemoryCategory.USER_GOALS,
            MemoryCategory.PROJECT_CONTEXT,
        ]
        for i, cat in enumerate(categories):
            for j in range(2):
                fact = make_fact(
                    fact_id=f"total_fact_{i}_{j}",
                    category=cat,
                    key=f"key_{i}_{j}",
                    confidence=0.5 + (i * 2 + j) * 0.05,
                )
                event = create_fact_added_event(
                    scope_id=scope_id,
                    fact=fact,
                    created_at_ms=1000000 + (i * 2 + j) * 1000,
                    expires_at_ms=10000000,
                )
                events.append(event)
        
        # Recompute multiple times
        results = []
        for _ in range(20):
            view = recompute_current_view(events, 5000000, caps)
            results.append(view_to_canonical_json(view))
        
        first = results[0]
        for i, r in enumerate(results[1:], 1):
            assert r == first, f"Run {i}: total cap result differs"
        
        view = recompute_current_view(events, 5000000, caps)
        assert view.total_active == 4, f"Expected 4 active, got {view.total_active}"
    
    def test_tie_break_uses_fact_id(self):
        """Tie-break uses fact_id lexicographically when other fields equal."""
        scope_id = "test_scope"
        caps = StoreCaps(max_facts_total=2, max_facts_per_category=10)
        
        # Create facts with identical priority fields except fact_id
        prov = make_provenance(collected_at_ms=1000000)
        events = []
        for fact_id in ["fact_c", "fact_a", "fact_b"]:
            fact = make_fact(
                fact_id=fact_id,
                key="same_key",
                confidence=0.8,
                provenance=prov,
            )
            event = create_fact_added_event(
                scope_id=scope_id,
                fact=fact,
                created_at_ms=1000000,
                expires_at_ms=10000000,
            )
            events.append(event)
        
        view = recompute_current_view(events, 5000000, caps)
        
        # fact_a and fact_b should be kept (lexicographically first)
        assert view.total_active == 2
        assert "fact_a" in view.active_facts, "fact_a should be kept (lex first)"
        assert "fact_b" in view.active_facts, "fact_b should be kept (lex second)"
        assert "fact_c" in view.dropped_due_to_caps, "fact_c should be dropped"


# ============================================================================
# GATE 4: Append-Only Invariants
# ============================================================================

class Gate4_AppendOnlyInvariants:
    """Test append-only invariants."""
    
    def test_read_events_returns_copy(self):
        """read_events returns a copy, not the internal list."""
        store = create_event_log_store()
        scope_id = "test_scope"
        
        fact = make_fact(fact_id="fact_copy")
        event = create_fact_added_event(
            scope_id=scope_id,
            fact=fact,
            created_at_ms=1000000,
            expires_at_ms=10000000,
        )
        store.append_event(scope_id, event)
        
        events1 = store.read_events(scope_id)
        events2 = store.read_events(scope_id)
        
        # Should be equal but not same object
        assert len(events1) == len(events2) == 1
        assert events1 is not events2, "read_events should return a copy"
    
    def test_appending_increases_length(self):
        """Appending events increases length."""
        store = create_event_log_store()
        scope_id = "test_scope"
        
        assert store.event_count(scope_id) == 0
        
        for i in range(5):
            fact = make_fact(fact_id=f"fact_{i}")
            event = create_fact_added_event(
                scope_id=scope_id,
                fact=fact,
                created_at_ms=1000000 + i * 1000,
                expires_at_ms=10000000,
            )
            store.append_event(scope_id, event)
            assert store.event_count(scope_id) == i + 1
    
    def test_duplicate_fact_added_rejected(self):
        """Duplicate FACT_ADDED for same fact_id is rejected (unless revoked)."""
        scope_id = "test_scope"
        caps = StoreCaps()
        
        fact1 = make_fact(fact_id="fact_dup", value_str="first")
        fact2 = make_fact(fact_id="fact_dup", value_str="second")
        
        event1 = create_fact_added_event(
            scope_id=scope_id,
            fact=fact1,
            created_at_ms=1000000,
            expires_at_ms=10000000,
        )
        event2 = create_fact_added_event(
            scope_id=scope_id,
            fact=fact2,
            created_at_ms=2000000,
            expires_at_ms=10000000,
        )
        
        view = recompute_current_view([event1, event2], 5000000, caps)
        
        # First add wins, second is ignored
        assert view.total_active == 1
        assert view.active_facts["fact_dup"].fact.value_str == "first"


# ============================================================================
# GATE 5: Fail-Closed
# ============================================================================

class Gate5_FailClosed:
    """Test fail-closed behavior."""
    
    def test_invalid_caps_returns_empty_view(self):
        """Invalid caps returns empty view with error."""
        events = []
        
        # Invalid: max_facts_total = 0
        caps = StoreCaps(max_facts_total=0, max_facts_per_category=10)
        view = recompute_current_view(events, 1000000, caps)
        
        assert view.total_active == 0
        assert view.error_code == "INVALID_CAPS"
    
    def test_invalid_caps_per_category_zero(self):
        """Invalid per-category cap returns empty view."""
        events = []
        caps = StoreCaps(max_facts_total=10, max_facts_per_category=0)
        view = recompute_current_view(events, 1000000, caps)
        
        assert view.error_code == "INVALID_CAPS"
    
    def test_caps_total_less_than_per_category_valid(self):
        """total < per_category is valid (total cap applies after per-category)."""
        scope_id = "test_scope"
        caps = StoreCaps(max_facts_total=5, max_facts_per_category=10)
        
        # Create some facts
        events = []
        for i in range(3):
            fact = make_fact(fact_id=f"fact_{i}")
            event = create_fact_added_event(scope_id, fact, 1000000, 10000000)
            events.append(event)
        
        view = recompute_current_view(events, 5000000, caps)
        
        assert view.error_code is None
        assert view.total_active == 3
    
    def test_empty_events_returns_empty_view(self):
        """Empty events list returns empty view (not error)."""
        caps = StoreCaps()
        view = recompute_current_view([], 1000000, caps)
        
        assert view.total_active == 0
        assert view.error_code is None


# ============================================================================
# GATE 6: No Forbidden Text
# ============================================================================

class Gate6_NoForbiddenText:
    """Test no forbidden text is stored."""
    
    def test_event_id_does_not_contain_raw_values(self):
        """Event ID is computed from structure, not raw values."""
        scope_id = "test_scope"
        
        # Create fact with sensitive value
        fact = make_fact(
            fact_id="fact_sensitive",
            value_str="SENSITIVE_USER_TEXT_123",
        )
        event = create_fact_added_event(
            scope_id=scope_id,
            fact=fact,
            created_at_ms=1000000,
            expires_at_ms=10000000,
        )
        
        # Event ID should not contain the raw value
        assert "SENSITIVE_USER_TEXT_123" not in event.event_id
        assert "SENSITIVE" not in event.event_id
    
    def test_view_serialization_uses_fact_ids_only(self):
        """View serialization uses fact IDs, not raw values."""
        scope_id = "test_scope"
        caps = StoreCaps()
        
        fact = make_fact(
            fact_id="fact_safe",
            value_str="SENSITIVE_TOOL_TEXT_456",
        )
        event = create_fact_added_event(
            scope_id=scope_id,
            fact=fact,
            created_at_ms=1000000,
            expires_at_ms=10000000,
        )
        
        view = recompute_current_view([event], 5000000, caps)
        json_str = view_to_canonical_json(view)
        
        # JSON should contain fact_id but not raw value
        assert "fact_safe" in json_str
        assert "SENSITIVE_TOOL_TEXT_456" not in json_str


# ============================================================================
# GATE 7: Compatibility with Adapter
# ============================================================================

class Gate7_AdapterCompatibility:
    """Test compatibility with existing adapter interface."""
    
    def test_memory_store_write_facts_with_expiry(self):
        """MemoryStore.write_facts_with_expiry works correctly."""
        store = create_memory_store("test_scope")
        
        fact = make_fact(fact_id="compat_fact")
        fact_ids = store.write_facts_with_expiry([fact], 10000000)
        
        assert fact_ids == ["compat_fact"]
        assert store.count(now_ms=5000000) == 1
    
    def test_memory_store_write_facts_legacy(self):
        """MemoryStore.write_facts (legacy) works correctly."""
        store = create_memory_store("test_scope")
        
        fact = make_fact(fact_id="legacy_fact")
        fact_ids = store.write_facts([fact], ttl_applied_ms=5000000, now_ms=1000000)
        
        assert fact_ids == ["legacy_fact"]
        # expires_at_ms = now_ms + ttl_applied_ms = 6000000
        assert store.count(now_ms=5000000) == 1  # Before expiry
        assert store.count(now_ms=7000000) == 0  # After expiry
    
    def test_memory_store_get_fact(self):
        """MemoryStore.get_fact works correctly."""
        store = create_memory_store("test_scope")
        
        fact = make_fact(fact_id="get_fact_test", value_str="test_value")
        store.write_facts_with_expiry([fact], 10000000)
        
        retrieved = store.get_fact("get_fact_test", now_ms=5000000)
        assert retrieved is not None
        assert retrieved.value_str == "test_value"
        
        # Non-existent fact
        assert store.get_fact("nonexistent", now_ms=5000000) is None


# ============================================================================
# GATE 8: Store Version
# ============================================================================

class Gate8_StoreVersion:
    """Test store version is always set."""
    
    def test_store_version_in_view(self):
        """store_version is always set in CurrentView."""
        caps = StoreCaps()
        
        # Empty view
        view1 = recompute_current_view([], 1000000, caps)
        assert view1.store_version == MEMORY_STORE_VERSION
        
        # With facts
        fact = make_fact(fact_id="version_fact")
        event = create_fact_added_event("scope", fact, 1000000, 10000000)
        view2 = recompute_current_view([event], 5000000, caps)
        assert view2.store_version == MEMORY_STORE_VERSION
        
        # With error
        bad_caps = StoreCaps(max_facts_total=0)
        view3 = recompute_current_view([], 1000000, bad_caps)
        assert view3.store_version == MEMORY_STORE_VERSION


# ============================================================================
# RUNNER
# ============================================================================

def run_all():
    """Run all tests."""
    print("=" * 60)
    print("Phase 19 Step 4: Memory Store Properties Tests")
    print("=" * 60)
    
    test_classes = [
        ("Gate 1: Deterministic Recomputation", Gate1_DeterministicRecomputation),
        ("Gate 2: Derived View Correctness", Gate2_DerivedViewCorrectness),
        ("Gate 3: Caps Enforcement", Gate3_CapsEnforcement),
        ("Gate 4: Append-Only Invariants", Gate4_AppendOnlyInvariants),
        ("Gate 5: Fail-Closed", Gate5_FailClosed),
        ("Gate 6: No Forbidden Text", Gate6_NoForbiddenText),
        ("Gate 7: Adapter Compatibility", Gate7_AdapterCompatibility),
        ("Gate 8: Store Version", Gate8_StoreVersion),
    ]
    
    failed = False
    for label, test_class in test_classes:
        print(f"\n{label}")
        instance = test_class()
        for method_name in sorted(dir(instance)):
            if method_name.startswith("test_"):
                try:
                    getattr(instance, method_name)()
                    print(f"  ✓ {method_name}")
                except AssertionError as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed = True
                except Exception as e:
                    print(f"  ✗ {method_name}: EXCEPTION: {e}")
                    failed = True
    
    print("\n" + "=" * 60)
    if failed:
        print("SOME TESTS FAILED ✗")
        sys.exit(1)
    else:
        print("ALL PHASE 19 STORE PROPERTIES TESTS PASSED ✓")
        print("=" * 60)


if __name__ == "__main__":
    run_all()
