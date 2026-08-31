"""[anec:slug] auto-linking and anecdote-title loader."""

from __future__ import annotations

import html as _html
import re
from pathlib import Path

from ..context import BuildContext


def load_anec_map(project_root: Path) -> dict[str, str]:
    """Map [anec:<slug>] tokens to a display title.

    Resolves only if docs/anecdotes/<slug>.md exists. Label is the
    frontmatter `title:` if present, else the file's first H1.
    """
    anec_dir = project_root / "docs" / "anecdotes"
    if not anec_dir.is_dir():
        return {}
    out: dict[str, str] = {}
    for p in sorted(anec_dir.glob("*.md")):
        if p.stem == "index":
            continue
        lines = p.read_text(encoding="utf-8").splitlines()
        title = None
        if lines and lines[0] == "---":
            for line in lines[1:]:
                if line == "---":
                    break
                if line.startswith("title:"):
                    title = line[6:].strip()
                    break
        if not title:
            for line in lines:
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
        out[p.stem] = title or p.stem
    return out


def link_anec_refs(
    html: str, ctx: BuildContext, current_stem: str = "", prefix: str = "../"
) -> str:
    """Auto-link [anec:<slug>] tokens to their anecdote page.

    The anecdote page's location depends on how the project renders the subdir:
    folder-mode (``anecdotes`` in ``SiteConfig.folder_mode_subdirs``, e.g.
    promotor) puts pages at ``docs/anecdotes/<slug>.html``; a plain root
    doc_subdir (e.g. connect, which needs ``build_doc_subdir`` for the rich
    ``anecdote.html`` twins) puts them at ``anecdotes/<slug>.html``. ``prefix``
    is the relative path from the citing page to the site root (``"../"`` for a
    doc_subdir/top-level page, ``"../../"`` for a folder-mode page one level
    deeper), so the href resolves from any page depth.
    """
    if not ctx.anec_map:
        return html
    base = ("docs/anecdotes"
            if "anecdotes" in ctx.config.folder_mode_subdirs else "anecdotes")
    pattern = re.compile(
        r'(<a\b[^>]*>.*?</a>)|(\[anec:([A-Za-z0-9][A-Za-z0-9_-]*)\])',
        re.DOTALL)

    def _replacer(m: re.Match) -> str:
        if m.group(1):
            return m.group(1)
        token, slug = m.group(2), m.group(3)
        label = ctx.anec_map.get(slug)
        if not label or slug == current_stem:
            return token
        return (f'<a class="anec-ref" href="{prefix}{base}/{slug}.html">'
                f'{_html.escape(label)}</a>')

    return pattern.sub(_replacer, html)
