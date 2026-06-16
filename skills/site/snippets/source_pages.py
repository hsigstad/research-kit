"""Canonical source-page renderer for project `source/site/build_all.py`.

Renders every `.py` / `.R` / `.sh` / `.sql` script under `source/` to
its own HTML page at `build/site/source/<subpath>.html`, with per-line
anchors (`#L42`). The dataset page's "Source:" line links to it; doc
pages can auto-link bare `script.py:42` mentions.

## How to integrate

1. Paste the three functions below in `source/site/build_all.py`.
2. In the dataset-page builder, change the source-script render so
   project-owned scripts become a hyperlink:

       if data.get("source_script_external"):
           page = page.replace("/* INJECT_SOURCE */", data["source_script"])
       else:
           rel = data["source_script"]
           href = "../" + rel.replace(".py", ".html").replace(".R", ".html") \
                              .replace(".sh", ".html").replace(".sql", ".html")
           page = page.replace(
               "/* INJECT_SOURCE */",
               f'<a href="{href}">{rel}</a>')

3. In `main()`, after the dataset pages, add:

       scripts = find_source_scripts()
       n_scripts = build_source_pages(scripts)
       print(f"  source/**/*.html ({n_scripts} scripts)")

4. Paste the CSS block below in the project's `templates/doc.html` (or
   whichever template the source pages reuse) so the per-line gutter
   has the right look.

The renderer reuses the project's existing `doc.html` template and the
existing `_build_nav_html(prefix, active)` helper — no new templates.

## CSS to add to templates/doc.html

```css
/* Source-script listings: clickable line gutter + per-line anchors so
   mentions like `script.py:42` scroll to the right row. */
pre.src-listing { font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
                  font-size: .82rem; line-height: 1.45; padding: .75rem 0;
                  overflow-x: auto; background: var(--card);
                  border: 1px solid var(--border); border-radius: 6px; }
.src-line { display: block; padding-left: 0; }
.src-line:target { background: #fff3cd; }
.src-ln { display: inline-block; width: 3.5em; padding-right: .6em;
          text-align: right; color: var(--muted); user-select: none;
          border-right: 1px solid var(--border); margin-right: .6em; }
.src-ln:hover { color: var(--accent); text-decoration: none; }
.src-code { white-space: pre; }
```

## The canonical definitions

(Copy from `# ──── BEGIN ────` to `# ──── END ────`, paste in build_all.py.)
"""

# ──── BEGIN source-pages snippet ────

import html as _html_lib
from pathlib import Path

# PROJECT_ROOT, SITE_DIR, TEMPLATE_DIR, NOINDEX, _build_nav_html are
# already defined by build_all.py — these constants/funcs are not
# reproduced here.

SCRIPT_EXTS = (".py", ".R", ".sh", ".sql")


def find_source_scripts() -> dict[str, Path]:
    """Map bare filename → absolute Path. Skips the site builder itself
    and __pycache__. On collision (rare) the first match wins.
    """
    root = PROJECT_ROOT / "source"
    out: dict[str, Path] = {}
    if not root.exists():
        return out
    for p in sorted(root.rglob("*")):
        if not p.is_file() or p.suffix not in SCRIPT_EXTS:
            continue
        rel = p.relative_to(PROJECT_ROOT)
        if "__pycache__" in rel.parts or rel.parts[:2] == ("source", "site"):
            continue
        name = p.name
        if name in out:
            continue
        out[name] = p
    return out


def script_out_name(script_path: Path) -> str:
    """source/X/foo.py → source/X/foo.html."""
    rel = script_path.relative_to(PROJECT_ROOT)
    return str(rel.with_suffix(".html"))


def build_source_pages(scripts: dict[str, Path]) -> int:
    """Render every script to its own HTML page with per-line anchors.

    Syntax highlighting is deliberately omitted: keep the per-line
    `id` contract simple. The doc.html template's `.src-listing` CSS
    handles formatting.
    """
    template = (TEMPLATE_DIR / "doc.html").read_text(encoding="utf-8")
    count = 0
    for path in sorted(set(scripts.values())):
        rel = path.relative_to(PROJECT_ROOT)
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
        page = page.replace(
            "<!-- INJECT_NAV -->",
            _build_nav_html(prefix=prefix, active=""))
        page = page.replace("<head>", f"<head>\n{NOINDEX}", 1)
        out = SITE_DIR / script_out_name(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(page, encoding="utf-8")
        count += 1
    return count

# ──── END source-pages snippet ────
