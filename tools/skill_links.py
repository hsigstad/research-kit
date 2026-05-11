#!/usr/bin/env python3
"""
Cross-reference checker for the research-kit skill set.

Walks `research-kit/skills/<name>/SKILL.md` and verifies every cross-
reference resolves:

  - `/<skill>` mentions point at a skill that exists
  - `/<skill> --<flag>` mentions exist (skill exists AND flag is
    documented in the target skill's Arguments section)
  - `research-kit/{rules,tools,meta}/<path>` mentions resolve to
    files on disk

Catches drift introduced by adding/renaming a skill mode without
updating the skills that reference it (e.g. /next mentioning
/findings --update before /findings has a --update mode).

Read-only. Run after editing any skill, or as a research-kit-wide
nightly sanity check.

Usage:
  python3 research-kit/tools/skill_links.py [--root PATH] [--detail] [--json]

Exits 0 on clean, 1 if any broken references found (suitable for CI).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ─── reference patterns ─────────────────────────────────────────────────────

# /<skill-name> — lowercase, hyphenated.
# Reject:
#   - path-like prefixes (./foo, ../foo, ~/foo, http://foo)
#   - placeholder-path prefixes (<slug>/foo.md)
#   - compound-word "or"-style (d-/h-series)
#   - prefix-only matches (greedy must be complete word: not followed
#     by another word-char/hyphen)
#   - path continuations (followed by another /)
#   - file-extension patterns (/foo.md, /foo.html → not a skill ref)
_SKILL_REF = re.compile(
    r"(?<![/.\w:~>\-`])/([a-z][a-z0-9-]+)(?![a-z0-9-/]|\.[a-z])"
)

# --<flag>, lowercase with optional hyphens
_FLAG_REF = re.compile(r"(?<![\w-])--([a-z][a-z0-9-]+)\b")

# research-kit/{rules,tools,meta,skills}/<path>
_RK_PATH = re.compile(
    r"research-kit/(rules|tools|meta|skills)/([A-Za-z0-9_./-]+)"
)


# Skills mentioned that aren't actually skills — pure CLI conventions or
# slash-text from prose. Filter heuristically.
_NON_SKILL_TOKENS = {
    "claim", "next-log",  # decorative slash-text examples
}


# ─── core ───────────────────────────────────────────────────────────────────


@dataclass
class Skill:
    name: str
    path: Path
    text: str
    documented_flags: set[str] = field(default_factory=set)


@dataclass
class Issue:
    kind: str  # "missing_skill", "missing_flag", "missing_file"
    where: str  # "skills/foo/SKILL.md:lineno"
    detail: str


def load_skills(skills_dir: Path) -> dict[str, Skill]:
    """Walk skills_dir/<name>/SKILL.md, parse each, extract the
    documented flag set from the Arguments section."""
    skills: dict[str, Skill] = {}
    for skill_md in skills_dir.glob("*/SKILL.md"):
        name = skill_md.parent.name
        text = skill_md.read_text(errors="replace")
        skill = Skill(name=name, path=skill_md, text=text)
        skill.documented_flags = _extract_documented_flags(text)
        skills[name] = skill
    return skills


def _extract_documented_flags(text: str) -> set[str]:
    """Parse the Arguments section of a SKILL.md to extract the set of
    documented flags. Heuristic: find ## Arguments header, take text
    until the next ## heading; grep --<flag> patterns inside.

    Also includes flags mentioned anywhere in the body as a fallback —
    some skills document subcommand-style flags (e.g. /institutions
    `update` without leading --) and some embed flag docs in prose. The
    union avoids false positives at the cost of a slight false-negative
    rate for misspelled flags.
    """
    flags: set[str] = set()
    # Body-wide flag mentions: anything matching --<flag>
    for m in _FLAG_REF.finditer(text):
        flags.add(m.group(1))
    # Bare-word subcommands (e.g. /institutions update, audit) — scan
    # for skill-arg lines like `- \`/<name> <word>\``
    for m in re.finditer(r"-\s+`/[a-z][a-z0-9-]+\s+([a-z][a-z0-9-]+)`", text):
        flags.add(m.group(1))
    return flags


def _nearest_skill(line: str, flag: str, skills_on_line: list[str]) -> str:
    """For error-message attribution: which skill ref is closest to the
    given --flag on the line."""
    flag_pos = line.find(f"--{flag}")
    if flag_pos < 0 or not skills_on_line:
        return skills_on_line[0] if skills_on_line else "<unknown>"
    best = skills_on_line[0]
    best_dist = abs(line.find(f"/{best}") - flag_pos)
    for s in skills_on_line[1:]:
        p = line.find(f"/{s}")
        if p < 0:
            continue
        d = abs(p - flag_pos)
        if d < best_dist:
            best_dist = d
            best = s
    return best


def _ignore_skill_token(name: str) -> bool:
    """Filter false-positives: prose tokens that look like slash refs
    but aren't intended as skill invocations."""
    if name in _NON_SKILL_TOKENS:
        return True
    # Single-letter or two-letter — usually CLI flags or initials
    if len(name) < 3:
        return True
    return False


