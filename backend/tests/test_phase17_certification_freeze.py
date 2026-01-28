"""
Phase 17 Step 9: Certification Freeze Tests

Verifies that certification artifacts exist and contain required elements.
"""

import os


class TestCertificationArtifactsExist:
    """Verify certification documentation and tests are present."""
    
    def test_certification_doc_exists(self):
        """Certification document must exist."""
        cert_path = "docs/PHASE17_CERTIFICATION.md"
        assert os.path.exists(cert_path), f"Certification doc missing: {cert_path}"
    
    def test_contract_doc_exists(self):
        """Contract document must exist."""
        contract_path = "docs/PHASE17_DEEP_THINKING_CONTRACT.md"
        assert os.path.exists(contract_path), f"Contract doc missing: {contract_path}"
    
    def test_eval_gates_test_exists(self):
        """Eval gates test file must exist."""
        gates_path = "backend/tests/test_phase17_eval_gates.py"
        assert os.path.exists(gates_path), f"Eval gates test missing: {gates_path}"


class TestCertificationDocContent:
    """Verify certification document contains required sections."""
    
    def test_cert_version_present(self):
        """Certification doc must contain version string."""
        cert_path = "docs/PHASE17_CERTIFICATION.md"
        with open(cert_path, 'r') as f:
            content = f.read()
        
        assert "PHASE17_CERT_VERSION" in content, "Missing PHASE17_CERT_VERSION"
        assert "17.9.0" in content, "Missing version number"
    
    def test_invariants_section_present(self):
        """Certification doc must contain invariants section."""
        cert_path = "docs/PHASE17_CERTIFICATION.md"
        with open(cert_path, 'r') as f:
            content = f.read()
        
        required_sections = [
            "INVARIANTS",
            "Non-Agentic Invariant",
            "State Mutation Invariant",
            "Fail-Closed Ladder",
            "StopReasons Exhaustive",
            "Deterministic Replay",
            "Telemetry Signature",
        ]
        
        for section in required_sections:
            assert section in content, f"Missing section: {section}"
    
    def test_gates_section_present(self):
        """Certification doc must contain gates section."""
        cert_path = "docs/PHASE17_CERTIFICATION.md"
        with open(cert_path, 'r') as f:
            content = f.read()
        
        required_gates = [
            "Gate A: Deterministic Replay Gate",
            "Gate B: Two-Strikes Downgrade Gate",
            "Gate C: StopReason Contract Gate",
            "Gate D: Telemetry & Summary Safety Gate",
        ]
        
        for gate in required_gates:
            assert gate in content, f"Missing gate: {gate}"
    
    def test_stop_reasons_listed(self):
        """Certification doc must list StopReason codes."""
        cert_path = "docs/PHASE17_CERTIFICATION.md"
        with open(cert_path, 'r') as f:
            content = f.read()
        
        required_stop_reasons = [
            "SUCCESS_COMPLETED",
            "VALIDATION_FAIL",
            "BUDGET_EXHAUSTED",
            "TIMEOUT",
            "BREAKER_TRIPPED",
            "ENTITLEMENT_CAP",
        ]
        
        for sr in required_stop_reasons:
            assert sr in content, f"Missing StopReason: {sr}"
    
    def test_evidence_commands_present(self):
        """Certification doc must contain evidence commands."""
        cert_path = "docs/PHASE17_CERTIFICATION.md"
        with open(cert_path, 'r') as f:
            content = f.read()
        
        assert "EVIDENCE COMMANDS" in content or "Evidence Commands" in content
        assert "compileall" in content, "Missing compileall command"


class TestFrozenComponentsDocumented:
    """Verify frozen components are documented."""
    
    def test_frozen_components_section_exists(self):
        """Certification doc must list frozen components."""
        cert_path = "docs/PHASE17_CERTIFICATION.md"
        with open(cert_path, 'r') as f:
            content = f.read()
        
        assert "FROZEN" in content, "Missing FROZEN section"
        
        frozen_files = [
            "router.py",
            "engine.py",
            "validator.py",
            "schema.py",
            "telemetry.py",
        ]
        
        for file in frozen_files:
            assert file in content, f"Missing frozen file: {file}"


# Self-check runner for local verification
if __name__ == "__main__":
    print("Running Phase 17 Certification Freeze Checks...")
    print()
    
    # Test artifacts exist
    print("Checking certification artifacts...")
    test_artifacts = TestCertificationArtifactsExist()
    test_artifacts.test_certification_doc_exists()
    print("✓ Certification doc exists")
    test_artifacts.test_contract_doc_exists()
    print("✓ Contract doc exists")
    test_artifacts.test_eval_gates_test_exists()
    print("✓ Eval gates test exists")
    
    # Test certification content
    print("\nChecking certification doc content...")
    test_content = TestCertificationDocContent()
    test_content.test_cert_version_present()
    print("✓ Cert version present")
    test_content.test_invariants_section_present()
    print("✓ Invariants section present")
    test_content.test_gates_section_present()
    print("✓ Gates section present")
    test_content.test_stop_reasons_listed()
    print("✓ StopReasons listed")
    test_content.test_evidence_commands_present()
    print("✓ Evidence commands present")
    
    # Test frozen components
    print("\nChecking frozen components documentation...")
    test_frozen = TestFrozenComponentsDocumented()
    test_frozen.test_frozen_components_section_exists()
    print("✓ Frozen components documented")
    
    print("\n" + "="*60)
    print("ALL CERTIFICATION FREEZE CHECKS PASSED ✓")
    print("="*60)
