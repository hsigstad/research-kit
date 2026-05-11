#!/usr/bin/env python3
"""
Citation token linter and manifest sync for the research workspace.

Lints [ns:key] citation tokens against:
  - external registry (research/refs/registry.toml)
  - internal anchors (docs/ "- id: ns:key" or paper \\label{ns:key})
  - literature .bib files

And regenerates docs/refs/manifest.toml for each project from the registry.

Usage:
  python citations.py                  # lint citations across workspace
  python citations.py <slug>           # one project
  python citations.py --sync           # regenerate manifests
  python citations.py --sync <slug>    # regenerate one project's manifest
  python citations.py --json
"""

from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

from _lint_common import Findings, WORKSPACE, emit, find_repos, read


# ---------------------------------------------------------------------------
# Citation namespaces
# ---------------------------------------------------------------------------

EXTERNAL_NAMESPACES = {
    "method", "catalog", "pipeline", "var", "idea", "proj", "inst",
}

INTERNAL_NAMESPACES = {
    "sec", "tab", "fig", "eq", "hyp", "decision", "result",
    "local-inst", "dataset", "local-method",
}

LITERATURE_NAMESPACE = "cite"

ALL_NAMESPACES = EXTERNAL_NAMESPACES | INTERNAL_NAMESPACES | {LITERATURE_NAMESPACE}

INTERNAL_ANCHOR_FILES = {
    "hyp":          "docs/hypotheses.md",
    "decision":     "docs/decisions.md",
    "result":       "docs/results.md",
    "local-inst":   "docs/institutions.md",
    "dataset":      "docs/data.md",
    "local-method": "docs/methods.md",
}

CITATION_TOKEN_RE = re.compile(
    r"(?<!`)"
    r"\[([a-z][a-z0-9-]*):"
    r"([a-zA-Z0-9_-]+)"
    r"\]"
    r"(?!`)"
)

MALFORMED_TOKEN_RE = re.compile(
    r"\[([A-Z][a-zA-Z0-9-]*):"
    r"([a-zA-Z0-9_-]+)\]"
    r"|\[([a-z][a-z0-9-]*):"
    r"([a-zA-Z0-9_]*[A-Z_][a-zA-Z0-9_]*)\]"
)

SKIP_DOC_SUBDIRS = {"emails", "whatsapp"}


# ---------------------------------------------------------------------------
# Registry TOML parser (simple key=value + [section] format)
# ---------------------------------------------------------------------------

def parse_registry(path: Path) -> dict[str, dict[str, str]]:
    """Parse registry.toml into {ns.key: {title, description, path?, anchor?}}."""
    entries: dict[str, dict[str, str]] = {}
    if not path.is_file():
        return entries
    current_section: str | None = None
    current: dict[str, str] = {}
    section_re = re.compile(r"^\[([a-z][a-z0-9_-]*\.[a-zA-Z0-9_-]+)\]\s*$")
    kv_re = re.compile(r'^(\w+)\s*=\s*"(.*?)"\s*$')

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sm = section_re.match(line)
        if sm:
            if current_section and current:
                entries[current_section] = current
            current_section = sm.group(1)
            current = {}
            continue
        kvm = kv_re.match(line)
        if kvm and current_section:
            current[kvm.group(1)] = kvm.group(2)
    if current_section and current:
        entries[current_section] = current
    return entries


def registry_lookup_key(registry: dict[str, dict[str, str]], ns: str, key: str) -> dict[str, str] | None:
    ns_map = {
        "method": "method", "catalog": "catalog", "pipeline": "pipeline",
        "var": "var", "idea": "idea", "proj": "project", "inst": "inst",
    }
    reg_ns = ns_map.get(ns, ns)
    return registry.get(f"{reg_ns}.{key}")


# ---------------------------------------------------------------------------
# BibTeX key extractor
# ---------------------------------------------------------------------------

BIB_KEY_RE = re.compile(r"@\w+\{([^,\s]+),")

def extract_bib_keys(repo: Path) -> set[str]:
    keys: set[str] = set()
    for bib_dir in [repo / "paper", repo / "docs" / "refs"]:
        if not bib_dir.is_dir():
            continue
        for bib in bib_dir.glob("*.bib"):
            for m in BIB_KEY_RE.finditer(read(bib)):
                keys.add(m.group(1))
    return keys


