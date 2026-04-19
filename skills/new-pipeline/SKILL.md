---
name: new-pipeline
description: "Scaffold a new data pipeline under pipelines/ with the pipeline directory structure and required docs. Use when the user wants to create a new data processing pipeline."
user_invocable: true
---

# Scaffold a new data pipeline

Create a new pipeline repository under `pipelines/`.

## Finding the workspace root

The workspace root contains `CLAUDE.md` alongside `projects/`, `pipelines/`, `$ROOT/data_catalog/`, `research/`. If the current directory is inside a project or pipeline, search upward to find the root. Use `$ROOT` for all paths below.

## Step 1: Gather information

Ask the user:

1. **Pipeline slug** — short directory name (e.g., `brazil`, `justica`, `politica`)
2. **Purpose** — what data does this pipeline clean/process?
3. **Input data** — raw data sources (check `$ROOT/data_catalog/` for existing ones)
4. **Output** — what cleaned datasets does it produce?

## Step 2: Create the directory structure

Follow the pipeline structure from `$ROOT/research/rules/project_docs_contract.md`:

```
$ROOT/pipelines/<slug>/
  README.md
  CLAUDE.md
  .claude/
    settings.local.json
  docs/
    summary.md
    thinking.md
    todo.md
    data.md
    decisions.md
    archive.md
  source/
  build/
    .gitkeep
```

Note: pipelines do NOT have `paper/`, `talk/`, or the full set of project docs (no meetings.md, feedback.md, literature.md, institutions.md, methods.md, results.md).

## Step 3: Populate files

### CLAUDE.md

```markdown
# <Pipeline Name> Pipeline

## Purpose
<from user input>

## Input
<data sources>

## Output
<cleaned datasets produced>

## Shared code
- Uses `diarios` module for court/legal data utilities — check `$ROOT/research/meta/diarios_api.md` before writing new helpers.

## Conventions
- Follow workspace rules in `$ROOT/research/rules/workspace.md`
- Documentation follows `$ROOT/research/rules/project_docs_contract.md` (pipeline section)
- Scripts follow the Inline Audit Trail (IAT) convention in `$ROOT/research/rules/inline_audit_trail.md`
```

### .claude/settings.local.json

```json
{
  "permissions": {
    "allow": [
      "Bash(python3:*)",
      "Bash(git add:*)",
      "Bash(git commit:*)"
    ]
  }
}
```

### docs/summary.md

Populate with the pipeline's purpose, input sources, and output description.

### docs/data.md

Document both input and output datasets using the data.md format. For pipelines, this file describes both sides — what goes in and what comes out.

### docs/todo.md

```markdown
# TODOs

## Setup
- [ ] Initial pipeline structure
  - created: <today's date>
```

### Other docs/ files

Create `thinking.md`, `decisions.md`, `archive.md` with their headers and empty template sections.

### README.md

```markdown
# <Pipeline Name>

<One-line description of what this pipeline produces>

See `docs/summary.md` for details.
```

## Step 4: Initialize git

```bash
cd $ROOT/pipelines/<slug> && git init
```

Create a `.gitignore`:
```
build/
*.pyc
__pycache__/
.ipynb_checkpoints/
```

## Step 5: Register the pipeline

1. Suggest updating the pipeline listing in `$ROOT/research/rules/workspace.md`.
2. Check `$ROOT/research/meta/data_linkages.md` — note which projects will consume this pipeline's output.

## Gotchas

- Pipelines are NOT projects. Do not create `paper/`, `talk/`, `meetings.md`, `feedback.md`, `literature.md`, `institutions.md`, `methods.md`, or `results.md`.
- Pipeline `docs/data.md` documents both inputs AND outputs (unlike project data.md which only documents usage).
- Build outputs are typically gitignored — they should be regenerable from source.
- Check `$ROOT/data_catalog/` for existing metadata about the input data sources before populating data.md.
