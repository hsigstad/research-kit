#!/usr/bin/env python3
"""PreToolUse hook: freeze the manuscript unless the session is authorized.

WHY. At a certain project stage the author wants control over the manuscript:
sessions must NOT edit the paper on their own initiative. When a paper is put in
"controlled mode" (a committed marker `paper/.controlled`), this hook blocks every
Edit/Write (and Bash write) to the manuscript prose UNLESS the current session has
been authorized — which only the `/voice` skill does, by writing a session-keyed
unlock marker. A blocked session is told to append its intended change to
`paper/queued_edits.md` instead; a later `/voice` session applies the queue in the
author's voice.

Scope of the block (ALL must hold, else the call is allowed):
  - tool is Edit/Write (target = file_path) or Bash (a write to such a path);
  - the target is manuscript prose: a `*.tex` under a `paper/` dir, not in
    `paper/figures/` or `paper/tables/` (hand-authored asset dirs);
  - that paper dir has a `.controlled` marker;
  - the session has no valid unlock marker.

The feature is DORMANT until `paper/.controlled` exists, so installing the hook
changes nothing until a paper is opted in. Fails OPEN on any error.

Unlock contract: `/voice` writes `~/.claude/state/paper_unlock_<session_id>`
(see the skill). Valid if present and younger than UNLOCK_TTL. Session-keyed, so
unlocking in one session never unlocks a concurrent session; stale markers for
dead session ids never match a new session.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

UNLOCK_TTL = 12 * 3600  # seconds; /voice refreshes it on each invocation
STATE = Path(os.path.expanduser("~/.claude/state"))


def manuscript_paper_dir(path: Path):
    """If `path` is manuscript prose, return its enclosing `paper/` dir, else None."""
    if path.suffix.lower() != ".tex":
        return None
    parts = path.parts
    if "paper" not in parts:
        return None
    # exclude hand-authored asset dirs (rebuilt from build/, not the manuscript)
    if "figures" in parts or "tables" in parts:
        return None
    i = parts.index("paper")
    return Path(*parts[: i + 1])


def is_controlled(paper_dir: Path) -> bool:
    try:
        return (paper_dir / ".controlled").exists()
    except Exception:
        return False


def session_authorized(session_id: str) -> bool:
    if not session_id:
        return False
    marker = STATE / f"paper_unlock_{session_id}"
    try:
        if not marker.exists():
            return False
        return (time.time() - marker.stat().st_mtime) < UNLOCK_TTL
    except Exception:
        return False


# Bash commands that write to a file path (conservative; defense-in-depth only).
_BASH_WRITE = re.compile(r"(>>?|\btee\b|\bsed\b[^|]*-i|\bdd\b|\bcp\b|\bmv\b|\btruncate\b)")
_TEX_TOKEN = re.compile(r"[^\s'\"]*paper/[^\s'\"]*\.tex\b")


def bash_targets(command: str):
    """Manuscript-looking .tex paths a Bash command appears to write to."""
    if not _BASH_WRITE.search(command):
        return []
    return [Path(m.group(0)) for m in _TEX_TOKEN.finditer(command)]


def deny(paper_dir: Path):
    queue = paper_dir / "queued_edits.md"
    print(
        f"BLOCKED: the manuscript in {paper_dir}/ is frozen (controlled mode).\n"
        f"Do NOT edit the paper prose directly. Instead append your intended change "
        f"to {queue} as an entry:\n"
        f"    ## <section> — <one-line what>\n"
        f"    Why: <reason>\n"
        f"    Draft (optional): <prose in the author's voice>\n"
        f"Then continue with the rest of the task. The author applies the queue in a "
        f"focused `/voice` session. If the author explicitly asked YOU to edit the "
        f"paper now, they must run `/voice <section>` — that authorizes this session.",
        file=sys.stderr,
    )
    sys.exit(2)


def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name", "")
    tinput = data.get("tool_input") or {}
    session_id = data.get("session_id", "")

    candidates = []
    if tool in ("Edit", "Write", "NotebookEdit"):
        fp = tinput.get("file_path") or tinput.get("notebook_path")
        if fp:
            candidates = [Path(fp)]
    elif tool == "Bash":
        candidates = bash_targets(tinput.get("command", ""))

    for cand in candidates:
        paper_dir = manuscript_paper_dir(cand)
        if paper_dir and is_controlled(paper_dir) and not session_authorized(session_id):
            deny(paper_dir)


try:
    main()
except SystemExit:
    raise
except Exception:
    pass  # fail open: never block on an internal error
sys.exit(0)
