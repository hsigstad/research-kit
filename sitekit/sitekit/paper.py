"""Build paper.html and talk.html from make4ht output.

Lifted from connect/serasa with the make4ht filename and paths parameterized
through SiteConfig. Includes the inline-footnote helper (fixed regex from
the /site skill snippet).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path

from .context import BuildContext
from .nav import inject_nav
from .templates import read_template


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


def build_paper_page(ctx: BuildContext) -> bool:
    """Build paper/index.html from make4ht output. Returns True on success."""
    cfg = ctx.config
    make4ht_dir = ctx.project_root / cfg.paper_makeht_dir
    # paper_tex like "paper.tex" -> make4ht emits "paper.html" and "paper.css"
    base_stem = Path(cfg.paper_tex).stem
    html_path = make4ht_dir / f"{base_stem}.html"
    if not html_path.exists():
        print(f"  paper/ (skipped — {html_path.relative_to(ctx.project_root)} not found)")
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
    html = inject_nav(html, ctx, prefix="../", active="paper")

    paper_dir = ctx.site_dir / "paper"
    paper_dir.mkdir(parents=True, exist_ok=True)
    for img in list(make4ht_dir.glob("*.png")) + list(make4ht_dir.glob("*.svg")):
        shutil.copy2(img, paper_dir / img.name)
    # No PDF copy — staticrypt only encrypts HTML, so a shipped PDF would
    # leak by direct URL. The make4ht HTML render is the paper page.

    (paper_dir / "index.html").write_text(html, encoding="utf-8")
    img_count = len(list(paper_dir.glob("*.png"))) + len(list(paper_dir.glob("*.svg")))
    print(f"  paper/index.html ({img_count} images)")
    return True


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
