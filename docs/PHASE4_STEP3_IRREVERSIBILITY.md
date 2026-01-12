# Phase 4 — Step 3: Irreversibility & Consequence Horizon

_Date: 2026-01-07_

## A. Core Concept Definitions
- **Irreversibility** measures whether the downstream effects of an action can be meaningfully undone within the system’s operating assumptions (time, resources, authority). It asks only “Can this be rolled back to the prior state without disproportionate cost or dependency on third parties?” It is categorical; it never estimates odds or severity.
- **Consequence Horizon** measures how far into the future (or into adjacent systems) the action’s effects propagate if left unchecked. It is a structural view of duration and reach, distinct from urgency or impact magnitude.
- These concepts differ from:
  - **Severity** — magnitude of harm; Step 3 ignores magnitude.
  - **Regret** — emotional response; Step 3 is emotionless.
  - **Inconvenience** — short-lived friction; Step 3 tracks reversibility even if the action is merely annoying.
  - **Probability** — likelihood is out of scope; Step 3 treats classifications as conditional (“if this happens, can it be undone?”).

## B. Reversibility Taxonomy (Ordered)
1. **Easily Reversible**
   - *Includes*: actions that can be undone locally with minimal resources (e.g., toggling a setting, undoing a draft edit, reversing a small internal transfer).  
   - *Excludes*: any step that depends on outside approval, irreversible disclosures, or destructive physical changes.  
   - Classification is informational only; it does not imply safety.
2. **Conditionally Reversible**
   - *Includes*: actions that can be rolled back but require coordination, time, or non-trivial cost (e.g., voiding a contract within a grace period, restoring a system snapshot if backups exist).  
   - *Excludes*: situations where reversal hinges on uncertain third-party decisions or legal rulings.  
   - Signals that reversal is possible but non-trivial; no judgments are made about whether reversal is worthwhile.
3. **Largely Irreversible**
   - *Includes*: actions that, once executed, cannot realistically be undone (e.g., disclosing secrets, permanent data deletion without backups, self-harm, irreversible surgeries, resource destruction).  
   - *Excludes*: hypothetical discussions or reversible simulations.  
   - Flags permanence without commenting on appropriateness or severity.

## C. Consequence Horizon Taxonomy (Ordered)
1. **Immediate / Short-Term**
   - Effects manifest within the current interaction window or a near-term cycle and remain localized. Third-party impact is minimal or absent.  
   - Does not assert triviality; some short-term effects can be serious yet confined.
2. **Medium-Term**
   - Effects span extended days or weeks and may require follow-up actions to resolve (e.g., contractual obligations, multi-step deployments). Impacts may touch adjacent teams or partners.  
   - Focuses on duration/propagation, not how “bad” the effect is.
3. **Long-Term / Cascading**
   - Effects persist for months or longer, or propagate into additional systems, legal contexts, or generations of data. Includes compounding or third-party knock-on effects (e.g., regulatory actions, public disclosures, irreversible personal harm).  
   - Classification highlights reach, not probability or moral weight.

## D. Input Scope & Dependencies
Step 3 may observe:
- Current user input (single turn)
- Step 0 intent category (decision framing)
- Step 1 proximity signal
- Step 2 outcome domains and their uncertainty marks

Step 3 must not observe:
- User identity, profile, or long-term history
- Emotional state or inferred feelings
- External datasets, forecasts, or biosensors
- Phase 3 internals (model outputs, enforcement logs)

## E. Output Contract
Step 3 emits an internal-only tuple:
- `reversibility_class` ∈ {easily_reversible, conditionally_reversible, largely_irreversible}
- `horizon_class` ∈ {short_term, medium_term, long_term}
- `uncertainty_flag` ∈ {clear, ambiguous, unknown}

Outputs:
- Are not surfaced to users
- Do not change runtime behavior directly
- Serve as inputs to Phase 4 Step 4 (rigor/friction) and Step 5 (final gating) only

## F. Uncertainty Handling Principles
- When cues conflict, bias toward **lower reversibility** (i.e., treat as harder to undo) and **longer horizon**; mark `uncertainty_flag = ambiguous`.
- When information is insufficient, set both classes to `largely_irreversible` / `long_term` only if irreversible cues exist; otherwise emit `unknown` with neutral defaults and document why.
- Never infer confidence from absence of evidence. Explicitly propagate `unknown` when reversibility or horizon cannot be deduced.

## G. Failure Modes & Misclassification Risks
Step 3 is designed to prevent:
1. **False Temporariness** — assuming actions can be undone when they cannot (e.g., treating a public leak as retractable).
2. **Downstream Blindness** — ignoring effects on dependent systems, third parties, or future obligations.
3. **Recovery Assumption** — presuming that recovery resources (backups, legal remedies) are guaranteed.
4. **Time Compression** — collapsing months-long consequences into short-term framing, which would undercut later safeguards.
5. **Severity Leakage** — misusing these classes as proxies for “badness” instead of structural permanence.

## H. Non-Goals of Step 3
Step 3 does **not**:
- Assess probability or likelihood of outcomes.
- Score severity, cost, or regret.
- Recommend, warn, or refuse.
- Escalate rigor or insert friction.
- Ask clarifying questions or alter prompts.
- Modify or reinterpret Phase 3 behavior.

> **Phase 4 Step 3 is now defined.** Any future implementation must treat these classifications as stable, internal scaffolding for downstream decision-aware cognition.
