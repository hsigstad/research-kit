"""[cite:key] auto-linking + bibliography loaders.

Cite-ref resolution order, in one pass:
  1. docs/literature/<key>.md exists -> link to that page (label is the
     page's H1 author-year prefix).
  2. [cite:<key>] appears on docs/literature/index.md -> link to
     literature/index.html#cite-<key> (label is the bib author-year,
     or the citekey if no bib entry).
  3. Else -> keep the literal [cite:key] token (a visible "no entry yet"
     signal).

Lifted verbatim from connect.
"""

from __future__ import annotations

import html as _html
import re
from pathlib import Path

from ..context import BuildContext


def load_cite_map(project_root: Path) -> dict[str, str]:
    """Map [cite:<key>] keys to a display label, for literature pages."""
    lit_dir = project_root / "docs" / "literature"
    if not lit_dir.is_dir():
        return {}
    out: dict[str, str] = {}
    for p in sorted(lit_dir.glob("*.md")):
        if p.stem == "index":
            continue
        label = p.stem
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                head = line[2:].strip()
                label = head.split(" — ")[0].strip() or head
                break
        out[p.stem] = label
    return out


def load_bib_authoryear(project_root: Path) -> dict[str, str]:
    """Map BibTeX key -> 'Surname (year)' / 'Surname et al. (year)'."""
    out: dict[str, str] = {}
    bib_dir = project_root / "paper"
    if not bib_dir.is_dir():
        return out
    entry_re = re.compile(r'@\w+\s*\{\s*([^,\s]+)\s*,([^@]*)', re.DOTALL)
    field_re = re.compile(
        r'(\w+)\s*=\s*(?:\{((?:[^{}]|\{[^{}]*\})*)\}|"([^"]*)")',
        re.DOTALL)
    for bib in sorted(bib_dir.glob("*.bib")):
        text = bib.read_text(encoding="utf-8", errors="replace")
        for m in entry_re.finditer(text):
            key = m.group(1).strip()
            body = m.group(2)
            fields: dict[str, str] = {}
            for fm in field_re.finditer(body):
                fields[fm.group(1).lower()] = (fm.group(2) or fm.group(3) or "").strip()
            year = fields.get("year", "").strip()
            author = fields.get("author", "").strip()
            if not author:
                continue
            authors = [a.strip() for a in re.split(r"\s+and\s+", author) if a.strip()]
            def _surname(name: str) -> str:
                name = re.sub(r"[{}]", "", name)
                return name.split(",")[0].strip() if "," in name else name.split()[-1]
            if len(authors) == 1:
                who = _surname(authors[0])
            elif len(authors) == 2:
                who = f"{_surname(authors[0])} & {_surname(authors[1])}"
            else:
                who = f"{_surname(authors[0])} et al."
            label = f"{who} ({year})" if year else who
            out[key] = label
    return out


def load_index_cite_map(
    project_root: Path,
    cite_map: dict[str, str],
    bib_authoryear: dict[str, str],
    mode: str = "connect",
) -> dict[str, str]:
    """Map citekey -> label for [cite:<key>] tokens on the literature page.

    `mode="connect"` reads docs/literature/index.md (a doc-subdir layout).
    `mode="flat"` reads docs/literature.md (a flat docs layout).
    """
    if mode == "flat":
        idx = project_root / "docs" / "literature.md"
    else:
        idx = project_root / "docs" / "literature" / "index.md"
    if not idx.is_file():
        return {}
    out: dict[str, str] = {}
    token_re = re.compile(r"\[cite:([A-Za-z0-9][A-Za-z0-9_-]*)\]")
    for line in idx.read_text(encoding="utf-8").splitlines():
        for key in token_re.findall(line):
            if key in cite_map:
                continue
            out[key] = bib_authoryear.get(key, key)
    return out


def link_cite_refs(html: str, ctx: BuildContext, current_stem: str = "",
                   prefix: str = "../") -> str:
    """Auto-link [cite:<key>] tokens to literature page or index anchor.

    Two URL layouts via SiteConfig.cite_refs_mode:
      - "connect": <prefix>literature/<key>.html or <prefix>literature/index.html#cite-<key>
      - "flat":    literature.html#cite-<key>  (one flat docs/literature.md)

    `prefix` is the relative path from the citing page to the site root, so the
    href resolves from any page depth (``"../"`` for a doc_subdir/top-level page,
    ``"../../"`` for a folder-mode page one level deeper).
    """
    if not ctx.cite_map and not ctx.index_cite_map:
        return html
    mode = ctx.config.cite_refs_mode
    pattern = re.compile(
        r'(<a\b[^>]*>.*?</a>)|(\[cite:([A-Za-z0-9][A-Za-z0-9_-]*)\])',
        re.DOTALL)

    def _replacer(m: re.Match) -> str:
        if m.group(1):
            return m.group(1)
        token, key = m.group(2), m.group(3)
        if mode == "flat":
            if current_stem == "literature":
                return token
            if key in ctx.index_cite_map:
                label = ctx.index_cite_map[key]
                # Flat literature renders to docs/literature.html; resolve it via
                # the page's site-root prefix so cite tokens work from any depth
                # (top-level docs, root subdirs, folder-mode pages).
                return (f'<a class="cite-ref" '
                        f'href="{prefix}docs/literature.html#cite-{key}">'
                        f'{_html.escape(label)}</a>')
            return token
        # connect mode
        if key in ctx.cite_map and key != current_stem:
            label = ctx.cite_map[key]
            return (f'<a class="cite-ref" href="{prefix}literature/{key}.html">'
                    f'{_html.escape(label)}</a>')
        if key in ctx.index_cite_map and current_stem != "index":
            label = ctx.index_cite_map[key]
            return (f'<a class="cite-ref" '
                    f'href="{prefix}literature/index.html#cite-{key}">'
                    f'{_html.escape(label)}</a>')
        return token

    return pattern.sub(_replacer, html)


def inject_index_cite_anchors(html: str, ctx: BuildContext) -> str:
    """Attach id="cite-<key>" anchors to literature-page bullets.

    Used on the literature index (connect mode: docs/literature/index.md;
    flat mode: docs/literature.md). For each bullet that contains
    [cite:<key>] (either resolved to an <a class="cite-ref"> link by
    link_cite_refs, or still as a literal token), hoists the citekey onto
    the wrapping <li> and drops the literal token if present.
    """
    if not ctx.index_cite_map and not ctx.cite_map:
        return html
    html = re.sub(
        r'<li>(\s*(?:<p>\s*)?<a class="cite-ref" '
        r'href="\.\./literature/([A-Za-z0-9][A-Za-z0-9_-]*)\.html")',
        r'<li id="cite-\2">\1',
        html)
    html = re.sub(
        r'<li>(\s*(?:<p>\s*)?)\[cite:([A-Za-z0-9][A-Za-z0-9_-]*)\]\s*',
        r'<li id="cite-\2">\1',
        html)
    return html
