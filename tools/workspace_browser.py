#!/usr/bin/env python3
"""
Workspace HTML browser — renders all workspace markdown files as a
browsable static site with resolved citation hyperlinks.

Walks ~/research/**/*.md, converts to HTML, resolves:
  - [ns:key] tokens → hyperlinks to the target file's HTML page
  - `LIA.9`-style backtick legal citations → inline tooltips (when cite.py available)

Usage:
  python3 workspace_browser.py                    # build to ~/research/build/browser/
  python3 workspace_browser.py --out /tmp/browser  # custom output
  python3 workspace_browser.py --workspace /path   # custom workspace root
"""

from __future__ import annotations

import argparse
import html
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import mistune

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

WORKSPACE = Path("~/research").expanduser()
DEFAULT_OUT = WORKSPACE / "build" / "browser"

# Directories to walk (relative to workspace root)
WALK_DIRS = [
    "projects",
    "pipelines",
    "research/ideas",
    "research/methods",
    "research/institutions",
    "research/meta",
    "research/rules",
    "research-kit/skills",
    "research-kit/rules",
    "research-kit/tools",
    "research-kit/meta",
    "data_catalog",
]

# Files/directories to skip
SKIP_DIRS = {".git", "__pycache__", "node_modules", "build", ".venv", "venv"}
SKIP_FILES = {"CLAUDE.md", "README.md"}

# ---------------------------------------------------------------------------
# Registry parser (duplicated from check.py — stdlib only)
# ---------------------------------------------------------------------------

def parse_registry(path: Path) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    if not path.is_file():
        return entries
    current_section: str | None = None
    current: dict[str, str] = {}
    section_re = re.compile(r"^\[([a-z][a-z0-9_-]*\.[a-zA-Z0-9_-]+)\]\s*$")
    kv_re = re.compile(r'^(\w+)\s*=\s*"(.*?)"\s*$')
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        sm = section_re.match(line)
        if sm:
            if current_section and current:
                entries[current_section] = current
            current_section = sm.group(1)
            current = {}
            continue
        kvm = kv_re.match(line)
        if kvm and current_section:
            current[kvm.group(1)] = kvm.group(2)
    if current_section and current:
        entries[current_section] = current
    return entries


# ---------------------------------------------------------------------------
# Citation token resolution
# ---------------------------------------------------------------------------

CITATION_TOKEN_RE = re.compile(
    r"\[([a-z][a-z0-9-]*):([a-zA-Z0-9_-]+)\]"
)

EXTERNAL_NS_MAP = {
    "method": "method", "catalog": "catalog", "pipeline": "pipeline",
    "var": "var", "idea": "idea", "proj": "project", "inst": "inst",
}

INTERNAL_NAMESPACES = {
    "sec", "tab", "fig", "eq", "hyp", "decision", "result",
    "local-inst", "dataset", "local-method",
}


def resolve_external(ns: str, key: str, registry: dict,
                     path_to_html: dict[str, str]) -> str | None:
    """Resolve an external [ns:key] to an HTML href, or None."""
    reg_ns = EXTERNAL_NS_MAP.get(ns)
    if not reg_ns:
        return None
    entry = registry.get(f"{reg_ns}.{key}")
    if not entry:
        return None
    src_path = entry.get("path", "")
    anchor = entry.get("anchor", "")
    if not src_path:
        return None
    # Find the HTML page for this source path
    # Try with and without .md extension
    candidates = [src_path]
    if not src_path.endswith(".md"):
        candidates.append(src_path + "/index.md")
        candidates.append(src_path + ".md")
    for c in candidates:
        if c in path_to_html:
            href = path_to_html[c]
            if anchor:
                href += f"#{anchor}"
            return href
    # If it's a directory, look for any file under it
    for p, h in path_to_html.items():
        if p.startswith(src_path + "/"):
            return h  # link to the first page under that dir
    return None


def resolve_internal(ns: str, key: str) -> str:
    """Resolve an internal anchor to a same-page fragment."""
    anchor_id = f"{ns}-{key}"
    return f"#{anchor_id}"


# ---------------------------------------------------------------------------
# Legal citation integration (optional — graceful degradation)
# ---------------------------------------------------------------------------

def try_load_cite_module(workspace: Path):
    """Try to import the legal citation finder. Returns find_citations or None."""
    cite_path = workspace / "research" / "institutions" / "brazil" / "tools" / "leis_artigos"
    if not cite_path.is_dir():
        return None
    # Set DB path so cite.resolve() can find institutions.db
    db_candidates = [
        workspace / "data" / "institutions.db",
        workspace / "data" / "lei" / "artigos.db",
    ]
    for db in db_candidates:
        if db.is_file():
            import os
            os.environ.setdefault("INSTITUTIONS_DB", str(db))
            break
    sys.path.insert(0, str(cite_path))
    try:
        import cite as cite_mod  # type: ignore
        return cite_mod.find_citations
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------

def render_markdown(text: str) -> str:
    """Convert markdown to HTML via mistune."""
    md = mistune.create_markdown(
        escape=False,
        plugins=["table", "strikethrough", "footnotes", "task_lists"],
    )
    return md(text)


def add_heading_ids(html_text: str) -> str:
    """Add id attributes to headings for anchor linking."""
    def slugify(text: str) -> str:
        text = re.sub(r"<[^>]+>", "", text)  # strip tags
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s]+", "-", text)
        return text

    def replacer(m):
        tag = m.group(1)
        attrs = m.group(2) or ""
        content = m.group(3)
        slug = slugify(content)
        return f"<{tag}{attrs} id=\"{slug}\">{content}</{tag}>"

    return re.sub(
        r"<(h[1-6])([^>]*)>(.*?)</\1>",
        replacer,
        html_text,
        flags=re.DOTALL,
    )


