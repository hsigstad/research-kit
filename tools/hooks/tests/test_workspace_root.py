#!/usr/bin/env python3
"""One workspace resolver, and it must work with cron's environment.

Two outages came from re-derived copies of this resolver falling through to a
bare $HOME/research (a stub on this host): the nightly sweep reported a false
clean (2026-07-06), and inbox_waker.py woke nobody for a day (2026-08-13). The
last check here is the one that matters most — it fails if a private copy comes
back by copy-paste.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[2]
WS = TOOLS.parent.parent            # <root>/research-kit/tools -> <root>
HOOKS = TOOLS / "hooks"
CRON_ENV = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": os.environ["HOME"]}

fails = 0


def check(label, cond, extra=""):
    global fails
    fails += not cond
    print(f"  {'ok ' if cond else 'FAIL'} {label} {extra}")


def resolves(expr, path_dir, env):
    """Evaluate `expr` in a subprocess with cwd=/ and the given env."""
    p = subprocess.run(
        [sys.executable, "-c",
         f"import sys; sys.path.insert(0, {str(path_dir)!r});\n{expr}"],
        cwd="/", env=env, capture_output=True, text=True)
    return (p.stdout.strip().splitlines() or [p.stderr.strip()[-200:]])[-1]


print("=== canonical resolver ===")
out = resolves("import workspace_root as w; print(w.workspace())", TOOLS, CRON_ENV)
check("resolves the real root with cron's env (no RESEARCH_WORKSPACE, no cwd)",
      out == str(WS), f"| got {out}")

out = resolves("import workspace_root as w; print(w.workspace())", TOOLS,
               {**CRON_ENV, "RESEARCH_WORKSPACE": "/tmp/fixture-ws"})
check("RESEARCH_WORKSPACE still wins (test fixtures rely on it)",
      out == "/tmp/fixture-ws", f"| got {out}")

print("=== every consumer, under cron's env ===")
# (module, attribute, directory to import from). Attributes are called if callable.
CONSUMERS = [
    ("nightly_sweep", "workspace", TOOLS),
    ("drain_outbox", "workspace", TOOLS),
    ("send_message", "workspace", TOOLS),
    ("gen_inventory", "workspace", TOOLS),
    ("_lint_common", "WORKSPACE", TOOLS),
    ("workspace_browser", "WORKSPACE", TOOLS),
    ("presence", "workspace", HOOKS),
    ("stop_check", "_workspace", HOOKS),
    ("posttool_convention_gate", "_workspace", HOOKS),
    ("userprompt_inbox", "workspace", HOOKS),
    ("style_lint_hook", "_workspace", TOOLS),
    ("style_rules_hook", "_workspace", TOOLS),
]
for mod, attr, d in CONSUMERS:
    out = resolves(f"import {mod} as m; v = m.{attr}; print(v() if callable(v) else v)",
                   d, CRON_ENV)
    check(f"{mod}.{attr}", out == str(WS), f"| got {out}")

print("=== the waker's own no-op guard ===")
p = subprocess.run([sys.executable, str(TOOLS / "inbox_waker.py"), "--dry-run"],
                   cwd="/", env={**CRON_ENV, "RESEARCH_WORKSPACE": "/tmp/nope"},
                   capture_output=True, text=True)
(Path.home() / ".claude/state/waker_complaint.json").unlink(missing_ok=True)
check("a wrong root complains instead of exiting silently",
      "resolved the wrong workspace root" in p.stderr, f"| {p.stderr.strip()[:60]}")

print("=== no re-derived copies ===")
# The exact fallback that caused both outages. workspace_root.py is the one file
# allowed to mention a bare ~/research, because it is the thing being replaced.
BAD = re.compile(r'Path\.home\(\)\s*/\s*"research"|Path\("~/research"\)')
offenders = []
for f in sorted(list(TOOLS.glob("*.py")) + list(HOOKS.glob("*.py"))):
    if f.name == "workspace_root.py":
        continue
    if BAD.search(f.read_text(errors="replace")):
        offenders.append(f.relative_to(WS))
check("nobody re-derives the root from $HOME/research",
      not offenders, f"| {', '.join(map(str, offenders))}" if offenders else "")

print(f"\n{'ALL PASS' if not fails else str(fails) + ' FAILURES'}")
sys.exit(1 if fails else 0)
