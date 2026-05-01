---
name: lint-docs
description: Run deterministic checks against the workspace doc-contract and source/build layer conventions, and optionally apply fixes interactively. Use when the user invokes /lint-docs, /lint-docs <slug>, /lint-docs --fix, or asks to "lint the docs" / "check doc structure" / "audit projects for contract drift" / "clean up the docs". For deeper LLM-assisted checks (theory↔hypotheses orphans, summary↔results contradictions), the user opts in with `--deep`.
---

# lint-docs

Reports contract drift across the research workspace. Two modes:

- **Deterministic (default).** Pure Python, runs in <2s across all projects, catches the cheap wins: missing required files, filename typos, todo/done hygiene, source↔build naming, em-dashes in paper prose, idea frontmatter validity. No LLM.
- **Deep (`--deep`).** LLM-assisted cross-doc checks. Run on demand for a single project. See `deep-checks.md` (TODO).

## How to invoke

| Form | What it does |
|------|--------------|
| `/lint-docs` | Lint all projects + pipelines + workspace-level (idea frontmatter). Report only. |
| `/lint-docs <slug>` | Lint one project or pipeline. Report only. |
| `/lint-docs --fix` | Lint, propose interactive fixes, apply approved fixes, commit per repo. |
| `/lint-docs <slug> --fix` | Same, scoped to one repo. |
| `/lint-docs --json` | Report-only mode, JSON output. |
| `/lint-docs --citations` | Lint `[ns:key]` citation tokens against registry, anchors, and BibTeX. |
| `/lint-docs <slug> --citations` | Same, scoped to one repo. |
| `/lint-docs --sync` | Regenerate `docs/refs/manifest.toml` for all projects from registry. |
| `/lint-docs <slug> --sync` | Same, scoped to one project. |
| `/lint-docs <slug> --deep` | (Future) LLM cross-doc checks. |

To run report mode:

```bash
python3 ~/research/research-kit/skills/lint-docs/check.py <slug?> [--json]
```

The script exits with status 1 if any errors are found (so it can gate CI). Warnings and info do not fail the check.

## Interactive fix flow (`--fix`)

When the user runs with `--fix`, follow this loop:

### 1. Run the check

```bash
python3 ~/research/research-kit/skills/lint-docs/check.py <slug?> --json
```

Parse JSON output. For each finding, look up the fix template in
`fixes.md` (sibling file). Findings with no auto-fix template
(merge.no-validate, archive.leakage, source.no-output for missing paper
artifacts) become "manual review" items, NOT numbered proposals.

### 2. Build the numbered proposal list

Group by repo. Number each proposal globally (1, 2, 3, …) so the user can
refer to any without disambiguating which repo.

For findings with alternatives, render as:

```
17. fisc/docs/actors.md non-canonical at docs/ root
    a. (default) move to docs/notes/actors.md
    b. move to docs/reference/actors.md
    c. add `actors.md` to canonical optional list
    d. delete
```

For findings with no alternatives, just one line:

```
3. audit/docs/todos.md → rename to docs/todo.md
```

When choosing a default for ambiguous cases (a/b/c), peek at the first
~30 lines of the file:

- Narrative prose → `briefs/`
- Tables / lookup material → `reference/`
- Otherwise → `notes/`

End the proposal with a manual-review section listing items not auto-fixable,
and a response-format reminder:

```
Manual review (no auto-fix):
- 6 .merge() calls without validate= in projects/audit/source/merge/ — pick 1:1, 1:m, m:1, m:m per call
- ...

Respond with:
- "go" or "all"          → apply every default
- "all except 6,9"       → apply defaults, skip those
- "all, 6b 9c"           → apply defaults, but use alternative b for 6 and c for 9
- "1,3,5"                → apply only those (defaults)
- "skip" or "abort"      → do nothing
```

### 3. Wait for user response

Parse the response. If unclear, ask one targeted clarification question.

### 4. Apply fixes

Apply each approved fix using Edit / Write / Bash (`git mv`, `mkdir -p`, etc.).
Apply atomically per repo so a partial failure doesn't leave half-applied state.

### 5. Commit per repo

For each repo with applied fixes, run a single commit. Message format (from
`fixes.md`):

```
Lint cleanup: <comma-separated short descriptions>

- <one bullet per fix, with count where applicable>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

Workspace-level fixes (e.g., adding to `ALLOWED_DOC_SUBFOLDERS` in `check.py`,
or adding a name to the canonical optional list in
`research-kit/rules/project_docs_contract.md`) commit to the workspace repo or
`research-kit` repo as appropriate.

### 6. Suggest push

After all commits, list the repos that received commits and ask:

```
Committed in:
- projects/audit (1 commit)
- projects/bind (1 commit)
- research-kit (1 commit, doc contract update)

