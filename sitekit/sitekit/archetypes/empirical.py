"""Empirical archetype: data sources, dataset pages, descriptives, tables.

Ported from fisc/source/site/build_all.py. Activated by SiteConfig.archetype
== "empirical". The archetype owns:

- The `Data` nav dropdown (sources list)
- `build/site/datasets/<id>.html` (per-dataset pages from summary cache JSON)
- `build/site/sources/<id>.html` (per-source-group overview pages)
- `build/site/docs/descriptives.html` (figures from build/figure/*.pdf)
- `build/site/docs/tables.html` (tables from build/table/*.md)
- Source-script pages for source/figure/*.py + source/table/*.py
- The `<!-- INJECT_SOURCE_CARDS -->` content on the landing page

Imports `source.summary.config` from the project (DATASETS, SOURCES,
CACHE_DIR) — set SiteConfig.summary_config_module to override.

Project-specific touches stay as hooks on SiteConfig (e.g. fisc's
`{{table: NAME}}` directive, figure-source link injection on doc pages).
"""

from __future__ import annotations

import html as _html_lib
import importlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from ..context import BuildContext
from ..nav import inject_nav
from ..templates import read_template
from ..render import md_to_html

# Source-page HTML helper imports (use the connect-style Pygments path
# when sitekit.links.script.CODE_CSS / highlight_source are available).
from ..links.script import highlight_source as _hl_pygments


HLJS_TAGS = (
    '<link rel="stylesheet" '
    'href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/github.min.css">'
    '<script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>'
    '<script>document.addEventListener("DOMContentLoaded",()=>hljs.highlightAll());</script>'
)


def _fmt_rows_short(n: int) -> str:
    """Format row count compactly: 533,351 -> '533K'."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.0f}K" if n >= 10_000 else f"{n / 1_000:.1f}K"
    return str(n)


def _inject_data(html: str, data: dict, marker: str = "/* INJECT_DATA */") -> str:
    """Replace the marker with a serialized JSON payload.

    Two template styles supported:

    1. `const DATA = /* INJECT_DATA */ {…};` (fisc) — brace-balanced
       replacement of the literal `{…}` that follows the marker; JSON
       is serialized compact (no extra whitespace) so the template's
       JS context stays clean.
    2. `const DATA = /* INJECT_DATA */;` (poll-sponsor-bias) — plain
       string replacement of the marker; JSON serialized with default
       formatting (spaces around `,` and `:`).
    """
    marker_pos = html.index(marker)
    # Scan ahead for the next non-whitespace character. If it's `{`, use
    # brace-balanced replacement; otherwise plain replace.
    i = marker_pos + len(marker)
    while i < len(html) and html[i].isspace():
        i += 1
    if i < len(html) and html[i] == "{":
        brace_start = i
        depth = 0
        while i < len(html):
            if html[i] == "{":
                depth += 1
            elif html[i] == "}":
                depth -= 1
                if depth == 0:
                    brace_end = i
                    break
            i += 1
        else:
            raise RuntimeError("Could not find closing brace for DATA object.")
        payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
        return html[:brace_start] + payload + html[brace_end + 1:]
    # Plain-replace fallback.
    payload = json.dumps(data, ensure_ascii=False)
    return html.replace(marker, payload, 1)


def _load_summary_config(ctx: BuildContext):
    """Import the project's source.summary.config (or fail gracefully)."""
    try:
        return importlib.import_module(ctx.config.summary_config_module)
    except ImportError:
        return None


def data_dropdown_items(ctx: BuildContext, prefix: str) -> list[tuple]:
    """Fisc-style Data dropdown: one item per SOURCE, linking to /sources/<id>.html.

    Wire into SiteConfig:

        nav_dropdowns=[("Data", "data", data_dropdown_items, "before")]
    """
    config_module = _load_summary_config(ctx)
    if config_module is None:
        return []
    sources = getattr(config_module, "SOURCES", [])
    return [(src.name, f"{prefix}sources/{src.id}.html") for src in sources]


