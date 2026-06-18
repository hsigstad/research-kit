"""Auto-link helpers: rewrite tokens like AN-NNN, [cite:key], H:slug, [anec:slug]."""

from .an import (
    link_an_refs,
    load_an_map,
    load_an_by_hypothesis,
    render_supporting_analyses_section,
    scan_finding_tags,
    inject_finding_tags,
)
from .cite import (
    link_cite_refs,
    load_cite_map,
    load_bib_authoryear,
    load_index_cite_map,
    inject_index_cite_anchors,
)
from .hyp import link_h_refs, load_h_slugs, load_hyp_titles
from .anec import link_anec_refs, load_anec_map
from .script import link_script_refs, load_script_index, highlight_source, CODE_CSS

__all__ = [
    "link_an_refs", "load_an_map", "load_an_by_hypothesis",
    "render_supporting_analyses_section",
    "scan_finding_tags", "inject_finding_tags",
    "link_cite_refs", "load_cite_map", "load_bib_authoryear",
    "load_index_cite_map", "inject_index_cite_anchors",
    "link_h_refs", "load_h_slugs", "load_hyp_titles",
    "link_anec_refs", "load_anec_map",
    "link_script_refs", "load_script_index", "highlight_source", "CODE_CSS",
]
