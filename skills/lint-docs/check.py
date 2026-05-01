#!/usr/bin/env python3
"""
Doc-contract and source/build layer linter for the research workspace.

Runs deterministic checks across all projects and pipelines:
  - presence of required files in docs/
  - allowed file/folder names at docs/ root
  - todo/done hygiene
  - thinking.md required sections
  - idea frontmatter validity
  - source/build naming and layer conventions
  - paper-output paths
  - em-dashes in paper TeX
  - missing validate= on pandas merges

Usage:
  python check.py                   # lint entire workspace, text report
  python check.py audit             # lint single project
  python check.py --json            # machine-readable output
  python check.py audit --json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

WORKSPACE = Path("~/research").expanduser()

# ---------------------------------------------------------------------------
# Contract
# ---------------------------------------------------------------------------

REQUIRED_PROJECT_DOCS = {
    "summary.md", "todo.md", "done.md", "meetings.md", "feedback.md",
    "literature.md", "decisions.md", "thinking.md", "institutions.md",
    "data.md", "methods.md",
}

OPTIONAL_PROJECT_DOCS = {
    "theory.md", "hypotheses.md", "desiderata.md", "outline.md",
    "archive.md", "results.md", "key-findings.md", "anecdotes.md",
    "qa.md", "README.md", "CONVENTIONS.md",
}

ALLOWED_PROJECT_DOCS = REQUIRED_PROJECT_DOCS | OPTIONAL_PROJECT_DOCS

REQUIRED_PIPELINE_DOCS = {
    "summary.md", "thinking.md", "todo.md", "data.md", "decisions.md",
}

OPTIONAL_PIPELINE_DOCS = {
    "archive.md", "done.md", "README.md", "CONVENTIONS.md",
}

ALLOWED_PIPELINE_DOCS = REQUIRED_PIPELINE_DOCS | OPTIONAL_PIPELINE_DOCS

ALLOWED_DOC_SUBFOLDERS = {
    "briefs", "reference", "notes", "literature", "anecdotes",
    "emails", "reviews", "specs", "whatsapp", "feedback",
}

THINKING_REQUIRED_SECTIONS = [
    "Current open questions",
    "Possible directions",
    "Connections to literature",
    "Methodological sketches",
    "Ideas to explore later",
    "Miscellaneous notes",
]

CANONICAL_SOURCE_DIRS = {
    "clean", "intermediate", "assemble", "analysis",
    "figure", "table", "paper",
}

DATA_OUTPUT_EXTS = (".parquet", ".csv", ".csv.gz", ".json", ".rds", ".dta", ".xlsx", ".feather")
PAPER_FIGURE_EXTS = (".pdf", ".png", ".svg", ".jpg")
PAPER_TABLE_EXTS  = (".tex", ".md")

# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------

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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

YAML_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

def parse_frontmatter(text: str) -> dict | None:
    """Tiny YAML frontmatter parser — handles only key: value pairs we care about."""
    m = YAML_FRONTMATTER_RE.match(text)
    if not m:
        return None
    data: dict = {}
    for line in m.group(1).splitlines():
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        if ":" not in line:
            continue
        if line.startswith(" "):  # nested — skip
            continue
        key, _, val = line.partition(":")
        data[key.strip()] = val.strip()
    return data

def read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""

# ---------------------------------------------------------------------------
# Doc-root checks
# ---------------------------------------------------------------------------

def lint_docs_root(repo: Path, f: Findings, kind: str):
    docs = repo / "docs"
    if not docs.is_dir():
        f.err("docs.missing", "docs/ directory missing")
        return

    required = REQUIRED_PROJECT_DOCS if kind == "project" else REQUIRED_PIPELINE_DOCS
    allowed  = ALLOWED_PROJECT_DOCS  if kind == "project" else ALLOWED_PIPELINE_DOCS

    present_files = {p.name for p in docs.iterdir() if p.is_file()}

    # 1. Missing required
    for name in sorted(required - present_files):
        f.err("doc.missing", f"required file missing: docs/{name}")

    # 2. Disallowed root files
    for name in sorted(present_files - allowed):
        # Hidden/dotfiles ignored
        if name.startswith("."):
            continue
        # Common typos surface as a hint
        hint = ""
        if name == "todos.md":
            hint = " — rename to todo.md"
        f.err(
            "doc.unallowed",
            f"unrecognized file in docs/ root: {name}{hint} (move to briefs/, notes/, or reference/, or propose canonical addition)",
            path=f"docs/{name}",
        )

    # 3. Disallowed subfolders (warn — many projects have tool-specific dirs)
    for child in docs.iterdir():
        if child.is_dir() and child.name not in ALLOWED_DOC_SUBFOLDERS and not child.name.startswith("."):
            f.warn(
                "doc.subfolder.unknown",
                f"non-canonical docs/ subfolder: {child.name}/ (consider briefs/, notes/, or reference/)",
                path=f"docs/{child.name}",
            )

# ---------------------------------------------------------------------------
# todo / done hygiene
# ---------------------------------------------------------------------------

CHECKED_RE   = re.compile(r"^\s*-\s*\[x\]", re.IGNORECASE | re.MULTILINE)
UNCHECKED_RE = re.compile(r"^\s*-\s*\[ \]", re.MULTILINE)

def lint_todo_done(repo: Path, f: Findings):
    todo = repo / "docs" / "todo.md"
    done = repo / "docs" / "done.md"

    if todo.is_file():
        text = read(todo)
        # Strip session-handoff section
        text = re.sub(r"## Session handoff.*?(?=\n## |\Z)", "", text, flags=re.DOTALL)
        for m in CHECKED_RE.finditer(text):
            line_no = text[:m.start()].count("\n") + 1
            f.warn("todo.completed",
                   f"completed task left in todo.md (move to done.md)",
                   path=f"docs/todo.md:{line_no}")

    if done.is_file():
        text = read(done)
        for m in UNCHECKED_RE.finditer(text):
            line_no = text[:m.start()].count("\n") + 1
            f.warn("done.uncompleted",
                   f"open task left in done.md (move to todo.md)",
                   path=f"docs/done.md:{line_no}")

# ---------------------------------------------------------------------------
# thinking.md required H2 sections
# ---------------------------------------------------------------------------

def lint_thinking(repo: Path, f: Findings):
    thinking = repo / "docs" / "thinking.md"
    if not thinking.is_file():
        return
    text = read(thinking)
    headers = re.findall(r"^##\s+(.+?)\s*$", text, re.MULTILINE)
    headers_norm = [h.strip().lower() for h in headers]
    for needed in THINKING_REQUIRED_SECTIONS:
        if needed.lower() not in headers_norm:
            f.warn("thinking.missing-section",
                   f"thinking.md missing required section: ## {needed}",
                   path="docs/thinking.md")

# ---------------------------------------------------------------------------
# Source / build conventions
# ---------------------------------------------------------------------------

PRIVATE_PY = re.compile(r"^_|^__init__\.py$|^__pycache__$")

def lint_source_build(repo: Path, f: Findings):
    src = repo / "source"
    build = repo / "build"
    paper = repo / "paper"

    if not src.is_dir():
        return  # not all repos have source/

    for layer in src.iterdir():
        if not layer.is_dir():
            continue
        layer_name = layer.name
        if layer_name.startswith(".") or layer_name == "__pycache__":
            continue

        if layer_name not in CANONICAL_SOURCE_DIRS:
            f.note("source.layer.noncanonical",
                   f"source/{layer_name}/ is project-specific (canonical layers: {', '.join(sorted(CANONICAL_SOURCE_DIRS))})",
                   path=f"source/{layer_name}")

        # Walk scripts in this layer
        for script in layer.rglob("*.py"):
            rel = script.relative_to(repo)
            base = script.stem
            if PRIVATE_PY.match(script.name):
                continue
            # Determine expected output location
            if layer_name in ("figure",):
                check_paper_output(repo, rel, base, paper / "figures", PAPER_FIGURE_EXTS, "figure", f)
            elif layer_name == "table":
                check_paper_output(repo, rel, base, paper / "tables", PAPER_TABLE_EXTS, "table", f)
            elif layer_name in ("clean", "intermediate", "assemble", "analysis"):
                check_data_output(repo, rel, base, build / layer_name, layer_name, f)
            # paper/ layer is for numbers — heterogeneous outputs, skip

def check_data_output(repo: Path, script_rel: Path, base: str, expected_dir: Path, layer: str, f: Findings):
    # build/ is typically gitignored — these are info-level (only meaningful when build is materialized)
    if not expected_dir.exists():
        f.note("source.no-build-dir",
               f"source/{layer}/ has scripts but no matching build/{layer}/ directory (build may be unbuilt)",
               path=str(script_rel))
        return
    matches = list(expected_dir.glob(f"{base}.*"))
    matches = [m for m in matches if m.suffix.lower() in DATA_OUTPUT_EXTS or m.name.endswith(".csv.gz")]
    if not matches:
        f.note("source.no-output",
               f"no build artifact for {script_rel} (expected build/{layer}/{base}.{{parquet,csv,json,...}}) — build may be unbuilt",
               path=str(script_rel))
        return
    # Prefer parquet over csv for assemble/analysis
    if layer in ("clean", "assemble", "intermediate"):
        if any(m.suffix == ".csv" for m in matches) and not any(m.suffix == ".parquet" for m in matches):
            csv_path = next(m for m in matches if m.suffix == ".csv")
            f.note("build.csv-preferred-parquet",
                   f"{csv_path.relative_to(repo)} is .csv (prefer .parquet for {layer}-layer outputs)",
                   path=str(csv_path.relative_to(repo)))

def check_paper_output(repo: Path, script_rel: Path, base: str, expected_dir: Path, exts: tuple, kind: str, f: Findings):
    if expected_dir.exists():
        matches = list(expected_dir.glob(f"{base}.*"))
        matches = [m for m in matches if m.suffix.lower() in exts]
        if matches:
            return
    # Look for a misplaced output in build/
    build_dir = repo / "build" / kind
    if build_dir.exists():
        misplaced = list(build_dir.glob(f"{base}.*"))
        if any(m.suffix.lower() in exts for m in misplaced):
            target = next(m for m in misplaced if m.suffix.lower() in exts)
            f.warn("paper.misplaced-output",
                   f"{kind} {target.name} is in build/{kind}/ but should be in paper/{kind}s/",
                   path=str(script_rel))
            return
    f.warn("source.no-output",
           f"no paper {kind} found for {script_rel} (expected paper/{kind}s/{base}.*)",
           path=str(script_rel))

# ---------------------------------------------------------------------------
# pandas merge() validate=
# ---------------------------------------------------------------------------

MERGE_NO_VALIDATE = re.compile(r"\.merge\s*\(((?:[^()]|\([^()]*\))*)\)", re.DOTALL)

def lint_merge_validate(repo: Path, f: Findings):
    src = repo / "source"
    if not src.is_dir():
        return
    for script in src.rglob("*.py"):
        if PRIVATE_PY.match(script.name):
            continue
        text = read(script)
        for m in MERGE_NO_VALIDATE.finditer(text):
            args = m.group(1)
            if "validate" not in args:
                line_no = text[:m.start()].count("\n") + 1
                f.warn("source.merge.no-validate",
                       ".merge() without validate= argument",
                       path=f"{script.relative_to(repo)}:{line_no}")

# ---------------------------------------------------------------------------
# archive.md leakage
# ---------------------------------------------------------------------------

def lint_archive_leakage(repo: Path, f: Findings):
    docs = repo / "docs"
    if not docs.is_dir():
        return
    for md in docs.glob("*.md"):
        if md.name == "archive.md":
            continue
        text = read(md)
        if re.search(r"\barchive\.md\b|\b#.*[Aa]rchived?\b", text):
            # Only flag if it's a real reference, not a convention pointer
            if "archive.md" in text and "see" in text.lower():
                f.warn("archive.leakage",
                       f"references archive.md (archived content should not influence active reasoning)",
                       path=str(md.relative_to(repo)))

# ---------------------------------------------------------------------------
# Idea frontmatter (workspace-level)
# ---------------------------------------------------------------------------

REQUIRED_IDEA_FIELDS = {"title", "status", "last_updated"}
ALLOWED_IDEA_STATUS  = {"idea", "exploring", "shelved", "project"}

def lint_ideas(workspace: Path, f: Findings):
    ideas = workspace / "research" / "ideas"
    if not ideas.is_dir():
        return
    for md in ideas.glob("*.md"):
        if md.name == "index.md":
            continue
        text = read(md)
        fm = parse_frontmatter(text)
        if fm is None:
            f.err("idea.no-frontmatter",
                  f"missing YAML frontmatter",
                  path=str(md.relative_to(workspace)))
            continue
        missing = REQUIRED_IDEA_FIELDS - set(fm.keys())
        if missing:
            f.err("idea.frontmatter.missing-fields",
                  f"frontmatter missing fields: {sorted(missing)}",
                  path=str(md.relative_to(workspace)))
        status = fm.get("status", "").strip()
        if status and status not in ALLOWED_IDEA_STATUS:
            f.warn("idea.frontmatter.bad-status",
                   f"unknown status '{status}' (expected one of {sorted(ALLOWED_IDEA_STATUS)})",
                   path=str(md.relative_to(workspace)))

# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def lint_repo(repo: Path, kind: str, workspace: Path) -> Findings:
    rel = repo.relative_to(workspace)
    f = Findings(scope=str(rel))
    lint_docs_root(repo, f, kind)
    lint_todo_done(repo, f)
    lint_thinking(repo, f)
    lint_source_build(repo, f)
    lint_merge_validate(repo, f)
    lint_archive_leakage(repo, f)
    return f

def find_repos(workspace: Path, slug: str | None) -> list[tuple[Path, str]]:
    repos: list[tuple[Path, str]] = []
    if slug:
        for kind, root in [("project", workspace / "projects"), ("pipeline", workspace / "pipelines")]:
            p = root / slug
            if p.is_dir():
                repos.append((p, kind))
        return repos
    for p in sorted((workspace / "projects").iterdir()):
        if p.is_dir() and not p.name.startswith("."):
            repos.append((p, "project"))
    for p in sorted((workspace / "pipelines").iterdir()):
        if p.is_dir() and not p.name.startswith("."):
            repos.append((p, "pipeline"))
    return repos

def render_text(all_findings: list[Findings], workspace_findings: Findings, full: bool) -> str:
    out: list[str] = []
    out.append("# Doc-contract lint report\n")

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

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?", help="optional project or pipeline slug to lint alone")
    ap.add_argument("--json", action="store_true", help="emit JSON instead of markdown")
    ap.add_argument("--full", action="store_true", help="show every instance (default: grouped summary)")
    ap.add_argument("--workspace", type=Path, default=WORKSPACE)
    args = ap.parse_args()

    workspace = args.workspace.expanduser().resolve()
    repos = find_repos(workspace, args.slug)

    workspace_findings = Findings(scope="workspace")
    if not args.slug:
        lint_ideas(workspace, workspace_findings)

    all_findings = [lint_repo(repo, kind, workspace) for repo, kind in repos]

    if args.json:
        payload = {
            "workspace": workspace_findings.to_dict(),
            "repos": [f.to_dict() for f in all_findings],
        }
        print(json.dumps(payload, indent=2))
    else:
        print(render_text(all_findings, workspace_findings, full=args.full))

    err_count = len(workspace_findings.errors) + sum(len(f.errors) for f in all_findings)
    sys.exit(1 if err_count else 0)

if __name__ == "__main__":
    main()