def data_dropdown_items_grouped(ctx: BuildContext, prefix: str) -> list[tuple]:
    """Poll-sponsor-bias-style Data dropdown: one item per DATASET, grouped
    by layer ("Raw (upstream)" then "Assembled"), linking to
    /<dataset_output_subdir>/<id>.html.

    Wire into SiteConfig:

        nav_dropdowns=[("Data", "data", data_dropdown_items_grouped)]

    (psb uses the default "after" position.)
    """
    cfg = ctx.config
    config_module = _load_summary_config(ctx)
    if config_module is None:
        return []
    summaries = _load_all_datasets(ctx, config_module)
    if not summaries:
        return []
    groups: dict[str, list[dict]] = {"raw": [], "assembled": []}
    for d in summaries:
        groups.setdefault(d.get("layer", "assembled"), []).append(d)
    items: list[tuple] = []
    label_for = {"raw": "Raw (upstream)", "assembled": "Assembled"}
    for layer in ("raw", "assembled"):
        entries = groups.get(layer, [])
        if not entries:
            continue
        items.append(("__group__", label_for[layer]))
        for d in entries:
            items.append((d["id"], f'{prefix}{cfg.dataset_output_subdir}/{d["id"]}.html'))
    return items


def _load_all_datasets(ctx: BuildContext, config_module) -> list[dict]:
    """Load every cached summary JSON, syncing fields from DatasetConfig
    where available (category, name, description, layer, source_script,
    source_script_external) so renames don't require a full re-summary.

    Iteration order depends on SiteConfig.dataset_iteration_order:
      "filename" — sorted(glob), fisc's historical order.
      "declared" — follow DATASETS declaration order; psb's needs."""
    site_cfg = ctx.config
    cache_dir = ctx.project_root / site_cfg.summary_cache_dir_rel
    if not cache_dir.exists():
        return []
    declared = list(getattr(config_module, "DATASETS", []))
    sync_attrs = (
        "category", "name", "description", "layer",
        "source_script", "source_script_external", "grain",
    )
    config_by_id = {d.id: d for d in declared}

    def _sync(data: dict, cfg) -> dict:
        for attr in sync_attrs:
            if hasattr(cfg, attr):
                data[attr] = getattr(cfg, attr)
        return data

    out: list[dict] = []
    if site_cfg.dataset_iteration_order == "declared" and declared:
        for cfg in declared:
            p = cache_dir / f"{cfg.id}.json"
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                out.append(_sync(data, cfg))
        return out

    for json_path in sorted(cache_dir.glob("*.json")):
        data = json.loads(json_path.read_text(encoding="utf-8"))
        cfg = config_by_id.get(data.get("id"))
        if cfg is not None:
            data = _sync(data, cfg)
        out.append(data)
    return out


def build_dataset_page(ctx: BuildContext, data: dict, out_subdir: str = "datasets") -> None:
    """Build one /<out_subdir>/<id>.html from a cached summary."""
    cfg = ctx.config
    template = read_template(cfg, "dataset.html")
    html = template.replace("/* INJECT_TITLE */", data["name"])
    html = html.replace("/* INJECT_DESCRIPTION */", data["description"])
    if cfg.inject_dataset_source_link:
        if "/* INJECT_GRAIN */" in html and "grain" in data:
            html = html.replace("/* INJECT_GRAIN */", data["grain"])
        if data.get("source_script_external"):
            html = html.replace("/* INJECT_SOURCE */", data["source_script"])
        else:
            rel = data.get("source_script", "")
            href = "../" + (
                rel.replace(".py", ".html")
                   .replace(".R", ".html")
                   .replace(".sh", ".html")
                   .replace(".sql", ".html")
            )
            html = html.replace(
                "/* INJECT_SOURCE */",
                f'<a href="{href}">{rel}</a>')
    html = inject_nav(html, ctx, prefix="../", active="data")
    html = _inject_data(html, data)

    out_dir = ctx.site_dir / out_subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / f'{data["id"]}.html').write_text(html, encoding="utf-8")
    print(f"  {out_subdir}/{data['id']}.html ({data['row_count']:,} rows)")


