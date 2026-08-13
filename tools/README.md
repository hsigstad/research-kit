# Tools

Workspace-shared command-line utilities consumed by skills, build
scripts, and direct CLI use. Stable interfaces; treat as research-kit's
public surface.

## Style

- **`style_lint.py`** — canonical mechanical prose linter. Single source
  of truth for the regex/heuristic style checks defined in
  `../rules/writing_style.md`. Eighteen rules covering AI-tell vocabulary,
  filler phrases, throat-clearing, editorializing, naked "this", plain-
  word violations, self-categorizing prefaces, forward references,
  hedging openers, sentence length, passive voice density, connective
  openers, stacked adjectives, synonym piling, "significantly"
  non-statistical, decimal precision, abstract first-sentence,
  and cute opening quotations.

  Consumed by:
  - `/style-check` (file-scoped, mechanical only)
  - `/style-review` (whole-document, mechanical pre-pass + LLM review)
  - `/validate-section` (section-scoped, mechanical pre-pass + LLM
    `style_prose` checks + ledger writes)

  All three skills delegate the mechanical layer here. Add new patterns
  in one place; all three pick them up.

  Usage:
  ```bash
  python3 style_lint.py <file_or_dir> [--format json] [--severity warning]
                                       [--rule <name>] [--rule <name>]
  ```

  Exits 1 if any violations exceed the severity threshold; 0 otherwise.

## Other tools in this directory

- **`workspace_root.py`** — the single workspace-root resolver. Import it;
  never re-derive the root. Anything that can run outside a Claude session
  (cron, a bare CLI invocation) has no `RESEARCH_WORKSPACE`, because only
  `hooks/run_hook.sh` exports it — and the old `$HOME/research` fallback is
  an unrelated stub on educloud, so a miss was silent. That cost two
  outages: the nightly sweep scanned zero repos and read as clean
  (2026-07-06), and `inbox_waker.py` fired every minute for a day and woke
  nobody (2026-08-13). Resolution order: `RESEARCH_WORKSPACE`, then
  `~/research`, `/workspace`, and finally this module's own tree — cron can
  strip the environment and the cwd, not `__file__`.

  ```python
  sys.path.insert(0, str(Path(__file__).resolve().parent))  # or parents[1] from hooks/
  from workspace_root import workspace
  ```

  `hooks/tests/test_workspace_root.py` checks every consumer under cron's
  environment and fails if a private copy of the resolver reappears.

- **`coverage.py`** — workspace-conventions health dashboard for a
  project. Read-only audit emitting a single-screen report on
  `artifacts.yaml` coverage and integrity, IAT presence in scripts,
  `validation.yaml` ageing, and `.run.json` dirty-commit flags. Pass
  `--detail` to list offending items, `--json` for machine output.
  Run before each `/next` session or on a schedule to catch drift.

  ```bash
  python3 research-kit/tools/coverage.py [--project PATH] [--detail] [--json]
  ```

- **`run_json.py`** — reference implementation of the per-artifact
  provenance sidecar (`research-kit/rules/run_json.md`). Each project
  copies this verbatim into `source/_run_json.py` and imports
  `write_run_json` from there.

- **`skill_links.py`** — research-kit-wide cross-reference checker.
  Walks every `research-kit/skills/**/SKILL.md` and verifies every
  `/skill`, `/skill --flag`, and `research-kit/{rules,tools,meta}/...`
  reference resolves. Catches the "I added `--status` but `/next`
  still references `--update`" drift class. Exits non-zero on broken
  refs (CI-friendly).

  ```bash
  python3 research-kit/tools/skill_links.py [--root PATH] [--detail] [--json]
  ```
