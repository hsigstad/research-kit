---
name: idea
description: "Create a new research idea with YAML frontmatter and add it to ideas/index.md. Use when the user wants to record a new research idea."
user_invocable: true
---

# New Research Idea

Create a research idea file with proper frontmatter and register it in the index.

## Finding the workspace root

The workspace root contains `CLAUDE.md` alongside `projects/`, `pipelines/`, `ideas/`, `research/`. If the current directory is inside a project or pipeline, search upward to find the root. Use `$ROOT` for all paths below.

## Step 1: Gather information

Ask the user (if not already provided):

1. **Title** — descriptive name for the idea
2. **Rank** — A (high priority), B (medium), C (low), or null (unranked)
3. **Tags** — 2-3 topic tags (check existing tags in `$ROOT/ideas/index.md` for consistency)
4. **Content** — the idea itself (can be brief)

Optionally ask:
- **Related project** — if connected to an existing project under `projects/`
- **Related ideas** — if it connects to existing ideas (check `$ROOT/ideas/index.md`)

## Step 2: Create the idea file

Derive a slug from the title (lowercase, hyphens, e.g., `optimal-appeals-system.md`).

Write `$ROOT/ideas/<slug>.md`:

```markdown
---
title: <Title>
rank: <A/B/C or null>
status: idea
tags: [<tag1>, <tag2>]
related_project: <projects/xxx or null>
last_updated: <today's date>
---

<Content — the idea description, motivation, possible approaches, etc.>
```

## Step 3: Update the index

Add a row to the appropriate table in `$ROOT/ideas/index.md`:

- **Ranked ideas table** (if rank is A, B, or C) — insert in rank order, then alphabetically within rank:
  ```
  | <rank> | [<title>](<slug>.md) | idea | <tag1>, <tag2> |
  ```

- **Unranked ideas table** (if rank is null):
  ```
  | [<title>](<slug>.md) | idea | <tag1>, <tag2> |
  ```

## Step 4: Suggest connections

After creating the idea, briefly check:
- `$ROOT/ideas/index.md` for related existing ideas (by tag overlap or topic)
- `$ROOT/research/meta/research_map.md` for connections to existing projects
- Mention any connections to the user but don't modify other files.

## Promotion to a folder (proto-project structure)

New ideas always start as flat `<slug>.md` files. When an idea
accumulates more than its description — literature notes, evaluation
documents, design notes, lit search artifacts — promote it to a
folder. The promoted layout is:

```
ideas/<slug>/
  summary.md       ← was <slug>.md, with frontmatter
  synthesis.md     ← literature read, if any
  evaluation.md    ← assessment as policy/theory
  todo.md          ← next steps, decision rule, time budget
  design.md        ← detailed design notes
  paper.tex        ← paper sketch once idea has crystallized
  references.bib   ← bibliography for paper.tex
  literature/      ← lit search artifacts (queries.json, candidates.json, etc.)
```

To promote a flat idea to a folder:

1. Create `ideas/<slug>/`
2. Move `<slug>.md` → `<slug>/summary.md`
3. Move any related material (e.g., from `ideas/literature/<slug>/`)
   into the new folder
4. Update the index link from `<slug>.md` to `<slug>/summary.md`
5. Update any internal links inside `summary.md` that referenced
   the old paths

The `/idea` skill itself only creates flat files. Promotion is a
manual step taken when an idea has clearly outgrown a single document.

## Gotchas

- Use existing tags where possible. Check `$ROOT/ideas/index.md` for the tag vocabulary already in use before inventing new tags.
- The slug should match the title closely — look at existing files for the naming convention (e.g., `effects-of-courts-on-corruption.md`).
- Status is always `idea` for new ideas. Other values (`exploring`, `shelved`, `project`) are set later.
- For small notes that don't warrant their own file, suggest adding to an existing topic collection in `$ROOT/ideas/topics/` instead.
- If the idea is clearly connected to an existing idea, mention it but don't merge them.
- If the user is recording an idea that already has substantial content (literature notes, evaluation, etc.), consider creating it directly as a folder instead of a flat file.
