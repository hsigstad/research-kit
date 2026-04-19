# research-kit

Shared infrastructure for AI-assisted research workflows. Pulled out of a
larger private workspace so collaborators (and anyone else) can use the
parts that aren't tied to specific projects or data.

## Contents

- **`skills/`** — Claude Code skill definitions (slash commands) for
  research tasks: literature search, data catalog lookup, news collection,
  meeting scheduling, project scaffolding, session handoff, etc. Each
  skill is a directory with a `SKILL.md` file. Symlink into
  `~/.claude/skills/<name>` to install.
- **`rules/`** — Generic conventions:
  - `inline_audit_trail.md` — code documentation standard (`INTENT`,
    `REASONING`, `ASSUMES`, etc.).
  - `project_docs_contract.md` — what each `docs/*.md` file is for and
    how to use it.
- **`tools/`** — Standalone scripts:
  - `literature_search.py` — Semantic Scholar + OpenAlex search, OA PDF
    fetcher, citation graph helper.
  - `package_workflows.sh` — bundles the workflow docs into a shareable
    zip.
- **`meta/`** — Methodology and setup docs:
  - `ai_research_workflow.md` — how to use AI through the stages of a
    research project without losing credibility.
  - `claude_code_workflows.md` — how the broader workspace is set up.
  - `claude_code_sandbox.md` — running Claude Code without permission
    prompts safely.
  - `diarios_api.md` — API summary for the
    [`diarios`](https://github.com/hsigstad/diarios) Python package.
- **`docker/claude-sandbox/`** — Containerized Claude Code sandbox
  (Dockerfile + Apptainer/Singularity definition + run scripts).

## Companion repos

- [`diarios`](https://github.com/hsigstad/diarios) — Brazilian
  official-diary parsing.
- [`llmkit`](https://github.com/hsigstad/llmkit) — LLM extraction toolkit
  (caching, validation, audit).
- [`newsbr`](https://github.com/hsigstad/newsbr) — Brazilian news
  collection (used by the `/anecdotes` skill).
- [`brazil-institutions`](https://github.com/hsigstad/brazil-institutions)
  — institutional reference for Brazilian legal/political research (used
  by the `/institutions` skill).

## Notes for users

Some skills assume a workspace layout (`projects/<slug>/docs/`,
`pipelines/<slug>/`, etc.) described in `meta/claude_code_workflows.md`.
A few contain personal paths or repo names you'll want to adapt to your
setup.

## License

MIT — see `LICENSE`.
