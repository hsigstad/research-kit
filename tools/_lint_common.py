"""Shared helpers for check_docs.py and citations.py."""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path


def _detect_workspace() -> Path:
    """Workspace root: RESEARCH_WORKSPACE env var, else first root that
    actually contains research-kit. A bare ~/research default silently
    lints zero repos on hosts where the workspace lives elsewhere
    (observed 2026-07-06: the nightly sweep reported a false clean)."""
    env = os.environ.get("RESEARCH_WORKSPACE")
    if env:
        return Path(env).expanduser()
    for cand in (Path("~/research").expanduser(), Path("/workspace")):
        if (cand / "research-kit").exists():
            return cand
    return Path("~/research").expanduser()


WORKSPACE = _detect_workspace()


class Findings:
    def __init__(self, scope: str):
        self.scope = scope
        self.errors: list[dict] = []
        self.warnings: list[dict] = []
        self.info: list[dict] = []

    def err(self, code: str, msg: str, path: str | None = None):
        self.errors.append({"code": code, "msg": msg, "path": path})

    def warn(self, code: str, msg: str, path: str | None = None):
        self.warnings.append({"code": code, "msg": msg, "path": path})

    def note(self, code: str, msg: str, path: str | None = None):
        self.info.append({"code": code, "msg": msg, "path": path})

    def to_dict(self):
        return {
            "scope": self.scope,
            "errors": self.errors,
            "warnings": self.warnings,
            "info": self.info,
        }

    def total(self):
        return len(self.errors) + len(self.warnings) + len(self.info)


def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""


def find_repos(workspace: Path, slug: str | None) -> list[tuple[Path, str]]:
    repos: list[tuple[Path, str]] = []
    if slug:
        # A slug must be a single repo name, not a path. Path-like slugs
        # (".", "..", "a/b", trailing slash) otherwise resolve to the
        # projects/ container or its parent, which then get linted as bogus
        # repos (missing docs/ + CLAUDE.md). Reject them up front, and keep
        # p.name == slug as a belt-and-suspenders check.
        if slug in {".", ".."} or "/" in slug or os.sep in slug:
            return []
        for kind, root in [("project", workspace / "projects"), ("pipeline", workspace / "pipelines")]:
            p = root / slug
            if p.is_dir() and p.name == slug:
                repos.append((p, kind))
        return repos
    projects = workspace / "projects"
    if projects.is_dir():
        for p in sorted(projects.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                repos.append((p, "project"))
    pipelines = workspace / "pipelines"
    if pipelines.is_dir():
        for p in sorted(pipelines.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                repos.append((p, "pipeline"))
    return repos


def render_text(all_findings: list[Findings], workspace_findings: Findings, full: bool, title: str = "Lint report") -> str:
    out: list[str] = []
    out.append(f"# {title}\n")

    total_err = sum(len(f.errors) for f in all_findings) + len(workspace_findings.errors)
    total_warn = sum(len(f.warnings) for f in all_findings) + len(workspace_findings.warnings)
    total_info = sum(len(f.info) for f in all_findings) + len(workspace_findings.info)
    out.append(f"**Totals:** {total_err} errors, {total_warn} warnings, {total_info} info")
    if not full:
        out.append("(grouped summary; rerun with --full for every instance)\n")
    else:
        out.append("")

    def render_grouped(items, label):
        if not items:
            return
        out.append(f"\n### {label}")
        groups: dict[str, list[dict]] = defaultdict(list)
        for it in items:
            groups[it["code"]].append(it)
        for code in sorted(groups):
            entries = groups[code]
            count = len(entries)
            sample = entries if full else entries[:3]
            header = f"- **[{code}]** ({count})" if count > 1 else f"- **[{code}]**"
            out.append(header)
            for e in sample:
                tag = f" `{e['path']}`" if e["path"] else ""
                out.append(f"  -{tag} {e['msg']}")
            if not full and count > len(sample):
                out.append(f"  - … +{count - len(sample)} more")

    def render_section(f: Findings):
        if not f.total():
            return
        out.append(f"\n## {f.scope}")
        render_grouped(f.errors, "Errors")
        render_grouped(f.warnings, "Warnings")
        render_grouped(f.info, "Info")

    render_section(workspace_findings)
    for f in all_findings:
        render_section(f)

    if total_err == 0 and total_warn == 0 and total_info == 0:
        out.append("\nNo issues found.")
    return "\n".join(out)


def emit(workspace_findings: Findings, all_findings: list[Findings], as_json: bool, full: bool, title: str):
    if as_json:
        payload = {
            "workspace": workspace_findings.to_dict(),
            "repos": [f.to_dict() for f in all_findings],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_text(all_findings, workspace_findings, full=full, title=title))
    err_count = len(workspace_findings.errors) + sum(len(f.errors) for f in all_findings)
    sys.exit(1 if err_count else 0)
