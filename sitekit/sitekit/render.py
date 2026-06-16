"""Markdown rendering, slug generation, HTML link rewriting.

Lifted from connect/build_all.py and parameterized so flat (bind/serasa)
and nested (connect/fisc) doc layouts share one code path.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

import mistune

from .config import SiteConfig
from .context import BuildContext


_md = mistune.create_markdown(plugins=["task_lists", "strikethrough", "table"])


def md_to_html(text: str) -> str:
    """Convert markdown to HTML using the shared mistune instance."""
    return _md(text)


def slugify(text: str) -> str:
    """Convert heading text to a URL-friendly slug."""
    text = re.sub(r"<[^>]+>", "", text)
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def strip_leading_h1(html: str) -> str:
    """Drop a leading <h1> — the page-header template already renders the title."""
    return re.sub(r"^\s*<h1[^>]*>.*?</h1>\s*", "", html, count=1, flags=re.DOTALL)


def add_heading_ids(html: str) -> str:
    """Add id attributes to h2-h6 elements that lack them."""
    def _replacer(m: re.Match) -> str:
        level, attrs, content = m.group(1), m.group(2) or "", m.group(3)
        if "id=" in attrs:
            return m.group(0)
        slug = slugify(content)
        return f'<h{level}{attrs} id="{slug}">{content}</h{level}>'
    return re.sub(r"<h([2-6])(\s[^>]*)?>(.+?)</h\1>", _replacer, html)


def rewrite_md_links(
    html: str,
    ctx: BuildContext,
    in_subdir: bool = False,
) -> str:
    """Rewrite relative .md hrefs to .html so cross-doc links work.

    Handles the workspace convention that top-level docs render under
    `build/site/docs/` while doc-subdir pages (e.g. docs/hypotheses/) render
    under `build/site/<subdir>/`. From a subdir page, `../theory.md` must
    become `../docs/theory.html`, not `theory.html`.

    Projects that flatten sibling subdirs (briefs/, notes/) into docs/
    declare those prefixes via SiteConfig.extra_strip_prefixes.

    Auto-detection note: callers know whether the current page is in a
    subdir; pass `in_subdir=True` for those. Flat projects (no doc subdirs)
    can leave it False.
    """
    cfg = ctx.config
    subdir_names = {s for s, _, _ in cfg.doc_subdirs}
    strip_prefixes = ("docs/", "../docs/", *cfg.extra_strip_prefixes)

    def _replacer(m: re.Match) -> str:
        href = m.group(1)
        if href.startswith(("http://", "https://", "//")):
            return m.group(0)
        new = href.replace(".md", ".html")
        for prefix in strip_prefixes:
            if new.startswith(prefix):
                new = new[len(prefix):]
                break
        else:
            if new.startswith("../"):
                remainder = new[3:]
                first_seg = remainder.split("/")[0] if "/" in remainder else ""
                if first_seg not in subdir_names:
                    if in_subdir and "/" not in remainder:
                        new = "../docs/" + remainder
                    else:
                        new = remainder
        return f'href="{new}"'
    return re.sub(r'href="([^"]*\.md(?:#[^"]*)?)"', _replacer, html)


# ---------------------------------------------------------------- math protect

# Bind-style math protection: protect $...$ / $$...$$ / \(...\) / \[...\] from
# the markdown renderer (which would mangle backslashes and asterisks) and
# restore them after.

_MATH_PATTERNS = [
    re.compile(r"\$\$.*?\$\$", re.DOTALL),
    re.compile(r"\$[^$\n]+?\$"),
    re.compile(r"\\\(.+?\\\)", re.DOTALL),
    re.compile(r"\\\[.+?\\\]", re.DOTALL),
]


def protect_math(text: str) -> tuple[str, dict[str, str]]:
    """Replace math spans with unique placeholders before markdown rendering."""
    placeholders: dict[str, str] = {}
    counter = [0]

    def _replace(m: re.Match) -> str:
        token = f"MATHPLACEHOLDER{counter[0]}MATHPLACEHOLDER"
        counter[0] += 1
        placeholders[token] = m.group(0)
        return token

    out = text
    for pat in _MATH_PATTERNS:
        out = pat.sub(_replace, out)
    return out, placeholders


def restore_math(html: str, placeholders: dict[str, str]) -> str:
    """Put math spans back after markdown rendering."""
    for token, original in placeholders.items():
        html = html.replace(token, original)
    return html
