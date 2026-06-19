"""Extra link rewriters that depend on shared workspace resources
outside the project tree — currently:

- `link_legal_refs`: backtick legal citations (`CPC.144.§3`, `LE.33.IV`)
  → tooltip-bearing chip linking to the brazil-institutions law page.
  Requires the `cite.py` resolver and `artigos.db` from the shared
  brazil-institutions repo. Gracefully no-ops if either is missing.
- `link_concept_refs`: `I:slug` tokens → canonical concept page on
  brazil-institutions. (Not implemented yet.)

These live in a separate module from `sitekit.links` because they
import from workspace-relative paths (`research/institutions/brazil/`)
and we want the import lazy so projects without those deps don't pay
the resolver-init cost on every build.
"""

from __future__ import annotations

import html as _html_lib
import os
import re
import sys
from pathlib import Path

from .context import BuildContext


_CITE_MOD = None
_CITE_MOD_TRIED = False
_LEGAL_TEXT_CACHE: dict[str, str] = {}


def _load_legal_resolver(workspace_root: Path):
    """Locate and import the brazil-institutions cite.py module.

    Idempotent; returns the module (or None) and caches the result so
    the resolver init runs once per build.
    """
    global _CITE_MOD, _CITE_MOD_TRIED
    if _CITE_MOD_TRIED:
        return _CITE_MOD
    _CITE_MOD_TRIED = True

    cite_dir = workspace_root / "research" / "institutions" / "brazil" / "tools" / "leis_artigos"
    if not cite_dir.is_dir():
        return None
    db = workspace_root / "data" / "lei" / "artigos.db"
    if db.is_file():
        os.environ.setdefault("INSTITUTIONS_DB", str(db))
    if str(cite_dir) not in sys.path:
        sys.path.insert(0, str(cite_dir))
    try:
        import cite as _cite_mod
    except Exception:
        return None
    _CITE_MOD = _cite_mod
    return _cite_mod


def _resolve_text(cite_mod, content: str) -> str:
    """Look up the verbatim statutory text for a backtick legal-citation
    token. Returns "" on any failure — callers leave the original chip
    untouched in that case."""
    if content in _LEGAL_TEXT_CACHE:
        return _LEGAL_TEXT_CACHE[content]
    text = ""
    try:
        parsed = cite_mod.parse(content)
        rows = cite_mod.resolve(parsed)
        parts = []
        for r in rows[:3]:
            keys = r.keys() if hasattr(r, "keys") else ()
            t = r["texto"] if "texto" in keys else ""
            if t:
                parts.append(t[:300])
        text = " | ".join(parts)
    except Exception:
        text = ""
    _LEGAL_TEXT_CACHE[content] = text
    return text


def link_legal_refs(html: str, ctx: BuildContext) -> str:
    """Resolve backtick legal citations such as `LE.33.IV` or `CPC.144.§3`.

    Backtick spans in the markdown render as `<code>…</code>`; those
    that parse as a legal citation AND resolve to article text become
    an `<a class="legal-cite">` link whose `title` attribute carries
    the verbatim statutory text (browser-native hover tooltip), and
    whose href points at the law's page on the brazil-institutions
    site. Code spans that don't parse as citations, or that parse but
    don't resolve to article text, are left as plain `<code>`.
    """
    cfg = ctx.config
    cite_mod = _load_legal_resolver(cfg.project_root.parent.parent)
    if cite_mod is None:
        return html

    base_url = cfg.brazil_institutions_url.rstrip("/") + "/"

    def _replacer(m: re.Match) -> str:
        content = m.group(1)
        try:
            parsed = cite_mod.parse(content)
        except Exception:
            return m.group(0)
        text = _resolve_text(cite_mod, content)
        if not text:
            return m.group(0)
        ident = getattr(parsed, "identifier", "")
        if not ident:
            return m.group(0)
        anchor = content.replace(".", "-").replace("§", "p")
        href = f"{base_url}laws/{ident}.html"
        if anchor != ident:
            href += f"#{anchor}"
        return (
            f'<a class="legal-cite" href="{href}" '
            f'title="{_html_lib.escape(text, quote=True)}">'
            f'{_html_lib.escape(content)}</a>'
        )

    return re.sub(r"<code>([^<]+)</code>", _replacer, html)


def link_concept_refs(html: str, ctx: BuildContext) -> str:
    """Placeholder — concept-ref linking is connect-specific for now."""
    return html
