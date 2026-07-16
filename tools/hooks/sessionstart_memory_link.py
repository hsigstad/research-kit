#!/usr/bin/env python3
"""SessionStart hook: keep educloud Claude memory unified.

Claude Code keys each memory store by the session's launch directory, which
fragments memory across per-path silos. This hook reconciles every research
project-key's `memory/` dir into a symlink to the canonical store
`~/.claude/projects/-workspace/memory` (a real directory that both the
non-sandbox login node and the /workspace sandbox share over the NFS home).

Design notes:
- Self-healing SWEEP: on every run it fixes ALL research keys, not just the
  current session's — so a fresh subdir launch (where this script's path may
  not even resolve) gets repaired by the next root-launched session.
- SAFE: only links a `memory/` dir that is MISSING or EMPTY. A non-empty store
  is left untouched with a warning (it may hold un-audited entries).
- Uses a RELATIVE symlink (`../-workspace/memory`) so it resolves regardless of
  where the NFS home is mounted, and never points outside ~/.claude/projects.
- Never blocks: always exits 0.
"""
import os
import shutil
import sys

CANONICAL_KEY = "-workspace"
RESEARCH_PREFIXES = ("-projects-ec113-henrik-research", "-workspace-")


def main():
    # Drain stdin (hook protocol); we don't need its contents.
    try:
        sys.stdin.read()
    except Exception:
        pass

    projects = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    if not os.path.isdir(projects):
        return

    canonical = os.path.join(projects, CANONICAL_KEY, "memory")
    # Canonical must be a real directory. If it's missing or is itself a
    # symlink, do nothing rather than guess.
    if not os.path.isdir(canonical) or os.path.islink(canonical):
        return

    for key in sorted(os.listdir(projects)):
        if key == CANONICAL_KEY:
            continue
        if not key.startswith(RESEARCH_PREFIXES):
            continue
        keydir = os.path.join(projects, key)
        if not os.path.isdir(keydir):
            continue
        memdir = os.path.join(keydir, "memory")

        if os.path.islink(memdir):
            continue  # already unified

        if os.path.isdir(memdir):
            entries = [f for f in os.listdir(memdir)
                       if f.endswith(".md") and f != "MEMORY.md"]
            if entries:
                print(f"[memory-link] {key}/memory holds {len(entries)} "
                      f"un-unified entr{'y' if len(entries) == 1 else 'ies'}; "
                      f"leaving alone — run the memory audit, then link it.",
                      file=sys.stderr)
                continue
            shutil.rmtree(memdir)  # empty (at most a stray MEMORY.md): safe

        try:
            if os.path.lexists(memdir):
                os.remove(memdir)
            os.symlink(os.path.join("..", CANONICAL_KEY, "memory"), memdir)
        except OSError as e:
            print(f"[memory-link] could not link {key}: {e}", file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never break session start
        print(f"[memory-link] error: {e}", file=sys.stderr)
    sys.exit(0)
