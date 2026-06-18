"""AN-NNN auto-linking and finding-tag injection."""

from __future__ import annotations

import html as _html
import re
from collections import defaultdict
from pathlib import Path

from ..context import BuildContext


_FINDING_TAG_RE = re.compile(r"[\U0001F7E2\U0001F7E1\U0001F534]")


def load_an_map(project_root: Path) -> dict[str, str]:
    """Map AN-NNN tokens to the stem of their analysis doc under docs/analyses/."""
    out: dict[str, str] = {}
    analyses_dir = project_root / "docs" / "analyses"
    if analyses_dir.is_dir():
        for p in sorted(analyses_dir.glob("an-*.md")):
            m = re.match(r"an-(\d+)", p.stem)
            if m:
                out[f"AN-{int(m.group(1)):03d}"] = p.stem
    return out


def _parse_an_frontmatter(text: str) -> dict[str, str]:
    """Extract top-level scalar fields from an AN .md frontmatter block.

    Only fields used by the supporting-analyses panel are captured — and only
    top-level scalars (not nested keys like `design:`). Quotes are stripped.
    """
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        # Only top-level keys (no leading whitespace) — skips `design:` children.
        m2 = re.match(r"^([a-zA-Z_][a-zA-Z0-9_]*):\s*(.*)$", line)
        if not m2:
            continue
        key, val = m2.group(1), m2.group(2).strip()
        # Strip surrounding quotes (YAML quoted scalars).
        if (val.startswith('"') and val.endswith('"')) or \
           (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        out[key] = val
    return out


def load_an_by_hypothesis(project_root: Path) -> dict[str, list[dict]]:
    """Group AN-page metadata by their `hypothesis:` frontmatter slug.

    Each entry is a dict with id, stem, headline, question, type, status,
    confidence. Used by `render_supporting_analyses_section` to inject a
    summary list onto hypothesis pages.
    """
    out: dict[str, list[dict]] = defaultdict(list)
    analyses_dir = project_root / "docs" / "analyses"
    if not analyses_dir.is_dir():
        return dict(out)
    for p in sorted(analyses_dir.glob("an-*.md")):
        fm = _parse_an_frontmatter(p.read_text(encoding="utf-8"))
        hyp = fm.get("hypothesis", "")
        if not hyp:
            continue
        out[hyp].append({
            "id": fm.get("id", p.stem),
            "stem": p.stem,
            "headline": fm.get("headline", ""),
            "question": fm.get("question", ""),
            "type": fm.get("type", ""),
            "status": fm.get("status", ""),
            "confidence": fm.get("confidence", ""),
        })
    return dict(out)


_CONF_ORDER = {"green": 0, "yellow": 1, "red": 2, "pending": 3}
_STATUS_ORDER = {"interpreted": 0, "exported": 1, "queued": 2}


def _render_an_entries(entries: list[dict], prefix: str) -> str:
    """Shared row renderer used by the hypothesis- and finding-page sections."""
    rows: list[str] = []
    for e in entries:
        an_id = (e["id"] or "").upper()
        if not an_id.startswith("AN-"):
            an_id = f"AN-{an_id}" if an_id else e["stem"].upper()
        conf = e["confidence"]
        conf_cls = {"green": "conf-green", "yellow": "conf-yellow",
                    "red": "conf-red"}.get(conf, "conf-pending")
        conf_chip = (f'<span class="conf-chip {conf_cls}">{_html.escape(conf)}</span>'
                     if conf else "")
        type_chip = (f'<span class="an-type-chip">{_html.escape(e["type"])}</span>'
                     if e["type"] else "")
        summary = _html.escape(e["headline"] or e["question"] or "")
        rows.append(
            '<div class="supporting-an">'
            '<div class="supporting-an-head">'
            f'<a class="supporting-an-id" href="{prefix}analyses/'
            f'{_html.escape(e["stem"])}.html">{_html.escape(an_id)}</a> '
            f'{conf_chip} {type_chip}'
            '</div>'
            f'<p class="an-headline">{summary}</p>'
            '</div>'
        )
    return "".join(rows)


def _load_an_index_by_stem(project_root: Path) -> dict[str, dict]:
    """Map AN stem → frontmatter dict (cached source for cited-analyses)."""
    out: dict[str, dict] = {}
    analyses_dir = project_root / "docs" / "analyses"
    if not analyses_dir.is_dir():
        return out
    for p in sorted(analyses_dir.glob("an-*.md")):
        fm = _parse_an_frontmatter(p.read_text(encoding="utf-8"))
        out[p.stem] = {
            "id": fm.get("id", p.stem),
            "stem": p.stem,
            "headline": fm.get("headline", ""),
            "question": fm.get("question", ""),
            "type": fm.get("type", ""),
            "status": fm.get("status", ""),
            "confidence": fm.get("confidence", ""),
        }
    return out


def render_cited_analyses_section(
    body_html_or_md: str, ctx: BuildContext, prefix: str = "../",
) -> str:
    """Render a 'Cited analyses' section listing every AN mentioned in the
    page body, in order of first appearance, deduped. Returns "" if none.

    Pulls each AN's `headline:` from its frontmatter so the section is a
    standalone summary view of the curated AN references in the page.
    """
    if not ctx.an_map or not ctx.an_index:
        return ""
    seen: set[str] = set()
    ordered_stems: list[str] = []
    for m in re.finditer(r"\bAN-(\d+)\b", body_html_or_md):
        key = f"AN-{int(m.group(1)):03d}"
        stem = ctx.an_map.get(key)
        if not stem or stem in seen:
            continue
        seen.add(stem)
        ordered_stems.append(stem)
    if not ordered_stems:
        return ""
    entries = [ctx.an_index[s] for s in ordered_stems if s in ctx.an_index]
    if not entries:
        return ""
    return (
        '<h2 id="cited-analyses">Cited analyses</h2>'
        '<div class="supporting-an-list">'
        + _render_an_entries(entries, prefix)
        + '</div>'
    )


def render_supporting_analyses_section(
    slug: str, ctx: BuildContext, prefix: str = "../",
) -> str:
    """Render '## Supporting analyses' for a hypothesis page.

    Lists every AN whose frontmatter `hypothesis:` matches `slug`, sorted by
    confidence (green → yellow → red → pending), then status (interpreted →
    exported → queued), then AN id. Each entry shows the AN id (linking to
    the AN page), confidence + type chips, and the AN's `headline:`.

    Returns "" if no ANs are tagged with this slug.
    """
    entries = ctx.an_by_hypothesis.get(slug, [])
    if not entries:
        return ""

    def _key(e: dict) -> tuple:
        return (_CONF_ORDER.get(e["confidence"], 4),
                _STATUS_ORDER.get(e["status"], 4),
                e["stem"])

    return (
        '<h2 id="supporting-analyses">Supporting analyses</h2>'
        '<div class="supporting-an-list">'
        + _render_an_entries(sorted(entries, key=_key), prefix)
        + '</div>'
    )


def scan_finding_tags(project_root: Path) -> dict[str, str]:
    """Map docs/findings/<slug>.md → first traffic-light emoji in the page body."""
    src_dir = project_root / "docs" / "findings"
    out: dict[str, str] = {}
    if not src_dir.is_dir():
        return out
    for path in sorted(src_dir.glob("*.md")):
        if path.stem == "index":
            continue
        m = _FINDING_TAG_RE.search(path.read_text(encoding="utf-8"))
        if m:
            out[path.stem] = m.group(0)
    return out


def inject_finding_tags(html: str, tags: dict[str, str]) -> str:
    """Prepend each finding's traffic-light tag to its overview bullet."""
    pat = re.compile(r'<li>(<a href="([^"/]+)\.html">)')
    def repl(m: re.Match) -> str:
        slug = m.group(2)
        if slug not in tags:
            return m.group(0)
        return f'<li>{tags[slug]} {m.group(1)}'
    return pat.sub(repl, html)


def link_an_refs(html: str, ctx: BuildContext, current_stem: str = "",
                 prefix: str = "../") -> str:
    """Auto-link bare AN-NNN tokens to their analysis page under analyses/.

    `prefix` is the relative path from the current page to the site root.
    Top-level docs and doc_subdir pages are at depth 1 (prefix="../");
    folder-mode pages (docs/<folder>/page.html) are at depth 2 (prefix="../../").
    """
    if not ctx.an_map:
        return html
    pattern = re.compile(r'(<a\b[^>]*>.*?</a>)|(\bAN-(\d+)\b)', re.DOTALL)

    def _replacer(m: re.Match) -> str:
        if m.group(1):
            return m.group(1)
        token, num = m.group(2), m.group(3)
        stem = ctx.an_map.get(f"AN-{int(num):03d}")
        if not stem or stem == current_stem:
            return token
        return f'<a href="{prefix}analyses/{stem}.html">{token}</a>'

    return pattern.sub(_replacer, html)
