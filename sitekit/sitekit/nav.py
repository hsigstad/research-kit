"""Top navigation bar HTML generation.

Lifted from connect/serasa with the project-specific bits parameterized
through SiteConfig. The CSS and JS blocks are identical across all current
projects — they ship in the package and are not configurable.
"""

from __future__ import annotations

from pathlib import Path

from .config import SiteConfig
from .context import BuildContext
from .paths import output_path


NAV_CSS = """\
<style>
  .site-nav {
    position: sticky; top: 0; z-index: 100;
    background: #212529; display: flex; align-items: center;
    padding: 0 2rem; height: 3rem;
  }
  .site-nav .nav-brand {
    color: #fff; text-decoration: none; font-weight: 600; font-size: 1rem;
    margin-right: auto;
  }
  .site-nav .nav-brand:hover { color: #e9ecef; }
  .site-nav .nav-link {
    color: #adb5bd; text-decoration: none; font-size: .85rem;
    padding: 0 .75rem; height: 3rem; display: flex; align-items: center;
    background: none; border: none; cursor: pointer; font-family: inherit;
  }
  .site-nav .nav-link:hover, .site-nav .nav-link.active { color: #fff; }
  .nav-dropdown { position: relative; }
  .dropdown-menu {
    display: none; position: absolute; top: 3rem; right: 0;
    background: var(--card); border: 1px solid var(--border); border-radius: 6px;
    box-shadow: 0 4px 16px rgba(0,0,0,.12); min-width: 220px;
    padding: .4rem 0; z-index: 200; max-height: 80vh; overflow-y: auto;
  }
  .nav-dropdown.open .dropdown-menu { display: block; }
  .dropdown-menu a {
    display: block; padding: .3rem 1rem; color: var(--fg);
    text-decoration: none; font-size: .82rem;
  }
  .dropdown-menu a:hover { background: #f5f3ee; }
  .dropdown-group-label {
    padding: .4rem 1rem .15rem; font-size: .68rem; font-weight: 700;
    color: var(--muted); text-transform: uppercase; letter-spacing: .04em;
  }
  .dropdown-divider { border-top: 1px solid var(--border); margin: .3rem 0; }
  .page-header {
    padding: .8rem 2rem; border-bottom: 1px solid var(--border);
    background: var(--card);
  }
  .page-header h1 { font-size: 1.3rem; font-weight: 600; }
  .page-header p { color: var(--muted); font-size: .85rem; margin-top: .15rem; }
</style>
"""

NAV_JS = """\
<script>
document.querySelectorAll('.nav-dropdown > .nav-link').forEach(function(btn) {
  btn.addEventListener('click', function(e) {
    e.stopPropagation();
    var dd = btn.parentElement;
    var wasOpen = dd.classList.contains('open');
    document.querySelectorAll('.nav-dropdown.open').forEach(function(d) { d.classList.remove('open'); });
    if (!wasOpen) dd.classList.add('open');
  });
});
document.addEventListener('click', function() {
  document.querySelectorAll('.nav-dropdown.open').forEach(function(d) { d.classList.remove('open'); });
});
</script>
"""

NOINDEX = '<meta name="robots" content="noindex, nofollow">'


def _brief_title(md_path: Path) -> str:
    for line in md_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("# "):
            return line[2:].strip()
    return md_path.stem.replace("-", " ").replace("_", " ").title()


