"""build_site() — top-level orchestration.

Wires the BuildContext, builds doc pages + subdirs + paper/talk + archetype
sections + hooks + index. Returns an integer exit code.
"""

from __future__ import annotations

import shutil

from .config import SiteConfig
from .context import BuildContext
from .docs import build_docs_section, build_doc_subdir
from .paper import build_paper_page, build_talk_page
from .index_page import build_index
from .analyses import build_analyses_index
from .script_pages import build_script_pages
from .archetypes import get_archetype
from .links import (
    load_an_map, load_h_slugs, load_hyp_titles,
    load_cite_map, load_bib_authoryear, load_index_cite_map,
    load_anec_map, load_script_index,
)


def build_site(config: SiteConfig) -> int:
    """Build the site for one project. Returns an exit code."""
    if config.site_dir.exists():
        shutil.rmtree(config.site_dir)
    config.site_dir.mkdir(parents=True, exist_ok=True)

    ctx = BuildContext(config=config)
    _populate_context(ctx)

    print("Building documentation pages...")
    docs_info = build_docs_section(ctx)

    print("\nBuilding doc subdirectories...")
    subdir_info: list[dict] = []
    for subdir, _label, _color in config.doc_subdirs:
        subdir_info.extend(build_doc_subdir(ctx, subdir))

    n_analyses = 0
    if config.enable_an_pages:
        print("\nBuilding analyses index...")
        n_analyses = build_analyses_index(ctx)

    n_scripts = 0
    if config.enable_script_pages:
        print("\nBuilding script pages...")
        n_scripts = build_script_pages(ctx)

    print(f"\nArchetype: {config.archetype}")
    archetype_out = get_archetype(config.archetype)(ctx, docs_info, subdir_info)
    sources_info: list[dict] = []
    if isinstance(archetype_out, dict):
        sources_info = archetype_out.get("sources_info", []) or []
        for extra in archetype_out.get("extra_docs_info", []) or []:
            docs_info.append(extra)

    print("\nBuilding paper page...")
    has_paper = build_paper_page(ctx)

    print("\nBuilding talk page...")
    has_talk = build_talk_page(ctx)

    extra_cards: list[str] = []
    if isinstance(archetype_out, dict) and archetype_out.get("extra_cards"):
        extra_cards.append(archetype_out["extra_cards"])

    print("\nRunning project hooks...")
    for hook in config.hooks:
        result = hook(ctx)
        if isinstance(result, dict) and result.get("extra_cards"):
            extra_cards.append(result["extra_cards"])

    print("\nBuilding index page...")
    build_index(
        ctx,
        docs_info=docs_info,
        subdir_info=subdir_info,
        sources_info=sources_info,
        extra_doc_cards="\n".join(extra_cards),
        has_paper=has_paper,
        has_talk=has_talk,
    )

    robots = config.site_dir / "robots.txt"
    robots.write_text("User-agent: *\nDisallow: /\n", encoding="utf-8")

    summary_parts = [
        f"{len(docs_info)} doc",
        f"{len(subdir_info)} subdir",
    ]
    if n_analyses:
        summary_parts.append(f"{n_analyses} analyses-index")
    if n_scripts:
        summary_parts.append(f"{n_scripts} script")
    print(f"\nDone: {' + '.join(summary_parts)} pages in {config.site_dir_rel}/")
    return 0


def _populate_context(ctx: BuildContext) -> None:
    """Load reference maps the configured features will need."""
    cfg = ctx.config
    root = cfg.project_root

    if cfg.enable_an_pages:
        ctx.an_map = load_an_map(root)
    if cfg.enable_hyp_refs:
        ctx.h_slugs = load_h_slugs(root)
        ctx.hyp_titles = load_hyp_titles(root)
    if cfg.enable_cite_refs:
        # In flat mode there's no docs/literature/<key>.md tree, so the
        # per-page cite map stays empty; INDEX_CITE_MAP carries everything.
        if cfg.cite_refs_mode == "flat":
            ctx.cite_map = {}
        else:
            ctx.cite_map = load_cite_map(root)
        ctx.bib_authoryear = load_bib_authoryear(root)
        ctx.index_cite_map = load_index_cite_map(
            root, ctx.cite_map, ctx.bib_authoryear, mode=cfg.cite_refs_mode)
    if cfg.enable_anec_refs:
        ctx.anec_map = load_anec_map(root)

    # Sample titles: used by the analysis-panel renderer if the project has a
    # docs/sample/ subdir.
    sample_dir = root / "docs" / "sample"
    if sample_dir.is_dir():
        from .nav import _brief_title
        ctx.sample_titles = {
            p.stem: _brief_title(p)
            for p in sample_dir.glob("*.md")
            if p.stem != "index"
        }

    if cfg.enable_script_pages:
        ctx.script_map, ctx.script_refs = load_script_index(
            ctx, cfg.doc_subdirs, cfg.doc_registry)
