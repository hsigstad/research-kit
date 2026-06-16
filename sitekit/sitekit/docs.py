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
from .paths import output_path
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
    prefix: str = "../",
) -> str:
    """Run text through the render + link-rewrite pipeline."""
    cfg = ctx.config

    if cfg.enable_math_protection:
        text, placeholders = protect_math(text)
    else:
        placeholders = {}

    content_html = md_to_html(text)
    if in_subdir and cfg.strip_subdir_leading_h1:
        content_html = strip_leading_h1(content_html)
    content_html = add_heading_ids(
        content_html, unicode_normalize=cfg.slugify_unicode_normalize)
    if cfg.link_rewriter is not None:
        content_html = cfg.link_rewriter(
            content_html, ctx, in_subdir=in_subdir, prefix=prefix)
    else:
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

    for postprocess in cfg.content_postprocessors:
        content_html = postprocess(content_html, ctx, current_stem, in_subdir)

    if placeholders:
        content_html = restore_math(content_html, placeholders)
    return content_html


def build_doc_page(ctx: BuildContext, rel_path: str, title: str) -> None:
    """Render a docs/*.md to its output location.

    Standard top-level docs go to docs/<stem>.html. Folder-mode subdirs
    preserve their subfolder (docs/hypotheses/H1.md → docs/hypotheses/H1.html).
    """
    cfg = ctx.config
    md_path = ctx.project_root / rel_path
    text = md_path.read_text(encoding="utf-8")
    stem = Path(rel_path).stem
    out, display, is_folder_mode = output_path(ctx, rel_path)
    content_html = _render_content(ctx, text, stem, in_subdir=False)

    if cfg.cite_refs_mode == "flat" and stem == "literature":
        from .links import inject_index_cite_anchors
        content_html = inject_index_cite_anchors(content_html, ctx)

    nav_prefix = "../../" if is_folder_mode else "../"
    template = read_template(cfg, "doc.html")
    html = template.replace("<!-- INJECT_TITLE -->", title)
    html = html.replace("<!-- INJECT_CONTENT -->", content_html)
    html = inject_nav(html, ctx, prefix=nav_prefix, active="docs")

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"  {display}")


def _discover_folder_mode_entries(ctx: BuildContext) -> list[tuple[str, str, str, str]]:
    """Auto-discover .md files under docs/<subdir>/ for folder-mode subdirs.

    Returns DOC_REGISTRY-shaped tuples. Skips index.md (typically already
    in the registry).
    """
    cfg = ctx.config
    if not cfg.folder_mode_auto_discover:
        return []
    discovered: list[tuple[str, str, str, str]] = []
    for subdir in cfg.folder_mode_subdirs:
        folder = ctx.project_root / "docs" / subdir
        if not folder.is_dir():
            continue
        for md in sorted(folder.glob("*.md")):
            if md.stem == "index":
                continue
            title = md.stem
            for line in md.read_text(encoding="utf-8").splitlines():
                if line.startswith("# "):
                    title = line[2:].strip()
                    break
            rel = str(md.relative_to(ctx.project_root))
            cat = f"{subdir.capitalize()} (folder mode)"
            discovered.append((rel, title, "", cat))
    return discovered


def build_docs_section(ctx: BuildContext) -> list[dict]:
    """Build all doc pages from DOC_REGISTRY plus auto-discovered folder-mode entries."""
    cfg = ctx.config
    (ctx.site_dir / "docs").mkdir(parents=True, exist_ok=True)
    docs_info: list[dict] = []
    all_entries = list(cfg.doc_registry) + _discover_folder_mode_entries(ctx)
    for rel_path, title, description, category in all_entries:
        md_path = ctx.project_root / rel_path
        if not md_path.exists():
            print(f"  {rel_path} (skipped — file not found)")
            continue
        build_doc_page(ctx, rel_path, title)
        _, display, _ = output_path(ctx, rel_path)
        stem_for_index = display.removeprefix("docs/").removesuffix(".html")
        docs_info.append({
            "stem": stem_for_index,
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

        meta_override = cfg.subdir_doc_meta.get(stem)
        if meta_override is not None:
            title = meta_override[0]
        elif cfg.subdir_title_fallback == "stem":
            title = stem.replace("-", " ").title()
        else:
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
