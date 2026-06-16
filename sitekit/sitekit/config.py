"""Per-project configuration for a sitekit build.

SiteConfig is the single object a project hands to build_site(). All
defaults assume the workspace conventions documented in research/rules/.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Literal, Optional

# (rel_path, title, description, category)
DocEntry = tuple[str, str, str, str]

# (subdir_name, nav_label, index_card_border_color)
SubdirEntry = tuple[str, str, str]

# (rel_path, href, label, description, priority, priority_class)
GuideBrief = tuple[str, str, str, str, str, str]

# Hook callable: receives BuildContext, returns whatever the hook produces
# (typically a list[dict] of items to surface on the index, or a bool).
# Forward-declared as Any here to avoid a circular import.
Hook = Callable[["object"], object]

Archetype = Literal["empirical", "theoretical", "mixed", "minimal"]


@dataclass
class SiteConfig:
    """Configuration for one project's site build.

    The minimal set of required fields is small; everything else has a
    sensible default and can be overridden per project.
    """

    # --- identity ---
    project_root: Path
    project_title: str
    paper_title: str = ""

    # --- archetype ---
    archetype: Archetype = "minimal"

    # --- inputs ---
    paper_tex: str = "paper.tex"     # filename under build/make4ht/
    talk_tex: str = "talk.tex"       # filename under build/make4ht_talk/
    paper_makeht_dir: str = "build/make4ht"
    talk_makeht_dir: str = "build/make4ht_talk"

    # --- doc structure ---
    doc_registry: list[DocEntry] = field(default_factory=list)
    doc_subdirs: list[SubdirEntry] = field(default_factory=list)
    index_only_subdirs: set[str] = field(default_factory=set)
    guide_briefs: list[GuideBrief] = field(default_factory=list)

    # Folder-mode subdirs: per-entry pages preserve their subfolder in the
    # output path. E.g. with folder_mode_subdirs=("hypotheses",), the file
    # docs/hypotheses/H1.md renders to build/site/docs/hypotheses/H1.html
    # rather than the default flat docs/H1.html. Subdirs NOT listed here
    # flatten (e.g. docs/briefs/foo.md → docs/foo.html when in the registry).
    folder_mode_subdirs: tuple[str, ...] = ()

    # Per-stem title / description overrides for doc subdirs. Keyed by the
    # markdown stem (e.g. "emerging-synthesis" -> ("Emerging Synthesis",
    # "Brief description")). When a subdir page's stem appears here, the
    # override wins over the fallback.
    subdir_doc_meta: dict[str, tuple[str, str]] = field(default_factory=dict)

    # Subdir-page title fallback when no subdir_doc_meta entry is present:
    #   "h1"   (default, connect/serasa style) — use the file's first H1.
    #   "stem" (fisc style) — use stem.replace("-", " ").title().
    subdir_title_fallback: str = "h1"

    # When True, the landing page renders an extra `<div class="doc-group">`
    # for each doc subdir (using the subdir's label from doc_subdirs).
    # Fisc-style empirical projects use this to surface findings/briefs/
    # notes/reference under "All Documentation". Connect-style projects
    # surface subdir content through other mechanisms (GUIDE_BRIEFS,
    # custom reference cards) and leave this False.
    index_subdir_groups: bool = False

    # Extra CSS appended to the nav's <style> block. Project-specific styles
    # (figure-source link badges, custom dropdown variants) that don't fit
    # anywhere else; included so projects can stay byte-equivalent against
    # their pre-extraction output without forking nav.py.
    extra_nav_css: str = ""

    # Full override of NAV_CSS. When set, replaces sitekit's bundled
    # nav CSS verbatim — used by projects (fisc) whose pre-extraction
    # CSS used hardcoded colors and want byte-equivalent diff before
    # converging to the design-system var(--…) palette.
    nav_css_override: str | None = None

    # Auto-discover .md files under docs/<subdir>/ for each folder_mode_subdirs
    # entry and append them to the registry at build time with category
    # f"{Subdir.capitalize()} (folder mode)". index.md is skipped because it's
    # typically already in the registry.
    folder_mode_auto_discover: bool = True

    # Extra href prefixes to strip in rewrite_md_links beyond the defaults
    # ("docs/", "../docs/"). For projects whose registry includes paths in
    # sibling subdirs (briefs/, notes/) that render flat into docs/.
    extra_strip_prefixes: tuple[str, ...] = ()

    # --- nav extras ---
    # Extra top-level nav links between brand and "Docs" dropdown. Tuples are
    # (label, href, active_key); active_key matches what hooks pass to
    # _inject_nav when rendering their pages.
    nav_extras: list[tuple[str, str, str]] = field(default_factory=list)

    # Additional dropdowns rendered alongside Docs. Each entry is
    # (label, active_key, items_fn) — appended AFTER Docs by default — or
    # (label, active_key, items_fn, position) where position is "before" |
    # "after" (the Docs dropdown). items_fn receives (ctx, prefix) and
    # returns a list of nav items. Each item is one of:
    #   (label, href)              → a plain link
    #   ("__group__", "Label")     → a group header
    #   ("__divider__", None)      → a divider line
    # An empty list suppresses the dropdown entirely.
    nav_dropdowns: list[tuple] = field(default_factory=list)

    # --- features (turn off if not needed) ---
    enable_an_pages: bool = True
    enable_cite_refs: bool = True
    enable_script_pages: bool = False
    enable_anec_refs: bool = True
    enable_hyp_refs: bool = True
    enable_concept_refs: bool = False
    enable_legal_refs: bool = False
    enable_math_protection: bool = False

    # Strip a leading <h1> from rendered doc-subdir pages (the template's
    # page-header already shows the title). Connect's default; fisc and
    # other projects whose subdir markdown doesn't start with H1 can
    # leave this on without effect, but projects that DO want the H1 in
    # the body (because of design conventions or hand-crafted markdown)
    # set False.
    strip_subdir_leading_h1: bool = True

    # Slugify behavior for heading ids:
    #   False (default, connect/serasa/poll-sponsor-bias style) — strip
    #     HTML tags, lowercase, collapse non-[a-z0-9] runs to hyphens.
    #     Accented chars become hyphens ("Sócios" → "s-cios").
    #   True (fisc style) — NFKD-normalize first to strip accents
    #     ("Sócios" → "socios"), and html-unescape entities before slugifying
    #     (so "&amp;" → "&" → dropped instead of "amp").
    slugify_unicode_normalize: bool = False

    # Cite-ref URL pattern.
    #   "connect" (default) — links to ../literature/<key>.html or
    #     ../literature/index.html#cite-<key>; expects literature as a doc
    #     subdir with per-key .md pages and an index.md.
    #   "flat" — links to literature.html#cite-<key>; expects a flat
    #     docs/literature.md with [cite:<key>] bullets.
    cite_refs_mode: str = "connect"

    # Paper-page extra substitutions. Callable returning a dict of
    # placeholder → replacement strings, applied to the paper template
    # after the standard inject (used by poll-sponsor-bias's MathJax
    # macro injection). Receives the BuildContext.
    paper_extra_substitutions: Callable | None = None

    # Optional override for the default rewrite_md_links. Signature:
    # `(html: str, ctx: BuildContext, *, in_subdir: bool, prefix: str) -> str`.
    # Receives the standard kwargs the default rewriter uses so projects
    # with a precomputed URL map (fisc-style) can swap in their own
    # algorithm without forking the rest of the pipeline. Default None
    # means "use sitekit.render.rewrite_md_links".
    link_rewriter: Callable | None = None

    # Extra content-postprocessing passes applied after the standard
    # rewrite_md_links + link_* refs pipeline. Each callable receives
    # `(html, ctx, current_stem, in_subdir)` and returns html. Used for
    # project-specific patterns (fisc's autolink_doc_refs, figure-source
    # badges, {{table:NAME}} directive expansion).
    content_postprocessors: list[Callable] = field(default_factory=list)

    # Strip <div class='author'> and <div class='thanks'> from the
    # make4ht paper body before rendering. Connect's pattern (default on)
    # because affiliation footnotes were considered sensitive on the
    # staticrypt-gated site; projects whose paper is publicly listed
    # already can set this False to keep the author block.
    paper_strip_author: bool = True

    # Reading-Guide placeholder messages for missing paper/talk. None
    # (default for talk) suppresses; default for paper is the workspace-
    # standard "Paper not yet built — run bash build.sh site …" message.
    talk_placeholder_msg: str | None = None
    paper_placeholder_msg: str = (
        "Paper not yet built &mdash; run <code>bash build.sh site</code> "
        "on a host with TeX."
    )

    # --- external resolvers ---
    brazil_institutions_url: str = "https://hsigstad.github.io/brazil-institutions/"

    # --- hooks ---
    # Called between core doc build and index build. Each hook receives the
    # BuildContext and may return a value the index layer can use (or None).
    hooks: list[Hook] = field(default_factory=list)

    # --- output ---
    site_dir_rel: str = "build/site"

    # --- archetype-specific (empirical) ---
    summary_cache_dir_rel: str = "source/summary/cache"
    # Python import path of the project's source/summary/config.py.
    # Default works for projects following the workspace convention.
    summary_config_module: str = "source.summary.config"
    # build/figure/ + build/table/ for descriptives & table page builders
    figure_build_dir_rel: str = "build/figure"
    table_build_dir_rel: str = "build/table"
    figure_source_dir_rel: str = "source/figure"
    table_source_dir_rel: str = "source/table"
    # Source-script page mode: "pygments" (default; syntax-highlighted via
    # the connect-style pages) OR "perline" (plain per-line `#L42` anchors,
    # poll-sponsor-bias / fisc-style).
    source_pages_mode: str = "pygments"
    # When True (default), build descriptives and tables pages alongside
    # the data section. Empirical-archetype projects use these.
    build_descriptives: bool = True
    build_tables: bool = True

    # --- archetype-specific (theoretical) ---
    cases_dir_rel: str = "cases"
    briefs_dir_rel: str = "briefs"
    extra_tex_pages: list[tuple[str, str]] = field(default_factory=list)
    # extra_tex_pages: list of (tex_filename, site_subdir) for projects with
    # multiple LaTeX outputs (e.g. bind's holdings.tex)

    @property
    def site_dir(self) -> Path:
        return self.project_root / self.site_dir_rel

    @property
    def template_search_dirs(self) -> list[Path]:
        """Project source/site/templates/ takes precedence, then the package's."""
        project_templates = (
            self.project_root / "source" / "site" / "templates"
        )
        pkg_templates = Path(__file__).parent / "templates"
        out = []
        if project_templates.is_dir():
            out.append(project_templates)
        out.append(pkg_templates)
        return out
