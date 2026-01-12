from __future__ import annotations

"""Executable reference entry point for the MCI pipeline.

This module wires the existing MCI into a deterministic end-to-end run.
It does not change cognition or behavior; it only invokes the pipeline.
"""

import sys

from mci_backend.app import main


def run(session_id: str, text: str) -> str:
    result = main.handle_request({"session_id": session_id, "text": text})
    # handle_request returns a dict with a single "reply" key.
    return str(result["reply"])


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: run_reference.py <session_id> <text>")
    sid = sys.argv[1]
    msg = sys.argv[2]
    output = run(sid, msg)
    print(output)
