"""
Phase 19 Import Compatibility Test

Regression test to ensure backwards compatibility with legacy memory imports.
This test verifies that service.py and other modules can import from backend.app.memory.
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def test_legacy_imports():
    """Test that legacy memory functions can be imported."""
    print("Test: Legacy imports from backend.app.memory")
    
    try:
        from backend.app.memory import (
            load_cognitive_style,
            save_cognitive_style,
            load_hypotheses,
            save_hypotheses,
            load_session_summary,
            save_session_summary,
            get_redis,
        )
        
        # Verify they are callable
        assert callable(load_cognitive_style), "load_cognitive_style should be callable"
        assert callable(save_cognitive_style), "save_cognitive_style should be callable"
        assert callable(load_hypotheses), "load_hypotheses should be callable"
        assert callable(save_hypotheses), "save_hypotheses should be callable"
        assert callable(load_session_summary), "load_session_summary should be callable"
        assert callable(save_session_summary), "save_session_summary should be callable"
        assert callable(get_redis), "get_redis should be callable"
        
        print("  ✓ All legacy functions imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_phase19_imports():
    """Test that Phase 19 memory schema and adapter can be imported."""
    print("Test: Phase 19 imports from backend.app.memory")
    
    try:
        from backend.app.memory import (
            MemoryFact,
            MemoryCategory,
            MemoryValueType,
            Provenance,
            ProvenanceType,
            validate_fact,
            sanitize_and_validate_fact,
            validate_fact_dict,
            MemoryWriteRequest,
            WriteResult,
            MemoryStore,
            write_memory,
            create_store,
            Tier,
            TierCaps,
            TIER_CAPS,
            ReasonCode,
        )
        
        # Verify key types
        assert MemoryFact is not None, "MemoryFact should be defined"
        assert MemoryCategory is not None, "MemoryCategory should be defined"
        assert callable(validate_fact), "validate_fact should be callable"
        assert callable(write_memory), "write_memory should be callable"
        
        print("  ✓ All Phase 19 types imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_service_import():
    """Test that backend.app.service can be imported (uses legacy memory)."""
    print("Test: Import backend.app.service")
    
    try:
        # This import will fail if memory imports are broken
        from backend.app import service
        
        assert hasattr(service, "ConversationService"), "ConversationService should be defined"
        
        print("  ✓ backend.app.service imported successfully")
        return True
    except ImportError as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_no_circular_imports():
    """Test that there are no circular import issues."""
    print("Test: No circular imports")
    
    try:
        # Import in different orders to catch circular imports
        import backend.app.memory
        import backend.app.memory.schema
        import backend.app.memory.adapter
        import backend.app.memory.legacy
        
        # Re-import to verify no issues
        from backend.app.memory import load_cognitive_style, MemoryFact
        
        print("  ✓ No circular import issues detected")
        return True
    except ImportError as e:
        print(f"  ✗ Circular import detected: {e}")
        return False


def run_all():
    """Run all import compatibility tests."""
    print("=" * 60)
    print("Phase 19 Import Compatibility Tests")
    print("=" * 60)
    print()
    
    results = []
    
    results.append(("Legacy imports", test_legacy_imports()))
    results.append(("Phase 19 imports", test_phase19_imports()))
    results.append(("Service import", test_service_import()))
    results.append(("No circular imports", test_no_circular_imports()))
    
    print()
    print("=" * 60)
    
    failed = [name for name, passed in results if not passed]
    
    if failed:
        print(f"FAILED: {', '.join(failed)}")
        print("=" * 60)
        sys.exit(1)
    else:
        print("ALL IMPORT COMPATIBILITY TESTS PASSED ✓")
        print("=" * 60)


if __name__ == "__main__":
    run_all()
