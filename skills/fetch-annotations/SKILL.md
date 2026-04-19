---
name: fetch-annotations
description: Pull hypothes.is annotations left by coauthors on a project's rendered site, map each one back to its source .md file, and walk the user through applying (or skipping) each as an edit. Use when the user wants to incorporate feedback left as web annotations.
user_invocable: true
---

# /fetch-annotations — Pull coauthor annotations from hypothes.is and apply them

Coauthors annotate the rendered project site via hypothes.is (sidebar on every
doc page and the paper). This skill fetches those annotations, maps each one
to the corresponding source `.md` file using the quoted text, and walks the
user through applying each as an edit to the repo.

## Arguments

- `/fetch-annotations` — target the current project (auto-detected)
- `/fetch-annotations [project-slug]` — target a specific project
- `/fetch-annotations --since 2026-04-01` — only annotations updated since date

## What you do

### 1. Locate project and site URL

Find workspace root by searching upward for `CLAUDE.md` next to `projects/`
and `pipelines/`. Resolve the project: `$ROOT/projects/{slug}/`.

Determine the site URL prefix:
- Look at `build.sh` for a `deploy_site` target pushing to `gh-pages`. If the
  repo is `hsigstad/{slug}`, the URL is `https://hsigstad.github.io/{slug}/`.
- If unclear, ask the user once.

### 2. Get the group ID (first time per project)

Private annotations live in a hypothes.is group. Check for a cached group ID:

- `$PROJECT/.claude/fetch-annotations.json` with `{"group": "..."}`

If not cached, ask the user for the group ID (visible in the group page URL:
`https://hypothes.is/groups/{ID}/{slug}`). Optionally cache it. For public
annotations only, no group is needed.

### 3. Fetch annotations

Run the shared tool:

```bash
python3 $ROOT/research/tools/fetch_annotations.py \
    --url-prefix https://hsigstad.github.io/{slug}/ \
    --group {GROUP_ID} \
    [--since YYYY-MM-DD] \
    --json > /tmp/annotations.json
```

For private groups, `HYPOTHESIS_TOKEN` must be exported (get one at
https://hypothes.is/account/developer). If the call fails with 401, prompt
the user to set it.

### 4. Map each annotation to a source file

Each annotation has:
- `url` — rendered page, e.g. `.../institutions.html`
- `quote` — exact text selected in the browser
- `text` — coauthor's comment
- `user`, `updated`, `tags`

Mapping rules:
- `{prefix}/institutions.html` → `$PROJECT/docs/institutions.md`
- `{prefix}/paper.html` → `$PROJECT/paper/paper.tex`
- `{prefix}/` (root) → `$PROJECT/README.md` (best guess; ask if unsure)

For each annotation, grep the `quote` in the mapped source file to locate the
line. If the quote matches multiple places or none, flag it and show what was
found. Quotes are rendered HTML text, so whitespace/line breaks in the source
may differ — fall back to matching the first 5–8 significant words.

### 5. Present the plan and walk through each annotation

Show a numbered summary first:

```
Found 7 annotations (5 with suggested edits, 2 pure comments):
  [1] docs/institutions.md:42  — Lucas  "the SPC registry was ..."
  [2] docs/methods.md:88       — Pedro  "typo: 'judgue' → 'judge'"
  ...
```

Then for each annotation, propose a concrete action:
- **Pure comment / question** → offer to append a note under a TODO section
  in the file, or skip.
- **Suggested edit** (typo fix, rewording, factual correction) → propose the
  specific Edit operation (old_string / new_string) based on the quote and
  comment text. Show the diff.
- **Ambiguous** → show the annotation and ask the user what to do.

For each one, ask: apply / skip / edit-my-version / stop. Apply approved
edits with the Edit tool one at a time so the user can see each change.

### 6. Report back

Summarize: how many annotations were applied, skipped, left for later.
List the annotation IDs that were applied so the user can resolve them on
hypothes.is (or reply to them there). Do NOT mark them resolved via the API
automatically — that's the coauthor's call.

## Notes and gotchas

- **Orphaned annotations:** if the site has been rebuilt and the quoted text
  no longer exists verbatim, the annotation still returns from the API but
  the grep will miss. Surface these explicitly rather than silently dropping.
- **HTML vs markdown:** hypothes.is selects rendered text, so markdown syntax
  (`**bold**`, `[link](url)`) won't appear in the quote. Match the visible
  text, then find the corresponding markdown in the source.
- **Paper annotations** map to `paper/paper.tex` but the quote is HTML text
  from make4ht output — expect LaTeX macros in the source around the match.
- **Never delete** annotations via the API. The skill is read + edit only.
- **Don't batch applies.** Walk the user through one at a time; a wrong
  auto-apply on a paragraph is painful to undo.
