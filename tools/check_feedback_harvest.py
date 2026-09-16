#!/usr/bin/env python3
"""Flag /fetch-annotations response logs that never got style-harvested.

Step 7 of /fetch-annotations is supposed to append style-flavored annotations
from each response log into research/rules/writing_feedback_log.md. It is a
model-discretion step and gets skipped silently. This check is the deterministic
backstop: for every projects/*/docs/annotations/responses_*.md, is there a
matching (date, project) block in the feedback log?

A pass that found no style feedback should still close the loop by appending a
one-line marker block:

    ## YYYY-MM-DD · {project} · {author}
    - **Status:** none — no style/mixed feedback in this pass

so the (date, project) key exists and this check stays quiet. Any response log
with no matching key — real entries or marker — is reported as a gap.

Emits the same shape as skill_links.py: {"n_gaps": N, "gaps": [ {...} ]}.
Exit status is always 0 (a reporter, not a gate); the nightly sweep surfaces it.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
# Feedback-log entry/marker header: "## 2026-09-15 · deterrence · hsigstad"
HEADER_RE = re.compile(r"^##\s+(\d{4}-\d{2}-\d{2})\s+·\s+([A-Za-z0-9_-]+)\s+·", re.M)


def find_workspace(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        if (d / "projects").is_dir() and (d / "research").is_dir():
            return d
    return None


def harvested_keys(log_path: Path) -> set[tuple[str, str]]:
    """(date, project) keys already present in the feedback log."""
    if not log_path.is_file():
        return set()
    text = log_path.read_text(encoding="utf-8")
    return {(m.group(1), m.group(2)) for m in HEADER_RE.finditer(text)}


def find_gaps(root: Path) -> list[dict]:
    log_path = root / "research" / "rules" / "writing_feedback_log.md"
    done = harvested_keys(log_path)
    gaps: list[dict] = []
    for resp in sorted(root.glob("projects/*/docs/annotations/responses_*.md")):
        m = DATE_RE.search(resp.name)
        if not m:
            continue
        date = m.group(1)
        # projects/<slug>/docs/annotations/responses_...
        project = resp.relative_to(root / "projects").parts[0]
        if (date, project) not in done:
            gaps.append({
                "project": project,
                "date": date,
                "path": str(resp.relative_to(root)),
                "detail": (f"{project} {date}: response log never style-harvested "
                           "into writing_feedback_log.md (run /fetch-annotations "
                           "Step 7, or append a 'no style feedback' marker)"),
            })
    return gaps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=None,
                    help="workspace root (default: detect from cwd)")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    args = ap.parse_args()

    root = args.root or find_workspace(Path.cwd())
    if root is None:
        print("could not locate workspace root (needs projects/ + research/)",
              file=sys.stderr)
        return 0
    root = root.resolve()

    gaps = find_gaps(root)
    if args.json:
        print(json.dumps({"n_gaps": len(gaps), "gaps": gaps}, indent=1))
    elif not gaps:
        print("harvest check: all response logs accounted for.")
    else:
        print(f"harvest check: {len(gaps)} un-harvested response log(s):")
        for g in gaps:
            print(f"  - {g['path']}  ({g['detail']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
