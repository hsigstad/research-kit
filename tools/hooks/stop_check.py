#!/usr/bin/env python3
"""Stop hook: doc-contract gate before the turn ends.

For each project/pipeline repo with uncommitted changes, runs
check_docs.py and collects ERRORS that touch the dirty files (so
pre-existing issues elsewhere never block). If any, blocks the stop with
a reason so Claude fixes them before finishing. Fails open on any
internal error; respects stop_hook_active to avoid loops.
"""
import json
import os
import subprocess
import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from workspace_root import workspace  # noqa: E402  (one resolver; see its docstring)

_workspace = workspace


WORKSPACE = _workspace()
TOOLS = WORKSPACE / "research-kit" / "tools"
MAX_REPOS = 4
TIMEOUT = 15


def dirty_files(repo: Path):
    out = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True, text=True, timeout=10,
    )
    files = []
    for line in out.stdout.splitlines():
        p = line[3:].strip().strip('"')
        if p:
            files.append(p)
    return files


def main():
    data = json.load(sys.stdin)
    if data.get("stop_hook_active"):
        sys.exit(0)

    problems = []
    checked = 0
    for kind in ("projects", "pipelines"):
        for repo in sorted((WORKSPACE / kind).iterdir()):
            if checked >= MAX_REPOS or not (repo / ".git").exists():
                continue
            dirty = dirty_files(repo)
            relevant = {f for f in dirty if f.startswith(("docs/", "source/", "build/", "paper/"))}
            if not relevant:
                continue
            checked += 1
            out = subprocess.run(
                ["python3", str(TOOLS / "check_docs.py"), repo.name, "--json"],
                capture_output=True, text=True, timeout=TIMEOUT,
            )
            j = json.loads(out.stdout)
            for r in j.get("repos", []):
                for f in r.get("errors", []):
                    fpath = f.get("path", "").split(":")[0]
                    if fpath in relevant:
                        problems.append(f"{kind}/{repo.name}: {f['path']} — {f['msg']}")

    if problems:
        reason = (
            "Doc-contract errors in files modified this session (check_docs.py). "
            "Fix before finishing:\n" + "\n".join(f"- {p}" for p in problems[:8])
        )
        print(json.dumps({"decision": "block", "reason": reason}))
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
