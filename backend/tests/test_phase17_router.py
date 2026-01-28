"""
Phase 17 Step 1: Router Unit Tests

Tests for deterministic pass router.
All tests must be fast, deterministic, and require no network.
"""

import pytest
from backend.app.deepthink.router import (
    RouterInput,
    Plan,
    build_plan,
    StopReason,
    MIN_PASS_TIMEOUT_MS,
    MIN_BUDGET_PER_PASS,
)


class TestDeterminism:
    """Test that router is deterministic."""
    
    def test_identical_inputs_produce_identical_plans(self):
        """Same RouterInput repeated 50 times -> identical Plan."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            breaker_tripped=False,
            total_budget_units=300,
            total_timeout_ms=3000,
            abuse_blocked=False,
        )
        
        plans = [build_plan(router_input) for _ in range(50)]
        
        # All plans should be identical
        first_plan = plans[0]
        for plan in plans[1:]:
            assert plan.effective_pass_count == first_plan.effective_pass_count
            assert plan.pass_plan == first_plan.pass_plan
            assert plan.per_pass_budget == first_plan.per_pass_budget
            assert plan.per_pass_timeout_ms == first_plan.per_pass_timeout_ms
            assert plan.stop_reason == first_plan.stop_reason
            assert plan.policy == first_plan.policy


class TestEntitlementCap:
    """Test entitlement-based blocking."""
    
    def test_free_tier_blocks_deepthink(self):
        """FREE tier -> effective_pass_count=0, stop_reason=ENTITLEMENT_CAP."""
        router_input = RouterInput(
            entitlement_tier="FREE",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 0
        assert plan.pass_plan == []
        assert plan.stop_reason == StopReason.ENTITLEMENT_CAP.value
    
    def test_pro_tier_max_3_passes(self):
        """PRO tier requested deep -> pass_count <= 3, never 5."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_budget_units=10000,  # Huge budget
            total_timeout_ms=10000,  # Huge timeout
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count <= 3
        assert plan.effective_pass_count > 0
        assert plan.stop_reason is None  # Deepthink enabled
    
    def test_max_tier_max_5_passes(self):
        """MAX tier -> pass_count <= 5."""
        router_input = RouterInput(
            entitlement_tier="MAX",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_budget_units=10000,
            total_timeout_ms=10000,
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count <= 5
        assert plan.effective_pass_count > 0
        assert plan.stop_reason is None
    
    def test_deepthink_disabled_flag(self):
        """deepthink_enabled=False -> disabled."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=False,
            env_mode="prod",
            requested_mode="deep",
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 0
        assert plan.stop_reason == StopReason.ENTITLEMENT_CAP.value


class TestRequestedModeCannotOverrideCaps:
    """Test that requested mode cannot override tier caps."""
    
    def test_pro_requested_deep_huge_budget_still_3_passes(self):
        """PRO + requested deep + huge budget -> still 3 passes max."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_budget_units=100000,
            total_timeout_ms=100000,
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 3  # Tier cap
        assert plan.stop_reason is None


class TestBreakerTripped:
    """Test breaker blocking."""
    
    def test_breaker_tripped_blocks_deepthink(self):
        """PRO + requested deep + breaker_tripped=True -> disabled, BREAKER_TRIPPED."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            breaker_tripped=True,
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 0
        assert plan.stop_reason == StopReason.BREAKER_TRIPPED.value


class TestTimeoutClamp:
    """Test timeout-based pass count reduction."""
    
    def test_timeout_allows_exactly_2_passes(self):
        """PRO tier cap 3, total_timeout_ms = 2*MIN_PASS_TIMEOUT_MS -> 2 passes."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_timeout_ms=2 * MIN_PASS_TIMEOUT_MS,
            total_budget_units=10000,  # Plenty of budget
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 2
        assert plan.stop_reason is None
    
    def test_timeout_below_2_passes_disables(self):
        """total_timeout_ms just below 2*MIN_PASS_TIMEOUT_MS -> disabled, BUDGET_EXHAUSTED."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_timeout_ms=2 * MIN_PASS_TIMEOUT_MS - 1,
            total_budget_units=10000,
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 0
        assert plan.stop_reason == StopReason.BUDGET_EXHAUSTED.value


class TestBudgetClamp:
    """Test budget-based pass count reduction."""
    
    def test_budget_allows_exactly_2_passes(self):
        """MAX tier cap 5, total_budget_units = 2*MIN_BUDGET_PER_PASS -> 2 passes."""
        router_input = RouterInput(
            entitlement_tier="MAX",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_budget_units=2 * MIN_BUDGET_PER_PASS,
            total_timeout_ms=10000,  # Plenty of timeout
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 2
        assert plan.stop_reason is None
    
    def test_budget_below_2_passes_disables(self):
        """total_budget_units < 2*MIN_BUDGET_PER_PASS -> disabled, BUDGET_EXHAUSTED."""
        router_input = RouterInput(
            entitlement_tier="MAX",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_budget_units=2 * MIN_BUDGET_PER_PASS - 1,
            total_timeout_ms=10000,
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 0
        assert plan.stop_reason == StopReason.BUDGET_EXHAUSTED.value


class TestPassPlanTemplateOrdering:
    """Test that pass plan templates are correct and ordered."""
    
    def test_2_passes_template(self):
        """2 passes -> [REFINE, STRESS_TEST]."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_timeout_ms=2 * MIN_PASS_TIMEOUT_MS,
            total_budget_units=2 * MIN_BUDGET_PER_PASS,
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 2
        assert plan.pass_plan == ["REFINE", "STRESS_TEST"]
    
    def test_3_passes_template(self):
        """3 passes -> [REFINE, COUNTERARG, STRESS_TEST]."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_timeout_ms=10000,
            total_budget_units=10000,
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 3
        assert plan.pass_plan == ["REFINE", "COUNTERARG", "STRESS_TEST"]
    
    def test_4_passes_template(self):
        """4 passes -> [REFINE, COUNTERARG, ALTERNATIVES, STRESS_TEST]."""
        router_input = RouterInput(
            entitlement_tier="MAX",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_timeout_ms=4 * MIN_PASS_TIMEOUT_MS,
            total_budget_units=4 * MIN_BUDGET_PER_PASS,
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 4
        assert plan.pass_plan == ["REFINE", "COUNTERARG", "ALTERNATIVES", "STRESS_TEST"]
    
    def test_5_passes_template(self):
        """5 passes -> [REFINE, COUNTERARG, STRESS_TEST, ALTERNATIVES, REGRET]."""
        router_input = RouterInput(
            entitlement_tier="MAX",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_timeout_ms=10000,
            total_budget_units=10000,
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 5
        assert plan.pass_plan == ["REFINE", "COUNTERARG", "STRESS_TEST", "ALTERNATIVES", "REGRET"]


class TestAllocationProperties:
    """Test resource allocation properties."""
    
    def test_timeout_sum_equals_total(self):
        """sum(per_pass_timeout_ms) == total_timeout_ms used."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_timeout_ms=3000,
            total_budget_units=300,
        )
        
        plan = build_plan(router_input)
        
        assert sum(plan.per_pass_timeout_ms) == 3000
    
    def test_budget_sum_equals_total(self):
        """sum(per_pass_budget) == total_budget_units used."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_timeout_ms=3000,
            total_budget_units=300,
        )
        
        plan = build_plan(router_input)
        
        assert sum(plan.per_pass_budget) == 300
    
    def test_each_timeout_gte_min(self):
        """Each per_pass_timeout_ms >= MIN_PASS_TIMEOUT_MS."""
        router_input = RouterInput(
            entitlement_tier="MAX",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_timeout_ms=6000,
            total_budget_units=600,
        )
        
        plan = build_plan(router_input)
        
        for timeout in plan.per_pass_timeout_ms:
            assert timeout >= MIN_PASS_TIMEOUT_MS
    
    def test_each_budget_gte_min(self):
        """Each per_pass_budget >= MIN_BUDGET_PER_PASS."""
        router_input = RouterInput(
            entitlement_tier="MAX",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_timeout_ms=6000,
            total_budget_units=600,
        )
        
        plan = build_plan(router_input)
        
        for budget in plan.per_pass_budget:
            assert budget >= MIN_BUDGET_PER_PASS


class TestStopReasonMapping:
    """Test that stop reasons are valid and mapped."""
    
    def test_no_unknown_stop_reason(self):
        """Router never returns unknown stop_reason."""
        test_cases = [
            RouterInput(entitlement_tier="FREE", deepthink_enabled=True, env_mode="prod", requested_mode="deep"),
            RouterInput(entitlement_tier="PRO", deepthink_enabled=False, env_mode="prod", requested_mode="deep"),
            RouterInput(entitlement_tier="PRO", deepthink_enabled=True, env_mode="prod", requested_mode="baseline"),
            RouterInput(entitlement_tier="PRO", deepthink_enabled=True, env_mode="prod", requested_mode="deep", breaker_tripped=True),
            RouterInput(entitlement_tier="PRO", deepthink_enabled=True, env_mode="prod", requested_mode="deep", abuse_blocked=True),
            RouterInput(entitlement_tier="PRO", deepthink_enabled=True, env_mode="prod", requested_mode="deep", total_timeout_ms=100),
            RouterInput(entitlement_tier="PRO", deepthink_enabled=True, env_mode="prod", requested_mode="deep", total_budget_units=10),
        ]
        
        valid_stop_reasons = {sr.value for sr in StopReason}
        
        for router_input in test_cases:
            plan = build_plan(router_input)
            if plan.stop_reason is not None:
                assert plan.stop_reason in valid_stop_reasons
    
    def test_enabled_deepthink_has_no_stop_reason(self):
        """When deepthink is enabled, stop_reason should be None."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            total_timeout_ms=3000,
            total_budget_units=300,
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count > 0
        assert plan.stop_reason is None


class TestAbuseBlocking:
    """Test abuse blocking."""
    
    def test_abuse_blocked_disables_deepthink(self):
        """abuse_blocked=True -> disabled, ABUSE."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="deep",
            abuse_blocked=True,
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 0
        assert plan.stop_reason == StopReason.ABUSE.value


class TestRequestedModeBaseline:
    """Test that baseline mode disables deepthink."""
    
    def test_baseline_mode_disables_deepthink(self):
        """requested_mode='baseline' -> disabled."""
        router_input = RouterInput(
            entitlement_tier="PRO",
            deepthink_enabled=True,
            env_mode="prod",
            requested_mode="baseline",
        )
        
        plan = build_plan(router_input)
        
        assert plan.effective_pass_count == 0
        assert plan.stop_reason == StopReason.ENTITLEMENT_CAP.value
