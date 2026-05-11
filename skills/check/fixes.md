# Fix templates per finding code

Reference for the `/check docs --fix` (and `/check --fix`) interactive flow.
For each finding code, this lists the default fix and any alternatives.
"Default" = alternative `a`.

If a finding's fix is "manual" (no auto-fix), do not include it in the numbered
proposal list — surface separately as "manual review" at the end.

---

## doc.missing

Required file is absent.

- **a (default)**: Create the file with the canonical heading template from
  `research-kit/rules/project_docs_contract.md` §6 for that file.
  - `done.md` → `# Done\n\nCompleted tasks, moved from \`todo.md\`.\n`
  - `todo.md` → `# TODOs\n\n`
  - `feedback.md` → `# Feedback\n\n`
  - others → minimal `# <Title>\n\n`

No alternatives.

## doc.unallowed

File at `docs/` root is not in the canonical allowlist.

If the filename is a typo of a canonical file (e.g., `todos.md` for `todo.md`):
- **a (default)**: Rename to canonical name (with `git mv`).
  - If the canonical file already exists, abort the fix and surface as manual.

If the filename ends in `~` or `.bak` or `.swp`:
- **a (default)**: Delete (backup/editor artifact).

Otherwise (genuine non-canonical content):
- **a (default)**: Move to `docs/notes/<name>` (with `git mv`).
- **b**: Move to `docs/briefs/<name>` (if narrative content).
- **c**: Move to `docs/reference/<name>` (if structured lookup material).
- **d**: Add `<name>` to the canonical optional list in
  `research-kit/rules/project_docs_contract.md` §4 and §5 (requires defining a
  semantic role — surface for user input on what role).
- **e**: Delete.

When generating the proposal, look at the first ~30 lines of the file to
choose a sensible default among a/b/c. Narrative prose → `b`; tables/lists →
`c`; otherwise `a`.

## doc.subfolder.unknown

Subfolder under `docs/` is not in the canonical allowlist.

- **a (default)**: Rename to a canonical name (`reference/`, `notes/`, or
  `briefs/`) — pick based on content.
- **b**: Move all files inside up one level into a canonical folder.
- **c**: Add the subfolder name to the allowed list in
  `research-kit/tools/check_docs.py` (`ALLOWED_DOC_SUBFOLDERS`).

## todo.completed

`[x]` line in `todo.md`. Move to `done.md`.

- **a (default)**: Move the line and its sub-bullets to `done.md` under a
  `## Migrated YYYY-MM-DD` heading. Preserve the line verbatim. Drop a
  `completed: <today>` sub-bullet.

No alternatives.

## done.uncompleted

`[ ]` line in `done.md`. Move to `todo.md`.

- **a (default)**: Move the line and its sub-bullets to `todo.md` under
  `## Migrated YYYY-MM-DD`.

No alternatives.

## thinking.missing-section

`thinking.md` is missing one of the six required H2 sections.

- **a (default)**: Append the missing H2 heading at the end of the file with
  no body. (Project authors rarely populate sections in advance — the empty
  heading just signals where future content goes.)
- **b**: Skip this fix (don't enforce strict template). Surface as info only.

## paper.misplaced-output

Deprecated — no longer emitted. Script outputs always live in `build/`;
`paper/` is hand-authored content only. See workspace.md §"Paper and
outputs".

## source.no-output (build artifact)

`info` level — typically just means `build/` isn't materialized. Skip.

## source.no-build-dir

`info` level — same. Skip.

## source.layer.noncanonical

`info` level — project-specific source layer (e.g., `source/scrape/`,
`source/talk/`). The contract explicitly allows project-specific folders.
Skip — no fix needed.

## build.csv-preferred-parquet

`info` level — `.csv` in clean/intermediate/assemble. Manual fix (changing
the script's output format is risky).

## source.merge.no-validate

Manual — can't pick the right `validate=` value automatically. Surface as
manual review with file:line list.

## archive.leakage

Manual — needs judgment about whether the reference is appropriate.

## idea.no-frontmatter

- **a (default)**: Add minimal frontmatter with placeholder values:

  ```yaml
  ---
  title: <slug derived from filename, title-cased>
  status: idea
  last_updated: <today YYYY-MM-DD>
  ---
  ```

## idea.frontmatter.missing-fields

- **a (default)**: Add the missing fields with placeholder values
  (`status: idea`, `last_updated: <today>`, `title: <slug>`). Don't overwrite
  existing fields.

## idea.frontmatter.bad-status

- **a (default)**: Skip (manual — needs human judgment to map invalid status
  to one of the four allowed values).

---

## Commit message convention

After applying fixes, commit per repo with a message of the form:

```
Lint cleanup: <comma-separated short fix descriptions>

- <one bullet per finding code, with count>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

Example:

```
Lint cleanup: rename todos.md, add done.md+feedback.md, em-dashes

- rename docs/todos.md → docs/todo.md
- add missing docs/done.md, docs/feedback.md
- replace 3 em-dashes (—) with -- in paper/paper.tex
- move docs/desiderata.md~ → deleted (backup file)
```

Workspace-level changes (e.g., updates to `research/rules/citations.md` or
`research/refs/registry.toml`) commit to the workspace repo, not project repos.
