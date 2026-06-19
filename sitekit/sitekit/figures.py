"""Copy generated figures into the site and rewrite <img> srcs.

Markdown AN/findings/etc. pages reference figures by repo-relative
paths (`../../build/figure/X.png`, `../../build/analysis/Y/Z.png`) so
that the same paths work when reading the markdown on GitHub or locally.
For the static site, those paths point outside the build output and
would 404. We copy every generated PNG/SVG into `build/site/figures/`
(flat, deduped by basename) and rewrite any `<img src>` whose path
contains `build/figure/` or `build/analysis/` to `<prefix>figures/<basename>`.

The `prefix` argument is the same one sitekit's render pipeline
already threads for depth-aware relative links — `"../"` for depth-1
pages (docs/X.html, analyses/X.html) and `"../../"` for folder-mode
pages (docs/hypotheses/X.html).
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from .context import BuildContext


_IMG_SRC_RE = re.compile(r'(<img\b[^>]*\bsrc=")([^"]+)(")')
_FIG_SOURCE_DIRS = ("figure", "analysis")
_NATIVE_WEB_EXTS = ("*.png", "*.svg")
_PDF_GLOB = "*.pdf"


def _pdf_to_png(pdf: Path, png: Path) -> bool:
    """Render the first page of a PDF to PNG using pdftoppm. Returns
    True on success. Quietly returns False if pdftoppm is missing or
    the conversion fails — callers fall back to leaving the PDF alone."""
    if not shutil.which("pdftoppm"):
        return False
    try:
        # pdftoppm appends "-1" to the output basename; render to a tmp
        # prefix then rename so the final filename matches png.name.
        tmp_prefix = png.with_suffix("")
        subprocess.run(
            ["pdftoppm", "-png", "-r", "150", "-f", "1", "-l", "1",
             "-singlefile", str(pdf), str(tmp_prefix)],
            check=True, capture_output=True,
        )
        rendered = tmp_prefix.with_suffix(".png")
        if rendered != png and rendered.exists():
            rendered.rename(png)
        return png.exists()
    except (subprocess.CalledProcessError, OSError):
        if png.exists():
            png.unlink()
        return False


def copy_site_figures(ctx: BuildContext) -> tuple[int, int]:
    """Copy every generated PNG/SVG under build/figure and build/analysis
    into build/site/figures/. For any PDF figure that lacks a same-stem
    PNG sibling, render a PNG fallback into the site directory so the
    <img src> rewriter can resolve `<name>.pdf` references to a viewable
    raster. Returns (copied, derived).

    Walks recursively (multi-output scripts can write into a folder named
    after the script: `build/figure/X/a.png`). Basenames are assumed
    globally unique inside a project, which is the workspace convention.
    """
    figures_dir = ctx.site_dir / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    derived = 0
    seen_pdfs: list[Path] = []
    for base in _FIG_SOURCE_DIRS:
        src = ctx.project_root / "build" / base
        if not src.is_dir():
            continue
        for pattern in _NATIVE_WEB_EXTS:
            for img in src.rglob(pattern):
                shutil.copy2(img, figures_dir / img.name)
                copied += 1
        seen_pdfs.extend(src.rglob(_PDF_GLOB))

    for pdf in seen_pdfs:
        target_png = figures_dir / (pdf.stem + ".png")
        if target_png.exists():
            continue
        if _pdf_to_png(pdf, target_png):
            derived += 1
    return copied, derived


def rewrite_img_paths(html: str, prefix: str = "../") -> str:
    """Rewrite <img src> values that point into build/figure or build/analysis
    so they resolve to the copy in build/site/figures/.

    For `.pdf` references, always rewrite to `.png` — browsers can't
    render PDF in <img>, and the figure-copy step has either copied a
    native PNG sibling or derived one with pdftoppm. (If neither is
    available the rewritten src will 404, which is the same outcome
    as leaving the .pdf in place — but at least the failure is
    diagnosable as "missing PNG" rather than "browser can't render PDF".)

    Non-figure srcs (absolute URLs, data: URIs, anchors, anything outside
    the two source dirs) are left untouched.
    """
    def _repl(m: re.Match) -> str:
        src = m.group(2).replace("\\", "/")
        if src.startswith(("http://", "https://", "//", "data:")):
            return m.group(0)
        if "build/figure/" not in src and "build/analysis/" not in src:
            return m.group(0)
        name = Path(src).name
        if name.lower().endswith(".pdf"):
            name = name[:-4] + ".png"
        return f'{m.group(1)}{prefix}figures/{name}{m.group(3)}'
    return _IMG_SRC_RE.sub(_repl, html)
