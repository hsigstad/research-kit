"""Analyses index page + analysis-frontmatter panel rendering.

Lifted from connect/build_all.py. The analyses index is built from
docs/reference/analysis-index.yaml (an append-only ledger of AN entries);
each AN page itself uses YAML frontmatter that this module renders as a
tiered info panel above the page body.
"""

from __future__ import annotations

import html as _html
import yaml
from pathlib import Path

from .context import BuildContext
from .nav import inject_nav
from .templates import read_template


AN_TYPE_ORDER = ["descriptive", "causal", "placebo", "robustness"]
AN_TYPE_LABEL = {
    "descriptive": "Descriptive", "causal": "Causal",
    "placebo": "Placebo", "robustness": "Robustness",
}
AN_TYPE_DESC = {
    "descriptive": "Sample composition, balance, raw means, exploratory cuts — no causal claim.",
    "causal": "Causal estimates: main effects, heterogeneity, decompositions, formal tests.",
    "placebo": "Falsification — effects that should be zero.",
    "robustness": "Does the main result hold under alternative definitions, sample selection, and measurement validation?",
}


def render_analysis_panel(meta: dict, ctx: BuildContext) -> tuple[str, str]:
    """Render analysis-page frontmatter as (headline_html, panel_html).

    Headline is a one-paragraph plain-English statement of the finding,
    rendered above the panel. The panel is tiered: top (hypothesis,
    confidence, type), design (sample, specification, etc.), provenance
    (script, target, commit, status, created) as a small muted footer.
    """

    def _dl(pairs: list[tuple[str, str]]) -> str:
        return "".join(
            f'<div class="an-row"><dt>{lbl}</dt><dd>{val}</dd></div>'
            for lbl, val in pairs
        )

    top_rows: list[tuple[str, str]] = []
    slug = meta.get("hypothesis")
    if slug:
        title = ctx.hyp_titles.get(slug)
        if title:
            top_rows.append(("Hypothesis",
                f'<a href="../hypotheses/{_html.escape(slug)}.html">'
                f'{_html.escape(title)}</a>'))
        else:
            top_rows.append(("Hypothesis", _html.escape(slug)))
    if meta.get("confidence"):
        conf = str(meta["confidence"])
        cls = {"green": "conf-green", "yellow": "conf-yellow",
               "red": "conf-red"}.get(conf, "conf-pending")
        top_rows.append(("Confidence",
            f'<span class="conf-chip {cls}">{_html.escape(conf)}</span>'))
    if meta.get("type"):
        top_rows.append(("Type", _html.escape(str(meta["type"]))))

    prov_rows: list[tuple[str, str]] = []
    for label, key in (("Script", "script"), ("Target", "target"),
                       ("Commit", "commit")):
        if meta.get(key):
            val = str(meta[key])
            if key == "commit":
                val = val[:12]
            prov_rows.append((label, f'<code>{_html.escape(val)}</code>'))
    if meta.get("status"):
        status = _html.escape(str(meta["status"]))
        if meta.get("status_date"):
            status += f' · {_html.escape(str(meta["status_date"]))}'
        prov_rows.append(("Status", status))
    if meta.get("created"):
        prov_rows.append(("Created", _html.escape(str(meta["created"]))))

    design = meta.get("design") or {}
    design_rows: list[tuple[str, str]] = []
    _design_labels = {"fe": "FE", "se": "SE", "iv": "IV", "ipw": "IPW"}
    for key, raw in design.items():
        if raw is None or str(raw) == "":
            continue
        if key == "sample":
            raw_str = str(raw)
            sep_pos = -1
            sep_len = 0
            for sep in (" — ", " – "):
                p = raw_str.find(sep)
                if p != -1:
                    sep_pos = p
                    sep_len = len(sep)
                    break

            if sep_pos == -1 and "," in raw_str:
                segs = [s.strip() for s in raw_str.split(",")]
                if any(s in ctx.sample_titles for s in segs):
                    rendered: list[str] = []
                    for s in segs:
                        if s in ctx.sample_titles:
                            rendered.append(
                                f'<a href="../sample/{_html.escape(s)}.html">'
                                f'{_html.escape(ctx.sample_titles[s])}</a>'
                            )
                        else:
                            rendered.append(_html.escape(s))
                    design_rows.append(("Sample", ", ".join(rendered)))
                    continue

            head = raw_str if sep_pos == -1 else raw_str[:sep_pos]
            tail = "" if sep_pos == -1 else raw_str[sep_pos + sep_len:]
            head_slug = head.strip()
            if head_slug in ctx.sample_titles:
                val = (f'<a href="../sample/{_html.escape(head_slug)}.html">'
                       f'{_html.escape(ctx.sample_titles[head_slug])}</a>')
            else:
                val = _html.escape(head_slug)
            if tail:
                val += f' — {_html.escape(tail)}'
            design_rows.append(("Sample", val))
            continue
        val = _html.escape(str(raw))
        if key == "specification":
            val = f'<code>{val}</code>'
        label = _design_labels.get(key, key.replace("_", " ").capitalize())
        design_rows.append((label, val))

    parts = ['<div class="an-panel">']
    if top_rows:
        parts.append(f'<dl class="an-meta an-meta-top">{_dl(top_rows)}</dl>')
    if design_rows:
        parts.append('<div class="an-panel-label">Design</div>')
        parts.append(f'<dl class="an-meta">{_dl(design_rows)}</dl>')
    if prov_rows:
        parts.append(f'<dl class="an-meta an-meta-prov">{_dl(prov_rows)}</dl>')
    parts.append('</div>')
    panel_html = "".join(parts)

    headline = meta.get("headline")
    headline_html = ""
    if headline:
        headline_html = (
            f'<p class="an-headline">{_html.escape(str(headline))}</p>'
        )

    return headline_html, panel_html


