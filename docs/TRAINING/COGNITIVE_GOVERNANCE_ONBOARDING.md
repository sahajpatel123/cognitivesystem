# Cognitive Governance Onboarding

This onboarding module introduces new engineers, product managers, and operations staff to cognitive governance for this system.

## 1. Session Overview (30–45 Minutes)

Recommended structure:

1. **Introduction (5 minutes)**
   - Purpose of cognitive governance.
   - High-level overview of the Cognitive Contract.
2. **Core Concepts (10–15 minutes)**
   - WHAT vs HOW separation.
   - Two-LLM architecture (Reasoning vs Expression).
   - Planner, hypotheses, and memory rules.
3. **Governance Framework (10–15 minutes)**
   - Governance Charter.
   - Roles and decision authority.
   - Change control and incident rules.
4. **Examples and Pitfalls (5–10 minutes)**
   - Good intentions that break the contract.
   - How pressure leads to erosion.
5. **Quiz and Self-Check (5 minutes)**
   - Short questions to confirm understanding.

## 2. Core Mental Models

- **"Cognition is law, not code"**
  - The Cognitive Contract defines how the system thinks.
  - Code must be aligned with the contract; code does not redefine the contract.
  - Changing cognition is a governance decision, not a normal engineering decision.

- **"Pressure is expected; erosion is optional"**
  - Latency, cost, and UX pressure will occur.
  - The system is designed to face such pressure without changing cognition.
  - Erosion happens only if people relax or ignore governance rules.

## 3. Concrete Examples of Good Intentions That Break the Contract

- Example 1: Prompt cleanup
  - Intent: "Make prompts shorter and easier to read."
  - Why it feels reasonable: It seems like improving readability without changing behavior.
  - Why it is forbidden: It can change how the models interpret instructions, altering cognition.

- Example 2: Fast-path for simple questions
  - Intent: "Skip reasoning for easy questions to reduce latency."
  - Why it feels reasonable: It appears to help users and reduce cost.
  - Why it is forbidden: It bypasses the Reasoning LLM and introduces cognition shortcuts.

- Example 3: Extending memory to improve experience
  - Intent: "Remember users across sessions so the system feels more helpful."
  - Why it feels reasonable: It aligns with common personalization approaches.
  - Why it is forbidden: It violates session-only memory and no-identity rules.

- Example 4: Temporary incident workaround
  - Intent: "During an outage, quickly switch to a simpler prompt."
  - Why it feels reasonable: It aims to maintain some service.
  - Why it is forbidden: It introduces a second cognitive configuration and erodes the contract.

## 4. Quiz and Self-Check

Answer these questions to check your understanding.

1. If you want to change the wording of a prompt to make it clearer, what category of change is this?
2. During a latency incident, can you skip the Reasoning LLM for some requests if all stakeholders agree?
3. Is it acceptable to remember a user’s preferences across sessions if they explicitly opt in?
4. Who can approve a change to memory TTL for session data?
5. What must be done if someone proposes a cognitive change during an incident?

Suggested answers:

1. It is a cognitive change and is governed.
2. No. Cognition must not be modified during incidents.
3. No. Cross-session identity and personalization are forbidden.
4. It is a change to memory rules and is outside normal operations; it must follow a higher-order governance process.
5. The proposal must be rejected and logged as governance pressure according to the Governance Charter.
