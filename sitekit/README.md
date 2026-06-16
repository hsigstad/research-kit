# sitekit

Shared static-site generator for research project sites in the workspace.

Each project's `source/site/build_all.py` reduces to a ~15-line shim that
hands a `SiteConfig` to `sitekit.build_site()`. The package owns the
rendering, navigation, templates, archetype-specific sections (empirical
data pages, theoretical cases pages), and the optional connect-style
features (AN pages, cite-refs, script pages).

## Install

From a project's environment, editable-install the package:

```bash
pip install -e ../../research-kit/sitekit
```

## Minimal usage

```python
# projects/<slug>/source/site/build_all.py
from .site import config
from sitekit import build_site

if __name__ == "__main__":
    raise SystemExit(build_site(config))
```

```python
# projects/<slug>/source/site/site.py
from pathlib import Path
from sitekit import SiteConfig

config = SiteConfig(
    project_root=Path(__file__).parent.parent.parent,
    project_title="Project Name",
    paper_title="Full Paper Title",
    archetype="empirical",  # or "theoretical" / "mixed"
    paper_tex="paper.tex",
    talk_tex="talk.tex",
    doc_registry=[
        # (rel_path, title, description, category)
        ("docs/summary.md", "Summary", "...", "Reference"),
    ],
)
```

## Project-local template overrides

The package ships defaults under `sitekit/templates/`. A project can override
any template by placing a same-named file under its `source/site/templates/`:
the build resolves project first, package second.

## Hooks

Project-specific sections (e.g. serasa's `build_specs_section`,
`build_results_page`) are registered as hooks on `SiteConfig`. Each hook
receives the `BuildContext` and may return a dict to be wired into
the index.

## Archetypes

- `empirical` — data sources grid, per-dataset / per-source pages,
  descriptives, tables.
- `theoretical` — cases, briefs, multi-tex paper builder, cases index.
- `mixed` — empirical base + theoretical extras (or vice versa) via hooks.
