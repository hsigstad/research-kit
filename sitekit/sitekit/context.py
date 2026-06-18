"""BuildContext threads runtime state through the build.

Replaces connect/fisc/bind/serasa's pattern of module-level dicts (AN_MAP,
CITE_MAP, etc.) loaded at import time. The context is created once per
build_site() call and passed to render helpers + hooks.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import SiteConfig


@dataclass
class BuildContext:
    """Resolved config + lazily-computed reference maps."""

    config: SiteConfig

    # Reference maps (populated by sitekit.links.* loaders the first time
    # they're needed).
    an_map: dict[str, str] = field(default_factory=dict)
    an_by_hypothesis: dict[str, list[dict]] = field(default_factory=dict)
    an_index: dict[str, dict] = field(default_factory=dict)
    h_slugs: set[str] = field(default_factory=set)
    cite_map: dict[str, str] = field(default_factory=dict)
    bib_authoryear: dict[str, str] = field(default_factory=dict)
    index_cite_map: dict[str, str] = field(default_factory=dict)
    anec_map: dict[str, str] = field(default_factory=dict)
    hyp_titles: dict[str, str] = field(default_factory=dict)
    sample_titles: dict[str, str] = field(default_factory=dict)
    finding_tags: dict[str, str] = field(default_factory=dict)
    script_map: dict[str, str] = field(default_factory=dict)
    script_refs: dict[str, list[tuple[str, str]]] = field(default_factory=dict)
    concepts: dict[str, dict] = field(default_factory=dict)

    # Optional injected resolvers (for legal cites — see links.legal).
    legal_resolver: Optional[object] = None
    legal_cache: dict[str, str] = field(default_factory=dict)

    @property
    def project_root(self) -> Path:
        return self.config.project_root

    @property
    def site_dir(self) -> Path:
        return self.config.site_dir
