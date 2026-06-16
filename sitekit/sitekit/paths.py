"""Output-path resolution for doc pages.

Lives in its own module to avoid circular imports between nav.py (which
needs to know href display strings) and docs.py (which writes to the
absolute output path).
"""

from __future__ import annotations

from pathlib import Path

from .context import BuildContext


def output_path(ctx: BuildContext, rel_path: str) -> tuple[Path, str, bool]:
    """Map docs/.../X.md → (absolute build path, display string, is_folder_mode).

    Folder-mode subdirs (declared in SiteConfig.folder_mode_subdirs)
    preserve their subfolder: docs/hypotheses/H1.md →
    build/site/docs/hypotheses/H1.html. Everything else flattens to
    docs/<stem>.html.
    """
    cfg = ctx.config
    parts = Path(rel_path).parts
    folder_mode = set(cfg.folder_mode_subdirs)
    if len(parts) >= 3 and parts[1] in folder_mode:
        subdir = parts[1]
        stem = Path(parts[-1]).stem
        out = ctx.site_dir / "docs" / subdir / f"{stem}.html"
        display = f"docs/{subdir}/{stem}.html"
        return out, display, True
    stem = Path(rel_path).stem
    out = ctx.site_dir / "docs" / f"{stem}.html"
    display = f"docs/{stem}.html"
    return out, display, False
