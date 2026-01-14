PYTHON ?= python
PYTEST ?= $(PYTHON) -m pytest

# Phase 14 backend suites
PHASE14_BACKEND_FAST_FILES = \
	backend/tests/test_phase14_e2e_adversarial_pipeline.py \
	backend/tests/test_phase14_unit_adversarial_phase9.py \
	backend/tests/test_phase14_unit_adversarial_phase10.py \
	backend/tests/test_phase14_unit_adversarial_phase11.py \
	backend/tests/test_phase14_unit_adversarial_phase12_schema_verify.py \
	backend/tests/test_phase14_integration_adversarial_pipeline.py \
	backend/tests/test_phase14_determinism.py

PHASE14_BACKEND_FULL_FILES = $(PHASE14_BACKEND_FAST_FILES) \
	backend/tests/test_phase11_expression_abuse.py \
	backend/tests/test_phase12_model_governance_abuse.py \
	backend/tests/test_phase12_model_output_schema.py \
	backend/tests/test_phase12_model_output_verify.py \
	backend/tests/test_phase12_fallback_rendering.py \
	backend/tests/test_phase12_invocation_pipeline.py \
	backend/tests/test_phase12_orchestrator.py \
	backend/tests/test_phase12_prompt_builder.py \
	backend/tests/test_phase12_model_runtime.py \
	backend/tests/test_phase13_chat_api_contract.py

.PHONY: test\:phase14\:backend\:fast
test\:phase14\:backend\:fast:
	$(PYTEST) $(PHASE14_BACKEND_FAST_FILES)

.PHONY: test\:phase14\:backend\:full
test\:phase14\:backend\:full:
	$(PYTEST) $(PHASE14_BACKEND_FULL_FILES)

.PHONY: test\:phase14\:ui\:phase13
test\:phase14\:ui\:phase13:
	cd frontend && npm run test:ui:phase13

.PHONY: test\:phase14\:ui\:phase14
test\:phase14\:ui\:phase14:
	cd frontend && npm run test:ui:phase14

.PHONY: test\:phase14\:ui\:full
test\:phase14\:ui\:full:
	cd frontend && npm run test:ui:full

.PHONY: test\:phase14\:all
test\:phase14\:all: test\:phase14\:backend\:fast test\:phase14\:ui\:phase14
