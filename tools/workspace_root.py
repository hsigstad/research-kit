#!/usr/bin/env python3
"""The one workspace-root resolver. Import it; do not re-derive it.

There were eight byte-identical copies of this function, and the family of bug
they share has bitten twice:

  2026-07-06  the nightly sweep linted zero repos and reported a false clean
  2026-08-13  inbox_waker.py ran every minute for a day and woke nobody

Both had the same shape. A caller outside a Claude session has no
RESEARCH_WORKSPACE — hooks only get it because run_hook.sh exports it, and cron
exports nothing — so resolution fell through to a bare $HOME/research. On this
host that path exists but is an unrelated stub, so the miss was silent: no
inbox/ to read, no repos to lint, exit 0, look healthy.

`self_root` is the fix. This module lives at <root>/research-kit/tools/, so its
own path names the workspace. cron can strip the environment and the cwd; it
cannot strip __file__.

Order is deliberate. RESEARCH_WORKSPACE still wins outright (tests point it at
fixtures), then the two historical candidates in their original order, so every
path that already resolved keeps resolving the same way — self_root only
rescues the case that used to return the stub.
"""
from __future__ import annotations

import os
from pathlib import Path

# <root>/research-kit/tools/workspace_root.py -> <root>
SELF_ROOT = Path(__file__).resolve().parents[2]


def workspace() -> Path:
    """Absolute workspace root: the directory containing research-kit/."""
    env = os.environ.get("RESEARCH_WORKSPACE")
    if env:
        return Path(env).expanduser()
    for cand in (Path.home() / "research", Path("/workspace"), SELF_ROOT):
        if (cand / "research-kit").exists():
            return cand
    return SELF_ROOT


if __name__ == "__main__":
    print(workspace())