_AN_CLUSTER_TAGS_DEFAULT = ["favoritism", "recusal", "market", "quality", "mechanism"]


_AN_INDEX_CSS = """<style>
.an-intro { font-size: .9rem; color: var(--muted); margin-bottom: 1rem; }
.an-filters { margin: 0 0 1.4rem; }
.an-filter-row { display: flex; flex-wrap: wrap; align-items: baseline;
  gap: .35rem; margin-bottom: .4rem; }
.an-filter-label { font-size: .68rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: .04em; color: var(--muted); width: 5.5rem; flex-shrink: 0; }
.an-chip { font: inherit; font-size: .78rem; padding: .15rem .6rem;
  border-radius: 999px; border: 1px solid var(--border); background: #fff;
  color: #444; cursor: pointer; }
.an-chip:hover { background: #f0f4f8; }
.an-chip.active { background: #212529; color: #fff; border-color: #212529; }
.an-group { margin: 0 0 1.6rem; }
.an-group.hidden, .an-row.hidden { display: none; }
.an-group h2 { display: flex; align-items: baseline; gap: .5rem; }
.an-count { font-size: .8rem; font-weight: 400; color: var(--muted); }
.an-group-desc { font-size: .82rem; color: var(--muted); margin: .2rem 0 .7rem; }
.an-row { display: flex; align-items: baseline; gap: .6rem; padding: .35rem .5rem;
  border-radius: 5px; }
.an-row:hover { background: #f0f4f8; }
.an-main { display: flex; align-items: baseline; gap: .6rem; flex: 1;
  min-width: 0; text-decoration: none; color: var(--fg); }
.an-main:hover .an-q { text-decoration: underline; }
.an-id { font-family: "SFMono-Regular", Consolas, monospace; font-size: .78rem;
  font-weight: 600; color: var(--accent); flex-shrink: 0; width: 4rem; }
.an-q { flex: 1; font-size: .86rem; }
.an-conf { font-size: .66rem; padding: .05rem .4rem; border-radius: 3px;
  flex-shrink: 0; text-transform: uppercase; letter-spacing: .03em;
  font-weight: 600; align-self: center; }
.an-conf-green { background: #d4edda; color: #155724; }
.an-conf-yellow { background: #fff3cd; color: #856404; }
.an-conf-red { background: #f8d7da; color: #721c24; }
.an-conf-pending { background: #e9ecef; color: #6c757d; }
.an-meta { font-size: .72rem; color: var(--muted); flex-shrink: 0; max-width: 17rem;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.an-meta a { color: var(--accent); text-decoration: none; }
.an-meta a:hover { text-decoration: underline; }
@media (max-width: 640px) { .an-meta { display: none; } .an-filter-label { width: 100%; } }
</style>"""

_AN_INDEX_JS = """<script>
(function () {
  var chips = document.querySelectorAll('.an-chip');
  var rows = document.querySelectorAll('.an-row');
  var groups = document.querySelectorAll('.an-group');
  function apply(f) {
    rows.forEach(function (r) {
      var show = !f || (' ' + r.dataset.tags + ' ').indexOf(' ' + f + ' ') !== -1;
      r.classList.toggle('hidden', !show);
    });
    groups.forEach(function (g) {
      g.classList.toggle('hidden', !g.querySelector('.an-row:not(.hidden)'));
    });
  }
  chips.forEach(function (c) {
    c.addEventListener('click', function () {
      chips.forEach(function (x) { x.classList.remove('active'); });
      c.classList.add('active');
      apply(c.dataset.filter);
    });
  });
})();
</script>"""