def rewrite_md_links(html_text: str, current_dir: str, path_to_html: dict[str, str]) -> str:
    """Rewrite .md href links to .html within the browser output."""
    def replacer(m):
        prefix = m.group(1)
        href = m.group(2)
        suffix = m.group(3)

        if href.startswith(("http://", "https://", "mailto:", "#")):
            return m.group(0)

        # Split anchor
        anchor = ""
        if "#" in href:
            href, anchor = href.rsplit("#", 1)
            anchor = "#" + anchor

        if href.endswith(".md"):
            # Resolve relative to current directory
            from pathlib import PurePosixPath
            resolved = str(PurePosixPath(current_dir) / href)
            # Normalize
            parts = []
            for part in resolved.split("/"):
                if part == "..":
                    if parts:
                        parts.pop()
                elif part != ".":
                    parts.append(part)
            resolved = "/".join(parts)

            if resolved in path_to_html:
                new_href = path_to_html[resolved]
                return f'{prefix}"{new_href}{anchor}"{suffix}'

        return m.group(0)

    result = re.sub(r'(href=)"([^"]*)"([^>]*>)', replacer, html_text)

    # Second pass: turn bare `filename.md` mentions in text into links.
    # Match word_chars.md inside <code> or as bare text (not already in an href).
    def bare_replacer(m):
        pre = m.group(1)
        filename = m.group(2)
        # Skip if inside an HTML tag attribute
        if pre and pre[-1] in ('"', "'", "="):
            return m.group(0)
        # Try to resolve
        candidates = [
            current_dir + "/" + filename,
            filename,
        ]
        for c in candidates:
            # Normalize
            parts = []
            for part in c.split("/"):
                if part == "..":
                    if parts:
                        parts.pop()
                elif part != ".":
                    parts.append(part)
            norm = "/".join(parts)
            if norm in path_to_html:
                href = path_to_html[norm]
                return f'{pre}<a href="{href}">{filename}</a>'
        return m.group(0)

    result = re.sub(
        r'((?:^|[>\s(]))([a-zA-Z0-9_/-]+\.md)\b',
        bare_replacer,
        result,
    )
    return result


def resolve_citation_tokens(html_text: str, registry: dict,
                            path_to_html: dict[str, str],
                            current_project: str | None) -> str:
    """Replace [ns:key] tokens in rendered HTML with hyperlinks."""
    def replacer(m):
        full = m.group(0)
        ns = m.group(1)
        key = m.group(2)

        if ns in EXTERNAL_NS_MAP:
            href = resolve_external(ns, key, registry, path_to_html)
            title = ""
            reg_ns = EXTERNAL_NS_MAP[ns]
            entry = registry.get(f"{reg_ns}.{key}")
            if entry:
                title = f' title="{html.escape(entry.get("description", ""))}"'
            if href:
                return (f'<a class="cite cite-{ns}" href="{href}"{title}>'
                        f'{ns}:{key}</a>')
            else:
                return f'<span class="cite cite-unresolved" title="unresolved">[{ns}:{key}]</span>'

        elif ns in INTERNAL_NAMESPACES:
            anchor = resolve_internal(ns, key)
            return (f'<a class="cite cite-internal" href="{anchor}">'
                    f'{ns}:{key}</a>')

        elif ns == "cite":
            return f'<span class="cite cite-bib">{ns}:{key}</span>'

        return full

    return CITATION_TOKEN_RE.sub(replacer, html_text)


def resolve_legal_citations(html_text: str, find_citations_fn,
                            legal_cache: dict | None = None,
                            law_map: dict | None = None) -> str:
    """Replace backtick legal citations with styled hyperlinks.

    If law_map is provided, citations link to the corresponding law page.
    If legal_cache is provided and the DB is available, tooltips show
    the verbatim article text.
    """
    if find_citations_fn is None:
        return html_text

    def replacer(m):
        content = m.group(1)
        try:
            from cite import parse as cite_parse  # type: ignore
            c = cite_parse(content)
        except (ValueError, Exception):
            return m.group(0)

        # Build tooltip text
        tooltip = ""
        cache_key = content
        if legal_cache is not None:
            if cache_key in legal_cache:
                tooltip = legal_cache[cache_key]
            else:
                tooltip = _lookup_legal_text(c, content)
                legal_cache[cache_key] = tooltip

        if not tooltip:
            tooltip = content

        title_attr = f' title="{html.escape(tooltip)}"'

        # Build href to law page if available
        href = None
        if law_map:
            if c.is_case:
                if "_juris" in law_map:
                    href = f'{law_map["_juris"]}#{content}'
            elif c.is_sv:
                pass  # no dedicated page yet
            elif c.is_stse:
                pass
            elif c.identifier in law_map:
                # Build anchor: LIA.9.I → LIA-9-I
                anchor = content.replace(".", "-").replace("§", "p")
                href = f'{law_map[c.identifier]}#{anchor}'

        if href:
            return (f'<a class="legal-cite" href="{href}"{title_attr}>'
                    f'{html.escape(content)}</a>')
        else:
            return (f'<code class="legal-cite"{title_attr}>'
                    f'{html.escape(content)}</code>')

    return re.sub(r"<code>([^<]+)</code>", replacer, html_text)


def _lookup_legal_text(citation, raw: str) -> str:
    """Query institutions.db for verbatim text of a legal citation."""
    try:
        from cite import resolve as cite_resolve  # type: ignore
        from cite import lookup_case, lookup_sv, lookup_stse, lookup_sstj, lookup_stst  # type: ignore

        if citation.is_case:
            entry = lookup_case(citation.identifier)
            if entry:
                holding = entry.get("holding_short") or entry.get("tese_certificada") or ""
                status = entry.get("status", "")
                parts = [raw]
                if holding:
                    parts.append(holding[:300])
                if status:
                    parts.append(f"[{status}]")
                return " — ".join(parts)
            return raw

        if citation.is_sv:
            entry = lookup_sv(citation.identifier)
            if entry:
                enunciado = entry.get("enunciado", "")
                return f"{raw} — {enunciado[:400]}" if enunciado else raw
            return raw

        if citation.is_stse:
            entry = lookup_stse(citation.identifier)
            if entry:
                enunciado = entry.get("enunciado", "")
                return f"{raw} — {enunciado[:400]}" if enunciado else raw
            return raw

        if citation.is_sstj:
            entry = lookup_sstj(citation.identifier)
            if entry:
                enunciado = entry.get("enunciado", "")
                return f"{raw} — {enunciado[:400]}" if enunciado else raw
            return raw

        if hasattr(citation, 'is_stst') and citation.is_stst:
            entry = lookup_stst(citation.identifier)
            if entry:
                enunciado = entry.get("enunciado", "")
                return f"{raw} — {enunciado[:400]}" if enunciado else raw
            return raw

        # Statute — query DB
        rows = cite_resolve(citation)
        if rows:
            texts = []
            for row in rows[:3]:  # limit to first 3 paths
                texto = row["texto"] or ""
                if texto:
                    texts.append(texto[:300])
            if texts:
                return " | ".join(texts)
        return raw

    except (FileNotFoundError, Exception):
        return raw


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def discover_md_files(workspace: Path) -> list[Path]:
    """Find all markdown files to include in the browser."""
    files: list[Path] = []
    for rel_dir in WALK_DIRS:
        d = workspace / rel_dir
        if not d.is_dir():
            continue
        for md in sorted(d.rglob("*.md")):
            # Skip excluded dirs
            if any(part in SKIP_DIRS for part in md.relative_to(workspace).parts):
                continue
            # Skip excluded files
            if md.name in SKIP_FILES:
                continue
            files.append(md)
    return files


