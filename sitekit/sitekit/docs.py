"""Build individual doc pages and doc subdirectories.

Wires render + nav + links into a single render pipeline. The pipeline is
deliberately permissive: features turned off in SiteConfig short-circuit
their link-rewriter pass.
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Optional

from .context import BuildContext
from .nav import inject_nav, _brief_title
from .render import (
    md_to_html, add_heading_ids, strip_leading_h1, rewrite_md_links,
    protect_math, restore_math,
)
from .templates import read_template
from .links import (
    link_an_refs, link_h_refs, link_cite_refs, link_anec_refs,
    link_script_refs, scan_finding_tags, inject_finding_tags,
    inject_index_cite_anchors,
)


def _split_frontmatter(text: str) -> tuple[Optional[dict], str]:
    """Split a leading `---`-delimited YAML frontmatter block."""
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    try:
        meta = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return None, text
    return (meta if isinstance(meta, dict) else None), text[end + 5:]


def _render_content(
    ctx: BuildContext,
    text: str,
    current_stem: str,
    in_subdir: bool,
) -> str:
    """Run text through the render + link-rewrite pipeline."""
    cfg = ctx.config

    if cfg.enable_math_protection:
        text, placeholders = protect_math(text)
    else:
        placeholders = {}

    content_html = md_to_html(text)
    if in_subdir:
        content_html = strip_leading_h1(content_html)
    content_html = add_heading_ids(content_html)
    content_html = rewrite_md_links(content_html, ctx, in_subdir=in_subdir)

    if cfg.enable_an_pages:
        content_html = link_an_refs(content_html, ctx, current_stem)
    if cfg.enable_hyp_refs:
        content_html = link_h_refs(content_html, ctx, current_stem)
    if cfg.enable_cite_refs:
        content_html = link_cite_refs(content_html, ctx, current_stem)
    if cfg.enable_anec_refs:
        content_html = link_anec_refs(content_html, ctx, current_stem)
    if cfg.enable_script_pages:
        content_html = link_script_refs(content_html, ctx)

    if cfg.enable_concept_refs:
        from .links_extra import link_concept_refs
        content_html = link_concept_refs(content_html, ctx)
    if cfg.enable_legal_refs:
        from .links_extra import link_legal_refs
        content_html = link_legal_refs(content_html, ctx)

    if placeholders:
        content_html = restore_math(content_html, placeholders)
    return content_html


def build_doc_page(ctx: BuildContext, rel_path: str, title: str) -> None:
    """Render a top-level docs/*.md to docs/<stem>.html."""
    cfg = ctx.config
    md_path = ctx.project_root / rel_path
    text = md_path.read_text(encoding="utf-8")
    stem = Path(rel_path).stem
    content_html = _render_content(ctx, text, stem, in_subdir=False)

    template = read_template(cfg, "doc.html")
    html = template.replace("<!-- INJECT_TITLE -->", title)
    html = html.replace("<!-- INJECT_CONTENT -->", content_html)
    html = inject_nav(html, ctx, prefix="../", active="docs")

    out = ctx.site_dir / "docs" / f"{stem}.html"
    out.write_text(html, encoding="utf-8")
    print(f"  docs/{stem}.html")


def build_docs_section(ctx: BuildContext) -> list[dict]:
    """Build all top-level doc pages from DOC_REGISTRY. Returns info dicts."""
    cfg = ctx.config
    (ctx.site_dir / "docs").mkdir(parents=True, exist_ok=True)
    docs_info: list[dict] = []
    for rel_path, title, description, category in cfg.doc_registry:
        md_path = ctx.project_root / rel_path
        if not md_path.exists():
            print(f"  docs/{Path(rel_path).stem}.html (skipped — file not found)")
            continue
        build_doc_page(ctx, rel_path, title)
        docs_info.append({
            "stem": Path(rel_path).stem,
            "title": title,
            "description": description,
            "category": category,
        })
    return docs_info


def build_doc_subdir(ctx: BuildContext, subdir: str) -> list[dict]:
    """Build pages from docs/<subdir>/*.md (and *.html for rich pages)."""
    cfg = ctx.config
    src_dir = ctx.project_root / "docs" / subdir
    if not src_dir.is_dir():
        return []
    out_dir = ctx.site_dir / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    info: list[dict] = []

    # Hand-built .html pages — rendered with the anecdote template if present,
    # otherwise the doc template. Each claims its stem and shadows the .md.
    html_stems: set[str] = set()
    rich_template_name = "anecdote.html" if subdir == "anecdotes" else "doc.html"
    for html_path in sorted(src_dir.glob("*.html")):
        stem = html_path.stem
        html_stems.add(stem)
        title = _fragment_title(html_path)
        try:
            template = read_template(cfg, rich_template_name)
        except FileNotFoundError:
            template = read_template(cfg, "doc.html")
        page = template.replace("<!-- INJECT_TITLE -->", title)
        page = page.replace("<!-- INJECT_CONTENT -->",
                            html_path.read_text(encoding="utf-8"))
        page = inject_nav(page, ctx, prefix="../", active="docs")
        (out_dir / f"{stem}.html").write_text(page, encoding="utf-8")
        print(f"  {subdir}/{stem}.html (rich)")
        info.append({"stem": stem, "title": title, "subdir": subdir})

    for md_path in sorted(src_dir.glob("*.md")):
        stem = md_path.stem
        if stem in html_stems:
            continue

        title = _brief_title(md_path)
        text = md_path.read_text(encoding="utf-8")
        meta, body = _split_frontmatter(text)
        content_html = _render_content(ctx, body, stem, in_subdir=True)

        if subdir == "findings" and stem == "index":
            tags = scan_finding_tags(ctx.project_root)
            content_html = inject_finding_tags(content_html, tags)
        if subdir == "literature" and stem == "index":
            content_html = inject_index_cite_anchors(content_html, ctx)

        body_class = ""
        if meta and subdir == "analyses":
            from .analyses import render_analysis_panel
            headline, panel = render_analysis_panel(meta, ctx)
            if cfg.enable_script_pages:
                panel = link_script_refs(panel, ctx)
            if cfg.enable_an_pages:
                panel = link_an_refs(panel, ctx, stem)
                headline = link_an_refs(headline, ctx, stem)
            content_html = headline + panel + content_html
            body_class = " no-toc"

        template = read_template(cfg, "doc.html")
        html = template.replace("<!-- INJECT_TITLE -->", title)
        html = html.replace("<!-- INJECT_CONTENT -->", content_html)
        html = html.replace("<!-- INJECT_BODY_CLASS -->", body_class)
        html = inject_nav(html, ctx, prefix="../", active="docs")

        (out_dir / f"{stem}.html").write_text(html, encoding="utf-8")
        print(f"  {subdir}/{stem}.html")
        info.append({"stem": stem, "title": title, "subdir": subdir})
    return info


def _fragment_title(html_path: Path) -> str:
    """Extract title from a <!-- title: ... --> comment in an HTML fragment."""
    import re
    text = html_path.read_text(encoding="utf-8")
    m = re.search(r"<!--\s*title:\s*(.+?)\s*-->", text)
    if m:
        return m.group(1)
    return html_path.stem.replace("_", " ").replace("-", " ").title()