def build_source_page(
    ctx: BuildContext, source_cfg, all_datasets: list[dict]
) -> dict:
    """Build one /sources/<id>.html overview page; return summary info dict."""
    cfg = ctx.config
    children = [d for d in all_datasets if d["category"] in source_cfg.categories]
    cat_order = {c: i for i, c in enumerate(source_cfg.categories)}
    children.sort(key=lambda d: (cat_order.get(d["category"], 99), -d["row_count"]))

    total_rows = sum(d["row_count"] for d in children)
    total_file_size = sum(d.get("file_size", 0) for d in children)
    dataset_count = len(children)

    temporal_range: dict[str, str | None] = {"min": None, "max": None}
    for d in children:
        for _col, t in (d.get("temporal") or {}).items():
            t_min, t_max = str(t["min"]), str(t["max"])
            if temporal_range["min"] is None or t_min < temporal_range["min"]:
                temporal_range["min"] = t_min
            if temporal_range["max"] is None or t_max > temporal_range["max"]:
                temporal_range["max"] = t_max

    featured: dict = {}
    if children:
        largest = max(children, key=lambda d: d["row_count"])
        featured["categorical"] = largest.get("categorical", {})
        featured["temporal"] = largest.get("temporal", {})

    ds_summaries = [
        {
            "id": d["id"],
            "name": d["name"],
            "description": d["description"],
            "category": d.get("category", ""),
            "row_count": d["row_count"],
            "col_count": d["col_count"],
            "file_size": d.get("file_size", 0),
        }
        for d in children
    ]

    page_data = {
        "id": source_cfg.id,
        "name": source_cfg.name,
        "description": source_cfg.description,
        "total_rows": total_rows,
        "total_file_size": total_file_size,
        "dataset_count": dataset_count,
        "temporal_range": temporal_range,
        "datasets": ds_summaries,
        "featured": featured,
    }

    # Per-source template override at templates/sources/<id>.html for
    # narrative pages (e.g. fisc's diarios that has no parquet backing).
    custom_path = None
    for search_dir in cfg.template_search_dirs:
        candidate = search_dir / "sources" / f"{source_cfg.id}.html"
        if candidate.is_file():
            custom_path = candidate
            break
    if custom_path is not None:
        template = custom_path.read_text(encoding="utf-8")
        custom_used = True
    else:
        template = read_template(cfg, "source.html")
        custom_used = False

    html = template.replace("/* INJECT_TITLE */", source_cfg.name)
    html = html.replace("/* INJECT_DESCRIPTION */", source_cfg.description)
    html = inject_nav(html, ctx, prefix="../", active="data")
    html = _inject_data(html, page_data)

    out = ctx.site_dir / "sources" / f"{source_cfg.id}.html"
    out.write_text(html, encoding="utf-8")
    label = "custom" if custom_used else f"{dataset_count} datasets, {total_rows:,} rows"
    print(f"  sources/{source_cfg.id}.html ({label})")

    return {"id": source_cfg.id, "name": source_cfg.name, "total_rows": total_rows}


def build_data_section(ctx: BuildContext) -> list[dict]:
    """Build all dataset and (optionally) source-group pages.

    Returns sources_info (empty list when build_source_group_pages is False
    — psb-style projects have no source/ overview pages).
    """
    cfg = ctx.config
    config_module = _load_summary_config(ctx)
    if config_module is None:
        return []
    sources = getattr(config_module, "SOURCES", [])
    all_datasets = _load_all_datasets(ctx, config_module)
    if not all_datasets:
        if cfg.build_source_group_pages and not any(not s.categories for s in sources):
            print("  (no summary JSON files found)")
            return []
        return []

    (ctx.site_dir / cfg.dataset_output_subdir).mkdir(parents=True, exist_ok=True)
    for data in all_datasets:
        build_dataset_page(ctx, data, out_subdir=cfg.dataset_output_subdir)

    if not cfg.build_source_group_pages:
        return []

    (ctx.site_dir / "sources").mkdir(exist_ok=True)
    sources_info = [build_source_page(ctx, src, all_datasets) for src in sources]
    return sources_info