# ---------------------------------------------------------------------------
# Internal anchor scanner
# ---------------------------------------------------------------------------

ANCHOR_ID_RE = re.compile(r"^\s*-\s*id:\s*(\S+)", re.MULTILINE)
LATEX_LABEL_RE = re.compile(r"\\label\{([^}]+)\}")

def extract_internal_anchors(repo: Path) -> set[str]:
    return {a for a, _locs in extract_internal_anchors_located(repo).items()}


def extract_internal_anchors_located(repo: Path) -> dict[str, list[tuple[str, int]]]:
    """Like extract_internal_anchors, but returns per-anchor (file, line_no) locations."""
    anchors: dict[str, list[tuple[str, int]]] = {}

    docs = repo / "docs"
    if docs.is_dir():
        for md in docs.rglob("*.md"):
            text = read(md)
            rel = str(md.relative_to(repo))
            for m in ANCHOR_ID_RE.finditer(text):
                line_no = text[:m.start()].count("\n") + 1
                anchors.setdefault(m.group(1), []).append((rel, line_no))

    paper = repo / "paper"
    if paper.is_dir():
        for tex in paper.rglob("*.tex"):
            text = read(tex)
            rel = str(tex.relative_to(repo))
            for m in LATEX_LABEL_RE.finditer(text):
                line_no = text[:m.start()].count("\n") + 1
                anchors.setdefault(m.group(1), []).append((rel, line_no))

    return anchors


# ---------------------------------------------------------------------------
# Citation token scanner
# ---------------------------------------------------------------------------

def scan_tokens(repo: Path) -> list[tuple[str, str, str, int]]:
    tokens: list[tuple[str, str, str, int]] = []
    search_dirs = [repo / "docs", repo / "paper"]

    for d in search_dirs:
        if not d.is_dir():
            continue
        globs = list(d.rglob("*.md")) + list(d.rglob("*.tex"))
        for f in globs:
            try:
                parts = f.relative_to(d).parts
                if parts and parts[0] in SKIP_DOC_SUBDIRS:
                    continue
            except ValueError:
                pass
            text = read(f)
            rel = str(f.relative_to(repo))
            cleaned = re.sub(r"`[^`]+`", "", text)
            for m in CITATION_TOKEN_RE.finditer(cleaned):
                line_no = cleaned[:m.start()].count("\n") + 1
                tokens.append((m.group(1), m.group(2), rel, line_no))
    return tokens


def scan_malformed_tokens(repo: Path) -> list[tuple[str, str, int]]:
    results: list[tuple[str, str, int]] = []
    search_dirs = [repo / "docs", repo / "paper"]

    for d in search_dirs:
        if not d.is_dir():
            continue
        for f in list(d.rglob("*.md")) + list(d.rglob("*.tex")):
            try:
                parts = f.relative_to(d).parts
                if parts and parts[0] in SKIP_DOC_SUBDIRS:
                    continue
            except ValueError:
                pass
            text = read(f)
            rel = str(f.relative_to(repo))
            cleaned = re.sub(r"`[^`]+`", "", text)
            for m in MALFORMED_TOKEN_RE.finditer(cleaned):
                line_no = cleaned[:m.start()].count("\n") + 1
                token_text = m.group(0)
                results.append((token_text, rel, line_no))
    return results


# ---------------------------------------------------------------------------
# Citation lint
# ---------------------------------------------------------------------------

