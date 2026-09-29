"""Per-exhibit provenance: registry resolution, dossier pages, caption chips.

Shared sitekit module (promoted from projects/deterrence, 2026-09-29). Lets a
paper site link each table/figure to the code + inputs that produced it:

  build_exhibit_map(root)      paper/exhibits.yaml -> build/paper/exhibit_map.json
                               (recipe + reads + in-repo import chain + macros +
                               cited_in from artifacts.yaml). Doubles as a lint.
  build_dossiers(root, ...)    one HTML page per exhibit under
                               build/site/paper/exhibits/ (recipe, rendered
                               exhibit, inputs, dependency chain, verbatim code).
  inject_exhibit_chips(html,   a per-caption 'Provenance ->' chip in the rendered
                       root)   paper, linking to the dossier.

OPT-IN. Nothing here runs unless a project wires it (hook + paper_content_transform)
and ships a paper/exhibits.yaml; see SiteConfig.exhibit_registry. Zero impact on
projects that don't. The exhibit->dataset 'Frozen inputs' section is an optional
callback the project supplies (datasets_fn), so it composes with any dataset-page
mechanism (or none).
"""
from __future__ import annotations

import ast
import base64
import html as _html
import json
import re
from pathlib import Path

import yaml

try:
    from pygments import highlight
    from pygments.formatters import HtmlFormatter
    from pygments.lexers import PythonLexer, get_lexer_for_filename
    _HAVE_PYGMENTS = True
except ImportError:  # graceful: plain <pre> fallback
    _HAVE_PYGMENTS = False

CODE_REL = "../../source"          # dossier -> rendered source-code page
_LABEL_RE = re.compile(r"\\label\{((?:tab|fig):[a-zA-Z0-9:_-]+)\}")
_READS_RE = re.compile(r"""["'](data/[^"']+|build/[^"']+\.(?:csv|parquet|json|tex))["']""")
_IMPORT_ROOTS = ("source",)


# ---------------------------------------------------------------------------
# exhibit map (exhibits.yaml -> exhibit_map.json) + lint
# ---------------------------------------------------------------------------
def _paper_labels(root: Path) -> set:
    labels: set = set()
    for tex in [root / "paper" / "paper.tex", *(root / "paper" / "shared").glob("*.tex")]:
        if tex.exists():
            labels |= set(_LABEL_RE.findall(tex.read_text(encoding="utf-8")))
    return labels


def _recipe(builder: Path) -> str:
    try:
        doc = ast.get_docstring(ast.parse(builder.read_text(encoding="utf-8"))) or ""
    except (SyntaxError, ValueError):
        return ""
    return " ".join(re.split(r"\n\s*\n|\nINTENT", doc.strip(), maxsplit=1)[0].split())


def _reads(builder: Path, own_input: str) -> list:
    txt = builder.read_text(encoding="utf-8")
    own = {own_input, own_input.replace(".tex", ".json"), own_input.replace(".json", ".tex")}
    return sorted(p for p in set(_READS_RE.findall(txt)) if p not in own)


def _mod_file(root: Path, dotted: str, builder: Path) -> str | None:
    rel = Path(*dotted.split(".")).as_posix() + ".py"
    cand = root / rel
    return rel if cand.exists() and cand != builder else None


def _imports(root: Path, builder: Path) -> list:
    try:
        tree = ast.parse(builder.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    mods: set = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if a.name.split(".")[0] in _IMPORT_ROOTS and (f := _mod_file(root, a.name, builder)):
                    mods.add(f)
        elif isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] in _IMPORT_ROOTS:
            hit = False
            for a in node.names:
                if f := _mod_file(root, f"{node.module}.{a.name}", builder):
                    mods.add(f); hit = True
            if not hit and (f := _mod_file(root, node.module, builder)):
                mods.add(f)
    return sorted(mods)


def _macros_from(root: Path, builder_rel: str) -> list:
    nums = root / "paper" / "numbers.json"
    if not nums.exists():
        return []
    data = json.loads(nums.read_text(encoding="utf-8"))
    rows = data.get("macros", data) if isinstance(data, dict) else data
    return sorted(n["macro"] for n in rows if n.get("script") == builder_rel)


