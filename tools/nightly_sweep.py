#!/usr/bin/env python3
"""Nightly workspace convention sweep (run by host cron).

Runs check_docs.py, citations.py, and check_macros.py workspace-wide plus
skill_links.py, and writes a morning report to
~/.claude/state/nightly_sweep_report.md ONLY when there is something to act
on; the SessionStart hook surfaces that file in the next session.
Deterministic linting only — no LLM involved.

Two signal classes:
  * errors      — always reported (the enforced floor; never baselined).
  * warnings    — reported only when NEW relative to a committed baseline
                  (research/rules/sweep_baseline.json). The large legacy
                  warning backlog is frozen into that baseline so the nightly
                  report surfaces regressions (a newly broken merge, a fresh
                  orphaned figure) instead of drowning them in known debt.

Regenerate the baseline after an intentional cleanup with:
    python3 nightly_sweep.py --update-baseline
Review the git diff of sweep_baseline.json before committing — every removed
fingerprint is debt you paid down; every added one is debt you accepted.
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

MAX_PER_SECTION = 25
DOC_TOOLS = ("check_docs", "citations", "check_macros")
_LINE_SUFFIX = re.compile(r":\d+$")


sys.path.insert(0, str(Path(__file__).resolve().parent))
from workspace_root import workspace  # noqa: E402  (cron gives us no env; see module docstring)


def baseline_path(ws: Path) -> Path:
    return ws / "research" / "rules" / "sweep_baseline.json"


def fingerprint(tool: str, scope: str, f: dict) -> str:
    """Stable identity for a warning: tool|scope|code|path-without-lineno.

    Line numbers are stripped so ordinary edits that shift a warning up or
    down a file do not read as a new regression; a warning appearing in a new
    file, or a new code in a repo, does surface.
    """
    code = f.get("code", "?")
    path = _LINE_SUFFIX.sub("", f.get("path") or f.get("msg", "?"))
    return f"{tool}|{scope}|{code}|{path}"


def collect(ws: Path):
    """Run every doc tool; return (errors, warnings) as lists of
    (tool, scope, finding-dict). Also returns skill_links issues."""
    tools = ws / "research-kit" / "tools"
    errors, warnings, failures = [], [], []
    for tool in DOC_TOOLS:
        cmd = ["python3", str(tools / f"{tool}.py"), "--json",
               "--workspace", str(ws)]
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            data = json.loads(out.stdout)
        except Exception as e:  # noqa: BLE001
            failures.append((tool, str(e)))
            continue
        scopes = data.get("repos", []) + [data.get("workspace", {})]
        for r in scopes:
            scope = r.get("scope", "?")
            for f in r.get("errors", []):
                errors.append((tool, scope, f))
            for f in r.get("warnings", []):
                warnings.append((tool, scope, f))
    return errors, warnings, failures


def skill_link_issues(ws: Path):
    tools = ws / "research-kit" / "tools"
    try:
        out = subprocess.run(
            ["python3", str(tools / "skill_links.py"), "--json", "--root", str(ws)],
            capture_output=True, text=True, timeout=120,
        )
        return json.loads(out.stdout).get("issues", []), None
    except Exception as e:  # noqa: BLE001
        return [], str(e)


def update_baseline(ws: Path) -> int:
    _, warnings, failures = collect(ws)
    if failures:
        print("refusing to write baseline — tool(s) failed:", failures, file=sys.stderr)
        return 1
    fps = sorted({fingerprint(t, s, f) for t, s, f in warnings})
    path = baseline_path(ws)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(
        {"generated": f"{datetime.now():%Y-%m-%d}", "count": len(fps),
         "fingerprints": fps}, indent=1) + "\n")
    print(f"wrote {path} ({len(fps)} baselined warning fingerprints)")
    return 0


def load_baseline(ws: Path):
    path = baseline_path(ws)
    if not path.exists():
        return None
    try:
        return set(json.loads(path.read_text()).get("fingerprints", []))
    except Exception:  # noqa: BLE001
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--update-baseline", action="store_true",
                    help="regenerate research/rules/sweep_baseline.json from current warnings")
    args = ap.parse_args()

    ws = workspace()
    if args.update_baseline:
        return update_baseline(ws)

    state = Path.home() / ".claude" / "state"
    state.mkdir(parents=True, exist_ok=True)
    report = state / "nightly_sweep_report.md"

    errors, warnings, failures = collect(ws)
    issues, sl_fail = skill_link_issues(ws)
    baseline = load_baseline(ws)

    # New warnings = those whose fingerprint is not in the committed baseline.
    if baseline is None:
        new_warnings = []
    else:
        new_warnings = [(t, s, f) for t, s, f in warnings
                        if fingerprint(t, s, f) not in baseline]

    lines = [
        f"# Nightly convention sweep — {datetime.now():%Y-%m-%d}",
        "",
        "Generated by research-kit/tools/nightly_sweep.py (cron). Mention",
        "problems to the user at a natural moment and offer to fix them.",
        "",
    ]

    # Errors — grouped by tool, always reported.
    by_tool_err = {}
    for t, s, f in errors:
        by_tool_err.setdefault(t, []).append((s, f))
    for tool in DOC_TOOLS:
        errs = by_tool_err.get(tool, [])
        lines.append(f"## {tool}: {len(errs)} error(s)")
        for scope, f in errs[:MAX_PER_SECTION]:
            lines.append(f"- {scope}: {f.get('path', '?')} — {f.get('msg', '')}")
        if len(errs) > MAX_PER_SECTION:
            lines.append(f"- ... and {len(errs) - MAX_PER_SECTION} more")
        lines.append("")

    for tool, err in failures:
        lines += [f"## {tool}: sweep failed ({err})", ""]

    # New warnings (regressions vs baseline).
    if baseline is None:
        lines += [
            "## warnings: not monitored (no baseline)",
            "- run `nightly_sweep.py --update-baseline` to start catching new warnings",
            "",
        ]
    elif new_warnings:
        lines.append(f"## new warnings since baseline: {len(new_warnings)}")
        for t, s, f in new_warnings[:MAX_PER_SECTION]:
            lines.append(f"- [{t}] {s}: {f.get('path', '?')} — {f.get('msg', '')}")
        if len(new_warnings) > MAX_PER_SECTION:
            lines.append(f"- ... and {len(new_warnings) - MAX_PER_SECTION} more")
        lines.append("")

    lines.append(f"## skill_links: {len(issues)} issue(s)")
    for issue in issues[:MAX_PER_SECTION]:
        lines.append(f"- {issue}")
    if len(issues) > MAX_PER_SECTION:
        lines.append(f"- ... and {len(issues) - MAX_PER_SECTION} more")
    if sl_fail:
        lines.append(f"- sweep failed ({sl_fail})")
    lines.append("")

    total = len(errors) + len(new_warnings) + len(issues) + len(failures) + (1 if sl_fail else 0)
    if total > 0:
        report.write_text("\n".join(lines))
    elif report.exists():
        report.unlink()
    with open(state / "nightly_sweep.log", "a") as fh:
        fh.write(f"[{datetime.now().isoformat(timespec='seconds')}] "
                 f"{len(errors)} error(s), {len(new_warnings)} new warning(s), "
                 f"{len(issues)} skill-link issue(s)\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