def lint_citations(repo: Path, f: Findings, kind: str, registry: dict[str, dict[str, str]]):
    tokens = scan_tokens(repo)
    bib_keys = extract_bib_keys(repo)
    anchor_locations = extract_internal_anchors_located(repo)
    internal_anchors = set(anchor_locations.keys())

    # Anchor uniqueness — scoping:
    #   - docs/  : globally unique across all .md files
    #   - paper/ : unique within a single .tex file (separate .tex files are
    #              independent documents, so e.g. main.tex and companion.tex
    #              may both define \label{sec:intro})
    for anchor, locs in anchor_locations.items():
        # group locs by scope-key
        by_scope: dict[str, list[tuple[str, int]]] = {}
        for path, line_no in locs:
            scope = path if path.endswith(".tex") else "docs"
            by_scope.setdefault(scope, []).append((path, line_no))
        for scope, scope_locs in by_scope.items():
            if len(scope_locs) < 2:
                continue
            primary = scope_locs[0]
            others = ", ".join(f"{p}:{l}" for p, l in scope_locs[1:])
            scope_desc = "docs" if scope == "docs" else scope
            f.err("anchor.duplicate",
                  f"anchor [{anchor}] declared in {len(scope_locs)} places within {scope_desc}: also at {others}",
                  path=f"{primary[0]}:{primary[1]}")

    used_external: set[tuple[str, str]] = set()

    for ns, key, rel, line_no in tokens:
        path_ref = f"{rel}:{line_no}"

        if ns in EXTERNAL_NAMESPACES:
            used_external.add((ns, key))
            entry = registry_lookup_key(registry, ns, key)
            if entry is None:
                f.err("cite.unresolved-external",
                      f"[{ns}:{key}] not found in workspace registry",
                      path=path_ref)

        elif ns == LITERATURE_NAMESPACE:
            if key not in bib_keys:
                f.err("cite.unresolved-bib",
                      f"[cite:{key}] not found in any .bib file",
                      path=path_ref)

        elif ns in INTERNAL_NAMESPACES:
            full_id = f"{ns}:{key}"
            if full_id not in internal_anchors:
                f.err("cite.unresolved-internal",
                      f"[{ns}:{key}] has no matching anchor (expected '- id: {ns}:{key}' or \\label{{{ns}:{key}}})",
                      path=path_ref)

        else:
            f.warn("cite.unknown-namespace",
                   f"[{ns}:{key}] uses unknown namespace '{ns}'",
                   path=path_ref)

    for token_text, rel, line_no in scan_malformed_tokens(repo):
        f.warn("cite.malformed",
               f"malformed citation token {token_text} (namespaces and keys must be lowercase kebab-case)",
               path=f"{rel}:{line_no}")

    if kind == "project":
        manifest_path = repo / "docs" / "refs" / "manifest.toml"
        manifest_present_keys: set[tuple[str, str]] = set()
        token_ns_map = {
            "method": "method", "catalog": "catalog", "pipeline": "pipeline",
            "var": "var", "idea": "idea", "project": "proj", "inst": "inst",
        }
        ns_to_reg = {v: k for k, v in token_ns_map.items()}

        if manifest_path.is_file():
            manifest = parse_registry(manifest_path)
            for section_key in manifest:
                parts = section_key.split(".", 1)
                if len(parts) != 2:
                    continue
                reg_ns, entry_key = parts
                token_ns = token_ns_map.get(reg_ns, reg_ns)
                manifest_present_keys.add((token_ns, entry_key))
                if (token_ns, entry_key) not in used_external:
                    f.warn("cite.orphan-manifest",
                           f"manifest entry [{section_key}] is not cited in any doc",
                           path="docs/refs/manifest.toml")

        # Reverse drift: cited externals that resolve in the registry but
        # aren't present in this project's manifest. Fix: /cite-sync.
        for (ns, key) in sorted(used_external):
            if (ns, key) in manifest_present_keys:
                continue
            if registry_lookup_key(registry, ns, key) is None:
                continue  # already reported as cite.unresolved-external
            reg_ns = ns_to_reg.get(ns, ns)
            f.warn("cite.missing-from-manifest",
                   f"[{ns}:{key}] is cited and in the registry but missing from docs/refs/manifest.toml (run /cite-sync to regenerate)",
                   path="docs/refs/manifest.toml")


def lint_citations_workspace(workspace: Path, registry: dict[str, dict[str, str]], f: Findings):
    for section_key, entry in registry.items():
        if section_key == "meta.version" or not isinstance(entry, dict):
            continue
        file_path = entry.get("path")
        if file_path and not (workspace / file_path).exists():
            f.warn("cite.registry-dangling",
                   f"registry [{section_key}] points to {file_path} which does not exist",
                   path="research/refs/registry.toml")


# ---------------------------------------------------------------------------
# Manifest sync
# ---------------------------------------------------------------------------