def _cited_in_map(root: Path) -> dict:
    art = root / "docs" / "reference" / "artifacts.yaml"
    if not art.exists():
        return {}
    doc = yaml.safe_load(art.read_text(encoding="utf-8")) or {}
    return {a["path"]: a.get("cited_in", []) for a in doc.get("artifacts", [])}


def build_exhibit_map(root: Path) -> int:
    """Resolve paper/exhibits.yaml -> build/paper/exhibit_map.json; return exit
    code (nonzero if a labelled exhibit is uncovered or a builder/input missing)."""
    registry = root / "paper" / "exhibits.yaml"
    out = root / "build" / "paper" / "exhibit_map.json"
    reg = yaml.safe_load(registry.read_text(encoding="utf-8"))["exhibits"]
    errors: list = []
    labelled = {e["label"] for e in reg if e.get("label")}
    in_paper = _paper_labels(root)
    for lab in sorted(labelled - in_paper):
        errors.append(f"registry label not found in paper: {lab}")
    for lab in sorted(in_paper - labelled):
        errors.append(f"paper label not covered by exhibits.yaml: {lab}")

    cited = _cited_in_map(root)
    result = []
    for e in reg:
        builder = root / e["builder"]
        input_path = root / e["input"]
        if not builder.exists():
            errors.append(f"builder missing: {e['builder']}")
        if not input_path.exists():
            errors.append(f"input missing: {e['input']}")
        result.append({
            "label": e.get("label"), "kind": e["kind"], "section": e.get("section", "main"),
            "caption": e.get("caption"), "input": e["input"], "input_exists": input_path.exists(),
            "builder": e["builder"], "builder_exists": builder.exists(),
            "recipe": _recipe(builder) if builder.exists() else "",
            "reads": _reads(builder, e["input"]) if builder.exists() else [],
            "imports": _imports(root, builder) if builder.exists() else [],
            "macros": _macros_from(root, e["builder"]),
            "cited_in": cited.get(e["input"], []),
        })
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"exhibits": result}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out.relative_to(root)} ({len(result)} exhibits)")
    if errors:
        import sys
        print("EXHIBIT MAP LINT — problems:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1
    print("exhibit map lint: OK")
    return 0


# ---------------------------------------------------------------------------
# dossier pages
# ---------------------------------------------------------------------------
def _slug(e: dict) -> str:
    base = e.get("label") or Path(e["input"]).stem
    return re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")


def _code_page(script_rel: str) -> str:
    return f'{CODE_REL}/{script_rel[len("source/"):].replace(".py", ".html").replace(".R", ".html")}'


def _hl(path: Path) -> str:
    src = path.read_text(encoding="utf-8")
    if not _HAVE_PYGMENTS:
        return f"<pre>{_html.escape(src)}</pre>"
    try:
        lexer = get_lexer_for_filename(path.name)
    except Exception:
        lexer = PythonLexer()
    return highlight(src, lexer, HtmlFormatter())


def _rendered_exhibit(root: Path, e: dict) -> str:
    if e["kind"] == "figure":
        png = root / e["input"].replace(".pdf", ".png")
        if png.exists():
            b64 = base64.b64encode(png.read_bytes()).decode()
            return (f'<img class="exhibit-img" alt="{_html.escape(e.get("caption") or "")}" '
                    f'src="data:image/png;base64,{b64}">')
    tex = root / e["input"]
    if tex.exists():
        return f'<pre class="tex">{_html.escape(tex.read_text(encoding="utf-8"))}</pre>'
    return '<p class="muted">(exhibit artifact not built)</p>'


def _run_line(root: Path, e: dict) -> str:
    rj = root / (e["input"] + ".run.json")
    if not rj.exists():
        return ""
    try:
        d = json.loads(rj.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return ""
    commit = (d.get("commit") or "")[:9] or "—"
    dirty = " (dirty)" if d.get("commit_dirty") else ""
    when = (d.get("ran_at") or "")[:10]
    return f'<p class="muted">Built from commit <code>{commit}</code>{dirty}{" on " + when if when else ""}</p>'


def _li_links(items, href_fn) -> str:
    if not items:
        return '<span class="muted">none</span>'
    return "".join(f'<li><a href="{href_fn(i)}"><code>{_html.escape(i)}</code></a></li>' for i in items)


def _li_plain(items) -> str:
    if not items:
        return '<span class="muted">none</span>'
    return "".join(f'<li><code>{_html.escape(i)}</code></li>' for i in items)


_CSS = HtmlFormatter().get_style_defs(".highlight") if _HAVE_PYGMENTS else ""


def _dossier_html(root: Path, e: dict, datasets: list | None) -> str:
    builder = root / e["builder"]
    kind = "Table" if e["kind"] == "table" else "Figure"
    title = f'{kind}: {e.get("caption") or Path(e["input"]).stem}'
    code = _hl(builder) if builder.exists() else "<p>(builder missing)</p>"
    ds = ("".join(f'<li><a href="{href}">{_html.escape(t)}</a></li>' for t, href in datasets)
          if datasets else '<span class="muted">see dependencies</span>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_html.escape(title)}</title>
<style>
 body{{max-width:56rem;margin:2rem auto;padding:0 1rem;font:16px/1.6 system-ui,sans-serif;color:#1a1a1a}}
 h1{{font-size:1.4rem}} h2{{font-size:1.05rem;margin-top:1.8rem;border-bottom:1px solid #e5e5e5;padding-bottom:.2rem}}
 .exhibit-img{{max-width:100%;border:1px solid #e5e5e5;border-radius:6px}}
 pre.tex{{background:#f6f7f9;border:1px solid #e5e5e5;border-radius:6px;padding:.8em;overflow-x:auto;font-size:.85em}}
 ul{{margin:.3rem 0 .3rem 1.2rem;padding:0}} code{{background:#f2f3f5;padding:.05em .3em;border-radius:3px;font-size:.9em}}
 .muted{{color:#888}} .recipe{{background:#f6f7f9;border-left:3px solid #5e3c99;padding:.6em .9em;border-radius:0 6px 6px 0}}
 .highlight{{background:#f8f8f8;border:1px solid #e5e5e5;border-radius:6px;padding:.6em;overflow-x:auto;font-size:.82em}}
 {_CSS}
</style></head><body>
<p><a href="index.html">&larr; all exhibits</a></p>
<h1>{_html.escape(title)}</h1>
<p class="muted">{e['section'].upper()} &middot; produced by
   <a href="{_code_page(e['builder'])}"><code>{_html.escape(e['builder'])}</code></a>
   &rarr; <code>{_html.escape(e['input'])}</code></p>
{_run_line(root, e)}
<h2>What it shows</h2><div class="recipe">{_html.escape(e.get('recipe') or '(no recipe)')}</div>
<h2>The exhibit</h2>{_rendered_exhibit(root, e)}
<h2>Cited in</h2><ul>{_li_plain(e.get('cited_in', []))}</ul>
<h2>Frozen inputs it stands on</h2><ul>{ds}</ul>
<h2>Directly reads</h2><ul>{_li_plain(e.get('reads', []))}</ul>
<h2>Depends on (in-repo)</h2><ul>{_li_links(e.get('imports', []), _code_page)}</ul>
<h2>Paper macros it feeds</h2><ul>{_li_plain(e.get('macros', []))}</ul>
<h2>Builder code &mdash; <a href="{_code_page(e['builder'])}">full page &rarr;</a></h2>
{code}
</body></html>
"""


def build_dossiers(root: Path, datasets_fn=None) -> int:
    """Render build/site/paper/exhibits/<slug>.html + index from exhibit_map.json.
    datasets_fn(exhibits) -> {slug: [(title, href)]} is an optional project hook
    for the 'Frozen inputs' section."""
    mp = root / "build" / "paper" / "exhibit_map.json"
    if not mp.exists():
        print("skip exhibit dossiers: exhibit_map.json absent")
        return 0
    exhibits = json.loads(mp.read_text())["exhibits"]
    ex_ds = {}
    if datasets_fn is not None:
        try:
            ex_ds = datasets_fn() or {}
        except Exception:
            ex_ds = {}
    out_dir = root / "build" / "site" / "paper" / "exhibits"
    out_dir.mkdir(parents=True, exist_ok=True)
    for e in exhibits:
        (out_dir / f"{_slug(e)}.html").write_text(
            _dossier_html(root, e, ex_ds.get(_slug(e))), encoding="utf-8")
    rows = "".join(
        f'<tr><td><a href="{_slug(e)}.html">{_html.escape(e.get("caption") or Path(e["input"]).stem)}</a></td>'
        f'<td>{e["kind"]}</td><td>{e["section"]}</td>'
        f'<td><a href="{_code_page(e["builder"])}"><code>{_html.escape(e["builder"])}</code></a></td></tr>'
        for e in exhibits)
    (out_dir / "index.html").write_text(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Paper exhibits — provenance</title>
<style>body{{max-width:60rem;margin:2rem auto;padding:0 1rem;font:16px/1.6 system-ui,sans-serif}}
table{{border-collapse:collapse;width:100%}} th,td{{text-align:left;padding:.4em .6em;border-bottom:1px solid #eee;vertical-align:top}}
code{{background:#f2f3f5;padding:.05em .3em;border-radius:3px;font-size:.85em}}</style></head><body>
<h1>Paper exhibits — provenance</h1>
<p>Each exhibit links to a dossier: recipe, rendered result, data it reads, code
dependencies, and the verbatim builder.</p>
<table><thead><tr><th>Exhibit</th><th>Kind</th><th>Section</th><th>Reproduced by</th></tr></thead>
<tbody>{rows}</tbody></table></body></html>""", encoding="utf-8")
    print(f"wrote {len(exhibits)} dossiers + index to {out_dir.relative_to(root)}")
    return len(exhibits)


# ---------------------------------------------------------------------------
# caption chips
# ---------------------------------------------------------------------------
def _norm(s: str) -> str:
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"&[a-z]+;|&#\d+;", " ", s)
    s = re.sub(r"[^a-z0-9 ]+", " ", s.lower())
    return re.sub(r"\s+", " ", s)


def _cpl(a: str, b: str) -> int:
    n = 0
    for x, y in zip(a, b):
        if x != y:
            break
        n += 1
    return n


_CAPTION_RE = re.compile(r"(<figcaption class='caption'>)(.*?)(</figcaption>)", re.DOTALL)


def inject_exhibit_chips(content: str, root: Path, min_prefix: int = 20) -> str:
    """Inject a 'Provenance ->' chip into each exhibit's <figcaption>, matched to a
    registry exhibit by longest shared normalized-caption prefix."""
    mp = root / "build" / "paper" / "exhibit_map.json"
    if not mp.exists():
        return content
    exhibits = json.loads(mp.read_text())["exhibits"]
    keyed = [(_norm(e["caption"]), e) for e in exhibits if e.get("caption")]

    def repl(m: re.Match) -> str:
        if "exh-chip" in m.group(2):
            return m.group(0)
        text = re.sub(r"^\s*(figure|table)\s*s?\d+\s*", "", _norm(m.group(2)).strip())
        best, best_len = None, 0
        for cap, e in keyed:
            pl = _cpl(text, cap.strip())
            if pl > best_len:
                best, best_len = e, pl
        if best is None or best_len < min_prefix:
            return m.group(0)
        chip = (f"<span class='exh-chip'> [<a href='exhibits/{_slug(best)}.html' "
                f"title='code + inputs that produced this exhibit'>Provenance &rarr;</a>]</span>")
        return m.group(1) + m.group(2) + chip + m.group(3)

    return _CAPTION_RE.sub(repl, content)