def md_path_to_html_path(rel: str) -> str:
    """Convert a workspace-relative .md path to an HTML output path."""
    if rel.endswith(".md"):
        return rel[:-3] + ".html"
    return rel + ".html"


# ---------------------------------------------------------------------------
# Navigation / index
# ---------------------------------------------------------------------------

def build_nav_tree(files: list[tuple[str, str]]) -> dict:
    """Build a nested dict from (rel_md_path, html_path) pairs."""
    tree: dict = {}
    for rel, html_path in files:
        parts = rel.split("/")
        node = tree
        for part in parts[:-1]:
            node = node.setdefault(part, {})
        node[parts[-1]] = html_path
    return tree


def render_nav_tree(tree: dict, depth: int = 0) -> str:
    """Render navigation tree as nested HTML list."""
    items = []
    # Separate directories and files
    dirs = {k: v for k, v in sorted(tree.items()) if isinstance(v, dict)}
    files = {k: v for k, v in sorted(tree.items()) if isinstance(v, str)}

    for name, subtree in dirs.items():
        inner = render_nav_tree(subtree, depth + 1)
        items.append(f'<li class="nav-dir"><details>'
                     f'<summary>{html.escape(name)}/</summary>{inner}</details></li>')
    for name, href in files.items():
        display = name.replace(".md", "")
        # For SKILL.md files, show parent directory name instead
        if display.upper() == "SKILL":
            # Extract skill name from href path (e.g., research-kit/skills/lint-docs/SKILL.html → lint-docs)
            parts = href.split("/")
            if len(parts) >= 2:
                display = parts[-2]
        items.append(f'<li class="nav-file"><a href="{href}">{html.escape(display)}</a></li>')

    return f'<ul class="nav-tree">{"".join(items)}</ul>'


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

CSS = """\
:root {
  --bg: #faf9f6; --card: #fffefa; --fg: #1a1a1a; --muted: #777;
  --link: #2563eb; --link-visited: #7c3aed;
  --border: #e5e2db; --code-bg: #f0ede6; --code-block-bg: #f5f3ee;
  --accent: #2563eb; --accent-light: #dbeafe;
  --cite-bg: #eef3fb; --cite-border: #93c5fd;
  --legal-bg: #fdf8e8; --legal-border: #e5d48b;
  --unresolved-bg: #fce8e8; --unresolved-border: #e8a0a0;
  --nav-bg: #f5f3ee; --sidebar-w: 300px; --header-h: 48px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #1a1916; --card: #222018; --fg: #e5e3dc; --muted: #999;
    --link: #60a5fa; --link-visited: #a78bfa;
    --border: #3a3830; --code-bg: #2a2820; --code-block-bg: #252318;
    --accent: #60a5fa; --accent-light: #1e3a5f;
    --cite-bg: #1e293b; --cite-border: #3b82f6;
    --legal-bg: #2a2510; --legal-border: #8b7a30;
    --unresolved-bg: #2a1515; --unresolved-border: #a04040;
    --nav-bg: #1f1d18; --card: #252318;
  }
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font: 17px/1.65 "Georgia","Times New Roman",serif;
       color: var(--fg); background: var(--bg); min-height: 100vh; }

/* Header bar */
.header { position: fixed; top: 0; left: 0; right: 0; height: var(--header-h);
          background: var(--card); border-bottom: 1px solid var(--border);
          display: flex; align-items: center; padding: 0 1.5rem; z-index: 100; }
.header-title { font: 600 1rem/1 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
                color: var(--fg); letter-spacing: .02em; }
.header-title a { color: inherit; text-decoration: none; }
.header-nav { margin-left: 2rem; display: flex; gap: 1.2rem; font-size: .85rem;
              font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.header-nav a { color: var(--muted); text-decoration: none; }
.header-nav a:hover { color: var(--fg); }

a { color: var(--link); text-decoration: none; }
a:visited { color: var(--link-visited); }
a:hover { text-decoration: underline; }

/* Layout */
.layout { display: flex; margin-top: var(--header-h); }

/* Sidebar */
.sidebar { width: var(--sidebar-w); background: var(--nav-bg); border-right: 1px solid var(--border);
           padding: 1rem; overflow-y: auto; position: fixed; top: var(--header-h); bottom: 0;
           font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.sidebar h2 { font-size: .85rem; text-transform: uppercase; letter-spacing: .05em;
              color: var(--muted); margin-bottom: .5rem; font-weight: 600; }
.nav-tree { list-style: none; font-size: .82rem; }
.nav-tree ul { padding-left: .6rem; }
.nav-tree li { margin: 1px 0; }
.nav-dir > details > summary { cursor: pointer; font-weight: 600; color: var(--muted);
                                padding: 2px 0; }
.nav-dir > details > summary:hover { color: var(--fg); }
.nav-file a { display: block; padding: 2px 6px; border-radius: 4px; color: var(--fg); }
.nav-file a:hover { background: var(--border); text-decoration: none; }
.nav-file a:visited { color: var(--fg); }

/* Main */
.main { margin-left: var(--sidebar-w); flex: 1; padding: 2rem 3rem 4rem;
        max-width: min(60rem, calc(100vw - var(--sidebar-w) - 4rem)); }
.breadcrumb { font: .8rem/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
              color: var(--muted); margin-bottom: 1.2rem; }
.breadcrumb a { color: var(--muted); }

/* Content */
h1, h2, h3, h4, h5, h6 { font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;
                           margin: 1.5em 0 .5em; line-height: 1.3;
                           scroll-margin-top: calc(var(--header-h) + 1rem); }
[id] { scroll-margin-top: calc(var(--header-h) + 1rem); }
h1 { font-size: 1.6rem; border-bottom: 1px solid var(--border); padding-bottom: .4rem; }
h2 { font-size: 1.25rem; }
h3 { font-size: 1.05rem; }
p { margin: .6em 0; }
ul, ol { margin: .5em 0 .5em 1.5em; }
li { margin: .15em 0; }
table { border-collapse: collapse; margin: 1em 0; font-size: .88rem;
        font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
th, td { border: 1px solid var(--border); padding: .45em .7em; text-align: left; }
th { background: var(--code-block-bg); font-weight: 600; }
tr:nth-child(even) td { background: var(--bg); }
pre { background: var(--code-block-bg); padding: 1em; border-radius: 5px; overflow-x: auto;
      font-size: .83rem; margin: 1em 0; border: 1px solid var(--border); }
code { background: var(--code-bg); padding: .15em .35em; border-radius: 3px; font-size: .88em; }
pre code { background: none; padding: 0; border: none; }
blockquote { border-left: 3px solid var(--accent); padding-left: 1em; color: var(--muted);
             margin: 1em 0; background: var(--code-block-bg); padding: .8em 1em; border-radius: 0 5px 5px 0; }
hr { border: none; border-top: 1px solid var(--border); margin: 2em 0; }
img { max-width: 100%; border-radius: 4px; }

/* Citations */
.cite { padding: 2px 5px; border-radius: 3px; font-size: .85em;
        font-family: "SF Mono","Fira Code",monospace; white-space: nowrap; }
.cite-method, .cite-catalog, .cite-pipeline, .cite-proj,
.cite-inst, .cite-idea, .cite-var { background: var(--cite-bg); border: 1px solid var(--cite-border); }
.cite-internal { background: var(--cite-bg); border: 1px solid var(--cite-border); }
.cite-bib { background: var(--code-bg); border: 1px solid var(--border); }
.cite-unresolved { background: var(--unresolved-bg); border: 1px solid var(--unresolved-border); }
.legal-cite { background: var(--legal-bg) !important; border: 1px solid var(--legal-border) !important;
              text-decoration: none !important; color: var(--fg) !important; }
a.legal-cite:hover { text-decoration: underline !important; }

/* Law pages */
.law-chapter { margin-top: 2em; color: var(--muted); font-size: 1.1rem; }
.law-section { margin-top: 1.2em; color: var(--muted); font-size: .95rem; font-weight: normal; font-style: italic; }
.law-caput { margin: 1em 0 .3em; font-weight: 500; scroll-margin-top: calc(var(--header-h) + 1rem); }
.law-path { margin: .2em 0 .2em 2em; font-size: .95em; scroll-margin-top: calc(var(--header-h) + 1rem); }
.law-case { margin: 1.5em 0; padding: 1em; border: 1px solid var(--border); border-radius: 6px; background: var(--card); }

/* Index page */
/* Multi-column list */
.col-list { columns: 3; column-gap: 2rem; list-style: none; margin: 1em 0; padding: 0; }
.col-list li { break-inside: avoid; padding: .3em 0; }
.col-list a { font-size: 1rem; }

/* Landing page */
.landing-cards { display: flex; gap: 1.5rem; align-items: flex-start; flex-wrap: wrap; }
.landing-card { flex: 1; min-width: 200px; }
.landing-card h2 { font-size: 1.1rem; margin: 0 0 .5rem; }
.landing-card h2 a { color: var(--fg); }
.landing-card ul { list-style: none; padding: 0; margin: 0; }
.landing-card ul li { padding: .15em 0; }
.landing-card .more { font-size: .85rem; margin-top: .3rem; }
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 0 1.5rem; }
@media (max-width: 768px) { .landing-cards { flex-direction: column; } }

.index-hero { text-align: center; padding: 3rem 0 2rem; }
.index-hero h1 { border: none; font-size: 2rem; margin-bottom: .3rem; }
.index-hero p { color: var(--muted); font-size: 1.05rem; max-width: 36rem; margin: 0 auto; }
.index-grid { display: grid; grid-template-columns: repeat(2, 1fr);
              gap: 1rem; margin-top: 1.5rem; }
.index-card { background: var(--card); border: 1px solid var(--border); border-radius: 8px;
              padding: 1.2rem 1.4rem; transition: box-shadow .15s; }
.index-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.06); }
.index-card h3 { margin: 0 0 .3rem; font-size: 1rem;
                 font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.index-card p { font-size: .85rem; color: var(--muted); margin: 0; }
.index-card .count { font-size: .8rem; color: var(--muted); margin-top: .4rem; }
.index-card ul { list-style: none; padding: 0; margin: .3rem 0 0; font-size: .88rem; }
.index-card ul li { padding: .1em 0; }
.subcard { margin-top: .5rem; padding: .4rem .6rem; background: var(--bg); border-radius: 4px; }
.subcard h4 { font-size: .8rem; color: var(--muted); margin: 0 0 .2rem; font-weight: 600;
              font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif; }
.subcard ul { font-size: .85rem; columns: 2; column-gap: 1.5rem; list-style: none; padding: 0; }
.subcard ul li { break-inside: avoid; }
.index-section { margin-top: 2.5rem; }
.index-section h2 { font-size: 1.1rem; color: var(--muted); border: none;
                    text-transform: uppercase; letter-spacing: .04em; margin-bottom: .8rem; }

@media (max-width: 768px) {
  .sidebar { display: none; }
  .main { margin-left: 0; padding: 1rem; }
  .header-nav { display: none; }
}
"""

