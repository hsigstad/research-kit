#!/usr/bin/env python3
"""
Coverage dashboard for the workspace research conventions.

Reads (best-effort; all optional — missing files skip cleanly):

  docs/reference/artifacts.yaml      script ↔ artifact ↔ doc reverse index
                                     (research-kit/rules/artifacts_yaml.md)
  docs/validation.yaml               verification ledger
  (legacy fallback: paper/validation.yaml)
                                     (research-kit/meta/validation_ledger.md)
  source/{table,figure}/*.py         analysis scripts
  build/{table,figure}/*             output artifacts and
  build/{table,figure}/*.run.json    provenance sidecars
                                     (research-kit/rules/run_json.md)
  docs/reference/key-findings.md     curated findings index (light parse)

Emits a single-screen health report grouped by index. Each check fires a
traffic-light glyph (✓ pass, ⚠ minor, ✗ major) plus counts. Pass --detail
to enumerate offending items; --json for machine-readable output.

Read-only — never writes. Run before each /next session, after a refactor,
or on a schedule to catch drift in the conventions.

Usage:
  python3 research-kit/tools/coverage.py [--project PATH] [--detail] [--json]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ─── project discovery ──────────────────────────────────────────────────────


def find_project_root(start: Path) -> Path | None:
    """Walk up from `start` to the nearest dir that looks like a project root:
    contains CLAUDE.md alongside docs/ and source/."""
    p = start.resolve()
    if p.is_file():
        p = p.parent
    for parent in [p, *p.parents]:
        if (parent / "CLAUDE.md").exists() and (parent / "docs").is_dir() \
                and (parent / "source").is_dir():
            return parent
    return None


# ─── file helpers ───────────────────────────────────────────────────────────


def _try_load_yaml(path: Path):
    if not path.exists():
        return None
    try:
        import yaml
    except ImportError:
        sys.stderr.write("pyyaml required: pip install pyyaml\n")
        sys.exit(2)
    return yaml.safe_load(path.read_text()) or {}


def _list_files(dir_: Path, suffixes: tuple[str, ...]) -> list[Path]:
    if not dir_.is_dir():
        return []
    out = []
    for p in dir_.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix not in suffixes:
            continue
        # Skip the sidecars
        if p.name.endswith(".run.json"):
            continue
        out.append(p)
    return sorted(out)


def _has_iat(script: Path) -> tuple[bool, list[str]]:
    """Check the script for IAT tags. Per research-kit/rules/inline_audit_trail.md
    tags can live anywhere (docstring header OR inline comments at the decision
    points). A script is "documented per IAT" if it carries any of the three
    tags at all — the spec is about *presence at the decision points*, not
    "all three present in the docstring."

    The check returns (pass, missing-from-the-set) so callers can distinguish
    "no IAT at all" from "has INTENT but no REASONING/ASSUMES."
    """
    try:
        text = script.read_text(errors="replace")
    except OSError:
        return (False, ["INTENT", "REASONING", "ASSUMES"])
    missing = []
    for tag in ("INTENT", "REASONING", "ASSUMES"):
        if not re.search(rf"\b{tag}\s*[:\-]", text):
            missing.append(tag)
    # A script is "ok" if it has at least one tag — the spec's bar.
    return (len(missing) < 3, missing)


# ─── checks ─────────────────────────────────────────────────────────────────


@dataclass
class Check:
    name: str
    status: str  # "✓" | "⚠" | "✗" | "—"
    summary: str
    items: list[str] = field(default_factory=list)


@dataclass
class Report:
    project_root: Path
    sections: dict[str, list[Check]] = field(default_factory=dict)

    def add(self, section: str, check: Check) -> None:
        self.sections.setdefault(section, []).append(check)


def check_artifacts(root: Path, report: Report) -> None:
    section = "ARTIFACTS"
    yaml_path = root / "docs" / "reference" / "artifacts.yaml"
    if not yaml_path.exists():
        report.add(section, Check("artifacts.yaml", "—",
                                  "not present — project hasn't opted in"))
        return

    doc = _try_load_yaml(yaml_path) or {}
    entries = doc.get("artifacts", [])
    report.add(section, Check("entries", "✓",
                              f"{len(entries)} indexed"))

    # 1. Build files not indexed.
    on_disk = set()
    for d in ("build/table", "build/figure"):
        for p in _list_files(root / d, (".csv", ".pdf", ".png", ".tex", ".md", ".parquet")):
            on_disk.add(str(p.relative_to(root)))

    # An artifacts.yaml entry with a .csv canonical claims its .md/.tex
    # siblings too. Build the set of all-claimed paths.
    claimed = set()
    for e in entries:
        path = e.get("path", "")
        if not path:
            continue
        claimed.add(path)
        # multi-format triples
        if path.endswith(".csv"):
            for ext in (".md", ".tex"):
                claimed.add(path[:-4] + ext)

    not_indexed = sorted(on_disk - claimed)
    # Filter out underscore-prefixed (exploratory one-shots) and obvious
    # non-citable companions
    not_indexed = [p for p in not_indexed
                   if not Path(p).name.startswith("_")
                   and not p.endswith(".aux") and not p.endswith(".log")]
    report.add(section, Check(
        "build/{table,figure} files not indexed",
        "✓" if not not_indexed else "⚠",
        f"{len(not_indexed)} files",
        not_indexed,
    ))

    # 2. Entries pointing at missing artifacts.
    missing_artifact = [e["path"] for e in entries
                        if e.get("path") and not (root / e["path"]).exists()]
    report.add(section, Check(
        "entries with missing artifact on disk",
        "✓" if not missing_artifact else "✗",
        f"{len(missing_artifact)} broken paths",
        missing_artifact,
    ))

    # 3. Entries pointing at missing scripts.
    missing_script = [f"{e['path']}  →  {e.get('script')}" for e in entries
                      if e.get("script") and not (root / e["script"]).exists()]
    report.add(section, Check(
        "entries with missing producing script",
        "✓" if not missing_script else "✗",
        f"{len(missing_script)} broken scripts",
        missing_script,
    ))

    # 4. Uncited entries (cited_in is empty).
    uncited = [e["path"] for e in entries if not e.get("cited_in")]
    report.add(section, Check(
        "entries with empty cited_in (produced but uncited)",
        "✓" if not uncited else "⚠",
        f"{len(uncited)} uncited",
        uncited,
    ))

    # 5. Empty tags.
    untagged = [e["path"] for e in entries if not e.get("tags")]
    report.add(section, Check(
        "entries with empty tags",
        "✓" if not untagged else "⚠",
        f"{len(untagged)} untagged",
        untagged,
    ))


def check_scripts(root: Path, report: Report) -> None:
    section = "SCRIPTS"
    scripts = []
    for d in ("source/table", "source/figure"):
        scripts.extend(_list_files(root / d, (".py",)))
    # Exclude underscore-prefixed (one-shot exploratory) by convention.
    pipeline = [s for s in scripts if not s.name.startswith("_")
                and not s.name.startswith("__")]
    exploratory = [s for s in scripts if s.name.startswith("_")
                   and not s.name.startswith("__")]
    report.add(section, Check(
        "pipeline scripts",
        "✓",
        f"{len(pipeline)} pipeline / {len(exploratory)} exploratory (_-prefixed)",
    ))

    # IAT presence — at least one of the three tags anywhere in the file
    # (presence is the spec's bar, not full INTENT/REASONING/ASSUMES coverage).
    no_iat = []
    for s in pipeline:
        ok, missing = _has_iat(s)
        if not ok:  # all three missing
            no_iat.append(str(s.relative_to(root)))
    total = len(pipeline)
    with_iat = total - len(no_iat)
    pct = (100 * with_iat / total) if total else 100.0
    report.add(section, Check(
        "IAT presence (any of INTENT/REASONING/ASSUMES)",
        "✓" if pct >= 90 else "⚠" if pct >= 70 else "✗",
        f"{with_iat}/{total} ({pct:.0f}%) carry an IAT tag",
        no_iat,
    ))


def check_validation(root: Path, report: Report) -> None:
    section = "VALIDATION LEDGER"
    canonical = root / "docs" / "validation.yaml"
    legacy = root / "paper" / "validation.yaml"
    path = canonical if canonical.exists() else legacy if legacy.exists() else None
    if path is None:
        report.add(section, Check("ledger", "—",
                                  "not present — project hasn't opted in"))
        return
    if path == legacy:
        report.add(section, Check(
            "location", "⚠",
            f"using legacy {legacy.relative_to(root)} — migrate to docs/",
        ))

    doc = _try_load_yaml(path) or {}
    rows = doc.get("scripts", [])
    statuses: dict[str, int] = {}
    for r in rows:
        s = r.get("status", "unknown")
        statuses[s] = statuses.get(s, 0) + 1
    summary = " · ".join(f"{k}={v}" for k, v in sorted(statuses.items()))
    report.add(section, Check("rows", "✓", f"{len(rows)} total — {summary}"))

    # Pending rows older than 60 days (best-effort: use file mtime as proxy if
    # row has no timestamp field; the spec stores ai_checks dates but a
    # newly-pending row has empty ai_checks).
    # Simple heuristic: if no human_check and no ai_checks dates, age unknown.
    aged_pending = []
    for r in rows:
        if r.get("status") != "pending":
            continue
        latest_date = None
        for c in r.get("ai_checks") or []:
            try:
                d = dt.date.fromisoformat(str(c.get("date")))
                if latest_date is None or d > latest_date:
                    latest_date = d
            except (TypeError, ValueError):
                pass
        if latest_date:
            age = (dt.date.today() - latest_date).days
            if age > 60:
                aged_pending.append(f"{r.get('script')} (last check {age}d ago)")
    report.add(section, Check(
        "pending rows older than 60 days",
        "✓" if not aged_pending else "⚠",
        f"{len(aged_pending)} aged",
        aged_pending,
    ))

    stale = [r["script"] for r in rows if r.get("status") == "stale"]
    report.add(section, Check(
        "stale rows",
        "✓" if not stale else "⚠",
        f"{len(stale)} stale",
        stale,
    ))


def check_sidecars(root: Path, report: Report) -> None:
    section = "PROVENANCE (.run.json)"
    sidecars = []
    for d in ("build/table", "build/figure"):
        sidecars.extend(_list_files(root / d, (".json",)))
        # _list_files excludes .run.json — refetch manually
    sidecars = []
    for d in ("build/table", "build/figure"):
        if not (root / d).is_dir():
            continue
        for p in (root / d).rglob("*.run.json"):
            if p.is_file():
                sidecars.append(p)

    if not sidecars:
        report.add(section, Check("sidecars", "—",
                                  "no .run.json files present yet"))
        return

    report.add(section, Check("sidecars", "✓",
                              f"{len(sidecars)} present"))

    dirty = []
    null_commit = []
    for s in sidecars:
        try:
            data = json.loads(s.read_text())
        except Exception:
            continue
        if data.get("commit_dirty"):
            dirty.append(str(s.relative_to(root)))
        if data.get("commit") is None:
            null_commit.append(str(s.relative_to(root)))

    report.add(section, Check(
        "runs flagged commit_dirty (provisional)",
        "✓" if not dirty else "⚠",
        f"{len(dirty)} dirty",
        dirty,
    ))
    if null_commit:
        report.add(section, Check(
            "sidecars with null commit (not in git repo at run time)",
            "⚠",
            f"{len(null_commit)} ungitted runs",
            null_commit,
        ))


def check_artifacts_cited_in_docs(root: Path, report: Report) -> None:
    """Cross-validate: every build/{table,figure}/X referenced in a doc has
    an artifacts.yaml entry covering it."""
    section = "CROSS-REFS"
    yaml_path = root / "docs" / "reference" / "artifacts.yaml"
    if not yaml_path.exists():
        return

    doc = _try_load_yaml(yaml_path) or {}
    claimed = set()
    for e in doc.get("artifacts", []):
        p = e.get("path", "")
        claimed.add(p)
        if p.endswith(".csv"):
            for ext in (".md", ".tex"):
                claimed.add(p[:-4] + ext)

    # Walk docs/ and references/ for build/{table,figure} mentions.
    pattern = re.compile(r"build/(?:table|figure)/[A-Za-z0-9_./-]+\.(?:csv|pdf|png|md|tex|parquet)")
    referenced = set()
    where: dict[str, list[str]] = {}
    for d in ("docs",):
        for md in (root / d).rglob("*.md"):
            try:
                text = md.read_text(errors="replace")
            except OSError:
                continue
            for ref in pattern.findall(text):
                referenced.add(ref)
                where.setdefault(ref, []).append(str(md.relative_to(root)))

    unindexed = sorted(referenced - claimed)
    report.add(section, Check(
        "doc references missing from artifacts.yaml",
        "✓" if not unindexed else "⚠",
        f"{len(unindexed)} unindexed",
        [f"{p}  ←  {','.join(where[p][:2])}" for p in unindexed],
    ))


# ─── output ─────────────────────────────────────────────────────────────────


def format_report(report: Report, detail: bool) -> str:
    lines: list[str] = []
    lines.append(f"Coverage report — {report.project_root}")
    lines.append("─" * 72)
    for section, checks in report.sections.items():
        lines.append(f"\n{section}")
        for c in checks:
            lines.append(f"  {c.status}  {c.name:54s}  {c.summary}")
            if detail and c.items:
                for it in c.items[:30]:
                    lines.append(f"        · {it}")
                if len(c.items) > 30:
                    lines.append(f"        … {len(c.items) - 30} more")
    return "\n".join(lines)


def report_to_json(report: Report) -> str:
    out = {
        "project": str(report.project_root),
        "sections": {
            section: [
                {"name": c.name, "status": c.status,
                 "summary": c.summary, "items": c.items}
                for c in checks
            ]
            for section, checks in report.sections.items()
        },
    }
    return json.dumps(out, indent=2, ensure_ascii=False)


# ─── main ───────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--project", type=Path, default=Path.cwd(),
                    help="project root (default: walk up from cwd)")
    ap.add_argument("--detail", action="store_true",
                    help="list offending items under each check")
    ap.add_argument("--json", action="store_true",
                    help="emit JSON instead of a human report")
    args = ap.parse_args()

    root = find_project_root(args.project)
    if root is None:
        sys.stderr.write(
            f"could not find project root from {args.project} — "
            f"expected CLAUDE.md alongside docs/ and source/\n"
        )
        return 2

    report = Report(project_root=root)
    check_artifacts(root, report)
    check_scripts(root, report)
    check_validation(root, report)
    check_sidecars(root, report)
    check_artifacts_cited_in_docs(root, report)

    if args.json:
        print(report_to_json(report))
    else:
        print(format_report(report, detail=args.detail))
    return 0


if __name__ == "__main__":
    sys.exit(main())
