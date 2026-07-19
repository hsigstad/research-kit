"""H:slug auto-linking and hypothesis-title loader."""

from __future__ import annotations

from pathlib import Path
import re

from ..context import BuildContext
from ..nav import _brief_title


def load_h_slugs(project_root: Path) -> set[str]:
    """Slugs of hypothesis pages under docs/hypotheses/."""
    hyp_dir = project_root / "docs" / "hypotheses"
    if not hyp_dir.is_dir():
        return set()
    return {p.stem for p in hyp_dir.glob("*.md") if p.stem != "index"}


def load_hyp_titles(project_root: Path) -> dict[str, str]:
    """Map hypothesis slug -> its '# H<N>: Title' text."""
    out: dict[str, str] = {}
    hyp_dir = project_root / "docs" / "hypotheses"
    if hyp_dir.is_dir():
        for p in hyp_dir.glob("*.md"):
            if p.stem != "index":
                out[p.stem] = _brief_title(p)
    return out


def link_h_refs(html: str, ctx: BuildContext, current_stem: str = "",
                prefix: str = "../") -> str:
    """Auto-link bare H:slug tokens to their hypothesis page.

    Hypothesis pages render folder-mode at build/site/docs/hypotheses/<slug>.html.
    `prefix` is the relative path from the citing page to the site root, so the
    href resolves from any page depth (``"../"`` for a doc_subdir/top-level page,
    ``"../../"`` for a folder-mode page one level deeper).
    """
    if not ctx.h_slugs:
        return html
    pattern = re.compile(r'(<a\b[^>]*>.*?</a>)|(\bH:([a-z0-9-]+))', re.DOTALL)

    def _replacer(m: re.Match) -> str:
        if m.group(1):
            return m.group(1)
        token, slug = m.group(2), m.group(3)
        if slug not in ctx.h_slugs or slug == current_stem:
            return token
        return f'<a href="{prefix}docs/hypotheses/{slug}.html">{token}</a>'

    return pattern.sub(_replacer, html)
