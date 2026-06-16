"""Template resolution: project source/site/templates/ overrides sitekit/templates/."""

from __future__ import annotations

from pathlib import Path

from .config import SiteConfig


class TemplateNotFoundError(FileNotFoundError):
    pass


def find_template(cfg: SiteConfig, name: str) -> Path:
    """Locate a template by name across the project then the package.

    Raises TemplateNotFoundError if neither location has it.
    """
    for d in cfg.template_search_dirs:
        candidate = d / name
        if candidate.is_file():
            return candidate
    raise TemplateNotFoundError(
        f"template {name!r} not found in any of: "
        + ", ".join(str(d) for d in cfg.template_search_dirs)
    )


def read_template(cfg: SiteConfig, name: str) -> str:
    """Read a template's text, project-first then package fallback."""
    return find_template(cfg, name).read_text(encoding="utf-8")