def build_nav_html(ctx: BuildContext, prefix: str = "", active: str = "") -> str:
    """Generate the site-wide navigation bar HTML."""
    cfg = ctx.config

    def _cls(section: str) -> str:
        return ' class="nav-link active"' if active == section else ' class="nav-link"'

    # Docs dropdown items grouped by category. Use output_path so
    # folder-mode entries (docs/hypotheses/index.md → docs/hypotheses/index.html)
    # get the right href instead of flattening into docs/index.html.
    groups: dict[str, list[tuple[str, str]]] = {}
    for rel_path, title, _desc, category in cfg.doc_registry:
        if not (cfg.project_root / rel_path).exists():
            continue
        _, display, _ = output_path(ctx, rel_path)
        href = f'{prefix}{display}'
        groups.setdefault(category, []).append((title, href))

    # Add subdirectory doc folders if they exist
    for subdir, label, _color in cfg.doc_subdirs:
        sub_path = cfg.project_root / "docs" / subdir
        if not sub_path.is_dir():
            continue
        if subdir in cfg.index_only_subdirs:
            groups[label] = [(f"All {label.lower()}", f"{prefix}{subdir}/index.html")]
            continue
        entries: list[tuple[str, str]] = []
        for md_path in sorted(sub_path.glob("*.md")):
            if md_path.stem in cfg.exclude_stems:
                continue
            meta_override = cfg.subdir_doc_meta.get(md_path.stem)
            if meta_override is not None:
                title = meta_override[0]
            elif cfg.subdir_title_fallback == "stem":
                title = md_path.stem.replace("-", " ").title()
            else:
                title = _brief_title(md_path)
            href = f'{prefix}{subdir}/{md_path.stem}.html'
            entries.append((title, href))
        if entries:
            groups[label] = entries

    doc_items: list[str] = []
    for i, (cat, entries) in enumerate(groups.items()):
        if i > 0:
            doc_items.append('<div class="dropdown-divider"></div>')
        doc_items.append(f'<div class="dropdown-group-label">{cat}</div>')
        for title, href in entries:
            doc_items.append(f'<a href="{href}">{title}</a>')
    doc_items_html = "\n    ".join(doc_items)

    # Nav extras (Paper(s) is always first; others are project-configured).
    # Multi-paper projects render a "Papers" dropdown listing each entry;
    # single-paper projects keep the legacy "Paper" link.
    extras_html: list[str] = []
    if cfg.papers:
        paper_items: list[str] = []
        for key, label, _tex, _makeht, _title in cfg.papers:
            paper_items.append(
                f'<a href="{prefix}paper/{key}/index.html">{label}</a>')
        # Include the listing page as a header link so users can land on
        # the index without picking one paper.
        paper_items_html = (
            f'<a href="{prefix}paper/index.html">All papers</a>\n    '
            '<div class="dropdown-divider"></div>\n    '
            + "\n    ".join(paper_items)
        )
        extras_html.append(
            f"""<div class="nav-dropdown">
    <button{_cls("paper")}>Papers &#9662;</button>
    <div class="dropdown-menu">
    {paper_items_html}
    </div>
  </div>"""
        )
    else:
        extras_html.append(
            f'<a href="{prefix}paper/index.html"{_cls("paper")}>Paper</a>'
        )
    for label, href_template, key in cfg.nav_extras:
        href = href_template.replace("{prefix}", prefix)
        extras_html.append(f'<a href="{href}"{_cls(key)}>{label}</a>')
    extras_block = "\n".join(f"  {e}" for e in extras_html)

    docs_dropdown = f"""<div class="nav-dropdown">
    <button{_cls("docs")}>Docs &#9662;</button>
    <div class="dropdown-menu">
    {doc_items_html}
    </div>
  </div>"""

    # Additional config-supplied dropdowns. Position is "after" by default
    # (rendered after Docs). "before" puts the dropdown ahead of Docs in
    # the nav (fisc's Data-then-Docs ordering).
    def _render_dropdown(label: str, key: str, items: list) -> str | None:
        if not items:
            return None
        rendered_items: list[str] = []
        first_group = True
        for item in items:
            if not item:
                continue
            marker = item[0]
            if marker == "__divider__":
                rendered_items.append('<div class="dropdown-divider"></div>')
            elif marker == "__group__":
                if not first_group:
                    rendered_items.append('<div class="dropdown-divider"></div>')
                first_group = False
                rendered_items.append(
                    f'<div class="dropdown-group-label">{item[1]}</div>')
            else:
                item_label, item_href = item
                rendered_items.append(f'<a href="{item_href}">{item_label}</a>')
        items_html = "\n    ".join(rendered_items)
        return (
            f"""<div class="nav-dropdown">
    <button{_cls(key)}>{label} &#9662;</button>
    <div class="dropdown-menu">
    {items_html}
    </div>
  </div>"""
        )

    before_dropdowns: list[str] = []
    after_dropdowns: list[str] = []
    for entry in cfg.nav_dropdowns:
        if len(entry) == 4:
            label, key, items_fn, position = entry
        else:
            label, key, items_fn = entry
            position = "after"
        rendered = _render_dropdown(label, key, items_fn(ctx, prefix))
        if rendered is None:
            continue
        (before_dropdowns if position == "before" else after_dropdowns).append(rendered)

    before_block = ("\n  " + "\n  ".join(before_dropdowns)) if before_dropdowns else ""
    after_block = ("\n  " + "\n  ".join(after_dropdowns)) if after_dropdowns else ""

    # Strip closing </style> from NAV_CSS, append extra_nav_css, restore tag.
    base_css = cfg.nav_css_override if cfg.nav_css_override is not None else NAV_CSS
    if cfg.extra_nav_css:
        nav_css = base_css.replace("</style>\n", cfg.extra_nav_css + "\n</style>\n")
    else:
        nav_css = base_css

    nav_html = f"""{nav_css}
<nav class="site-nav">
  <a href="{prefix}index.html" class="nav-brand">{cfg.project_title}</a>
  <a href="{prefix}index.html"{_cls("home")}>Home</a>
{extras_block}{before_block}
  {docs_dropdown}{after_block}
</nav>
{NAV_JS}"""
    return nav_html


def inject_nav(
    html: str, ctx: BuildContext, prefix: str = "", active: str = ""
) -> str:
    """Replace <!-- INJECT_NAV --> with the generated nav and add noindex.

    Also substitutes <!-- INJECT_PROJECT_TITLE --> (used by bundled
    templates that aren't project-locked) and defaults INJECT_BODY_CLASS
    to empty so the placeholder doesn't leak.
    """
    html = html.replace("<!-- INJECT_NAV -->", build_nav_html(ctx, prefix, active))
    html = html.replace("<!-- INJECT_PROJECT_TITLE -->", ctx.config.project_title)
    html = html.replace("<!-- INJECT_BODY_CLASS -->", "")
    html = html.replace("<head>", f"<head>\n{NOINDEX}", 1)
    return html
