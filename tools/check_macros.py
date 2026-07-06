#!/usr/bin/env python3
"""
Paper numeric-macro linter, workspace-wide.

Generalizes projects/electoral-justice/source/paper/check_macros.py to
every project that uses the paper-macro system
(research-kit/rules/paper_macros.md). A project opts in by having a
generated numbers.tex; projects without one are skipped.

Checks, per project:
  * undefined macros (error)  -- a token in the paper that matches a
    macro-family prefix but has no \\newcommand in numbers.tex; the
    paper builds with a cryptic error or, worse, renders stale text
  * dead macros (warning)     -- defined in numbers.tex but never cited
    in any paper .tex; usually a renamed or abandoned number
  * stale numbers.tex (warning) -- the generator script is newer than
    the generated numbers.tex, so the paper may cite outdated values.
    This is the lint form of the 2026-07-05 electoral-justice incident
    (paper carried pre-correction estimates).

Usage:
  python check_macros.py                # all projects, text report
  python check_macros.py <slug>         # one project
  python check_macros.py --json         # machine-readable
  python check_macros.py --workspace P  # explicit workspace root
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from _lint_common import Findings, WORKSPACE, emit, find_repos, read

NUMBERS_CANDIDATES = ("paper/numbers.tex", "build/paper/numbers.tex")
GENERATOR_CANDIDATES = ("source/paper/numbers.py",)
NEWCOMMAND_RE = re.compile(r"\\(?:re)?newcommand\{\\([A-Za-z]+)\}")
CONTROL_WORD_RE = re.compile(r"\\([A-Za-z]+)")
PREFIX_RE = re.compile(r"^([A-Z][a-z]+)")


def _strip_comments(tex: str) -> str:
    out = []
    for line in tex.splitlines():
        m = re.search(r"(?<!\\)%", line)
        out.append(line if m is None else line[: m.start()])
    return "\n".join(out)


def paper_tex_files(repo: Path, numbers: Path) -> list[Path]:
    paper = repo / "paper"
    if not paper.is_dir():
        return []
    return [p for p in sorted(paper.glob("*.tex")) if p.resolve() != numbers.resolve()]


def lint_repo_macros(repo: Path, workspace: Path) -> Findings | None:
    f = Findings(scope=str(repo.relative_to(workspace)))
    numbers = next(
        (repo / rel for rel in NUMBERS_CANDIDATES if (repo / rel).is_file()), None
    )
    if numbers is None:
        return None  # project does not use the macro system

    defined = set(NEWCOMMAND_RE.findall(read(numbers)))
    tex_files = paper_tex_files(repo, numbers)
    used: set[str] = set()
    for p in tex_files:
        used |= set(CONTROL_WORD_RE.findall(_strip_comments(read(p))))

    rel_numbers = numbers.relative_to(workspace)
    for name in sorted(defined - used):
        f.warn(
            "macro.dead",
            f"\\{name} defined in {rel_numbers.name} but never cited in paper/*.tex",
            path=str(rel_numbers),
        )

    # Undefined: tokens that share a defined macro family's prefix
    # (e.g. Desc, Bunch, Enf) continued in CamelCase, without a
    # definition. The CamelCase requirement keeps package commands
    # like \Description out.
    prefixes = {m.group(1) for name in defined if (m := PREFIX_RE.match(name))}
    for tok in sorted(used - defined):
        pm = PREFIX_RE.match(tok)
        if pm and pm.group(1) in prefixes and len(tok) > len(pm.group(1)) \
                and tok[len(pm.group(1))].isupper():
            f.err(
                "macro.undefined",
                f"\\{tok} used in paper/*.tex but not defined in {rel_numbers.name}",
                path=str(rel_numbers),
            )

    generator = next(
        (repo / rel for rel in GENERATOR_CANDIDATES if (repo / rel).is_file()), None
    )
    if generator is not None and generator.stat().st_mtime > numbers.stat().st_mtime:
        f.warn(
            "macro.stale-numbers",
            f"{generator.relative_to(repo)} is newer than {rel_numbers.name} — "
            "regenerate before trusting paper numbers",
            path=str(rel_numbers),
        )
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?", help="optional project slug to lint alone")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--workspace", type=Path, default=WORKSPACE)
    args = ap.parse_args()

    workspace = args.workspace.expanduser().resolve()
    repos = [r for r, kind in find_repos(workspace, args.slug) if kind == "project"]

    workspace_findings = Findings(scope="workspace")
    if not repos:
        workspace_findings.err(
            "workspace.no-repos",
            f"no project repos found under {workspace} — wrong --workspace / "
            "RESEARCH_WORKSPACE? A scan of zero repos must not read as clean.",
        )

    all_findings = [
        lf for repo in repos if (lf := lint_repo_macros(repo, workspace)) is not None
    ]
    emit(workspace_findings, all_findings, as_json=args.json, full=args.full,
         title="Paper macro lint report")


if __name__ == "__main__":
    main()
