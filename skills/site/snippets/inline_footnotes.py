"""
Canonical helper: inline make4ht footnotes as hover tooltips.

Problem
-------
make4ht splits a paper into paper.html + paper2.html, paper3.html, ...
Footnote markers in paper.html link cross-page (`paper2.html#fn1x0`),
but build_all.py typically only ships paper.html as paper/index.html —
so those links 404.

Solution
--------
Before stripping the body out of paper.html, scan paper[0-9]*.html for
the footnote-text divs, extract each footnote body keyed by `fn_id`,
and rewrite the cross-page footnote-mark links in paper.html into
inline `<span class="fn-inline">` blocks with a `<span class="fn-tooltip">`
child. The paper.html template's CSS shows the tooltip on hover/focus.

Two parts: this Python helper, plus the matching CSS rules in
templates/paper.html (see inline_footnotes_css.html in this snippets/
dir).

Regex gotcha (2026-06-16)
-------------------------
make4ht 2024+ inserts an extra `<a id='x2-…'></a>` anchor between the
`<a id='fn1x0'>` and the `<sup>`:

    <a id='fn1x0'><a id='x2-1002x1'></a>   <sup>1</sup></a></span>

The earlier regex used `\s*<sup` which fails on this variant. Use
`.*?<sup` to be robust to either form. This file is the canonical
source — when porting `_inline_footnotes` into a project, copy from
here, not from another project that may carry the old strict regex.
"""

from __future__ import annotations

import re
from pathlib import Path


def inline_footnotes(content: str, make4ht_dir: Path) -> str:
    """Rewrite paper.html footnote-mark links into inline tooltip spans.

    Args:
        content: the HTML body extracted from `make4ht/paper.html`.
        make4ht_dir: directory containing paper.html + paper2.html, ...

    Returns:
        content with footnote-mark links replaced by `<span class="fn-inline">`
        tooltip blocks. Unmatched links are left as-is.
    """
    footnotes: dict[str, tuple[str, str]] = {}
    for fn_page in sorted(make4ht_dir.glob("paper[0-9]*.html")):
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