Push? (y / pick which / n)
```

Don't auto-push. If push fails (sandbox / no remote / permissions), report and
move on — don't retry destructively.

### Edge cases

- **Conflicts when renaming.** If `todos.md` should rename to `todo.md` but
  `todo.md` already exists, abort that fix and flag it manually.
- **Multiple fixes on the same file.** Apply in order: deletes last, content
  edits before moves.
- **Workspace registry changes.** If a fix involves adding to canonical
  optional list, the user must specify the semantic role. Surface as a single
  follow-up question, not as part of the main loop.
- **Empty selection.** If the user says "skip" or only references manual
  items, exit cleanly without commits.

## What it checks (deterministic)

### Doc structure
- Required files present at `docs/` root (project: 11 files; pipeline: 5 files).
- Files at `docs/` root are in the canonical allowlist. Common typos (`todos.md` → `todo.md`) get a hint.
- Subfolders at `docs/` are warned if outside the known set (`briefs/ reference/ notes/ literature/ anecdotes/ emails/ reviews/ specs/ whatsapp/ feedback/`).

### todo / done hygiene
- `todo.md` has no `[x]` items (skipping session-handoff section).
- `done.md` has no `[ ]` items.

### thinking.md
- All six required H2 sections present.

### Source/build conventions
- `source/<layer>/` directories that aren't canonical (`clean/ intermediate/ assemble/ analysis/ figure/ table/ paper/`) are noted as project-specific.
- Each non-private `source/<layer>/X.py` should have a matching build artifact:
  - `source/clean/`, `source/intermediate/`, `source/assemble/`, `source/analysis/` → `build/<layer>/<base>.{parquet,csv,json,...}`
  - `source/figure/` → `paper/figures/<base>.{pdf,png,...}`
  - `source/table/` → `paper/tables/<base>.{tex,md}`
- Figure or table outputs found under `build/` instead of `paper/` are flagged as misplaced.
- `.csv` outputs in clean/intermediate/assemble layers are noted (prefer `.parquet`).

### Code style
- `.merge()` calls without `validate=` argument are warned.

### archive.md leakage
- Active docs that reference `archive.md` are warned.

### Idea frontmatter (workspace-level)
- Each `research/ideas/*.md` has YAML frontmatter with `title`, `status`, `last_updated`.
- `status` value is one of `idea | exploring | shelved | project`.

### Citation tokens (`--citations`)
- Every `[ns:key]` token resolves: external via registry, internal via `- id:` anchors or `\label{}`, literature via `.bib`.
- Malformed tokens (`[Method:foo]`, `[ns:Foo_Bar]`) are flagged.
- Orphan manifest entries — entries in `docs/refs/manifest.toml` not cited by any doc.
- Dangling registry entries — `path` in `research/refs/registry.toml` pointing to non-existent files (workspace-level).
- Skips `docs/emails/` and `docs/whatsapp/` (non-content subdirectories).

### Manifest sync (`--sync`)
- Walks each project's `docs/` and `paper/` for external `[ns:key]` tokens.
- Looks up each in `research/refs/registry.toml`.
- Writes the public-facing subset (title + description only, no path/anchor) to `docs/refs/manifest.toml`.
- Reports which projects were updated vs already current.

## What it does NOT check (deferred to `--deep`)

- Theory ↔ hypotheses coverage (every prediction has a matching theory result; every theory result has a matching prediction).
- Summary ↔ results contradictions.
- Speculative phrasing in "settled" docs (high false-positive rate, needs LLM judgment).
- Whether `literature.md` relevance assessments match how each entry is used elsewhere.
- IAT comment accuracy against actual code behavior.
- Citation token resolution (`[ns:key]` → registry / anchor) — now covered by `--citations` mode.

## Output

Markdown report grouped by repo, with errors, warnings, and info under each. Workspace-level findings (idea frontmatter) appear first.

JSON output (`--json`) has shape:

```json
{
  "workspace": {"scope": "workspace", "errors": [...], "warnings": [...], "info": [...]},
  "repos": [
    {"scope": "projects/audit", "errors": [...], "warnings": [...], "info": [...]},
    ...
  ]
}
```

Each finding has `code`, `msg`, and (often) `path`. Codes are stable identifiers — see `check.py` for the full list.

## Implementation

- `check.py` — single-file Python (no external deps; uses stdlib `pathlib`, `re`, `argparse`, `json`).
- Tiny custom YAML frontmatter parser (we only need `key: value` for ideas).
- Designed to run in <2s across the full workspace.

## When to extend

Add a check when you find yourself manually inspecting the same kind of drift across multiple projects. Each check should be:

1. Deterministic (no LLM).
2. Cheap (sub-second per project).
3. Specific (a clear code, a clear message, a clear path).

Avoid heuristic checks with high false-positive rates — those belong in `--deep` mode.