def sync_manifest(repo: Path, registry: dict[str, dict[str, str]], dry_run: bool = False) -> tuple[Path, bool, str]:
    tokens = scan_tokens(repo)

    used_external: dict[str, set[str]] = defaultdict(set)
    for ns, key, _rel, _line in tokens:
        if ns in EXTERNAL_NAMESPACES:
            used_external[ns].add(key)

    lines: list[str] = []
    lines.append("# Project citation manifest")
    lines.append("#")
    lines.append("# Auto-generated by: python citations.py --sync")
    lines.append("# Source of truth: research/refs/registry.toml")
    lines.append("#")
    lines.append("# Each entry is a workspace citation used in this project's docs.")
    lines.append("# Coauthors with project-only access can read titles and descriptions")
    lines.append("# here without seeing workspace-internal paths.")
    lines.append("")

    ns_order = ["method", "catalog", "pipeline", "var", "idea", "proj", "inst"]
    ns_to_reg = {
        "method": "method", "catalog": "catalog", "pipeline": "pipeline",
        "var": "var", "idea": "idea", "proj": "project", "inst": "inst",
    }

    entry_count = 0
    for ns in ns_order:
        keys = sorted(used_external.get(ns, []))
        if not keys:
            continue
        reg_ns = ns_to_reg[ns]
        for key in keys:
            entry = registry.get(f"{reg_ns}.{key}")
            if entry is None:
                continue
            lines.append(f"[{reg_ns}.{key}]")
            lines.append(f'title = "{entry.get("title", "")}"')
            lines.append(f'description = "{entry.get("description", "")}"')
            lines.append("")
            entry_count += 1

    content = "\n".join(lines) + "\n" if entry_count > 0 else ""

    manifest_path = repo / "docs" / "refs" / "manifest.toml"
    existing = read(manifest_path) if manifest_path.is_file() else ""
    changed = content != existing

    if not dry_run and changed and content:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(content, encoding="utf-8")

    return manifest_path, changed, content


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def lint_repo(repo: Path, kind: str, workspace: Path, registry: dict[str, dict[str, str]]) -> Findings:
    rel = repo.relative_to(workspace)
    f = Findings(scope=str(rel))
    lint_citations(repo, f, kind, registry)
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug", nargs="?", help="optional project or pipeline slug")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--full", action="store_true")
    ap.add_argument("--sync", action="store_true",
                    help="regenerate docs/refs/manifest.toml for each project from registry")
    ap.add_argument("--dry-run", action="store_true",
                    help="with --sync: show what would change without writing")
    ap.add_argument("--workspace", type=Path, default=WORKSPACE)
    args = ap.parse_args()

    workspace = args.workspace.expanduser().resolve()
    registry_path = workspace / "research" / "refs" / "registry.toml"
    registry = parse_registry(registry_path)
    if not registry:
        print("ERROR: could not parse registry at", registry_path, file=sys.stderr)
        sys.exit(1)

    if args.sync:
        repos = find_repos(workspace, args.slug)
        changed_repos: list[str] = []
        verb = "would update" if args.dry_run else "updated"
        for repo, kind in repos:
            if kind != "project":
                continue
            manifest_path, changed, _content = sync_manifest(repo, registry, dry_run=args.dry_run)
            rel = repo.relative_to(workspace)
            if changed:
                changed_repos.append(str(rel))
                print(f"  {verb}  {manifest_path.relative_to(workspace)}")
            elif manifest_path.is_file():
                print(f"  current  {manifest_path.relative_to(workspace)}")
            else:
                print(f"  (empty)  {rel}/docs/refs/manifest.toml — no external citations")
        if changed_repos:
            print(f"\nManifests updated in: {', '.join(changed_repos)}")
        else:
            print("\nAll manifests up to date.")
        sys.exit(0)

    repos = find_repos(workspace, args.slug)
    workspace_findings = Findings(scope="workspace")
    if not args.slug:
        lint_citations_workspace(workspace, registry, workspace_findings)

    all_findings = [lint_repo(repo, kind, workspace, registry) for repo, kind in repos]

    emit(workspace_findings, all_findings, as_json=args.json, full=args.full, title="Citation lint report")


if __name__ == "__main__":
    main()
