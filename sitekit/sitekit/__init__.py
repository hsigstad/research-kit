"""sitekit — shared static-site generator for research projects.

See README.md for usage. Public API:

- SiteConfig            : per-project configuration dataclass.
- BuildContext          : runtime state passed to hooks and link rewriters.
- build_site(config)    : main entry point.
"""

from .config import SiteConfig
from .context import BuildContext
from .build import build_site

__all__ = ["SiteConfig", "BuildContext", "build_site"]
