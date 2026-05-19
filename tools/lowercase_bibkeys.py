#!/usr/bin/env python3
"""Migrate CamelCase BibTeX keys to lowercase across a project.

Per `research/rules/citations.md` + the literature skill, citekeys must be
lowercase `{author}{year}{word}`. This script rewrites mixed-case bib keys
to their lowercased form and updates every reference in `paper/**/*.tex`
and `docs/**/*.md`. Collisions (an existing lowercase entry already owns
the target name) abort the run so the user can resolve manually.

Usage:
  python3 lowercase_bibkeys.py <project-dir> [--apply]

Default is a dry run that prints the rename plan. Pass --apply to write.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


BIB_KEY_RE = re.compile(r"^(@\w+\s*\{\s*)([^,\s]+)(\s*,)", re.MULTILINE)
# Matches natbib + biblatex cite commands: \cite, \citep, \citet, \citeauthor,
# \nocite, \parencite, \Parencite, \textcite, \autocite, \footcite, \fullcite,
# \smartcite, \supercite, \citeyear, \citetitle, etc. — anything containing
# "cite" or "Cite" followed by a {...} argument.
TEX_CITE_RE = re.compile(
    r"(\\[A-Za-z]*[Cc]ite[A-Za-z]*\*?\s*(?:\[[^\]]*\])*\s*\{)([^}]*)(\})")
MD_CITE_RE = re.compile(r"\[cite:([A-Za-z0-9][A-Za-z0-9_-]*)\]")


def collect_bib_keys(bib_paths: list[Path]) -> dict[Path, list[str]]:
    """{bib_path: [keys in declaration order]}."""
    out: dict[Path, list[str]] = {}
    for p in bib_paths:
        text = p.read_text(encoding="utf-8", errors="replace")
        out[p] = [m.group(2) for m in BIB_KEY_RE.finditer(text)]
    return out


def build_rename_map(all_keys: dict[Path, list[str]]) -> tuple[dict[str, str], list[str]]:
    """Return (rename_map, collisions). Skips keys already lowercase."""
    flat: set[str] = set()
    for keys in all_keys.values():
        flat.update(keys)
    rename: dict[str, str] = {}
    collisions: list[str] = []
    for k in flat:
        low = k.lower()
        if low == k:
            continue
        if low in flat and low != k:
            collisions.append(f"{k} -> {low} (already taken by another entry)")
            continue
        if low in rename.values():
            other = next(orig for orig, new in rename.items() if new == low)
            collisions.append(f"{k} and {other} both lowercase to {low}")
            continue
        rename[k] = low
    return rename, collisions


def rewrite_bib(path: Path, rename: dict[str, str], apply: bool) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    n = 0
    def _sub(m):
        nonlocal n
        prefix, key, suffix = m.group(1), m.group(2), m.group(3)
        if key in rename:
            n += 1
            return f"{prefix}{rename[key]}{suffix}"
        return m.group(0)
    new = BIB_KEY_RE.sub(_sub, text)
    if apply and n:
        path.write_text(new, encoding="utf-8")
    return n


def rewrite_tex(path: Path, rename: dict[str, str], apply: bool) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    n = 0
    def _sub(m):
        nonlocal n
        prefix, keys, suffix = m.group(1), m.group(2), m.group(3)
        parts = [k.strip() for k in keys.split(",")]
        new_parts: list[str] = []
        for k in parts:
            if k in rename:
                n += 1
                new_parts.append(rename[k])
            else:
                new_parts.append(k)
        return f"{prefix}{', '.join(new_parts)}{suffix}"
    new = TEX_CITE_RE.sub(_sub, text)
    if apply and n:
        path.write_text(new, encoding="utf-8")
    return n


def rewrite_md(path: Path, rename: dict[str, str], apply: bool) -> int:
    text = path.read_text(encoding="utf-8", errors="replace")
    n = 0
    def _sub(m):
        nonlocal n
        key = m.group(1)
        if key in rename:
            n += 1
            return f"[cite:{rename[key]}]"
        return m.group(0)
    new = MD_CITE_RE.sub(_sub, text)
    if apply and n:
        path.write_text(new, encoding="utf-8")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("project", type=Path, help="Project directory (contains paper/ and docs/)")
    ap.add_argument("--apply", action="store_true", help="Write changes (default: dry run)")
    args = ap.parse_args()

    project: Path = args.project.resolve()
    paper_dir = project / "paper"
    docs_dir = project / "docs"

    bib_paths = sorted(paper_dir.glob("*.bib")) if paper_dir.is_dir() else []
    if not bib_paths:
        print(f"No .bib files in {paper_dir}", file=sys.stderr)
        return 1

    all_keys = collect_bib_keys(bib_paths)
    rename, collisions = build_rename_map(all_keys)

    print(f"# {project.name}")
    print(f"  bib files: {len(bib_paths)}")
    print(f"  total keys: {sum(len(v) for v in all_keys.values())}")
    print(f"  to rename: {len(rename)}")
    if collisions:
        print("  COLLISIONS (must resolve manually):")
        for c in collisions:
            print(f"    - {c}")
        print()
        if args.apply:
            print("  aborting --apply due to collisions", file=sys.stderr)
            return 2

    if not rename:
        print("  nothing to do.")
        return 0

    # Show a sample of the rename map
    sample = list(rename.items())[:8]
    print("  sample renames:")
    for old, new in sample:
        print(f"    {old}  ->  {new}")
    if len(rename) > 8:
        print(f"    … +{len(rename) - 8} more")

    bib_touched = tex_touched = md_touched = 0
    for p in bib_paths:
        n = rewrite_bib(p, rename, args.apply)
        if n:
            bib_touched += n
            print(f"  .bib  {p.relative_to(project)}: {n} key rewrites")
    if paper_dir.is_dir():
        for p in paper_dir.rglob("*.tex"):
            n = rewrite_tex(p, rename, args.apply)
            if n:
                tex_touched += n
                print(f"  .tex  {p.relative_to(project)}: {n} cite rewrites")
    if docs_dir.is_dir():
        for p in docs_dir.rglob("*.md"):
            n = rewrite_md(p, rename, args.apply)
            if n:
                md_touched += n
                print(f"  .md   {p.relative_to(project)}: {n} cite rewrites")

    mode = "applied" if args.apply else "would rewrite (dry run)"
    print(f"  {mode}: {bib_touched} bib + {tex_touched} tex + {md_touched} md references")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