PAGE_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<base href="{base_href}">
<title>{title} — Workspace Browser</title>
<link rel="stylesheet" href="style.css">
</head>
<body>
<header class="header">
  <span class="header-title"><a href="index.html">Workspace</a></span>
  <nav class="header-nav">
    <a href="projects/index.html">Projects</a>
    <a href="pipelines/index.html">Pipelines</a>
    <a href="research/index.html">Research</a>
    <a href="data_catalog/index.html">Data</a>
  </nav>
</header>
<div class="layout">
<nav class="sidebar">
<h2>Files</h2>
{nav}
</nav>
<main class="main">
<div class="breadcrumb">{breadcrumb}</div>
{content}
</main>
</div>
<script>
// Fix anchor links broken by base tag
document.addEventListener('click',function(e){{
  var a=e.target.closest('a');if(!a)return;
  var h=a.getAttribute('href');
  if(h&&h.charAt(0)==='#'){{e.preventDefault();
    var el=document.getElementById(h.slice(1));
    if(el)el.scrollIntoView();history.replaceState(null,'',h);}}
}});
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

def build_breadcrumb(rel_path: str, path_to_html: dict[str, str]) -> str:
    parts = rel_path.split("/")
    crumbs = ['<a href="index.html">workspace</a>']
    for i, part in enumerate(parts[:-1]):
        # Try to find an index page for this path segment
        segment_path = "/".join(parts[:i+1])
        # Section-level index (projects/, pipelines/, etc.)
        if i == 0:
            crumbs.append(f'<a href="{segment_path}/index.html">{html.escape(part)}</a>')
        else:
            # Try to find summary.md or any page in this directory
            summary_key = segment_path + "/docs/summary.md"
            if summary_key in path_to_html:
                crumbs.append(f'<a href="{path_to_html[summary_key]}">{html.escape(part)}</a>')
            else:
                crumbs.append(html.escape(part))
    crumbs.append(f"<strong>{html.escape(parts[-1])}</strong>")
    return " / ".join(crumbs)


