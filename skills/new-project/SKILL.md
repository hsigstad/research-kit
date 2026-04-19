---
name: new-project
description: "Scaffold a new research project from materials the user has placed in a folder under projects/. Reads existing files to extract context instead of asking questions. Use when the user wants to create a new research project."
user_invocable: true
---

# Scaffold a new research project

You are creating a new research project repository under `projects/`.

## Finding the workspace root

The workspace root contains `CLAUDE.md` alongside `projects/`, `pipelines/`, `$ROOT/data_catalog/`, `research/`. If the current directory is inside a project or pipeline, search upward to find the root. Use `$ROOT` for all paths below.

## Step 1: Identify the project folder and read existing materials

The user has already created a folder under `projects/<slug>/` and may have placed materials in it (PDFs, notes, descriptions, data files, drafts, etc.).

1. **Infer the slug** from the folder name. If the skill was invoked with an argument, use that as the slug. Otherwise, look for recently created folders under `projects/` that lack the canonical structure (no `docs/` directory).
2. **Read every file** in the project folder. These are the user's seed materials — project descriptions, research proposals, paper drafts, notes, data documentation, etc.
3. **Extract context** from these materials:
   - Research question and motivation
   - Current focus / what to work on first
   - Methods and identification strategy
   - Data sources
   - Relevant literature
   - Institutional background
   - Any other information that maps to the docs/ files
4. **Check workspace context** for connections:
   - `$ROOT/research/meta/data_linkages.md` and `$ROOT/data_catalog/` for existing datasets
   - `$ROOT/research/meta/variable_dictionary.md` for known variables
   - `$ROOT/research/meta/research_map.md` for related projects
   - `$ROOT/ideas/` for an idea entry that originated this project

**Only ask questions if** critical information cannot be inferred from the materials and workspace context. If you do need to ask, ask at most one or two targeted questions — not a full interview.

## Step 2: Create the directory structure

Follow the canonical structure from `$ROOT/research/rules/project_docs_contract.md`. **Do not overwrite any files the user already placed in the folder.** Create only what is missing.

```
$ROOT/projects/<slug>/
  README.md
  CLAUDE.md
  .claude/
    settings.local.json
  docs/
    summary.md
    thinking.md
    todo.md
    done.md
    meetings.md
    feedback.md
    literature.md
    institutions.md
    data.md
    methods.md
    decisions.md
  source/
  build/
    .gitkeep
  paper/
    tables/
    figures/
    references.bib
  talk/          # create only if user requests
  references/    # create only if user requests
```

## Step 3: Populate files

Populate docs/ files using context extracted from the user's materials. The more the user provided, the richer the initial documentation should be. Files for which no relevant information was found get their header and empty template sections only.

### CLAUDE.md

Follow the pattern of existing projects (see any `$ROOT/projects/*/CLAUDE.md` for examples):

```markdown
# <slug>

Read `docs/summary.md` and `docs/todo.md` (if available) before making changes.

**Current focus:** <inferred from materials>

**Identification:** <inferred from materials, or omit if unknown>

**Shared code:** Use `diarios` for court parsing and cleaning. Do not modify `diarios` without asking.

**Data policy:** Never read raw data files. Dataset metadata is in `../../data_catalog/`.
```

Adapt sections based on what the materials actually contain. Don't include sections that have no content.

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

Add domain-specific `WebFetch` permissions if the materials mention specific data sources or websites.

### docs/summary.md

Populate with research question, motivation, and conceptual framework extracted from the user's materials. Use the format from `project_docs_contract.md`.

### docs/todo.md

```markdown
# TODOs

## Setup
- [ ] Initial data exploration
  - created: <today's date>

## <topic from current focus>
- [ ] <first task inferred from materials>
  - created: <today's date>
```

### Other docs/ files

- **data.md** — populate if the materials describe datasets
- **methods.md** — populate if the materials describe identification strategy or methods
- **literature.md** — populate if the materials cite papers
- **institutions.md** — populate if the materials describe institutional context
- **thinking.md** — place any speculative or exploratory content from the materials here
- Remaining files: create with header and empty template sections per the contract formats in `project_docs_contract.md` section 6.

### README.md

```markdown
# <Project Title>

<One-line research question>

See `docs/summary.md` for details.
```

## Step 4: Handle the user's seed materials

After scaffolding, the user's original files are still in the project folder. Ask the user whether to:
- Move them to a subfolder (e.g., `references/` or `docs/notes/`)
- Leave them where they are
- Delete them (now that their content has been absorbed into docs/)

## Step 5: Register the project

1. Check `$ROOT/research/rules/workspace.md` — note the new project in the `projects/` listing if the user wants to update it.
2. Check `$ROOT/research/meta/research_map.md` — suggest where it fits in the project clusters.
3. If the project originated from an idea in `$ROOT/ideas/`, update the idea's frontmatter (`status: project`, `related_project: $ROOT/projects/<slug>`).
4. Suggest creating a project brief in `$ROOT/research/project_briefs/`.

## Step 6: Initialize git

```bash
cd $ROOT/projects/<slug> && git init
```

Create a `.gitignore`:
```
build/
*.pyc
__pycache__/
.ipynb_checkpoints/
```

## Gotchas

- **Never overwrite files the user placed in the folder.** The user's materials are the source of truth.
- Do NOT create optional docs files (theory.md, hypotheses.md, results.md, etc.) unless the user asks or the materials clearly warrant them.
- Do NOT create `talk/` or `references/` directories unless requested.
- Pipeline repos are different — they have fewer docs files and no `paper/`. If the user actually wants a pipeline, tell them and use the pipeline structure from the contract.
- Always use today's date (from system context) for created dates.
- Check `$ROOT/research/meta/variable_dictionary.md` and `$ROOT/research/meta/data_linkages.md` before populating data.md — the dataset may already be documented.