def _esc(text: object) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_analyses_index(
    ctx: BuildContext,
    cluster_tags: list[str] | None = None,
) -> int:
    """Generate analyses/index.html from docs/reference/analysis-index.yaml.

    Returns the number of analyses indexed (0 if the YAML ledger is absent).
    """
    cfg = ctx.config
    ledger = ctx.project_root / "docs" / "reference" / "analysis-index.yaml"
    if not ledger.is_file():
        print("  analyses/index.html (skipped — analysis-index.yaml not found)")
        return 0
    entries = yaml.safe_load(ledger.read_text(encoding="utf-8")) or []
    if cluster_tags is None:
        cluster_tags = _AN_CLUSTER_TAGS_DEFAULT

    by_type: dict[str, list[dict]] = {}
    for e in entries:
        by_type.setdefault(e.get("type", "causal"), []).append(e)

    h_tags = sorted({t for e in entries for t in e.get("tags", [])
                     if t.startswith("H:")})
    clusters = [c for c in cluster_tags
                if any(c in e.get("tags", []) for e in entries)]

    def _chip(filt: str, label: str) -> str:
        return f'<button class="an-chip" data-filter="{filt}">{_esc(label)}</button>'

    rows = ['<div class="an-filter-row"><span class="an-filter-label">Type</span>'
            '<button class="an-chip active" data-filter="">All</button>'
            + "".join(_chip(t, AN_TYPE_LABEL[t]) for t in AN_TYPE_ORDER if t in by_type)
            + '</div>']
    if clusters:
        rows.append('<div class="an-filter-row">'
                    '<span class="an-filter-label">Cluster</span>'
                    + "".join(_chip(c, c) for c in clusters) + '</div>')
    if h_tags:
        rows.append('<div class="an-filter-row">'
                    '<span class="an-filter-label">Hypothesis</span>'
                    + "".join(_chip(h.lower(), h) for h in h_tags) + '</div>')
    filter_bar = f'<div class="an-filters">{"".join(rows)}</div>'

    sections: list[str] = []
    for t in AN_TYPE_ORDER:
        group = sorted(by_type.get(t, []), key=lambda e: e["id"])
        if not group:
            continue
        body: list[str] = []
        for e in group:
            tags = e.get("tags", [])
            data = " ".join(dict.fromkeys([t] + [x.lower() for x in tags]))
            conf = e.get("confidence", "pending")
            href = Path(e["file"]).stem + ".html"
            meta = [x for x in tags if x.startswith("H:") or x in cluster_tags]

            def _meta_item(x: str) -> str:
                if x.startswith("H:") and x[2:] in ctx.h_slugs:
                    return f'<a href="../hypotheses/{x[2:]}.html">{_esc(x)}</a>'
                return _esc(x)

            meta_html = (
                f'<span class="an-meta">'
                f'{" &middot; ".join(_meta_item(x) for x in meta)}</span>'
                if meta else "")
            body.append(
                f'<div class="an-row" data-tags="{_esc(data)}">'
                f'<a class="an-main" href="{href}">'
                f'<span class="an-id">{e["id"].upper()}</span>'
                f'<span class="an-q">{_esc(e.get("question", ""))}</span></a>'
                f'<span class="an-conf an-conf-{conf}">{conf}</span>'
                f'{meta_html}</div>'
            )
        sections.append(
            f'<section class="an-group" data-type="{t}">'
            f'<h2>{AN_TYPE_LABEL[t]} <span class="an-count">{len(group)}</span></h2>'
            f'<p class="an-group-desc">{AN_TYPE_DESC[t]}</p>'
            + "".join(body) + '</section>'
        )

    intro = (
        '<p class="an-intro">Every analysis run for this project, one document '
        'per entry &mdash; generated from '
        '<code>docs/reference/analysis-index.yaml</code>. Each <code>AN-NNN</code> '
        'records the question, script, design, results, and a confidence tag. '
        'Filter with the chips below.</p>'
    )
    content = (_AN_INDEX_CSS + intro + filter_bar
               + f'<div class="an-sections">{"".join(sections)}</div>'
               + _AN_INDEX_JS)

    template = read_template(cfg, "doc.html")
    html = template.replace("<!-- INJECT_TITLE -->", "Analyses")
    html = html.replace("<!-- INJECT_CONTENT -->", content)
    html = inject_nav(html, ctx, prefix="../", active="docs")
    out = ctx.site_dir / "analyses" / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"  analyses/index.html ({len(entries)} analyses, grouped by type)")
    return len(entries)
