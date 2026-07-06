#!/usr/bin/env python3
"""SessionStart hook: surface pending automation reports.

Prints ~/.claude/state/nightly_sweep_report.md (written by
nightly_sweep.py when the workspace-wide lint sweep found errors) into
the new session's context. The sweep deletes the report when a later
run comes back clean, so this hook never needs to clean up. Fails open
on any error.
"""
import sys
from pathlib import Path

MAX_BYTES = 6000


def main() -> None:
    report = Path.home() / ".claude" / "state" / "nightly_sweep_report.md"
    if not report.is_file():
        return
    body = report.read_text(errors="replace")[:MAX_BYTES]
    print(body.rstrip())


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
