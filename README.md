# Human-Adaptive Cognitive Conversational System

This project implements a **cognitive orchestration layer** on top of LLM APIs. It is **not** a chatbot, prompt wrapper, or AGI demo. Its goal is to act as a **thinking partner** that:

- Lets users express thoughts naturally and messily.
- Reasons internally in a structured, disciplined way.
- Responds in a style aligned with the user’s thinking.
- Detects misunderstandings and missing fundamentals.
- Self-corrects within a session by **down-weighting** wrong reasoning paths (never deleting them).

The primary demo domain is **learning OOP (OOPS) in Python**, but the architecture is **domain-agnostic**.

---

## Core Philosophy

- **User controls _what_ to think** (topic, goal, intent).
- **System controls _how_ to think** (reasoning structure, rigor, correction).
- Reasoning is **machine-level**: structured, rigorous, self-correcting.
- Expression is **human-level**: casual, aligned with the user’s style.
- Explicit style overrides (e.g. "be normal", "be formal") affect **only expression**, never reasoning.
- Memory is **short-term (3–5 hours)**, **pattern-based**, **not identity-based**.

The system must **never imitate human flaws**. It absorbs cognitive rigor so the human doesn’t have to.

---

## Architectural Pipeline (Mandatory)

Per user message, the system runs a fixed pipeline:

1. **User Input**  
2. **Intent + Cognitive Style Inference**  
3. **Hidden Structured Reasoning (LLM Call #1)**  
4. **Expression Renderer (LLM Call #2, style-aligned)**  
5. **User Output**

Constraints:

- Reasoning output is **never** shown directly to the user.
- Expression may be informal and flowing, but is always grounded in the hidden reasoning.
- Reasoning and presentation are **separate steps and separate prompts**.

---

## Key Components (Conceptual)

Back-end cognitive engine:

- **Intent & Style Inferencer**  
  Infers user intent (goal, topic) and cognitive style (abstraction level, formality, analogy preference).

- **Reasoning Orchestrator (LLM #1)**  
  Runs hidden, structured reasoning, proposes and updates internal hypotheses, and produces an intermediate answer representation.

- **Hypothesis Store & Session Memory**  
  Tracks hypotheses (with support/refute scores) and short-lived cognitive patterns (what explanations worked/failed). Wrong paths are **down-weighted, never deleted**.

- **Expression Renderer (LLM #2)**  
  Converts the intermediate answer into a user-facing response that matches the user’s style, without altering the underlying conclusions.

- **Feedback & Telemetry**  
  Uses user disagreement/confusion as a high-value signal to adjust hypothesis weights and explanation strategies.

---

## Learning & Self-Correction

- All outputs are treated as **hypotheses**, not facts.
- Wrong reasoning paths are **down-weighted**, not removed.
- The system remembers **why** something failed (e.g., which explanation pattern confused the user).
- No hard deletions or locked beliefs; influence is adjusted softly over time within a session.

---

## Demo Context: OOP in Python

For demonstration, the system is configured to handle vague, confused questions about **Object-Oriented Programming in Python**, for example:

> "I kinda get classes but not really, like when to actually use them in Python?"

The system should:

- Detect missing fundamentals (e.g., objects vs classes, state vs behavior).
- Explain concepts using the user’s own language and preferred level of abstraction.
- Avoid textbook definitions unless necessary.
- Redirect to basics **without embarrassment or tutoring tone**.

The same architecture should generalize to other domains.

---

## Technical Orientation

- Built as a **web-based conversational system** with a back-end cognitive engine.
- Uses **multiple LLM calls per turn**:
  - LLM #1: hidden structured reasoning and hypothesis management.
  - LLM #2: style-aligned expression rendering.
- Designed for **clean architecture**: clear module boundaries, explicit data models, and well-defined decision points.
- No fine-tuning or AGI claims; this is about **cognitive orchestration**, not new model training.

---

## Non-Goals / Strict Do-Not’s

This project explicitly avoids:

- A single-prompt chatbot that merges reasoning and presentation.
- Long-term, identity-based personalization beyond a session.
- Over-formal, tutor-like behavior unless explicitly requested.
- Benchmark optimization or AGI marketing.

---

## Next Steps (Implementation)

Typical implementation phases in this repository:

1. **Define core types and interfaces** for:
   - User messages, intent, cognitive style, reasoning traces, hypotheses, session memory, expression plans.
2. **Implement the cognitive engine skeleton**:
   - Intent/Style inference, Reasoning Orchestrator, Hypothesis Store, Expression Renderer.
3. **Wire up LLM clients** with separate prompts for reasoning and expression.
4. **Add a minimal web UI** for interactive demo (Python OOP first, then domain-agnostic).

This README describes the **design contract**. All code in this repo should respect and preserve these principles.
