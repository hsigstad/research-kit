"""Build code/<stem>.html pages for source scripts referenced from docs.

The script-page system (load_script_index → build_script_pages →
link_script_refs) is connect's pattern. Other projects may opt in by
setting `enable_script_pages=True` on SiteConfig.
"""

from __future__ import annotations

from pathlib import Path

from .context import BuildContext
from .nav import inject_nav
from .templates import read_template
from .links.script import highlight_source, CODE_CSS


def build_script_pages(ctx: BuildContext) -> int:
    """Render each script in ctx.script_map as a code page."""
    cfg = ctx.config
    if not ctx.script_map:
        return 0
    out_dir = ctx.site_dir / "code"
    out_dir.mkdir(parents=True, exist_ok=True)
    template = read_template(cfg, "doc.html")
    for path, stem in sorted(ctx.script_map.items(), key=lambda kv: kv[1]):
        source = (ctx.project_root / path).read_text(encoding="utf-8")
        meta = (
            f'<p class="code-meta">Source: <code>{path}</code> &middot; '
            f'{len(source.splitlines())} lines &middot; '
            'read-only snapshot from the site build</p>'
        )
        backlinks = ""
        refs = ctx.script_refs.get(path, [])
        if refs:
            items = "".join(
                f'<li><a href="{href}">{title}</a></li>' for href, title in refs
            )
            backlinks = (
                '<p class="code-meta" style="margin-bottom:.35rem">'
                'Referenced by</p>'
                f'<ul class="code-refs">{items}</ul>'
            )
        content = (
            f"{CODE_CSS}\n{meta}\n{backlinks}\n{highlight_source(path, source)}"
        )
        html = template.replace("<!-- INJECT_TITLE -->", Path(path).name)
        html = html.replace("<!-- INJECT_CONTENT -->", content)
        html = inject_nav(html, ctx, prefix="../", active="")
        (out_dir / f"{stem}.html").write_text(html, encoding="utf-8")
    print(f"  code/ ({len(ctx.script_map)} script pages)")
    return len(ctx.script_map)