def _pdf_to_png(pdf_path: Path, out_dir: Path) -> Path:
    """Convert a single-page PDF to PNG via pdftoppm."""
    stem = pdf_path.stem
    out_path = out_dir / f"{stem}.png"
    subprocess.run(
        ["pdftoppm", "-png", "-r", "200", "-singlefile",
         str(pdf_path), str(out_dir / stem)],
        check=True, capture_output=True,
    )
    return out_path


def build_descriptives_page(ctx: BuildContext) -> dict | None:
    """Build docs/descriptives.html from build/figure/*.pdf."""
    cfg = ctx.config
    figure_dir = ctx.project_root / cfg.figure_build_dir_rel
    pdfs = sorted(figure_dir.glob("*.pdf")) if figure_dir.exists() else []
    if not pdfs:
        print("  docs/descriptives.html (skipped — no figures)")
        return None

    figures_site_dir = ctx.site_dir / "figures"
    figures_site_dir.mkdir(exist_ok=True)

    png_names: list[str] = []
    for pdf in pdfs:
        try:
            _pdf_to_png(pdf, figures_site_dir)
            png_names.append(pdf.stem)
        except Exception as e:
            print(f"    warning: could not convert {pdf.name}: {e}")

    figure_src_dir = ctx.project_root / cfg.figure_source_dir_rel
    parts = ["<h2>Figures</h2>"]
    for stem in png_names:
        title = stem.replace("_", " ").title()
        parts.append(
            f'<h3>{title}</h3>'
            f'<p><img src="../figures/{stem}.png" alt="{title}"></p>'
        )
        if (figure_src_dir / f"{stem}.py").exists():
            parts.append(
                f'<div class="figure-source-link">'
                f'<a href="../source/figure/{stem}.html" '
                f'title="source script: source/figure/{stem}.py">'
                f'&lt;/&gt; <code>source/figure/{stem}.py</code></a></div>'
            )
    content_html = "\n".join(parts)

    template = read_template(cfg, "doc.html")
    html = template.replace("<!-- INJECT_TITLE -->", "Descriptives")
    html = html.replace("<!-- INJECT_CONTENT -->", content_html)
    html = inject_nav(html, ctx, prefix="../", active="docs")

    out = ctx.site_dir / "docs" / "descriptives.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"  docs/descriptives.html ({len(png_names)} figures)")

    return {
        "stem": "descriptives",
        "title": "Descriptives",
        "description": "Figures",
        "category": "Descriptives",
    }


def build_tables_page(ctx: BuildContext) -> dict | None:
    """Build docs/tables.html from build/table/*.md."""
    cfg = ctx.config
    table_dir = ctx.project_root / cfg.table_build_dir_rel
    src_dir = ctx.project_root / cfg.table_source_dir_rel
    md_files = sorted(table_dir.glob("*.md")) if table_dir.exists() else []
    if not md_files:
        print("  docs/tables.html (skipped — no table markdown files)")
        return None

    parts = ["<h2>Tables</h2>"]
    for md_path in md_files:
        stem = md_path.stem
        title = stem.replace("_", " ").title()
        parts.append(f'<h3 id="{stem}">{title}</h3>')
        parts.append(md_to_html(md_path.read_text(encoding="utf-8")))
        if (src_dir / f"{stem}.py").exists():
            parts.append(
                f'<div class="figure-source-link">'
                f'<a href="../source/table/{stem}.html" '
                f'title="source script: source/table/{stem}.py">'
                f'&lt;/&gt; <code>source/table/{stem}.py</code></a></div>'
            )
    content_html = "\n".join(parts)

    template = read_template(cfg, "doc.html")
    html = template.replace("<!-- INJECT_TITLE -->", "Tables")
    html = html.replace("<!-- INJECT_CONTENT -->", content_html)
    html = inject_nav(html, ctx, prefix="../", active="docs")

    out = ctx.site_dir / "docs" / "tables.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html, encoding="utf-8")
    print(f"  docs/tables.html ({len(md_files)} tables)")

    return {
        "stem": "tables",
        "title": "Tables",
        "description": "All generated tables",
        "category": "Descriptives",
    }


