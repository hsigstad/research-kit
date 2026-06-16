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

    # Nav extras (Paper is always first; others are project-configured)
    extras_html: list[str] = []
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

    # Additional config-supplied dropdowns rendered after Docs (e.g. Data).
    extra_dropdowns = []
    for label, key, items_fn in cfg.nav_dropdowns:
        items = items_fn(ctx, prefix)
        if not items:
            continue
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
        extra_dropdowns.append(
            f"""<div class="nav-dropdown">
    <button{_cls(key)}>{label} &#9662;</button>
    <div class="dropdown-menu">
    {items_html}
    </div>
  </div>"""
        )
    extra_dropdowns_block = ("\n  " + "\n  ".join(extra_dropdowns)) if extra_dropdowns else ""

    nav_html = f"""{NAV_CSS}
<nav class="site-nav">
  <a href="{prefix}index.html" class="nav-brand">{cfg.project_title}</a>
  <a href="{prefix}index.html"{_cls("home")}>Home</a>
{extras_block}
  {docs_dropdown}{extra_dropdowns_block}
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
