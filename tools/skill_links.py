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

Also checks **link coverage**: a skill only exists for a session that
can see it, and each kind of session reads a different directory of
symlinks (see `_LINK_LOCATIONS`). A skill added to research-kit but
linked into only one of them is invisible to everyone else — that
drift is silent, since the skill itself is perfectly well-formed.

Coverage compares *names and link targets only*, never `exists()`:
Saga's links point through bind-mounts that exist only inside her
jail, so they dangle host-side by design. To omit a skill from one
location on purpose, list it in `<location>/.skill-links-ignore`
(one name per line, `#` comments).

Read-only. Run after editing any skill, or as a research-kit-wide
nightly sanity check.

Usage:
  python3 research-kit/tools/skill_links.py [--root PATH] [--detail] [--json]
                                            [--link-dir PATH ...] [--no-coverage]

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


# ─── link coverage ──────────────────────────────────────────────────────────

# Where skills have to be linked to be reachable, and by whom. Each is
# (label, path-relative-to-what, description). Missing directories are
# skipped silently — the laptop has no `work/`, and a fresh clone has no
# user-level dir.
#
#   user       ~/.claude/skills            host sessions; absolute links
#   workspace  <root>/.claude/skills       sandboxed sessions jailed to the
#                                          workspace; relative links, since
#                                          absolute ones escape the jail
#   saga       <root>/../work/.claude/skills
#                                          the work brain, jailed to `work/`;
#                                          relative links through bind-mounts
#                                          that only exist inside her jail
def _link_locations(root: Path, extra: list[Path]) -> list[tuple[str, Path]]:
    candidates = [
        ("user", Path.home() / ".claude" / "skills"),
        ("workspace", root / ".claude" / "skills"),
        ("saga", root.parent / "work" / ".claude" / "skills"),
    ]
    candidates += [(str(p), p) for p in extra]
    return [(label, p) for label, p in candidates if p.is_dir()]


def _ignored_names(loc: Path) -> set[str]:
    """Names a location deliberately omits — the skill sets are curated,
    so a prune must not read as drift."""
    f = loc / ".skill-links-ignore"
    if not f.is_file():
        return set()
    names = set()
    for line in f.read_text(errors="replace").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            names.add(line)
    return names


# A link target naming a research-kit skill, however it is spelled:
# absolute (~/.claude/skills) or relative with any number of ../ hops.
_LINK_TARGET = re.compile(r"research-kit/skills/([A-Za-z0-9_.-]+)/?$")


def _serves_root(entries: dict[str, Path | None], root: Path) -> bool:
    """Does this location link into *this* workspace?

    Only absolute targets can say: `~/.claude/skills` may point at a
    different checkout entirely, and judging it against this root would
    report every one of its links as stale. Relative targets are taken
    on trust — Saga's resolve through bind-mounts that don't exist
    host-side, so following them here would prove nothing.
    """
    roots = set()
    for target in entries.values():
        if target is None or not target.is_absolute():
            continue
        s = str(target)
        i = s.find("/research-kit/skills/")
        if i > 0:
            roots.add(s[:i])
    return not roots or str(root) in roots


def check_coverage(root: Path, skills: dict[str, Skill],
                   extra: list[Path]) -> list[Issue]:
    """Every research-kit skill should be linked into every location.

    Deliberately target-text-based: `exists()` is meaningless for Saga's
    links, which resolve only inside her jail.
    """
    issues: list[Issue] = []
    for label, loc in _link_locations(root, extra):
        entries = {p.name: (p.readlink() if p.is_symlink() else None)
                   for p in loc.iterdir() if not p.name.startswith(".")}
        if not _serves_root(entries, root):
            continue
        ignored = _ignored_names(loc)
        where = f"{label}:{_display_path(loc)}"

        for name in sorted(set(skills) - set(entries) - ignored):
            issues.append(Issue(
                "missing_link",
                where,
                f"/{name} not linked — invisible to {label} sessions",
            ))

        # A link left behind by a renamed or deleted skill. Only judge
        # entries that *name* a research-kit skill; teach skills and
        # one-offs like /referee live elsewhere and are none of our business.
        for name, target in sorted(entries.items()):
            if target is None:
                continue
            m = _LINK_TARGET.search(str(target))
            if m and m.group(1) not in skills:
                issues.append(Issue(
                    "stale_link",
                    where,
                    f"{name} → {target} — no such skill in research-kit/skills/",
                ))
    return issues


def _display_path(p: Path) -> str:
    """Shorten a location for reporting: ~ for home, else as given."""
    try:
        return "~/" + str(p.relative_to(Path.home()))
    except ValueError:
        return str(p)


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
                  detail: bool, locations: list[str] | None = None) -> str:
    lines: list[str] = []
    lines.append(f"Skill cross-ref check — {len(skills)} skills audited")
    if locations:
        lines.append(f"Link coverage — {', '.join(locations)}")
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
            "missing_link": "skills not linked into a session's skill dir",
            "stale_link": "links to skills that no longer exist",
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
    ap.add_argument("--link-dir", type=Path, action="append", default=[],
                    metavar="PATH",
                    help="extra skill-link directory to check for coverage "
                         "(repeatable); the standard three are automatic")
    ap.add_argument("--no-coverage", action="store_true",
                    help="skip the link-coverage check (cross-refs only)")
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
    if not args.no_coverage:
        issues.extend(check_coverage(root, skills, args.link_dir))

    locations = ([] if args.no_coverage
                 else [f"{label} ({_display_path(p)})"
                       for label, p in _link_locations(root, args.link_dir)])
    if args.json:
        print(report_to_json(issues))
    else:
        print(format_report(issues, skills, detail=args.detail,
                            locations=locations))
    return 0 if not issues else 1


if __name__ == "__main__":
    sys.exit(main())