def _build_source_pages_hljs(ctx: BuildContext) -> int:
    """Render source/figure/*.py + source/table/*.py with highlight.js."""
    cfg = ctx.config
    template = read_template(cfg, "doc.html")
    total = 0
    for kind in ("figure", "table"):
        scripts_dir_rel = (
            cfg.figure_source_dir_rel if kind == "figure"
            else cfg.table_source_dir_rel
        )
        build_dir_rel = (
            cfg.figure_build_dir_rel if kind == "figure"
            else cfg.table_build_dir_rel
        )
        scripts_dir = ctx.project_root / scripts_dir_rel
        if not scripts_dir.exists():
            continue
        out_dir = ctx.site_dir / "source" / kind
        out_dir.mkdir(parents=True, exist_ok=True)
        count = 0
        for script in sorted(scripts_dir.glob("*.py")):
            stem = script.stem
            if stem.startswith("_"):
                continue
            text = script.read_text(encoding="utf-8")
            escaped = _html_lib.escape(text)

            build_dir = ctx.project_root / build_dir_rel
            outputs = sorted(build_dir.glob(f"{stem}.*"))
            output_block = ""
            if outputs:
                items = "".join(
                    f'<li><code>build/{kind}/{p.name}</code></li>' for p in outputs
                )
                output_block = f'<p>Outputs:</p><ul>{items}</ul>'

            content_html = (
                f'<p>Source: <code>source/{kind}/{stem}.py</code></p>'
                f'{output_block}'
                f'<pre><code class="language-python">{escaped}</code></pre>'
            )

            title = f"source/{kind}/{stem}.py"
            html_doc = template.replace("<!-- INJECT_TITLE -->", title)
            html_doc = html_doc.replace("<!-- INJECT_CONTENT -->", content_html)
            html_doc = inject_nav(html_doc, ctx, prefix="../../", active="")
            html_doc = html_doc.replace("</body>", f"{HLJS_TAGS}\n</body>", 1)

            (out_dir / f"{stem}.html").write_text(html_doc, encoding="utf-8")
            count += 1
        print(f"  source/{kind}/ ({count} scripts)")
        total += count
    return total


_PERLINE_EXTS = (".py", ".R", ".sh", ".sql")


