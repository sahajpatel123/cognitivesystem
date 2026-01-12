# Change Prohibition for Phase 2

This document explicitly forbids changes inside the scope of Phase 2 after
certification and lock.

## 1. Prohibited Actions

The following actions are prohibited within Phase 2:

- "Just a small refactor" of MCI code.
- "Harmless logging" added to the MCI pipeline.
- "Minor prompt cleanup" or wording changes.
- "Temporary debugging hacks" inserted into core logic.
- "Performance tweaks" or optimization changes.
- Any edits to reasoning, expression, memory, or invariants logic.
- Any expansion of observability beyond what is already defined.
- Any modification of tests that changes their meaning.

## 2. Certification Invalidation Rule

- Any prohibited change **invalidates** Phase 2 certification.
- Once a prohibited change is made, the MCI can no longer be treated as the
  certified reference implementation.

## 3. Requirement for New Work

- Any desire to change behavior, add features, or evolve cognition requires
  starting a new Phase 3 (or later) effort.
- Such work must be treated as a separate program with its own charter and
  certification path.

## 4. Why Prohibition Exists

Prohibition exists to preserve correctness before evolution.

- The locked MCI serves as a stable reference point.
- Without a fixed reference, it is not possible to distinguish intentional
  evolution from unintentional drift.
- Preventing changes ensures that any future behavior differences are explicit
  and attributable to separate work, not silent modifications.
