# Organizational Governance Playbook

This playbook explains how cognitive governance works in day-to-day work. It is intended for engineers, product managers, and operations staff.

## 1. Why Cognitive Systems Fail Under Human Pressure

Cognitive systems often fail not because of technical defects, but because people under pressure change how the system thinks.

Common sources of pressure include:

- Latency complaints.
- Cost alarms.
- Stakeholder demands for faster or more engaging behavior.
- Desire to "clean up" prompts or flows.

If these pressures lead to changes in cognition, the system can silently stop doing what it was certified to do. The goal of governance is to prevent this.

## 2. Cognition Is Constitutionally Protected

- The Cognitive Contract defines how the system thinks.
- The Governance Charter defines who may decide what.
- Cognition is not a normal tuning parameter.
- Cognition is protected in the same way as a constitutional rule: changing it requires a separate, explicit governance process, not a routine ticket or pull request.

In day-to-day work, you must assume that cognition, prompts, planner behavior, hypothesis rules, and memory rules are not changeable.

## 3. Things That Feel Safe but Are Not

The following actions may feel like minor, safe changes but are not. They are governed and usually forbidden.

- "Minor" prompt tweaks:
  - Rewording instructions to be more friendly or concise.
  - Changing examples in prompts to "improve" style.
  - Adding hints to make the model faster or cheaper.
- Planner adjustments:
  - Changing the structure of plans.
  - Removing or adding sections.
- Reasoning changes:
  - Skipping the Reasoning LLM for some requests.
  - Adding a shortcut path for "simple" questions.
- Expression behavior changes:
  - Making answers more confident than the reasoning.
  - Softening or removing constraints in user-facing text.
- Memory and hypothesis changes:
  - Increasing or decreasing memory duration.
  - Keeping information across sessions.
  - Adding any form of personalization.

If a change modifies what the system concludes, remembers, assumes, or how it decides what to say, it is a cognitive change and is not safe by default.

## 4. Simple Decision Flow for Changes

Use this flow before proposing or approving any change.

1. **Identify what you want to change.**
   - Example categories:
     - UI layout or copy on the frontend.
     - API routing, retries, or timeouts.
     - Prompts.
     - Planner behavior.
     - Reasoning or expression code.
     - Hypothesis or memory handling.

2. **Classify the change.**
   - If it touches prompts, planner, reasoning, expression, hypotheses, or memory → it is a **cognitive change**.
   - If it modifies infrastructure, rate limits, deployment, or logging without altering cognition → it is a **delivery change**.
   - If it changes user-facing presentation only (without changing responses) → it is a **UX change**.

3. **Apply governance rules.**
   - **Cognitive change**:
     - Forbidden under normal operations.
     - Cannot be approved by engineers, product, delivery, or incident command.
     - Requires a separate governance process outside this playbook.
   - **Delivery change**:
     - May be approved by the Delivery Owner according to the Governance Charter.
   - **UX change**:
     - May be approved by the Product Owner if it does not alter cognition.

4. **Decide next step.**
   - If the change is cognitive or contract-threatening → **do not proceed**.
   - If the change is delivery or UX and within role authority → follow normal review and deployment procedures.

## 5. Quick Reference Table

| Change idea                                 | Category         | Can proceed via normal process? |
|--------------------------------------------|------------------|----------------------------------|
| Increase instance count                     | Delivery change  | Yes, with Delivery Owner         |
| Adjust rate limits                          | Delivery change  | Yes, with Delivery Owner         |
| Modify frontend layout                      | UX change        | Yes, with Product Owner          |
| Reword prompts to be shorter                | Cognitive change | No                               |
| Skip reasoning for repeat questions         | Cognitive change | No                               |
| Extend memory across sessions               | Cognitive change | No                               |
| Add personalization based on past sessions  | Cognitive change | No                               |
| Cache final responses exactly               | Delivery change  | Yes, with Delivery Owner         |

When unsure, treat a proposed change as cognitive until proven otherwise and escalate according to the Governance Charter.