def _build_source_pages_perline(ctx: BuildContext) -> int:
    """Render every source/**/*.{py,R,sh,sql} with per-line `#L42` anchors.

    No syntax highlighting — keeps the per-line `id` contract simple. Skips
    source/site/* (the build script itself) and __pycache__.
    """
    cfg = ctx.config
    root = ctx.project_root / "source"
    if not root.exists():
        return 0
    template = read_template(cfg, "doc.html")
    NOINDEX_LOCAL = '<meta name="robots" content="noindex, nofollow">'
    count = 0
    seen: dict[str, Path] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix not in _PERLINE_EXTS:
            continue
        rel = path.relative_to(ctx.project_root)
        if "__pycache__" in rel.parts or rel.parts[:2] == ("source", "site"):
            continue
        if path.name in seen:
            continue
        seen[path.name] = path

    for path in sorted(seen.values()):
        rel = path.relative_to(ctx.project_root)
        depth = len(rel.parts) - 1
        prefix = "../" * depth
        text = path.read_text(errors="replace")
        escaped = _html_lib.escape(text)
        lines = escaped.split("\n")
        n_width = max(2, len(str(len(lines))))
        rendered = "".join(
            f'<span class="src-line" id="L{i}">'
            f'<a class="src-ln" href="#L{i}">{i:>{n_width}}</a> '
            f'<span class="src-code">{line or " "}</span>'
            f'</span>'
            for i, line in enumerate(lines, start=1)
        )
        content = (
            f'<p>Source: <code>{rel}</code> '
            f'(<a href="{prefix}index.html">back to index</a>)</p>'
            f'<pre class="src-listing">{rendered}</pre>'
        )
        page = template.replace("<!-- INJECT_TITLE -->", str(rel))
        page = page.replace("<!-- INJECT_CONTENT -->", content)
        page = inject_nav(page, ctx, prefix=prefix, active="")
        out = ctx.site_dir / str(rel.with_suffix(".html"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        count += 1
    print(f"  source/**/*.html ({count} scripts)")
    return count


def build_source_pages(ctx: BuildContext) -> int:
    """Render source-script pages per config mode/scope."""
    cfg = ctx.config
    if cfg.source_pages_mode == "perline" or cfg.source_pages_scope == "all_source":
        return _build_source_pages_perline(ctx)
    return _build_source_pages_hljs(ctx)


# ---------------------------------------------------------------------------
# Helpers — generally-useful patterns lifted from fisc. Importable from
# sitekit.archetypes.empirical so project site.py files can reuse them.
# ---------------------------------------------------------------------------


def build_doc_url_map(
    doc_registry: list[tuple[str, str, str, str]],
    subdir_doc_registry: Iterable[tuple[str, str, str, str]] = (),
) -> dict[str, str]:
    """Build a precomputed map: authored markdown path → site-root html path.

    Lets the link rewriter resolve cross-doc references whether the author
    wrote `summary.md`, `docs/summary.md`, `briefs/why-exfis-fail.md`, or
    `docs/briefs/why-exfis-fail.md`.

    subdir_doc_registry is a list of (rel_path, _title, _desc, subdir) tuples
    where subdir is the directory name (e.g. "briefs") that the entry
    renders to at site root.
    """
    m: dict[str, str] = {}
    for rel_path, _t, _d, _c in doc_registry:
        stem = Path(rel_path).stem
        target = f"docs/{stem}.html"
        m[f"{stem}.md"] = target
        m[f"docs/{stem}.md"] = target
    for rel_path, _t, _d, subdir in subdir_doc_registry:
        stem = Path(rel_path).stem
        target = f"{subdir}/{stem}.html"
        m[f"{subdir}/{stem}.md"] = target
        m[f"docs/{subdir}/{stem}.md"] = target
    return m


def make_url_map_link_rewriter(url_map: dict[str, str]):
    """Build a SiteConfig.link_rewriter callable backed by a precomputed map.

    Accepts the standard kwargs (in_subdir, prefix) but uses prefix only;
    in_subdir is ignored because the map already encodes target locations.
    """
    href_re = re.compile(r'href="([^"]*\.md(?:#[^"]*)?)"')

    def _rewriter(html: str, ctx, *, in_subdir: bool = False, prefix: str = "../") -> str:
        def _replacer(m: re.Match) -> str:
            href = m.group(1)
            if href.startswith(("http://", "https://", "//", "#")):
                return m.group(0)
            path, _sep, frag = href.partition("#")
            target = url_map.get(path)
            if target is None:
                new = href.replace(".md", ".html")
            else:
                new = prefix + target + (f"#{frag}" if frag else "")
            return f'href="{new}"'
        return href_re.sub(_replacer, html)

    return _rewriter


def make_autolink_doc_refs(url_map: dict[str, str]):
    """Build a content-postprocessor that turns bare `<code>path.md</code>`
    mentions into hyperlinks. Mirrors fisc's _autolink_doc_refs.

    Project uses it via SiteConfig.content_postprocessors=[...].
    """
    def _postprocess(html: str, ctx, current_stem: str, in_subdir: bool) -> str:
        prefix = "../"  # subdir + flat top-level docs both live one level down

        # Protect existing anchors so we don't re-link their inner <code>.
        anchors: list[str] = []
        def _save_anchor(m: re.Match) -> str:
            anchors.append(m.group(0))
            return f"\x00A{len(anchors) - 1}\x00"
        protected = re.sub(r"<a\s[^>]*>.*?</a>", _save_anchor, html, flags=re.DOTALL)

        def _replacer(m: re.Match) -> str:
            body = m.group(1)
            path, _sep, frag = body.partition("#")
            target = url_map.get(path)
            if target is None:
                return m.group(0)
            href = prefix + target + (f"#{frag}" if frag else "")
            return f'<a href="{href}"><code>{body}</code></a>'

        linked = re.sub(
            r"<code>([^<\s]+\.md(?:#[^<\s]+)?)</code>", _replacer, protected)
        return re.sub(r"\x00A(\d+)\x00", lambda m: anchors[int(m.group(1))], linked)

    return _postprocess


def attach_figure_source_links(html: str, ctx, current_stem: str, in_subdir: bool) -> str:
    """Append a 'view source' badge after each <img> pointing to build/figure.

    Matches <img src="(.../)?figures/<stem>.png"> and, if the corresponding
    source/figure/<stem>.py exists, appends a styled source-link badge.
    """
    figures_dir = ctx.project_root / ctx.config.figure_source_dir_rel
    figure_re = re.compile(
        r'<img\s+[^>]*?src="(?:\.\./)?figures/(?P<stem>[^"./]+)\.png"[^>]*>'
    )
    prefix = "../"

    def _replacer(m: re.Match) -> str:
        stem = m.group("stem")
        if not (figures_dir / f"{stem}.py").exists():
            return m.group(0)
        link_url = f'{prefix}source/figure/{stem}.html'
        badge = (
            f'<span class="figure-source-link">'
            f'<a href="{link_url}" title="source script: source/figure/{stem}.py">'
            f'&lt;/&gt; <code>source/figure/{stem}.py</code></a></span>'
        )
        return m.group(0) + badge

    return figure_re.sub(_replacer, html)


def expand_table_directives(html: str, ctx, current_stem: str, in_subdir: bool) -> str:
    """Expand `{{table: NAME}}` directives by inlining build/table/<NAME>.md."""
    cfg = ctx.config
    table_dir = ctx.project_root / cfg.table_build_dir_rel
    src_dir = ctx.project_root / cfg.table_source_dir_rel
    prefix = "../"

    block_re = re.compile(
        r'<p>\s*\{\{\s*table\s*:\s*([a-zA-Z0-9_-]+)\s*\}\}\s*</p>')
    inline_re = re.compile(
        r'\{\{\s*table\s*:\s*([a-zA-Z0-9_-]+)\s*\}\}')

    def _render(name: str) -> str:
        md_file = table_dir / f"{name}.md"
        src_file = src_dir / f"{name}.py"
        if not md_file.exists():
            return (
                f'<div class="table-missing">'
                f'<em>Missing <code>build/table/{name}.md</code> — '
                f'run <code>python3 source/table/{name}.py</code> '
                f'(or migrate it to <code>write_table</code>).</em></div>'
            )
        out = md_to_html(md_file.read_text(encoding="utf-8"))
        if src_file.exists():
            link_url = f'{prefix}source/table/{name}.html'
            out += (
                f'<div class="figure-source-link">'
                f'<a href="{link_url}" title="source script: source/table/{name}.py">'
                f'&lt;/&gt; <code>source/table/{name}.py</code></a></div>'
            )
        return out

    html = block_re.sub(lambda m: _render(m.group(1)), html)
    html = inline_re.sub(lambda m: _render(m.group(1)), html)
    return html


# ---------------------------------------------------------------------------


def run_empirical(
    ctx: BuildContext,
    docs_info: list[dict],
    subdir_info: list[dict],
) -> dict:
    """Empirical-archetype build steps. Returns a dict with sources_info."""
    cfg = ctx.config
    extra: list[dict] = []

    if cfg.build_descriptives:
        info = build_descriptives_page(ctx)
        if info:
            extra.append(info)
    if cfg.build_tables:
        info = build_tables_page(ctx)
        if info:
            extra.append(info)

    build_source_pages(ctx)
    sources_info = build_data_section(ctx)

    return {"sources_info": sources_info, "extra_docs_info": extra}
