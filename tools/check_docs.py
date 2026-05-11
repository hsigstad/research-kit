#!/usr/bin/env python3
"""
Doc-contract and source/build layer linter for the research workspace.

Runs deterministic checks across all projects and pipelines:
  - presence of required files in docs/
  - allowed file/folder names at docs/ root
  - todo/done hygiene
  - thinking.md required sections
  - idea frontmatter validity (workspace-level)
  - source/build naming and layer conventions, including multi-output folders
  - paper-output paths
  - missing validate= on pandas merges

Usage:
  python check_docs.py                   # lint entire workspace, text report
  python check_docs.py <slug>            # lint single project or pipeline
  python check_docs.py --json            # machine-readable output
  python check_docs.py --full            # show every instance
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from _lint_common import Findings, WORKSPACE, emit, find_repos, read


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

YAML_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)

def parse_frontmatter(text: str) -> dict | None:
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
        if line.startswith(" "):
            continue
        key, _, val = line.partition(":")
        data[key.strip()] = val.strip()
    return data


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

    for name in sorted(required - present_files):
        f.err("doc.missing", f"required file missing: docs/{name}")

    for name in sorted(present_files - allowed):
        if name.startswith("."):
            continue
        hint = ""
        if name == "todos.md":
            hint = " — rename to todo.md"
        f.err(
            "doc.unallowed",
            f"unrecognized file in docs/ root: {name}{hint} (move to briefs/, notes/, or reference/, or propose canonical addition)",
            path=f"docs/{name}",
        )

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
        return

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

        for script in layer.rglob("*.py"):
            rel = script.relative_to(repo)
            base = script.stem
            if PRIVATE_PY.match(script.name):
                continue
            if layer_name in ("figure",):
                check_paper_output(repo, rel, base, paper / "figures", PAPER_FIGURE_EXTS, "figure", f)
            elif layer_name == "table":
                check_paper_output(repo, rel, base, paper / "tables", PAPER_TABLE_EXTS, "table", f)
            elif layer_name in ("clean", "intermediate", "assemble", "analysis"):
                check_data_output(repo, rel, base, build / layer_name, layer_name, f)

    # Reverse: walk build/ and paper/ outputs, flag files with no matching script.
    check_build_orphans(repo, f)

def check_build_orphans(repo: Path, f: Findings):
    src = repo / "source"
    if not src.is_dir():
        return

    def script_stems(layer: str) -> set:
        d = src / layer
        if not d.is_dir():
            return set()
        return {p.stem for p in d.glob("*.py") if not PRIVATE_PY.match(p.name)}

    def lint_dir(out_dir: Path, layer: str, exts: tuple, code_prefix: str):
        if not out_dir.is_dir():
            return
        stems = script_stems(layer)
        for item in out_dir.iterdir():
            if item.name.startswith("."):
                continue
            if item.is_dir():
                if item.name not in stems:
                    f.warn(f"{code_prefix}.orphan-folder",
                           f"{item.relative_to(repo)}/ has no matching source/{layer}/{item.name}.py",
                           path=str(item.relative_to(repo)))
                continue
            if not item.is_file():
                continue
            if item.suffix.lower() not in exts and not item.name.endswith(".csv.gz"):
                continue
            stem = item.stem
            if stem in stems:
                continue
            parent = next((s for s in stems if stem.startswith(s + "_")), None)
            if parent:
                f.warn(f"{code_prefix}.naming-violation",
                       f"{item.relative_to(repo)} should live under {out_dir.relative_to(repo)}/{parent}/ (multi-output folder convention)",
                       path=str(item.relative_to(repo)))
            else:
                f.warn(f"{code_prefix}.orphan",
                       f"{item.relative_to(repo)} has no matching source/{layer}/{stem}.py",
                       path=str(item.relative_to(repo)))

    build = repo / "build"
    paper = repo / "paper"
    for layer in ("clean", "intermediate", "assemble", "analysis"):
        lint_dir(build / layer, layer, DATA_OUTPUT_EXTS, "build")
    lint_dir(paper / "figures", "figure", PAPER_FIGURE_EXTS, "paper.figure")
    lint_dir(paper / "tables", "table", PAPER_TABLE_EXTS, "paper.table")
    lint_dir(build / "figure", "figure", PAPER_FIGURE_EXTS, "build.figure")
    lint_dir(build / "table", "table", PAPER_TABLE_EXTS + DATA_OUTPUT_EXTS, "build.table")

def check_data_output(repo: Path, script_rel: Path, base: str, expected_dir: Path, layer: str, f: Findings):
    if not expected_dir.exists():
        f.note("source.no-build-dir",
               f"source/{layer}/ has scripts but no matching build/{layer}/ directory (build may be unbuilt)",
               path=str(script_rel))
        return
    folder = expected_dir / base
    if folder.is_dir() and any(p.suffix.lower() in DATA_OUTPUT_EXTS or p.name.endswith(".csv.gz") for p in folder.iterdir() if p.is_file()):
        return
    matches = list(expected_dir.glob(f"{base}.*"))
    matches = [m for m in matches if m.suffix.lower() in DATA_OUTPUT_EXTS or m.name.endswith(".csv.gz")]
    if not matches:
        f.note("source.no-output",
               f"no build artifact for {script_rel} (expected build/{layer}/{base}.{{parquet,csv,json,...}} or build/{layer}/{base}/<name>.*) — build may be unbuilt",
               path=str(script_rel))
        return
    if layer in ("clean", "assemble", "intermediate"):
        if any(m.suffix == ".csv" for m in matches) and not any(m.suffix == ".parquet" for m in matches):
            csv_path = next(m for m in matches if m.suffix == ".csv")
            f.note("build.csv-preferred-parquet",
                   f"{csv_path.relative_to(repo)} is .csv (prefer .parquet for {layer}-layer outputs)",
                   path=str(csv_path.relative_to(repo)))

def check_paper_output(repo: Path, script_rel: Path, base: str, expected_dir: Path, exts: tuple, kind: str, f: Findings):
    if expected_dir.exists():
        folder = expected_dir / base
        if folder.is_dir() and any(p.suffix.lower() in exts for p in folder.iterdir() if p.is_file()):
            return
        matches = list(expected_dir.glob(f"{base}.*"))
        matches = [m for m in matches if m.suffix.lower() in exts]
        if matches:
            return
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
           f"no paper {kind} found for {script_rel} (expected paper/{kind}s/{base}.* or paper/{kind}s/{base}/<name>.*)",
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
# CLAUDE.md presence
# ---------------------------------------------------------------------------

def lint_claude_md(repo: Path, f: Findings, kind: str):
    if kind != "project":
        return
    if not (repo / "CLAUDE.md").is_file():
        f.warn("project.no-claude-md",
               "project root has no CLAUDE.md (required by workspace.md 'How to proceed in a session')",
               path="CLAUDE.md")


# ---------------------------------------------------------------------------
# .gitignore must exclude build/
# ---------------------------------------------------------------------------

def lint_gitignore_build(repo: Path, f: Findings):
    if not (repo / "source").is_dir():
        return  # only repos with source/ produce build artifacts
    gi = repo / ".gitignore"
    if not gi.is_file():
        f.warn("gitignore.no-build",
               "no .gitignore at repo root — build/ outputs risk being committed",
               path=".gitignore")
        return
    text = read(gi)
    has_build = any(
        re.match(r"^\s*/?build/?\s*$", line)
        for line in text.splitlines()
        if not line.lstrip().startswith("#")
    )
    if not has_build:
        f.warn("gitignore.no-build",
               ".gitignore does not exclude build/ — outputs risk being committed",
               path=".gitignore")


# ---------------------------------------------------------------------------
# decisions.md entry format: ## YYYY-MM-DD — <title>
# ---------------------------------------------------------------------------

DECISIONS_HEADER_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s+[—\-]\s+\S", re.MULTILINE)
DECISIONS_ANY_H2_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)

def lint_decisions(repo: Path, f: Findings):
    decisions = repo / "docs" / "decisions.md"
    if not decisions.is_file():
        return
    text = read(decisions)
    valid_starts = {m.start() for m in DECISIONS_HEADER_RE.finditer(text)}
    for m in DECISIONS_ANY_H2_RE.finditer(text):
        if m.start() in valid_starts:
            continue
        title = m.group(1).strip()
        # Skip non-entry headers (table of contents, etc.) — only flag those
        # that look like attempted entries (date-ish prefix or dash separator)
        if re.match(r"^\d{4}", title) or "—" in title or " - " in title:
            line_no = text[:m.start()].count("\n") + 1
            f.warn("decisions.bad-header",
                   f"decisions.md entry header doesn't match `## YYYY-MM-DD — <title>`: '## {title}'",
                   path=f"docs/decisions.md:{line_no}")


# ---------------------------------------------------------------------------
# Handoff filename format: docs/notes/handoffs/<ISO>_<tag>.md
# ---------------------------------------------------------------------------

HANDOFF_FILENAME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}(T\d{2}[-:]?\d{2}(?:[-:]?\d{2})?)?_[a-z0-9][a-z0-9\-]*\.md$"
)

def lint_handoffs(repo: Path, f: Findings):
    handoffs = repo / "docs" / "notes" / "handoffs"
    if not handoffs.is_dir():
        return
    for md in handoffs.glob("*.md"):
        if md.name == "README.md":
            continue
        if not HANDOFF_FILENAME_RE.match(md.name):
            f.warn("handoff.bad-filename",
                   f"handoff filename should be `<ISO-timestamp>_<short-tag>.md` (got '{md.name}')",
                   path=str(md.relative_to(repo)))


# ---------------------------------------------------------------------------
# Underscore-prefixed scripts shouldn't be cited from docs
# ---------------------------------------------------------------------------

def lint_underscore_cited(repo: Path, f: Findings):
    src = repo / "source"
    docs = repo / "docs"
    paper = repo / "paper"
    if not src.is_dir():
        return

    underscore_scripts: list[Path] = []
    for layer in src.iterdir():
        if not layer.is_dir() or layer.name.startswith(".") or layer.name == "__pycache__":
            continue
        for script in layer.rglob("_*.py"):
            if script.name == "__init__.py" or "__pycache__" in script.parts:
                continue
            underscore_scripts.append(script.relative_to(repo))

    if not underscore_scripts:
        return

    search_targets: list[str] = []
    for s in underscore_scripts:
        search_targets.append(str(s))                       # source/foo/_bar.py
        search_targets.append(str(s).replace("source/", "build/").replace(".py", ""))  # build/foo/_bar (folder or stem)

    for doc_dir in (docs, paper):
        if not doc_dir.is_dir():
            continue
        for md in list(doc_dir.rglob("*.md")) + list(doc_dir.rglob("*.tex")):
            text = read(md)
            for target in search_targets:
                if target in text:
                    line_no = text.find(target)
                    line_no = text[:line_no].count("\n") + 1
                    f.warn("source.underscore-cited",
                           f"doc cites underscore-prefixed (opted-out) script: {target}",
                           path=f"{md.relative_to(repo)}:{line_no}")
                    break  # one finding per doc per script is enough


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def lint_repo(repo: Path, kind: str, workspace: Path) -> Findings:
    rel = repo.relative_to(workspace)
    f = Findings(scope=str(rel))
    lint_claude_md(repo, f, kind)
    lint_gitignore_build(repo, f)
    lint_docs_root(repo, f, kind)
    lint_todo_done(repo, f)
    lint_thinking(repo, f)
    lint_decisions(repo, f)
    lint_handoffs(repo, f)
    lint_source_build(repo, f)
    lint_merge_validate(repo, f)
    lint_archive_leakage(repo, f)
    lint_underscore_cited(repo, f)
    return f


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

    emit(workspace_findings, all_findings, as_json=args.json, full=args.full, title="Doc-contract lint report")


if __name__ == "__main__":
    main()
