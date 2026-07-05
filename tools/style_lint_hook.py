#!/usr/bin/env python3
"""Post-edit style-lint hook for Claude Code.

Triggered on Edit/Write tool use. When the edited file is a paper .tex
file, runs style_lint.py and surfaces warning-or-higher violations back
into the conversation. Silent on green.

Reads tool-call context as JSON from stdin (Claude Code hook protocol).
Writes violations to stdout. Always exits 0 — the lint is informational,
not blocking.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def _workspace() -> Path:
    env = os.environ.get("RESEARCH_WORKSPACE")
    if env:
        return Path(env)
    for cand in (Path.home() / "research", Path("/workspace")):
        if (cand / "research-kit").exists():
            return cand
    return Path.home() / "research"


LINTER = _workspace() / "research-kit" / "tools" / "style_lint.py"


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
    if not p.exists():
        return 0
    if not LINTER.exists():
        return 0

    cmd = ["python3", str(LINTER), str(p), "--severity", "warning"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except (subprocess.TimeoutExpired, OSError):
        return 0

    if result.returncode == 0:
        return 0  # no violations, silent

    violations = f"[style-lint] {p.name} — warning-level violations:\n{result.stdout}"
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": violations,
        }
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
