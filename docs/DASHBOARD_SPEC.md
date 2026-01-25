# Dashboard Spec — Phase 16 Step 6 (Passive Observability)

Purpose: visualize `/api/chat` health via structured logs-derived metrics. No vendor-specific tooling implied.

## Panels
1. **RPS / Throughput**
   - Source: count of `chat.summary` (sampled) scaled; focus on error-unsampled cases.
2. **Latency p50/p95/p99**
   - Metric: `latency_ms` bucketed by `status_code` class (2xx/4xx/5xx).
3. **Error Rate**
   - Ratio of 4xx/5xx to total; separate provider vs client errors.
4. **FailureType Counts**
   - Breakdown of `failure_type`: timeout, provider_unavailable, budget_exceeded, safety_blocked, etc.
5. **Mode / Tier Distribution**
   - `requested_mode` vs `granted_mode`; `plan` overlays for tier composition.
6. **Breaker / Budget Activity**
   - Counts of `breaker_open`, `budget_block`, `budget_scope` occurrences.
7. **WAF Limiter Hits**
   - Track `waf_limiter` occurrences and error overlays.
8. **Sampling Rate Visibility**
   - Observed ratio of sampled successes vs total; ensure ~2% on 2xx paths.

## How to Interpret
- Rising latency without error rate increase: check upstream model latency, routing plan, and timeouts.
- Spikes in `failure_type=provider_unavailable` or `timeout_where=provider/total`: inspect provider health and budgets.
- Increases in `budget_block` or `budget_scope` signals: adjust quotas or investigate abuse; confirm no false positives.
- Divergence between `requested_mode` and `granted_mode`: indicates downgrades or tier restrictions.
- WAF limiter spikes: validate limiter backend health and false positives.
- Sampling drift: if sampled success rate deviates far from 2%, verify hashing and request_id propagation.

## Non-goals
- No vendor-specific dashboards; this is a conceptual spec for any log-based tool.
- No runtime feedback loops; dashboards are read-only observability aids.
