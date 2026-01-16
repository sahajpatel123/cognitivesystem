# MCI Reference Status

This document defines the status of the Minimal Correct Implementation (MCI)
after Phase 2 is certified and locked.

## 1. What the MCI Is

The MCI is:

- A **correctness baseline** that reflects the Cognitive Contract.
- A **reference artifact** for reasoning about system behavior.
- A **test oracle** for future phases when comparing behavior.

## 2. What the MCI Is Not

The MCI is not:

- A production system.
- An optimization target.
- A user experience system.
- A learning or adaptive system.

It is not intended to be deployed directly to end users.

## 3. Relationship to Future Phases

Future phases may:

- Wrap the MCI.
- Replace the MCI with new implementations.
- Extend behavior in separate programs.

Future phases must **not modify** the locked MCI reference. Any evolution must
be implemented outside this reference and treated as a distinct layer or
program.
