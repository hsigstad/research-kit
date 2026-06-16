"""AN-NNN auto-linking and finding-tag injection."""

from __future__ import annotations

import re
from pathlib import Path

from ..context import BuildContext


_FINDING_TAG_RE = re.compile(r"[\U0001F7E2\U0001F7E1\U0001F534]")


def load_an_map(project_root: Path) -> dict[str, str]:
    """Map AN-NNN tokens to the stem of their analysis doc under docs/analyses/."""
    out: dict[str, str] = {}
    analyses_dir = project_root / "docs" / "analyses"
    if analyses_dir.is_dir():
        for p in sorted(analyses_dir.glob("an-*.md")):
            m = re.match(r"an-(\d+)", p.stem)
            if m:
                out[f"AN-{int(m.group(1)):03d}"] = p.stem
    return out


def scan_finding_tags(project_root: Path) -> dict[str, str]:
    """Map docs/findings/<slug>.md → first traffic-light emoji in the page body."""
    src_dir = project_root / "docs" / "findings"
    out: dict[str, str] = {}
    if not src_dir.is_dir():
        return out
    for path in sorted(src_dir.glob("*.md")):
        if path.stem == "index":
            continue
        m = _FINDING_TAG_RE.search(path.read_text(encoding="utf-8"))
        if m:
            out[path.stem] = m.group(0)
    return out


def inject_finding_tags(html: str, tags: dict[str, str]) -> str:
    """Prepend each finding's traffic-light tag to its overview bullet."""
    pat = re.compile(r'<li>(<a href="([^"/]+)\.html">)')
    def repl(m: re.Match) -> str:
        slug = m.group(2)
        if slug not in tags:
            return m.group(0)
        return f'<li>{tags[slug]} {m.group(1)}'
    return pat.sub(repl, html)


def link_an_refs(html: str, ctx: BuildContext, current_stem: str = "") -> str:
    """Auto-link bare AN-NNN tokens to their analysis page under analyses/."""
    if not ctx.an_map:
        return html
    pattern = re.compile(r'(<a\b[^>]*>.*?</a>)|(\bAN-(\d+)\b)', re.DOTALL)

    def _replacer(m: re.Match) -> str:
        if m.group(1):
            return m.group(1)
        token, num = m.group(2), m.group(3)
        stem = ctx.an_map.get(f"AN-{int(num):03d}")
        if not stem or stem == current_stem:
            return token
        return f'<a href="../analyses/{stem}.html">{token}</a>'

    return pattern.sub(_replacer, html)
