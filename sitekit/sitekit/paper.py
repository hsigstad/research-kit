"""Build paper.html and talk.html from make4ht output.

Lifted from connect/serasa with the make4ht filename and paths parameterized
through SiteConfig. Includes the inline-footnote helper (fixed regex from
the /site skill snippet).
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

from .context import BuildContext
from .nav import inject_nav
from .templates import read_template


def _resolve_external_figures(content: str, tex_source_dir: Path,
                               html_dir: Path) -> None:
    """Materialise external <img> references in `content` into `html_dir`.

    make4ht emits `<img src='X'>` where X is the path the LaTeX source
    used (e.g. `../build/figure/foo-.png` for `\\includegraphics{../
    build/figure/foo.pdf}`). Two issues this resolves:

    1. ImageMagick's default policy on Debian/Ubuntu blocks PDF
       rasterising, so make4ht's auto-convert step silently produces no
       PNG.
    2. Even if a PNG existed in build/figure/, it would be at the
       project's build/figure/ location — not under the site tree, so
       the deployed paper page would 404 on it.

    Strategy: parse every `<img src=...>` that points outside the
    make4ht output directory; resolve the source PDF relative to
    `tex_source_dir` (the directory paper.tex lives in — that's how
    LaTeX interprets the `\\includegraphics` paths); if a PDF exists,
    convert it with `pdftoppm` (not subject to ImageMagick's PDF
    policy); place the result at the same path relative to `html_dir`
    so the HTML reference resolves at deploy time.

    Two distinct relative-path interpretations apply to the same `src`:
      - LaTeX-side (find the source): relative to `tex_source_dir`.
      - Site-side (where to write): relative to `html_dir`, the
        directory the rendered HTML lives in (e.g. site_dir/paper/).
        Not the site root — that breaks the `..` resolution and writes
        outside the site tree.

    Idempotent — skips conversion if the destination PNG already exists.
    """
    import tempfile
    site_root = html_dir.parent
    seen: set[str] = set()
    for m in re.finditer(r"<img[^>]+src=['\"]([^'\"]+)['\"]", content,
                          flags=re.IGNORECASE):
        src = m.group(1)
        if src in seen:
            continue
        seen.add(src)
        if src.startswith(("http://", "https://", "data:", "#")):
            continue
        if "/" not in src:
            continue  # local make4ht_dir; already copied by caller
        expected_abs = (tex_source_dir / src).resolve()
        dest_abs = (html_dir / src).resolve()
        if not str(dest_abs).startswith(str(site_root)):
            # Defensive: refuse to write outside the site tree.
            continue
        if dest_abs.exists():
            continue
        if expected_abs.exists():
            dest_abs.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(expected_abs, dest_abs)
            continue
        # PNG missing — convert source PDF via pdftoppm.
        # make4ht's convention: foo.pdf -> foo-<page>.png. Single-page
        # PDFs commonly produce foo-.png (dash + empty page suffix).
        png_name = expected_abs.name
        if not png_name.endswith(".png"):
            continue
        stem = png_name[:-4]
        base = stem.rsplit("-", 1)[0] if "-" in stem else stem
        pdf = expected_abs.parent / f"{base}.pdf"
        if not (pdf.exists() and shutil.which("pdftoppm")):
            continue
        dest_abs.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix=".pdftoppm_") as workdir:
            subprocess.run(
                ["pdftoppm", "-png", "-r", "150", str(pdf),
                 os.path.join(workdir, base)],
                check=False, capture_output=True,
            )
            produced = sorted(Path(workdir).glob(f"{base}-*.png"))
            for p in produced:
                # If only one page produced and the make4ht-expected
                # name uses the empty-suffix convention (foo-.png),
                # rename pdftoppm's foo-1.png to match.
                target_name = p.name
                if len(produced) == 1 and png_name.endswith("-.png"):
                    target_name = png_name
                shutil.copy2(p, dest_abs.parent / target_name)


def inline_footnotes(content: str, make4ht_dir: Path, base_stem: str = "paper") -> str:
    """Rewrite cross-page footnote-mark links into inline tooltip spans.

    See research-kit/skills/site/snippets/inline_footnotes.py for the
    full rationale (make4ht splits the paper across multiple HTML files
    but we only ship the first one — links to fn-pages would otherwise
    404).
    """
    footnotes: dict[str, tuple[str, str]] = {}
    for fn_page in sorted(make4ht_dir.glob(f"{base_stem}[0-9]*.html")):
        fn_html = fn_page.read_text(encoding="utf-8")
        for m in re.finditer(
            r"<div class='footnote-text'>\s*.*?"
            r"<a id='(fn\d+x\d+)'>.*?<sup[^>]*>(\d+)</sup></a></span>"
            r"(.*?)</div>",
            fn_html, re.DOTALL,
        ):
            fn_id, fn_num, fn_body = m.group(1), m.group(2), m.group(3)
            clean = re.sub(r"<span class='ecrm-\d+'>(.*?)</span>", r"\1", fn_body).strip()
            footnotes[fn_id] = (fn_num, clean)

    if not footnotes:
        return content

    def _replace_fn(m: re.Match) -> str:
        href = m.group(1)
        sup = m.group(2)
        fn_id = href.split("#")[-1] if "#" in href else ""
        if fn_id in footnotes:
            _num, body = footnotes[fn_id]
            return (
                f'<span class="fn-inline" tabindex="0">'
                f'<sup class="textsuperscript">{sup}</sup>'
                f'<span class="fn-tooltip">{body}</span>'
                f'</span>'
            )
        return m.group(0)

    return re.sub(
        r"""<span class=['"]footnote-mark['"]><a\s*\n?href=['"]([^'"]+)['"]><sup class=['"]textsuperscript['"]>(\d+)</sup></a></span>""",
        _replace_fn, content,
    )


def _extract_body(raw_html: str) -> str:
    """Pull the <body>...</body> content out of a make4ht HTML file."""
    body_start = raw_html.find("<body")
    body_start = raw_html.find(">", body_start) + 1
    body_end = raw_html.find("</body>")
    return raw_html[body_start:body_end].strip()


def _render_paper_html(
    ctx: BuildContext,
    tex_filename: str,
    makeht_dir_rel: str,
    out_dir: Path,
    prefix: str,
) -> bool:
    """Render one paper into out_dir/index.html. Returns True on success.

    Shared between single-paper and multi-paper builds. `prefix` is the
    relative path from the rendered HTML back to the site root (e.g.
    "../" for /paper/index.html, "../../" for /paper/<key>/index.html).
    """
    cfg = ctx.config
    make4ht_dir = ctx.project_root / makeht_dir_rel
    base_stem = Path(tex_filename).stem
    html_path = make4ht_dir / f"{base_stem}.html"
    if not html_path.exists():
        print(f"  {out_dir.relative_to(ctx.site_dir)}/ "
              f"(skipped — {html_path.relative_to(ctx.project_root)} not found)")
        return False

    raw_html = html_path.read_text(encoding="utf-8")
    content = _extract_body(raw_html)

    if cfg.paper_strip_author:
        # Strip author names and affiliation footnotes — historically a
        # privacy default for staticrypt-gated sites where the LaTeX
        # \thanks line shouldn't ship in the rendered HTML.
        content = re.sub(r"<div class='author'>.*?</div>", "", content, flags=re.DOTALL)
        content = re.sub(r"<div class='thanks'>.*?</div>", "", content, flags=re.DOTALL)

    content = inline_footnotes(content, make4ht_dir, base_stem)

    if cfg.paper_content_transform is not None:
        content = cfg.paper_content_transform(ctx, content)

    css_path = make4ht_dir / f"{base_stem}.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    template = read_template(cfg, "paper.html")
    html = template.replace("<!-- INJECT_PAPER_CSS -->", css)
    html = html.replace("<!-- INJECT_CONTENT -->", content)
    if cfg.paper_extra_substitutions is not None:
        for placeholder, value in cfg.paper_extra_substitutions(ctx).items():
            html = html.replace(placeholder, value)
    html = inject_nav(html, ctx, prefix=prefix, active="paper")

    out_dir.mkdir(parents=True, exist_ok=True)
    for img in list(make4ht_dir.glob("*.png")) + list(make4ht_dir.glob("*.svg")):
        shutil.copy2(img, out_dir / img.name)
    # External figures (\\includegraphics{../build/figure/...}) — make4ht
    # emits relative <img src> paths assuming PDFs were rasterised, but
    # ImageMagick's PDF policy may have blocked that. Resolve via
    # pdftoppm and mirror to the site tree so the paths still work.
    # tex_source_dir = ctx.project_root / "paper" (the standard project
    # convention — paper.tex's directory; LaTeX interprets ../build/
    # figure/... relative to that).
    _resolve_external_figures(
        content, ctx.project_root / "paper", out_dir
    )
    # No PDF copy — staticrypt only encrypts HTML, so a shipped PDF would
    # leak by direct URL. The make4ht HTML render is the paper page.

    (out_dir / "index.html").write_text(html, encoding="utf-8")
    img_count = len(list(out_dir.glob("*.png"))) + len(list(out_dir.glob("*.svg")))
    print(f"  {out_dir.relative_to(ctx.site_dir)}/index.html ({img_count} images)")
    return True


def build_paper_page(ctx: BuildContext) -> bool:
    """Build paper/index.html from make4ht output. Returns True on success.

    Single-paper mode (cfg.papers empty). For multi-paper projects, use
    build_papers_section instead.
    """
    cfg = ctx.config
    return _render_paper_html(
        ctx,
        tex_filename=cfg.paper_tex,
        makeht_dir_rel=cfg.paper_makeht_dir,
        out_dir=ctx.site_dir / "paper",
        prefix="../",
    )


def build_papers_section(ctx: BuildContext) -> dict[str, bool]:
    """Build /paper/<key>/index.html for each cfg.papers entry, plus a
    /paper/index.html landing page listing all entries.

    Returns {key: built_ok} per entry. The landing page is always written
    when cfg.papers is non-empty, regardless of per-paper build success.
    """
    cfg = ctx.config
    results: dict[str, bool] = {}
    for key, _label, tex_filename, makeht_dir_rel, _title in cfg.papers:
        results[key] = _render_paper_html(
            ctx,
            tex_filename=tex_filename,
            makeht_dir_rel=makeht_dir_rel,
            out_dir=ctx.site_dir / "paper" / key,
            prefix="../../",
        )
    _build_papers_index(ctx, results)
    return results


def _build_papers_index(ctx: BuildContext, results: dict[str, bool]) -> None:
    """Write the /paper/index.html listing page for multi-paper projects."""
    cfg = ctx.config
    cards: list[str] = []
    for key, label, _tex, _makeht, title in cfg.papers:
        built = results.get(key, False)
        title_html = title or label
        if built:
            cards.append(
                f'<a class="paper-card" href="{key}/index.html">'
                f'<div class="paper-card-label">{label}</div>'
                f'<div class="paper-card-title">{title_html}</div>'
                f'<span class="paper-card-cta">Read paper &rarr;</span></a>'
            )
        else:
            cards.append(
                f'<div class="paper-card paper-card-placeholder">'
                f'<div class="paper-card-label">{label}</div>'
                f'<div class="paper-card-title">{title_html}</div>'
                f'<div class="paper-card-msg">{cfg.paper_placeholder_msg}</div></div>'
            )
    template = read_template(cfg, "paper_list.html")
    html = template.replace("<!-- INJECT_PAPER_CARDS -->", "\n".join(cards))
    html = inject_nav(html, ctx, prefix="../", active="paper")
    out_dir = ctx.site_dir / "paper"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"  paper/index.html ({len(cards)} papers listed)")


