#!/usr/bin/env python3
"""PostToolUse hook (Edit|Write): deterministic convention feedback.

Routes the just-edited file to the matching workspace linter and, when
violations touch that file, exits 2 so the message reaches Claude for an
immediate same-turn fix. Fails open (exit 0) on any internal error so a
hook bug can never block editing.

Routing:
  projects|pipelines/<slug>/docs/**/*.md   -> citations.py <slug>, findings filtered to file
  projects|pipelines/<slug>/source/**/*.py -> in-script checks: INTENT header, merge(validate=)
  **/paper/**/*.tex                        -> style_lint.py (warning+)
  ~/Dropbox/referee/**                     -> style_lint.py + ASCII-only scan
"""
import json
import os
import re
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


WORKSPACE = _workspace()
TOOLS = WORKSPACE / "research-kit" / "tools"
MAX_LINES = 10
TIMEOUT = 20


def fail_open(msg=""):
    sys.exit(0)


def report(header, lines):
    body = "\n".join(lines[:MAX_LINES])
    extra = len(lines) - MAX_LINES
    if extra > 0:
        body += f"\n... and {extra} more"
    print(f"{header}\n{body}", file=sys.stderr)
    sys.exit(2)


def run_json(cmd):
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    return json.loads(out.stdout)


def check_docs_md(path: Path):
    # projects/<slug>/docs/foo.md -> lint citations for that slug, keep
    # only findings in this file.
    rel = path.relative_to(WORKSPACE)
    kind, slug = rel.parts[0], rel.parts[1]
    rel_in_repo = str(Path(*rel.parts[2:]))
    data = run_json(["python3", str(TOOLS / "citations.py"), slug, "--json"])
    hits = []
    for repo in data.get("repos", []):
        for sev in ("errors", "warnings"):
            for f in repo.get(sev, []):
                if f.get("path", "").split(":")[0] == rel_in_repo:
                    hits.append(f"- {f['path']}: {f['msg']}")
    if hits:
        report(
            f"Citation-convention violations in {rel_in_repo} "
            f"(workspace rule: use [ns:key] tokens, no bare prose citations). Fix now:",
            hits,
        )


def check_source_py(path: Path):
    text = path.read_text(errors="replace")
    lines = text.splitlines()
    hits = []
    head = "\n".join(lines[:60])
    if "INTENT" not in head:
        hits.append(
            "- missing IAT header: no INTENT comment in the first 60 lines "
            "(see research-kit/rules/inline_audit_trail.md)"
        )
    for i, line in enumerate(lines):
        if re.search(r"\.merge\(|\bpd\.merge\(", line) and "#" != line.lstrip()[:1]:
            window = "\n".join(lines[i : i + 6])
            if "validate=" not in window:
                hits.append(f"- line {i + 1}: merge() without validate= (workspace rule)")
    if hits:
        report(f"Script-convention violations in {path.name}. Fix now:", hits)


def style_lint(path: Path, ascii_only: bool):
    hits = []
    try:
        data = run_json(
            ["python3", str(TOOLS / "style_lint.py"), str(path),
             "--format", "json", "--severity", "warning"]
        )
        for v in data if isinstance(data, list) else []:
            hits.append(f"- line {v.get('line', '?')} [{v.get('rule')}]: {v.get('message', v.get('suggestion', ''))}")
    except Exception:
        pass
    if ascii_only:
        for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            bad = sorted({c for c in line if ord(c) > 127})
            if bad:
                hits.append(f"- line {i}: non-ASCII {' '.join(repr(c) for c in bad)} (referee reports are ASCII-only; use -- not em-dash)")
    if hits:
        report(f"Prose-style violations in {path.name}. Fix now:", hits)


def main():
    data = json.load(sys.stdin)
    if data.get("tool_name") not in ("Edit", "Write"):
        fail_open()
    fp = (data.get("tool_input") or {}).get("file_path")
    if not fp:
        fail_open()
    path = Path(fp).resolve()
    if not path.exists():
        fail_open()

    referee_root = Path.home() / "Dropbox" / "referee"
    if referee_root in path.parents:
        style_lint(path, ascii_only=True)
        return
    if path.suffix == ".tex" and "paper" in path.parts:
        style_lint(path, ascii_only=False)
        return
    try:
        rel = path.relative_to(WORKSPACE)
    except ValueError:
        fail_open()
    if len(rel.parts) < 3 or rel.parts[0] not in ("projects", "pipelines"):
        fail_open()
    if rel.parts[2] == "docs" and path.suffix == ".md":
        check_docs_md(path)
    elif rel.parts[2] == "source" and path.suffix == ".py":
        check_source_py(path)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
