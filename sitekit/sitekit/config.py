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

    # --- nav extras ---
    # Extra top-level nav links between brand and "Docs" dropdown. Tuples are
    # (label, href, active_key); active_key matches what hooks pass to
    # _inject_nav when rendering their pages.
    nav_extras: list[tuple[str, str, str]] = field(default_factory=list)

    # --- features (turn off if not needed) ---
    enable_an_pages: bool = True
    enable_cite_refs: bool = True
    enable_script_pages: bool = False
    enable_anec_refs: bool = True
    enable_hyp_refs: bool = True
    enable_concept_refs: bool = False
    enable_legal_refs: bool = False
    enable_math_protection: bool = False

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