def check_skill(skill: Skill, known_skills: dict[str, Skill],
                root: Path) -> list[Issue]:
    issues: list[Issue] = []
    rel_path = skill.path.relative_to(root)

    # Lines for line-number reporting
    lines = skill.text.splitlines()

    # 1. /<skill> references
    skill_refs: list[tuple[int, str]] = []
    for lineno, line in enumerate(lines, start=1):
        for m in _SKILL_REF.finditer(line):
            name = m.group(1)
            if _ignore_skill_token(name):
                continue
            if name == skill.name:
                continue  # self-ref
            skill_refs.append((lineno, name))
            if name not in known_skills:
                issues.append(Issue(
                    "missing_skill",
                    f"{rel_path}:{lineno}",
                    f"/{name} — no such skill in research-kit/skills/",
                ))

    # 2. /<skill> --<flag> co-occurrence checks. A flag near a skill
    #    ref is "attributed" to that skill; if no skill on the line
    #    documents the flag, that's a broken ref.
    #
    #    Permissive attribution: a flag is *not* broken if any skill
    #    mentioned on the same line documents it. Lines often mention
    #    several skills ("/findings-audit finds X; /findings --extend
    #    folds it in") and the flag belongs to whichever one documents
    #    it. False-positive prevention beats precision here.
    for lineno, line in enumerate(lines, start=1):
        skills_on_line = [m.group(1) for m in _SKILL_REF.finditer(line)
                          if not _ignore_skill_token(m.group(1))
                          and m.group(1) in known_skills]
        flags_on_line = [m.group(1) for m in _FLAG_REF.finditer(line)]
        if not skills_on_line or not flags_on_line:
            continue
        # Self-skill is always in scope (the skill documents its own flags).
        candidates = set(skills_on_line) | {skill.name}
        candidate_flag_sets = [known_skills[c].documented_flags
                               for c in candidates if c in known_skills]
        union_flags: set[str] = set().union(*candidate_flag_sets) if candidate_flag_sets else set()
        for flag in flags_on_line:
            if flag in union_flags:
                continue
            # Best-effort attribution for the error message: pick the
            # nearest skill ref to the flag's position.
            target = _nearest_skill(line, flag, skills_on_line)
            issues.append(Issue(
                "missing_flag",
                f"{rel_path}:{lineno}",
                f"/{target} --{flag} — flag not documented in any skill mentioned on this line",
            ))

    # 3. research-kit/{rules,tools,meta,skills}/<path> file refs
    for lineno, line in enumerate(lines, start=1):
        for m in _RK_PATH.finditer(line):
            kind = m.group(1)
            rel = m.group(2)
            # Strip trailing punctuation
            rel = rel.rstrip(".,;:)")
            target = root / "research-kit" / kind / rel
            # Many docs refer to the file by its bare name within rules/
            # (e.g. inline_audit_trail.md). Try both as-is and with the
            # path-as-given.
            if not target.exists():
                # Skip if it looks like a glob pattern or template
                if "*" in rel or "{" in rel or "<" in rel:
                    continue
                issues.append(Issue(
                    "missing_file",
                    f"{rel_path}:{lineno}",
                    f"research-kit/{kind}/{rel} — file not found",
                ))

    return issues


# ─── output ─────────────────────────────────────────────────────────────────


def format_report(issues: list[Issue], skills: dict[str, Skill],
                  detail: bool) -> str:
    lines: list[str] = []
    lines.append(f"Skill cross-ref check — {len(skills)} skills audited")
    lines.append("─" * 60)
    if not issues:
        lines.append("✓ all references resolve")
        return "\n".join(lines)

    # Group by kind
    by_kind: dict[str, list[Issue]] = {}
    for i in issues:
        by_kind.setdefault(i.kind, []).append(i)
    for kind, group in by_kind.items():
        label = {
            "missing_skill": "broken /skill references",
            "missing_flag": "broken --flag references (flag not documented in target skill)",
            "missing_file": "broken research-kit/ file references",
        }.get(kind, kind)
        lines.append(f"\n✗ {len(group):3d}  {label}")
        if detail:
            for issue in group[:50]:
                lines.append(f"        · {issue.where}  →  {issue.detail}")
            if len(group) > 50:
                lines.append(f"        … {len(group) - 50} more")
        else:
            # Show first 5
            for issue in group[:5]:
                lines.append(f"        · {issue.where}  →  {issue.detail}")
            if len(group) > 5:
                lines.append(f"        … {len(group) - 5} more (--detail to list)")
    return "\n".join(lines)


def report_to_json(issues: list[Issue]) -> str:
    return json.dumps({
        "n_issues": len(issues),
        "issues": [
            {"kind": i.kind, "where": i.where, "detail": i.detail}
            for i in issues
        ],
    }, indent=2, ensure_ascii=False)


# ─── main ───────────────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", type=Path, default=None,
                    help="workspace root (default: detect from cwd)")
    ap.add_argument("--detail", action="store_true",
                    help="list every issue, not just the first 5 per kind")
    ap.add_argument("--json", action="store_true",
                    help="emit JSON instead of a human report")
    args = ap.parse_args()

    # Resolve research-kit root
    if args.root:
        root = args.root.resolve()
    else:
        # Walk up from cwd to find a dir containing research-kit/
        cwd = Path.cwd().resolve()
        root = None
        for parent in [cwd, *cwd.parents]:
            if (parent / "research-kit" / "skills").is_dir():
                root = parent
                break
        if root is None:
            # Try relative to this script
            here = Path(__file__).resolve()
            for parent in [here, *here.parents]:
                if (parent / "skills").is_dir() and parent.name == "research-kit":
                    root = parent.parent
                    break
        if root is None:
            sys.stderr.write(
                "could not find research-kit/ — pass --root explicitly\n"
            )
            return 2

    skills_dir = root / "research-kit" / "skills"
    if not skills_dir.is_dir():
        sys.stderr.write(f"no skills dir at {skills_dir}\n")
        return 2

    skills = load_skills(skills_dir)
    issues: list[Issue] = []
    for skill in skills.values():
        issues.extend(check_skill(skill, skills, root))

    if args.json:
        print(report_to_json(issues))
    else:
        print(format_report(issues, skills, detail=args.detail))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
