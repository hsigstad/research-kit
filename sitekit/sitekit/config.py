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

    # Additional dropdowns rendered after the Docs dropdown. Each entry is
    # (label, active_key, items_fn). items_fn receives the BuildContext and
    # returns a list of nav items. Each item is one of:
    #   (label, href)              → a plain link
    #   ("__group__", "Label")     → a group header
    #   ("__divider__", None)      → a divider line
    # An empty list suppresses the dropdown entirely.
    nav_dropdowns: list[tuple[str, str, Callable]] = field(default_factory=list)

    # --- features (turn off if not needed) ---
    enable_an_pages: bool = True
    enable_cite_refs: bool = True
    enable_script_pages: bool = False
    enable_anec_refs: bool = True
    enable_hyp_refs: bool = True
    enable_concept_refs: bool = False
    enable_legal_refs: bool = False
    enable_math_protection: bool = False

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

    # Strip <div class='author'> and <div class='thanks'> from the
    # make4ht paper body before rendering. Connect's pattern (default on)
    # because affiliation footnotes were considered sensitive on the
    # staticrypt-gated site; projects whose paper is publicly listed
    # already can set this False to keep the author block.
    paper_strip_author: bool = True

    # Reading-Guide placeholder message when has_talk is False. None
    # (default) suppresses the placeholder entirely; a string emits a
    # `<div class="guide-card placeholder">` with that HTML message.
    talk_placeholder_msg: str | None = None

    # --- external resolvers ---
    brazil_institutions_url: str = "https://hsigstad.github.io/brazil-institutions/"

    # --- hooks ---
    # Called between core doc build and index build. Each hook receives the
    # BuildContext and may return a value the index layer can use (or None).
    hooks: list[Hook] = field(default_factory=list)

    # --- output ---
    site_dir_rel: str = "build/site"

    # --- archetype-specific (empirical) ---
    summary_cache_dir_rel: str = "build/summary"

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
