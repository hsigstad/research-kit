"""Theoretical archetype: case-extraction pages, a grouped cases index, and
extra standalone LaTeX pages (e.g. an enriched-holdings companion doc).

Ported from bind/source/site/build_all.py. Activated by
SiteConfig.archetype == "theoretical". The archetype owns:

- build/site/cases/<stem>.html — one page per cases/extractions/*.md,
  rendered through the standard doc pipeline (so cite/AN/anec refs work).
- build/site/cases/index.html — cases grouped by area + topic, via the
  project's cases_index_template (kept project-local; no canonical default).
- build/site/<out_subdir>/index.html — each SiteConfig.extra_tex_pages entry
  (make4ht → canonical paper template). Skipped gracefully without TeX.
- An "extra_cards" cases section injected above the index doc grid.

Everything else a theoretical project needs (docs, briefs/notes subdirs,
paper page, citations) uses stock sitekit mechanisms / project hooks; only
the case-extraction machinery is archetype-specific because bind is the sole
theoretical project.

Project-specific touches (e.g. bind's SCOTUS citation-extraction pages) stay
as hooks on SiteConfig.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ..context import BuildContext
from ..docs import _render_content
from ..nav import inject_nav
from ..templates import read_template


# ---------------------------------------------------------------------------
# Case discovery
# ---------------------------------------------------------------------------

def _extract_case_title(md_path: Path) -> str:
    """First H1 in the case markdown, else a titleized stem."""
    for line in md_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return md_path.stem.replace("_", " ").title()


def _short_name(full_title: str) -> str:
    """Strip a trailing US-reports citation: 'Brown…, 347 U.S. 483 (1954)' → 'Brown…'."""
    m = re.match(r"^(.+?),\s+\d+\s+U\.?S\.?", full_title)
    return m.group(1) if m else full_title


def _year_from_stem(stem: str) -> str:
    m = re.search(r"(\d{4})$", stem)
    return m.group(1) if m else ""


def _discover_cases(ctx: BuildContext) -> list[dict]:
    """Discover cases/extractions/*.md, sorted by (area, year)."""
    cfg = ctx.config
    src = ctx.project_root / cfg.cases_extractions_rel
    if not src.is_dir():
        return []
    default_area = next(iter(cfg.cases_area_labels), "")
    cases: list[dict] = []
    for md_path in sorted(src.glob("*.md")):
        stem = md_path.stem
        full_title = _extract_case_title(md_path)
        cases.append({
            "stem": stem,
            "area": cfg.cases_area_map.get(stem, default_area),
            "full_title": full_title,
            "short_name": _short_name(full_title),
            "year": _year_from_stem(stem),
        })
    cases.sort(key=lambda c: (c["area"], c["year"]))
    return cases


def cases_nav_items(ctx: BuildContext, prefix: str) -> list:
    """nav_dropdowns items_fn: cases grouped by area label.

    Returns [] when there are no cases (suppresses the dropdown).
    """
    cfg = ctx.config
    cases = _discover_cases(ctx)
    if not cases:
        return []
    items: list = []
    for area_code, label in cfg.cases_area_labels.items():
        area_cases = [c for c in cases if c["area"] == area_code]
        if not area_cases:
            continue
        items.append(("__group__", label))
        for c in area_cases:
            items.append((c["short_name"], f'{prefix}cases/{c["stem"]}.html'))
    return items


# ---------------------------------------------------------------------------
# Page builders
# ---------------------------------------------------------------------------

def _build_case_page(ctx: BuildContext, case: dict) -> None:
    """Render one case extraction through the standard doc pipeline."""
    cfg = ctx.config
    md_path = ctx.project_root / cfg.cases_extractions_rel / f'{case["stem"]}.md'
    text = md_path.read_text(encoding="utf-8")
    content_html = _render_content(
        ctx, text, case["stem"], in_subdir=False, prefix="../")

    template = read_template(cfg, "doc.html")
    html = template.replace("<!-- INJECT_TITLE -->", case["short_name"])
    html = html.replace("<!-- INJECT_CONTENT -->", content_html)
    html = inject_nav(html, ctx, prefix="../", active="cases")

    out = ctx.site_dir / "cases" / f'{case["stem"]}.html'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"  cases/{case['stem']}.html")


def _build_cases_index(ctx: BuildContext, cases: list[dict]) -> None:
    """Build cases/index.html grouped by area then topic."""
    cfg = ctx.config
    template = read_template(cfg, cfg.cases_index_template)
    by_stem = {c["stem"]: c for c in cases}

    parts: list[str] = []
    for area_code, area_label in cfg.cases_area_labels.items():
        topics = cfg.cases_topic_map.get(area_code, [])
        if not topics:
            continue
        parts.append(f'<h2 class="area-heading">{area_label}</h2>')
        for topic_name, stems in topics:
            topic_cases = [by_stem[s] for s in stems if s in by_stem]
            topic_cases.sort(key=lambda c: c["year"])
            if not topic_cases:
                continue
            parts.append(f'<h3 class="topic-label">{topic_name}</h3>')
            cards = [
                f'<a class="case-card" href="{c["stem"]}.html">'
                f'<span class="case-name">{c["short_name"]}</span>'
                f'<span class="case-year">{c["year"]}</span></a>'
                for c in topic_cases
            ]
            parts.append(f'<div class="case-grid">{chr(10).join(cards)}</div>')

    html = template.replace("<!-- INJECT_CASES_BY_TOPIC -->", "\n".join(parts))
    html = html.replace("<!-- INJECT_CASE_COUNT -->", str(len(cases)))
    html = inject_nav(html, ctx, prefix="../", active="cases")

    out = ctx.site_dir / "cases" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"  cases/index.html ({len(cases)} cases)")


def _extract_body(raw_html: str) -> str:
    body_start = raw_html.find("<body")
    body_start = raw_html.find(">", body_start) + 1
    body_end = raw_html.find("</body>")
    return raw_html[body_start:body_end].strip()


def _build_extra_tex_page(
    ctx: BuildContext, tex_file: str, out_subdir: str, nav_active: str,
    title: str, subtitle: str,
) -> bool:
    """make4ht a standalone .tex → build/site/<out_subdir>/index.html.

    Skipped gracefully when TeX/make4ht is unavailable or the source is
    absent (the page then builds on a TeX-capable host).
    """
    cfg = ctx.config
    paper_dir = ctx.project_root / "paper"
    tex_path = paper_dir / tex_file
    if not tex_path.exists():
        print(f"  {out_subdir}/ (skipped — paper/{tex_file} not found)")
        return False

    stem = Path(tex_file).stem
    build_dir = ctx.project_root / "build" / f"make4ht-{stem}"
    html_path = build_dir / f"{stem}.html"

    if not html_path.exists():
        build_dir.mkdir(parents=True, exist_ok=True)
        try:
            result = subprocess.run(
                ["make4ht", "-d", str(build_dir), tex_file, "html5,mathjax"],
                cwd=str(paper_dir), capture_output=True, text=True, timeout=180,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            print(f"  {out_subdir}/ (skipped — make4ht unavailable)")
            return False
        if result.returncode != 0 or not html_path.exists():
            print(f"  {out_subdir}/ (skipped — make4ht failed for {tex_file})")
            return False

    content = _extract_body(html_path.read_text(encoding="utf-8"))
    css_path = build_dir / f"{stem}.css"
    css = css_path.read_text(encoding="utf-8") if css_path.exists() else ""

    template = read_template(cfg, "paper.html")
    html = template.replace("<!-- INJECT_PAPER_CSS -->", css)
    html = html.replace("<!-- INJECT_CONTENT -->", content)
    html = html.replace("<!-- INJECT_TITLE -->", title)
    html = html.replace("<!-- INJECT_SUBTITLE -->", subtitle)
    html = inject_nav(html, ctx, prefix="../", active=nav_active)

    out_dir = ctx.site_dir / out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    for img in list(build_dir.glob("*.png")) + list(build_dir.glob("*.svg")):
        shutil.copy2(img, out_dir / img.name)
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    print(f"  {out_subdir}/index.html")
    return True


def _cases_index_card(cases: list[dict]) -> str:
    """A 'Cases' section injected above the index doc grid."""
    if not cases:
        return ""
    return (
        '<h2>Cases</h2>\n'
        '<div class="doc-groups"><div class="doc-group">'
        f'<h3>Case extractions</h3><ul class="link-list">'
        f'<li><a href="cases/index.html">Browse all {len(cases)} cases '
        '&rarr;</a></li></ul></div></div>'
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_theoretical(
    ctx: BuildContext,
    docs_info: list[dict],
    subdir_info: list[dict],
) -> dict:
    """Build cases + extra tex pages; return index extras."""
    cases = _discover_cases(ctx)
    if cases:
        print("\nBuilding cases...")
        for case in cases:
            _build_case_page(ctx, case)
        _build_cases_index(ctx, cases)

    if ctx.config.extra_tex_pages:
        print("\nBuilding extra TeX pages...")
        for entry in ctx.config.extra_tex_pages:
            tex_file, out_subdir, nav_active, title, subtitle = entry
            _build_extra_tex_page(
                ctx, tex_file, out_subdir, nav_active, title, subtitle)

    return {"extra_cards": _cases_index_card(cases)}
