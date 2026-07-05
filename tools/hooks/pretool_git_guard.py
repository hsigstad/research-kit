#!/usr/bin/env python3
"""PreToolUse hook (Bash): block bulk git staging in shared repos.

Multiple Claude sessions work the same repos concurrently in this
workspace; `git add -A` / `git add .` sweeps another session's edits
into this session's commit (it happened: 2026-06-09). Exit 2 blocks the
command and tells Claude to stage files explicitly.
"""
import json
import re
import sys

SEGMENT_SPLIT = re.compile(r"[\n;|&]+")
ENV_ASSIGN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


def is_bulk_add(command: str) -> bool:
    """True if any command segment is a `git ... add` with -A/--all/`.`."""
    for seg in SEGMENT_SPLIT.split(command):
        toks = seg.strip().split()
        i = 0
        while i < len(toks) and ENV_ASSIGN.match(toks[i]):
            i += 1
        if i >= len(toks) or toks[i] != "git":
            continue
        i += 1
        while i < len(toks) and toks[i].startswith("-"):
            i += 2 if toks[i] == "-C" else 1
        if i >= len(toks) or toks[i] != "add":
            continue
        if any(a in ("-A", "--all", ".") for a in toks[i + 1:]):
            return True
    return False


try:
    data = json.load(sys.stdin)
    cmd = (data.get("tool_input") or {}).get("command", "")
    if is_bulk_add(cmd):
        print(
            "Blocked: `git add -A` / `git add .` is not allowed in this workspace — "
            "concurrent sessions share these repos and bulk staging sweeps their edits "
            "into your commit. Stage the files you changed explicitly by name.",
            file=sys.stderr,
        )
        sys.exit(2)
except SystemExit:
    raise
except Exception:
    pass
sys.exit(0)