def build_page(rel_md: str, md_text: str, registry: dict,
               path_to_html: dict[str, str], nav_html: str,
               find_citations_fn, base_href: str,
               legal_cache: dict | None = None,
               law_map: dict | None = None) -> str:
    """Render a single markdown file to a full HTML page."""
    # Determine current project (for internal anchor resolution)
    current_project = None
    if rel_md.startswith("projects/"):
        parts = rel_md.split("/")
        if len(parts) >= 2:
            current_project = parts[1]

    # Extract title from first heading or filename
    title_match = re.match(r"^#\s+(.+)", md_text, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else Path(rel_md).stem

    # Render markdown
    body = render_markdown(md_text)
    body = add_heading_ids(body)

    # Resolve links
    current_dir = str(Path(rel_md).parent)
    body = rewrite_md_links(body, current_dir, path_to_html)
    body = resolve_citation_tokens(body, registry, path_to_html, current_project)
    body = resolve_legal_citations(body, find_citations_fn, legal_cache, law_map)

    breadcrumb = build_breadcrumb(rel_md, path_to_html)

    return PAGE_TEMPLATE.format(
        title=html.escape(title),
        base_href=base_href,
        nav=nav_html,
        breadcrumb=breadcrumb,
        content=body,
    )


def build_index_page(registry: dict, path_to_html: dict[str, str],
                     nav_html: str, file_count: int, base_href: str,
                     workspace: Path) -> str:
    """Build the index.html landing page."""
    # Group files by top-level directory
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for rel, html_path in path_to_html.items():
        top = rel.split("/")[0]
        groups[top].append((rel, html_path))

    # Rank projects by most recent file modification
    def _slug_activity(section: str) -> list[tuple[str, float]]:
        slugs: dict[str, float] = {}
        for rel, hp in groups.get(section, []):
            parts = rel.split("/")
            if len(parts) >= 2:
                slug = parts[1]
                try:
                    mtime = (workspace / rel).stat().st_mtime
                except OSError:
                    mtime = 0
                if slug not in slugs or mtime > slugs[slug]:
                    slugs[slug] = mtime
        return sorted(slugs.items(), key=lambda x: -x[1])

    def _project_href(slug):
        site_index = workspace / "projects" / slug / "build" / "site" / "index.html"
        if site_index.is_file():
            return f"../../projects/{slug}/build/site/index.html"
        return f"projects/{slug}/index.html"

    # --- Projects card: top by recent activity ---
    project_activity = _slug_activity("projects")
    top_projects = project_activity[:10]
    proj_items = []
    for slug, _ in top_projects:
        href = _project_href(slug)
        proj_items.append(f'<li><a href="{href}">{html.escape(slug)}</a></li>')
    proj_html = (
        f'<div class="index-card landing-card">'
        f'<h2><a href="projects/index.html">Projects</a></h2>'
        f'<ul class="col-list">{"".join(proj_items)}</ul>'
    )
    if len(project_activity) > 10:
        proj_html += f'<p class="more"><a href="projects/index.html">all {len(project_activity)} &rarr;</a></p>'
    proj_html += '</div>'

    # --- Pipelines card ---
    pipeline_activity = _slug_activity("pipelines")
    pipe_items = []
    for slug, _ in pipeline_activity:
        summary_hp = None
        for rel, hp in groups.get("pipelines", []):
            if rel == f"pipelines/{slug}/docs/summary.md":
                summary_hp = hp
                break
        href = summary_hp or groups.get("pipelines", [(None, "#")])[0][1]
        pipe_items.append(f'<li><a href="{href}">{html.escape(slug)}</a></li>')
    pipe_html = (
        f'<div class="index-card landing-card">'
        f'<h2><a href="pipelines/index.html">Pipelines</a></h2>'
        f'<ul class="col-list">{"".join(pipe_items)}</ul>'
        f'</div>'
    )

    # --- Research card: two-column with key subdirs ---
    catalog_hp = path_to_html.get("data_catalog/DATA_CATALOG.md", "data_catalog/index.html")
    research_left = [
        ("methods", "research/index.html"),
        ("meta", "research/index.html"),
        ("institutions", "research/institutions/index.html"),
        ("ideas", "research/ideas/index.html"),
    ]
    research_right = [
        ("rules", "research/index.html"),
        ("skills", "research/index.html"),
        ("data catalog", catalog_hp),
    ]
    left_items = "".join(
        f'<li><a href="{href}">{html.escape(name)}</a></li>'
        for name, href in research_left
    )
    right_items = "".join(
        f'<li><a href="{href}">{html.escape(name)}</a></li>'
        for name, href in research_right
    )
    research_html = (
        f'<div class="index-card landing-card">'
        f'<h2><a href="research/index.html">Research</a></h2>'
        f'<div class="two-col">'
        f'<ul>{left_items}</ul>'
        f'<ul>{right_items}</ul>'
        f'</div>'
        f'</div>'
    )

    content = f"""\
<div class="landing-cards">
{proj_html}
{pipe_html}
{research_html}
</div>
"""

    return PAGE_TEMPLATE.format(
        title="Workspace",
        base_href=base_href,
        nav=nav_html,
        breadcrumb="<strong>workspace</strong>",
        content=content,
    )


def build_section_index(section: str, groups: dict, registry: dict,
                        path_to_html: dict[str, str],
                        nav_html: str, base_href: str,
                        workspace: Path) -> str:
    """Build a landing page for a top-level section (projects/, pipelines/, etc.)."""
    files = sorted(groups.get(section, []))

    def _slug_groups(files):
        slugs: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for rel, hp in files:
            parts = rel.split("/")
            if len(parts) >= 2:
                slugs[parts[1]].append((rel, hp))
        return slugs

    def _render_files_with_subcards(file_list: list[tuple[str, str]],
                                     depth: int = 2) -> str:
        """Render a list of files, grouping subfolders as subcards.

        depth is the path component index where files vs subfolders split.
        E.g. for pipelines/brazil/docs/data.md, depth=2 splits at docs/.
        """
        root_items = []
        subfolder_items: dict[str, list[tuple[str, str]]] = defaultdict(list)

        for rel, hp in sorted(file_list):
            parts = rel.split("/")
            if len(parts) > depth + 1:
                # File is in a subfolder
                subfolder = parts[depth]
                subfolder_items[subfolder].append((rel, hp))
            else:
                p = Path(rel)
                name = p.parent.name if p.stem.upper() == "SKILL" else p.stem
                root_items.append(f'<li><a href="{hp}">{html.escape(name)}</a></li>')

        result = ""
        if root_items:
            result += f'<ul class="col-list">{"".join(root_items)}</ul>'

        for subfolder in sorted(subfolder_items):
            sub_items = []
            for rel, hp in sorted(subfolder_items[subfolder]):
                p = Path(rel)
                name = p.parent.name if p.stem.upper() == "SKILL" else p.stem
                sub_items.append(f'<li><a href="{hp}">{html.escape(name)}</a></li>')
            result += (f'<div class="subcard">'
                       f'<h4>{html.escape(subfolder)}</h4>'
                       f'<ul>{"".join(sub_items)}</ul></div>')

        return result

    def _project_href(slug):
        """Link to project site if it exists, else to fallback doc listing."""
        site_index = workspace / "projects" / slug / "build" / "site" / "index.html"
        if site_index.is_file():
            # base is build/browser/, site is at projects/<slug>/build/site/
            # need ../../projects/<slug>/build/site/index.html
            return f"../../projects/{slug}/build/site/index.html"
        return f"projects/{slug}/index.html"

    if section == "projects":
        title = "Projects"
        slugs = _slug_groups(files)
        items = []
        for slug in sorted(slugs):
            href = _project_href(slug)
            items.append(f'<li><a href="{href}">{html.escape(slug)}</a></li>')
        body = (f'<h1>{title}</h1>\n'
                f'<ul class="col-list">{"".join(items)}</ul>')

    elif section == "pipelines":
        title = "Pipelines"
        slugs = _slug_groups(files)
        cards = []
        for slug in sorted(slugs):
            inner = _render_files_with_subcards(slugs[slug], depth=2)
            cards.append(
                f'<div class="index-card">'
                f'<h3>{html.escape(slug)}</h3>'
                f'{inner}</div>'
            )
        body = f'<h1>{title}</h1>\n<div class="index-grid">{"".join(cards)}</div>'

    elif section in ("research", "research-kit"):
        title = "Research"
        # Combine research/ and research-kit/ files
        all_files = sorted(groups.get("research", []) + groups.get("research-kit", []))
        subdirs: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for rel, hp in all_files:
            parts = rel.split("/")
            # Group by second path component (research/methods → methods, research-kit/skills → skills)
            if len(parts) >= 2:
                subdirs[parts[1]].append((rel, hp))
        # Sections that are small enough to show inline pages
        expand = {"methods", "meta", "rules", "refs", "skills", "tools"}
        sections_html = []
        for subdir in ["methods", "meta", "rules", "skills", "tools", "refs", "ideas", "institutions"]:
            if subdir not in subdirs:
                continue
            sub_files = sorted(subdirs[subdir])
            if subdir in expand:
                label = subdir
                if subdir in ("skills", "tools"):
                    label = f"kit/{subdir}"
                # Skills: flat list (one folder per skill, no subcards)
                if subdir == "skills":
                    items = []
                    for rel, hp in sub_files:
                        p = Path(rel)
                        name = p.parent.name if p.stem.upper() == "SKILL" else p.stem
                        items.append(f'<li><a href="{hp}">{html.escape(name)}</a></li>')
                    inner = f'<ul class="col-list">{"".join(items)}</ul>'
                else:
                    inner = _render_files_with_subcards(sub_files, depth=2)
                sections_html.append(
                    f'<div class="index-card">'
                    f'<h3>{html.escape(label)}</h3>'
                    f'{inner}</div>'
                )
            else:
                # ideas, institutions — card with link
                sections_html.append(
                    f'<div class="index-card">'
                    f'<h3><a href="research/{subdir}/index.html">'
                    f'{html.escape(subdir)}</a></h3>'
                    f'<p class="count">{len(sub_files)} pages</p>'
                    f'</div>'
                )
        body = f'<h1>{title}</h1>\n<div class="index-grid">{"".join(sections_html)}</div>'

    elif section == "data_catalog":
        title = "Data Catalog"
        items = []
        for rel, hp in files:
            name = Path(rel).stem
            items.append(f'<li><a href="{hp}">{html.escape(name)}</a></li>')
        body = f'<h1>{title}</h1>\n<ul class="col-list">{"".join(items)}</ul>'

    else:
        title = section
        items = []
        for rel, hp in files:
            items.append(f'<li><a href="{hp}">{html.escape(rel)}</a></li>')
        body = f'<h1>{title}</h1>\n<ul>{"".join(items)}</ul>'

    return PAGE_TEMPLATE.format(
        title=title,
        base_href=base_href,
        nav=nav_html,
        breadcrumb=f'<a href="index.html">workspace</a> / <strong>{section}</strong>',
        content=body,
    )


def build_project_doc_listing(slug: str, files: list[tuple[str, str]],
                              nav_html: str, base_href: str) -> str:
    """Build a fallback listing page for a project without a site."""
    items = []
    for rel, hp in sorted(files):
        name = Path(rel).name.replace(".md", "")
        items.append(f'<li><a href="{hp}">{html.escape(name)}</a></li>')
    content = f'<h1>{slug}</h1>\n<p>No project site built. Documentation pages:</p>\n<ul>{"".join(items)}</ul>'
    return PAGE_TEMPLATE.format(
        title=slug,
        base_href=base_href,
        nav=nav_html,
        breadcrumb=f'<a href="index.html">workspace</a> / <a href="projects/index.html">projects</a> / <strong>{slug}</strong>',
        content=content,
    )


# ---------------------------------------------------------------------------
# Law pages — one HTML page per law with anchored articles
# ---------------------------------------------------------------------------

def build_law_pages(workspace: Path, out_dir: Path, nav_html: str,
                    base_href: str) -> dict[str, str]:
    """Generate HTML pages for each law in institutions.db.

    Returns a map of citation-prefix → relative html path for linking.
    E.g. {"LIA": "laws/LIA.html", "CF": "laws/CF.html"}
    """
    import sqlite3

    db_candidates = [
        workspace / "data" / "institutions.db",
        workspace / "data" / "lei" / "artigos.db",
    ]
    db_path = None
    for p in db_candidates:
        if p.is_file():
            db_path = p
            break
    if not db_path:
        return {}

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row

    # Get all laws
    laws = con.execute(
        "SELECT DISTINCT apelido FROM artigo ORDER BY apelido"
    ).fetchall()

    law_map: dict[str, str] = {}
    laws_dir = out_dir / "laws"
    laws_dir.mkdir(parents=True, exist_ok=True)

    for (apelido,) in laws:
        rows = con.execute(
            "SELECT * FROM artigo WHERE apelido = ? AND vigente_ate IS NULL "
            "ORDER BY ordem ASC",
            [apelido],
        ).fetchall()
        if not rows:
            continue

        # Get law title from first row
        numero = rows[0]["numero_lei"] or ""
        ano = rows[0]["ano_lei"] or ""
        law_title = f"{apelido}"
        if numero and ano:
            law_title += f" (Lei {numero}/{ano})"

        # Build body grouped by capitulo/secao/artigo
        body_parts = []
        current_cap = None
        current_sec = None
        current_art = None

        for row in rows:
            cap = row["capitulo_titulo"]
            sec = row["secao_titulo"]
            art = row["artigo"]
            art_letra = row["artigo_letra"] or ""
            path = row["path"] or ""
            texto = row["texto"] or ""

            # Chapter heading
            if cap and cap != current_cap:
                cap_num = row["capitulo"] or ""
                body_parts.append(
                    f'<h2 class="law-chapter">Cap. {html.escape(cap_num)} &mdash; '
                    f'{html.escape(cap)}</h2>'
                )
                current_cap = cap
                current_sec = None

            # Section heading
            if sec and sec != current_sec:
                sec_num = row["secao"] or ""
                body_parts.append(
                    f'<h3 class="law-section">Seção {html.escape(sec_num)} &mdash; '
                    f'{html.escape(sec)}</h3>'
                )
                current_sec = sec

            # Article anchor: LIA.9, LIA.9.I, LIA.9.§1
            art_id = f"{apelido}.{art}"
            if art_letra:
                art_id += f"-{art_letra}"
            if path and path != "caput":
                art_id += f".{path}"

            # Anchor id (dots to dashes for valid HTML ids)
            anchor = art_id.replace(".", "-").replace("§", "p")

            css_class = "law-caput" if path == "caput" else "law-path"
            body_parts.append(
                f'<p class="{css_class}" id="{html.escape(anchor)}">'
                f'{html.escape(texto)}</p>'
            )

        content = f'<h1>{html.escape(law_title)}</h1>\n' + "\n".join(body_parts)

        page_html = PAGE_TEMPLATE.format(
            title=law_title,
            base_href=base_href,
            nav=nav_html,
            breadcrumb=(f'<a href="index.html">workspace</a> / '
                        f'<a href="laws/index.html">laws</a> / '
                        f'<strong>{html.escape(apelido)}</strong>'),
            content=content,
        )

        out_file = laws_dir / f"{apelido}.html"
        out_file.write_text(page_html, encoding="utf-8")
        law_map[apelido] = f"laws/{apelido}.html"

    # Build laws index
    items = "".join(
        f'<li><a href="laws/{html.escape(ap)}.html">{html.escape(ap)}</a></li>'
        for ap in sorted(law_map)
    )
    index_content = f'<h1>Laws</h1>\n<ul class="col-list">{items}</ul>'
    index_html = PAGE_TEMPLATE.format(
        title="Laws",
        base_href=base_href,
        nav=nav_html,
        breadcrumb='<a href="index.html">workspace</a> / <strong>laws</strong>',
        content=index_content,
    )
    (laws_dir / "index.html").write_text(index_html, encoding="utf-8")

    # Build jurisprudence page
    try:
        sys.path.insert(0, str(workspace / "research" / "institutions" / "brazil" / "tools" / "leis_artigos"))
        import cite as cite_mod
        juris_idx = cite_mod.load_juris_index()
        cases = juris_idx.get("cases", {})
        if cases:
            case_parts = []
            for key in sorted(cases):
                entry = cases[key]
                holding = entry.get("holding_short") or entry.get("tese_certificada") or ""
                status = entry.get("status", "")
                anchor = key
                case_parts.append(
                    f'<div class="law-case" id="{html.escape(anchor)}">'
                    f'<h3>{html.escape(key)}</h3>'
                    f'<p><strong>Status:</strong> {html.escape(status)}</p>'
                )
                if holding:
                    case_parts.append(f'<p>{html.escape(holding)}</p>')
                case_parts.append('</div>')
            juris_html = PAGE_TEMPLATE.format(
                title="Jurisprudence",
                base_href=base_href,
                nav=nav_html,
                breadcrumb='<a href="index.html">workspace</a> / <strong>jurisprudence</strong>',
                content=f'<h1>Jurisprudence</h1>\n' + "\n".join(case_parts),
            )
            (out_dir / "jurisprudence.html").write_text(juris_html, encoding="utf-8")
            law_map["_juris"] = "jurisprudence.html"
    except Exception:
        pass

    con.close()
    print(f"Generated {len(law_map)} law/jurisprudence pages")
    return law_map


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Build workspace HTML browser")
    ap.add_argument("--workspace", type=Path, default=WORKSPACE)
    ap.add_argument("--out", type=Path, default=None,
                    help="Output directory (default: <workspace>/build/browser/)")
    ap.add_argument("--full", action="store_true",
                    help="Force full rebuild (ignore mtime cache)")
    args = ap.parse_args()

    workspace = args.workspace.expanduser().resolve()
    out_dir = (args.out or workspace / "build" / "browser").resolve()

    print(f"Workspace: {workspace}")
    print(f"Output:    {out_dir}")

    # Load registry
    registry_path = workspace / "research" / "refs" / "registry.toml"
    registry = parse_registry(registry_path)
    if not registry:
        print(f"WARNING: could not load registry from {registry_path}", file=sys.stderr)

    # Try to load legal citation module
    find_citations_fn = try_load_cite_module(workspace)
    if find_citations_fn:
        print("Legal citation resolver loaded")
    else:
        print("Legal citation resolver not available (cite.py) — skipping legal citations")

    # Discover files
    md_files = discover_md_files(workspace)
    print(f"Found {len(md_files)} markdown files")

    # Build path maps
    # rel_md → html output path (relative to out_dir)
    path_to_html: dict[str, str] = {}
    for md in md_files:
        rel = str(md.relative_to(workspace))
        path_to_html[rel] = md_path_to_html_path(rel)

    # Also add directory-level entries for registry paths that point to dirs
    for key, entry in registry.items():
        p = entry.get("path", "")
        if p and not p.endswith(".md"):
            # It's a directory reference — find first file under it
            for rel, hp in path_to_html.items():
                if rel.startswith(p + "/"):
                    path_to_html[p] = hp
                    break

    # Base href for file:// compatibility
    base_href = out_dir.as_uri() + "/"

    # Build navigation
    file_pairs = [(str(md.relative_to(workspace)), path_to_html[str(md.relative_to(workspace))])
                  for md in md_files]
    nav_tree = build_nav_tree(file_pairs)
    nav_html = render_nav_tree(nav_tree)

    # Incremental build: detect which files changed since last build.
    # If the file set changed (new/deleted files) or registry changed,
    # we must rebuild all pages (nav tree changes). Otherwise only
    # rebuild pages whose source .md is newer than the output .html.
    registry_mtime = registry_path.stat().st_mtime if registry_path.is_file() else 0
    nav_marker = out_dir / ".nav_marker"
    force_all = args.full

    if not force_all and nav_marker.is_file():
        # Check if file set changed
        old_file_set = set(nav_marker.read_text(encoding="utf-8").splitlines())
        new_file_set = {str(md.relative_to(workspace)) for md in md_files}
        if old_file_set != new_file_set:
            force_all = True
            print("File set changed — full rebuild")
        elif registry_mtime > nav_marker.stat().st_mtime:
            force_all = True
            print("Registry changed — full rebuild")
    else:
        force_all = True

    # Generate law pages from institutions.db
    law_map = build_law_pages(workspace, out_dir, nav_html, base_href)

    # Shared cache for legal citation DB lookups (avoids repeated queries)
    legal_cache: dict[str, str] = {}

    # Render pages
    rendered = 0
    skipped = 0
    for md in md_files:
        rel = str(md.relative_to(workspace))
        html_path = path_to_html[rel]
        out_file = out_dir / html_path

        # Skip if output is newer than source (incremental)
        if not force_all and out_file.is_file():
            if out_file.stat().st_mtime >= md.stat().st_mtime:
                skipped += 1
                continue

        try:
            md_text = md.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  SKIP {rel}: {e}", file=sys.stderr)
            continue

        page_html = build_page(rel, md_text, registry, path_to_html,
                               nav_html, find_citations_fn, base_href,
                               legal_cache, law_map)

        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(page_html, encoding="utf-8")
        rendered += 1

    # Write shared CSS
    (out_dir / "style.css").write_text(CSS, encoding="utf-8")

    # Write workspace_nav.js — project sites can optionally load this
    # to show a small link back to the workspace browser. Only exists
    # on the local machine, so coauthors never see it.
    nav_js = (
        '(function(){'
        'var a=document.createElement("a");'
        'a.href="' + base_href + 'index.html";'
        'a.textContent="\\u2302";'  # ⌂
        'a.title="Workspace browser";'
        'a.style.cssText="position:fixed;top:8px;left:8px;z-index:9999;'
        'font-size:20px;text-decoration:none;color:#999;opacity:.4;'
        'transition:opacity .2s";'
        'a.onmouseover=function(){this.style.opacity="1"};'
        'a.onmouseout=function(){this.style.opacity=".4"};'
        'document.body.appendChild(a);'
        '})();'
    )
    (out_dir / "workspace_nav.js").write_text(nav_js, encoding="utf-8")

    # Write nav marker (file list for change detection)
    nav_marker.parent.mkdir(parents=True, exist_ok=True)
    nav_marker.write_text(
        "\n".join(str(md.relative_to(workspace)) for md in md_files),
        encoding="utf-8",
    )

    # Build section index pages
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for rel, hp in path_to_html.items():
        top = rel.split("/")[0]
        groups[top].append((rel, hp))

    for section in ["projects", "pipelines", "research", "data_catalog"]:
        if section not in groups:
            continue
        section_html = build_section_index(section, groups, registry,
                                           path_to_html, nav_html, base_href,
                                           workspace)
        section_file = out_dir / section / "index.html"
        section_file.parent.mkdir(parents=True, exist_ok=True)
        section_file.write_text(section_html, encoding="utf-8")
        # research-kit shares the research landing page
        if section == "research" and "research-kit" in groups:
            kit_file = out_dir / "research-kit" / "index.html"
            kit_file.parent.mkdir(parents=True, exist_ok=True)
            kit_file.write_text(section_html, encoding="utf-8")

    # Build research sub-section index pages (ideas, institutions)
    if "research" in groups:
        research_subdirs: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for rel, hp in groups["research"]:
            parts = rel.split("/")
            if len(parts) >= 2:
                research_subdirs[parts[1]].append((rel, hp))

        for subdir_name in ["ideas", "institutions"]:
            if subdir_name not in research_subdirs:
                continue
            sub_files = sorted(research_subdirs[subdir_name])
            if subdir_name == "institutions":
                # Split into topics/ and root reference files
                topics = [(r, h) for r, h in sub_files
                          if "/topics/" in r]
                reference = [(r, h) for r, h in sub_files
                             if "/topics/" not in r]
                parts_html = []
                if reference:
                    items = "".join(
                        f'<li><a href="{hp}">{html.escape(Path(rel).stem)}</a></li>'
                        for rel, hp in reference
                    )
                    parts_html.append(f'<h2>Reference</h2>\n<ul class="col-list">{items}</ul>')
                if topics:
                    items = "".join(
                        f'<li><a href="{hp}">{html.escape(Path(rel).stem)}</a></li>'
                        for rel, hp in topics
                    )
                    parts_html.append(f'<h2>Topics</h2>\n<ul class="col-list">{items}</ul>')
                content = f'<h1>Institutions</h1>\n' + "\n".join(parts_html)
            else:
                items = "".join(
                    f'<li><a href="{hp}">{html.escape(Path(rel).stem)}</a></li>'
                    for rel, hp in sub_files
                )
                content = f'<h1>{subdir_name.title()}</h1>\n<ul class="col-list">{items}</ul>'

            idx_html = PAGE_TEMPLATE.format(
                title=subdir_name.title(),
                base_href=base_href,
                nav=nav_html,
                breadcrumb=(f'<a href="index.html">workspace</a> / '
                            f'<a href="research/index.html">research</a> / '
                            f'<strong>{subdir_name}</strong>'),
                content=content,
            )
            idx_file = out_dir / "research" / subdir_name / "index.html"
            idx_file.parent.mkdir(parents=True, exist_ok=True)
            idx_file.write_text(idx_html, encoding="utf-8")

    # Build fallback doc listing pages for projects without sites
    if "projects" in groups:
        project_slugs: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for rel, hp in groups["projects"]:
            parts = rel.split("/")
            if len(parts) >= 2:
                project_slugs[parts[1]].append((rel, hp))
        for slug, slug_files in sorted(project_slugs.items()):
            site_index = workspace / "projects" / slug / "build" / "site" / "index.html"
            if not site_index.is_file():
                listing_html = build_project_doc_listing(slug, slug_files,
                                                         nav_html, base_href)
                listing_file = out_dir / "projects" / slug / "index.html"
                listing_file.parent.mkdir(parents=True, exist_ok=True)
                listing_file.write_text(listing_html, encoding="utf-8")

    # Build main index
    index_html = build_index_page(registry, path_to_html, nav_html, rendered + skipped, base_href, workspace)
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")

    if skipped:
        print(f"\nRendered {rendered} pages, skipped {skipped} unchanged + index → {out_dir}/")
    else:
        print(f"\nRendered {rendered} pages + index → {out_dir}/")
    print(f"Open: file://{out_dir}/index.html")


if __name__ == "__main__":
    main()
