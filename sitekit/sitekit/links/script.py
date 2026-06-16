"""Script-page rendering and bocconi/source path auto-linking.

Lifted from connect. Renders each docs-referenced source script to its own
HTML page with Pygments-highlighted code; rewrites bare path mentions and
existing anchors to point at the rendered page.
"""

from __future__ import annotations

import html as _html
import re
from pathlib import Path
from typing import Optional

from ..context import BuildContext
from ..nav import _brief_title

try:
    from pygments import highlight as _pyg_highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import get_lexer_for_filename
    from pygments.lexers.special import TextLexer
    from pygments.util import ClassNotFound
    _PYGMENTS = True
except ImportError:
    _PYGMENTS = False


_SCRIPT_EXTS = ("R", "r", "py", "do", "sh")
# Configurable script-root prefix; defaults to bocconi/source/ (connect's),
# but project hooks can rebuild the regex by importing _build_script_re.
_DEFAULT_SCRIPT_ROOT = "bocconi/source"


def _build_script_re(root_prefix: str = _DEFAULT_SCRIPT_ROOT) -> re.Pattern:
    return re.compile(
        re.escape(root_prefix)
        + r"/[A-Za-z0-9_./-]+\.(?:"
        + "|".join(_SCRIPT_EXTS)
        + r")"
    )


_SCRIPT_PATH_RE = _build_script_re()


if _PYGMENTS:
    CODE_CSS = (
        "<style>\n"
        + HtmlFormatter(cssclass="highlight").get_style_defs(".highlight")
        + """
.code-meta { font-size: .8rem; color: var(--muted); margin-bottom: .9rem; }
.code-refs { font-size: .85rem; margin: 0 0 1.1rem; padding-left: 1.3rem; }
.code-refs li { margin-bottom: .15rem; }
.highlighttable { display: table; width: 100%; margin: 0 0 .8rem;
  border: 1px solid var(--border); border-radius: 6px; overflow: hidden;
  font-size: .82rem; }
.highlighttable td { border: none; padding: 0; vertical-align: top; }
.highlighttable tr:nth-child(even) td { background: none; }
.highlighttable .linenos { width: 1%; white-space: nowrap; background: #f0f2f4;
  -webkit-user-select: none; user-select: none; }
.highlighttable .linenos pre { color: #aab0b8; padding: .9rem .55rem;
  background: none; border: none; }
.highlighttable .code .highlight pre { margin: 0; border: none;
  border-radius: 0; }
</style>"""
    )
else:
    CODE_CSS = (
        "<style>.code-meta { font-size: .8rem; color: var(--muted); "
        "margin-bottom: .9rem; }</style>"
    )


def highlight_source(path: str, source: str) -> str:
    """Render a source file as highlighted HTML."""
    if _PYGMENTS:
        try:
            lexer = get_lexer_for_filename(path)
        except ClassNotFound:
            lexer = TextLexer()
        formatter = HtmlFormatter(linenos="table", cssclass="highlight")
        return _pyg_highlight(source, lexer, formatter)
    return f'<pre class="highlight"><code>{_html.escape(source)}</code></pre>'


def load_script_index(
    ctx: BuildContext,
    doc_subdirs: list[tuple[str, str, str]],
    doc_registry: list[tuple[str, str, str, str]],
    script_root: str = _DEFAULT_SCRIPT_ROOT,
) -> tuple[dict[str, str], dict[str, list[tuple[str, str]]]]:
    """Scan docs/ for script paths and return (script_map, script_refs)."""
    project_root = ctx.project_root
    script_re = _build_script_re(script_root)
    subdir_names = {s for s, _, _ in doc_subdirs}
    registry_rel = {rp for rp, *_ in doc_registry}

    def _page_href(md_path: Path) -> Optional[str]:
        rel = md_path.relative_to(project_root / "docs")
        if len(rel.parts) == 2 and rel.parts[0] in subdir_names:
            return f"../{rel.parts[0]}/{md_path.stem}.html"
        if len(rel.parts) == 1 and f"docs/{md_path.name}" in registry_rel:
            return f"../docs/{md_path.stem}.html"
        return None

    raw_refs: dict[str, list[tuple[str, str]]] = {}
    docs_dir = project_root / "docs"
    if docs_dir.is_dir():
        for md in sorted(docs_dir.rglob("*.md")):
            paths = set(script_re.findall(md.read_text(encoding="utf-8")))
            href = _page_href(md) if paths else None
            if not href:
                continue
            entry = (href, _brief_title(md))
            for p in paths:
                raw_refs.setdefault(p, []).append(entry)

    script_map: dict[str, str] = {}
    script_refs: dict[str, list[tuple[str, str]]] = {}
    owner: dict[str, str] = {}
    for path in sorted(raw_refs):
        if not (project_root / path).is_file():
            continue
        stem = Path(path).name
        if owner.get(stem, path) != path:
            stem = f"{Path(path).parent.name}__{stem}"
        owner[stem] = path
        script_map[path] = stem
        script_refs[path] = sorted(set(raw_refs[path]))
    return script_map, script_refs


def link_script_refs(html: str, ctx: BuildContext, script_root: str = _DEFAULT_SCRIPT_ROOT) -> str:
    """Link script paths to their rendered code page."""
    if not ctx.script_map:
        return html

    script_re = _build_script_re(script_root)

    def _href_repl(m: re.Match) -> str:
        inner = script_re.search(m.group(1))
        if inner and inner.group(0) in ctx.script_map:
            return f'href="../code/{ctx.script_map[inner.group(0)]}.html"'
        return m.group(0)

    html = re.sub(
        rf'href="([^"]*{re.escape(script_root)}/[^"]*)"',
        _href_repl,
        html,
    )

    token = re.compile(
        r"(<a\b[^>]*>.*?</a>)|(<[^>]+>)|(" + script_re.pattern + r")",
        re.DOTALL,
    )

    def _bare_repl(m: re.Match) -> str:
        if m.group(1) or m.group(2):
            return m.group(0)
        path = m.group(3)
        stem = ctx.script_map.get(path)
        return f'<a href="../code/{stem}.html">{path}</a>' if stem else path

    return token.sub(_bare_repl, html)
