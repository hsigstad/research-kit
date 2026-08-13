#!/usr/bin/env python3
"""Pre-edit writing-rules hook for Claude Code.

Triggered on Edit/Write tool use. When the edited file is a paper .tex
file AND this is the first such edit in the current session, surfaces
the writing rules (research-kit baseline + workspace overlay) back to
the model as additionalContext via hookSpecificOutput. After the first
firing in a session, silent.

The intent is to cover the judgment-laden rules that style_lint.py
can't see (paragraph flow, topic sentences, voice preservation, etc.).
The deterministic subset is already enforced per-edit by
style_lint_hook.py.
"""

import json
import os
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_root import workspace  # noqa: E402  (one resolver; see its docstring)

_workspace = workspace


CHEAT_SHEET = _workspace() / "research-kit" / "rules" / "writing_style_judgment.md"
MARKER_DIR = Path("/tmp")


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") not in ("Edit", "Write"):
        return 0

    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path:
        return 0

    p = Path(file_path)
    if p.suffix != ".tex":
        return 0
    if "paper" not in p.parts:
        return 0

    session_id = payload.get("session_id")
    if not session_id:
        return 0
    marker = MARKER_DIR / f"style_rules_shown_{session_id}"
    if marker.exists():
        return 0

    if not CHEAT_SHEET.exists():
        return 0

    msg = CHEAT_SHEET.read_text()
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "additionalContext": msg,
        }
    }))
    try:
        marker.touch()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
