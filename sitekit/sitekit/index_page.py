"""Landing page (index.html) builder.

Supports two layouts via two placeholders that an index template may use:

- `<!-- INJECT_GUIDE_CARDS -->` — Reading Guide cards model (connect, fisc,
  bind, the canonical /site SKILL.md design). Used when SiteConfig.guide_briefs
  is populated.
- `<!-- INJECT_PAPER_CARD --> / <!-- INJECT_TALK_CARD -->` — legacy
  Paper+Talk hero card model (serasa). Used when the template contains
  those placeholders.

A template can use either or both. The builder also handles the always-on
`<!-- INJECT_DOC_CARDS -->` placeholder (groups of documentation links).

This dual support lets projects migrate to sitekit without redesigning their
index in the same step.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .context import BuildContext
from .nav import inject_nav
from .templates import read_template


def _guide_card(href: str, label: str, desc: str, priority: str, priority_class: str) -> str:
    return (
        f'<a class="guide-card" href="{href}">'
        f'<div class="priority {priority_class}">{priority}</div>'
        f'<div class="label">{label}</div>'
        f'<div class="desc">{desc}</div>'
        '</a>'
    )


def _guide_placeholder(label: str, msg: str) -> str:
    return (
        '<div class="guide-card placeholder">'
        f'<div class="label">{label}</div>'
        f'<div class="desc">{msg}</div>'
        '</div>'
    )


def _hero_card(kind: str, paper_title: str, href: str | None) -> str:
    if href is None:
        return (
            '<div class="hero-card" style="border-left-color:#adb5bd">'
            f'<div class="hero-sub">{kind} not available '
            '&mdash; run <code>bash build.sh site</code>.</div></div>'
        )
    if kind == "Paper":
        return (
            f'<a class="hero-card" href="{href}">'
            '<div class="hero-title">Paper</div>'
            f'<div class="hero-sub">{paper_title}</div>'
            '<span class="hero-cta">Read paper &rarr;</span></a>'
        )
    return (
        f'<a class="hero-card" href="{href}">'
        f'<div class="hero-title">{kind}</div>'
        '<div class="hero-sub">Presentation slides (beamer)</div>'
        f'<span class="hero-cta">View slides &rarr;</span></a>'
    )


def build_index(
    ctx: BuildContext,
    docs_info: list[dict],
    subdir_info: list[dict] | None = None,
    extra_doc_cards: str = "",
    has_paper: bool = False,
    has_talk: bool = False,
) -> None:
    """Build the landing page.

    `extra_doc_cards` is raw HTML inserted ABOVE the standard doc-group grid;
    project hooks (serasa's specs+results row) use this slot to add their own
    sections to the index without forking the index template.
    """
    cfg = ctx.config
    subdir_info = subdir_info or []
    template = read_template(cfg, "index.html")
    html = template

    if "<!-- INJECT_GUIDE_CARDS -->" in template:
        guide_cards: list[str] = []
        if has_paper:
            guide_cards.append(_guide_card(
                "paper/index.html", "Paper",
                cfg.paper_title or "Paper",
                "Start here", "priority-start",
            ))
        for rel_path, href, label, desc, priority, pclass in cfg.guide_briefs:
            if not (ctx.project_root / rel_path).exists():
                continue
            guide_cards.append(_guide_card(href, label, desc, priority, pclass))
        if not has_paper and not guide_cards:
            guide_cards.append(_guide_placeholder(
                "Paper",
                "Paper not yet built &mdash; run <code>bash build.sh site</code> on a host with TeX.",
            ))
        html = html.replace("<!-- INJECT_GUIDE_CARDS -->", "\n".join(guide_cards))

    if "<!-- INJECT_PAPER_CARD -->" in template:
        paper_card = _hero_card(
            "Paper", cfg.paper_title,
            "paper/index.html" if has_paper else None,
        )
        html = html.replace("<!-- INJECT_PAPER_CARD -->", paper_card)
    if "<!-- INJECT_TALK_CARD -->" in template:
        talk_card = _hero_card(
            "Talk", cfg.paper_title,
            "talk/index.html" if has_talk else None,
        )
        html = html.replace("<!-- INJECT_TALK_CARD -->", talk_card)

    # Doc cards grouped by category
    groups: dict[str, list[dict]] = {}
    for doc in docs_info:
        groups.setdefault(doc["category"], []).append(doc)
    subdoc_by_dir: dict[str, list[dict]] = {}
    for item in subdir_info:
        subdoc_by_dir.setdefault(item["subdir"], []).append(item)

    doc_html: list[str] = []
    for cat, docs in groups.items():
        links = "".join(
            f'<li><a href="docs/{d["stem"]}.html">{d["title"]}</a></li>'
            for d in docs
        )
        doc_html.append(
            f'<div class="doc-group"><h3>{cat}</h3>'
            f'<ul class="link-list">{links}</ul></div>'
        )

    html = html.replace(
        "<!-- INJECT_DOC_CARDS -->",
        (extra_doc_cards + "\n" if extra_doc_cards else "") + "\n".join(doc_html),
    )

    html = inject_nav(html, ctx, prefix="", active="home")

    out = ctx.site_dir / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"  index.html ({len(docs_info)} docs, {len(subdir_info)} subdir pages)")
