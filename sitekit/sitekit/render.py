"""Markdown rendering, slug generation, HTML link rewriting.

Lifted from connect/build_all.py and parameterized so flat (bind/serasa)
and nested (connect/fisc) doc layouts share one code path.
"""

from __future__ import annotations

import html as _html_lib
import re
import unicodedata
from pathlib import Path
from typing import Optional

import mistune

from .config import SiteConfig
from .context import BuildContext


_md = mistune.create_markdown(plugins=["task_lists", "strikethrough", "table"])


def md_to_html(text: str) -> str:
    """Convert markdown to HTML using the shared mistune instance."""
    return _md(text)


def slugify(text: str, unicode_normalize: bool = False) -> str:
    """Convert heading text to a URL-friendly slug.

    Default behavior (connect-style): strip HTML tags, lowercase, collapse
    non-[a-z0-9] runs to hyphens. Accented chars become hyphens.

    When unicode_normalize=True (fisc-style): also html-unescape entities
    and NFKD-normalize to drop accents before slugifying. Set per-project
    via SiteConfig.slugify_unicode_normalize.
    """
    text = re.sub(r"<[^>]+>", "", text)
    if unicode_normalize:
        text = _html_lib.unescape(text)
        text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def strip_leading_h1(html: str) -> str:
    """Drop a leading <h1> — the page-header template already renders the title."""
    return re.sub(r"^\s*<h1[^>]*>.*?</h1>\s*", "", html, count=1, flags=re.DOTALL)


def add_heading_ids(html: str, unicode_normalize: bool = False) -> str:
    """Add id attributes to h2-h6 elements that lack them."""
    def _replacer(m: re.Match) -> str:
        level, attrs, content = m.group(1), m.group(2) or "", m.group(3)
        if "id=" in attrs:
            return m.group(0)
        slug = slugify(content, unicode_normalize=unicode_normalize)
        return f'<h{level}{attrs} id="{slug}">{content}</h{level}>'
    return re.sub(r"<h([2-6])(\s[^>]*)?>(.+?)</h\1>", _replacer, html)


def rewrite_md_links(
    html: str,
    ctx: BuildContext,
    in_subdir: bool = False,
    prefix: str = "../",
    is_folder_mode: bool = False,
) -> str:
    """Rewrite relative .md hrefs to .html so cross-doc links work.

    Handles the workspace convention that top-level docs render under
    `build/site/docs/` while doc-subdir pages (e.g. docs/hypotheses/) render
    under `build/site/<subdir>/`. From a subdir page, `../theory.md` must
    become `../docs/theory.html`, not `theory.html`.

    Projects that flatten sibling subdirs (briefs/, notes/) into docs/
    declare those prefixes via SiteConfig.extra_strip_prefixes.

    `prefix` is the relative path from the current page to the site root
    (e.g. `"../"` for `build/site/docs/foo.html`, `"../../"` for folder-mode
    pages at `build/site/docs/<folder>/foo.html`). Used to compose paths
    into doc_subdir outputs which live at `build/site/<subdir>/` rather
    than under `docs/`.

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
        # `extra_strip_prefixes` containing "../" would mangle paths into
        # doc_subdirs by stripping the leading `../`. Check that case first
        # and route through prefix instead.
        sd_match = None
        for sd in subdir_names:
            if new.startswith(f"../{sd}/"):
                sd_match = sd
                break
        if sd_match:
            return f'href="{prefix}{new[3:]}"'
        # Source path starting directly with a doc_subdir name (e.g.
        # `analyses/an-001.md` from a top-level docs page) targets the
        # subdir output at build/site/<subdir>/ — route via prefix.
        bare_first = new.split("/", 1)[0] if "/" in new else new.rstrip("/")
        if bare_first in subdir_names:
            return f'href="{prefix}{new}"'
        if is_folder_mode:
            # Folder-mode pages render at build/site/docs/<folder>/<stem>.html
            # and preserve the docs/ tree, so a source-relative link already
            # matches the output layout: e.g. `../hypotheses.md` from
            # docs/findings/x.md → `../hypotheses.html` (up to docs/), and a
            # sibling `other-slug.md` stays same-dir. Only .md→.html (done
            # above) plus the doc_subdir routing (handled above) apply; do not
            # strip the leading `../`.
            return f'href="{new}"'
        for sp in strip_prefixes:
            if new.startswith(sp):
                new = new[len(sp):]
                # If the strip uncovered a doc_subdir reference, route it
                # via prefix so the relative path matches the actual output
                # location (build/site/<subdir>/...).
                first_seg = new.split("/", 1)[0] if "/" in new else ""
                if first_seg in subdir_names:
                    new = f"{prefix}{new}"
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
    html = re.sub(r'href="([^"]*\.md(?:#[^"]*)?)"', _replacer, html)

    # Bare directory hrefs targeting a doc_subdir (e.g. href="analyses/" or
    # href="../analyses/") — route via prefix to the subdir's output root.
    def _dir_replacer(m: re.Match) -> str:
        href = m.group(1)
        if href.startswith("../"):
            tail = href[3:]
        else:
            tail = href
        seg = tail.rstrip("/")
        if seg in subdir_names:
            return f'href="{prefix}{seg}/"'
        return m.group(0)

    return re.sub(r'href="(\.\./[A-Za-z0-9_-]+/|[A-Za-z0-9_-]+/)"',
                  _dir_replacer, html)


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


_VERDICT_LEAD_PATTERN = re.compile(
    r'<blockquote>\s*<p><strong>'
    r'((?:Evidence strength|Verdict|Status)[^<]*)'
    r'</strong>',
    re.IGNORECASE,
)


def _classify_verdict(strong_text: str) -> str:
    """Bucket a verdict label by keyword. Order is intentional:
    refuted → mixed → confirmed → pending. 'refuted' wins over 'strong'
    so 'Strong evidence of refutation' reads as refuted; 'mixed' wins
    over 'pending' so 'Mixed; decisive test pending' reads as mixed."""
    t = strong_text.lower()
    if "refut" in t or "against" in t:
        return "verdict-refuted"
    if any(k in t for k in ("mixed", "partial", "moderate", "weak", "first descriptive")):
        return "verdict-mixed"
    if any(k in t for k in ("confirm", "strong", "support", "very strong")):
        return "verdict-confirmed"
    if any(k in t for k in ("not tested", "untested", "pending")):
        return "verdict-pending"
    return "verdict-neutral"


def style_verdict_callouts(html: str) -> str:
    """Tag <blockquote>s that open with **Evidence strength:** (or Verdict /
    Status) so doc.html CSS can render them as a colored verdict card.

    The bolded lead text is classified into one of:
      verdict-refuted / verdict-mixed / verdict-confirmed /
      verdict-pending / verdict-neutral

    Match is anchored to the blockquote start to avoid wrapping nested
    quotes or false positives elsewhere in the body.
    """
    def _repl(m: re.Match) -> str:
        bucket = _classify_verdict(m.group(1))
        return (
            f'<blockquote class="verdict-callout {bucket}">'
            f'<p><strong>{m.group(1)}</strong>'
        )
    return _VERDICT_LEAD_PATTERN.sub(_repl, html)