def build_talk_page(ctx: BuildContext) -> bool:
    """Build talk/index.html from make4ht output. Returns True on success."""
    cfg = ctx.config
    make4ht_dir = ctx.project_root / cfg.talk_makeht_dir
    base_stem = Path(cfg.talk_tex).stem
    html_path = make4ht_dir / f"{base_stem}.html"
    if not html_path.exists():
        print(f"  talk/ (skipped — {html_path.relative_to(ctx.project_root)} not found)")
        return False

    raw_html = html_path.read_text(encoding="utf-8")
    content = _extract_body(raw_html)

    css_path = make4ht_dir / f"{base_stem}.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    template = read_template(cfg, "talk.html")
    html = template.replace("<!-- INJECT_TALK_CSS -->", css)
    html = html.replace("<!-- INJECT_CONTENT -->", content)
    html = inject_nav(html, ctx, prefix="../", active="talk")

    talk_dir = ctx.site_dir / "talk"
    talk_dir.mkdir(parents=True, exist_ok=True)
    for img in list(make4ht_dir.glob("*.png")) + list(make4ht_dir.glob("*.svg")):
        shutil.copy2(img, talk_dir / img.name)

    (talk_dir / "index.html").write_text(html, encoding="utf-8")
    img_count = len(list(talk_dir.glob("*.png"))) + len(list(talk_dir.glob("*.svg")))
    print(f"  talk/index.html ({img_count} images)")
    return True
