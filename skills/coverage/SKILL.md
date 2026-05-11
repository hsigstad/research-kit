---
name: coverage
description: "Audit a project's adherence to workspace research conventions (artifacts.yaml integrity, IAT presence, validation ledger ageing, .run.json provenance, cross-ref consistency). Surfaces actionable gaps and proposes the right --update follow-up for each."
user_invocable: true
---

# /coverage — Workspace-conventions health audit

Run the coverage dashboard for a project, interpret the results, and
propose surgical fixes for each gap. Thin wrapper around
`research-kit/tools/coverage.py` — the Python tool emits the raw
report; this skill turns it into an interaction by surfacing only the
actionable items and routing each gap to the right follow-up
(`/findings --update`, `/hypothesis --update`, `/iat-check`, etc.).

## Arguments

- `/coverage` — full audit of the current project. Show a focused
  report: ✗ and ⚠ items only, ✓ sections collapsed to one line.
- `/coverage <project-slug>` — run against a specific project under
  `projects/`. Otherwise inferred from cwd.
- `/coverage --detail` — enumerate every offending item, not just
  counts and the first few.
- `/coverage --fix` — walk each gap interactively and propose the
  suggested follow-up. Each proposal waits for explicit
  confirm/skip — no batch apply.
- `/coverage --json` — pass through to the Python tool; emit raw JSON
  for tooling consumption.

## Procedure

### 1. Find the project root

The workspace root contains `CLAUDE.md` alongside `projects/`,
`pipelines/`, `ideas/`, `research/`. Project root is
`$ROOT/projects/<slug>/`. Search upward from cwd if not given.
If neither cwd nor an explicit slug resolves, fail with a useful
message.

### 2. Run the underlying tool

```bash
python3 $ROOT/research-kit/tools/coverage.py --project $PROJ --json
```

If the tool is missing, surface it — the project may not have
`research-kit` cloned as a sibling. The tool requires `pyyaml`; if
`ImportError`, tell the user to `pip install pyyaml`.

Parse the JSON output.

### 3. Render the focused report

Group output by the five sections (ARTIFACTS, SCRIPTS, VALIDATION
LEDGER, PROVENANCE, CROSS-REFS). For each section:

- If every check is `✓`: emit one line `<section>: clean`.
- If any check is `⚠` or `✗`: list those checks with their counts
  and the first 5 offending items. Truncate with `… N more` and
  remind the user that `--detail` shows the full list.

Open with a one-line top-level summary: `N gaps across M sections`.

### 4. Suggest follow-ups (default mode — read-only)

For each gap, append a one-line suggestion the user could run next.
Do not propose to run anything; this mode is purely informational.

| Gap | Suggested follow-up |
|---|---|
| `entries with missing artifact on disk` | The artifact was deleted or renamed. Either delete the entry, or fix its `path` if the artifact moved. |
| `entries with missing producing script` | The script was renamed/deleted. Fix the entry's `script` field (and search-and-replace across `validation.yaml`, `done.md`, briefs, etc.). |
| `entries with empty cited_in` (produced but uncited) | If the artifact is load-bearing, run `/findings --extend` or `/hypothesis --extend` to add a citation. Otherwise mark the entry with a comment. |
| `entries with empty tags` | Tag from the filename prefix (d-/h-series) and the substantive theme. A `/next` `--update` may add tags as a side effect. |
| `build/{table,figure} files not indexed` | Long-tail descriptive artifacts not cited from any doc. Add to `artifacts.yaml` only when first cited; otherwise leave. |
| `scripts missing IAT` | Run `/iat-check <script>` to surface the decision points that need INTENT / REASONING / ASSUMES tags. |
| `validation ledger using legacy paper/ location` | `git mv paper/validation.yaml docs/validation.yaml` (and the `.md` companion). See `research-kit/meta/validation_ledger.md`. |
| `pending validation rows older than 60d` | The script hasn't been validated. Run `/validate-section` on a section that cites it, or invoke `/validate-section --all` for a bulk sweep. |
| `stale validation rows` | Hash drifted since last sign-off. Re-run `/validate-section`; if `closure_hash` changed, also re-check the closure. |
| `sidecars with commit_dirty: true` | The run happened with uncommitted changes — results are provisional. Either commit the changes and re-run, or document the dirty state in the entry. |
| `sidecars with null commit` | Run happened outside a git repo. Usually harmless, but flag if the artifact is paper-cited. |
| `doc references missing from artifacts.yaml` | A doc cites `build/...` but the path isn't indexed. Append an `artifacts.yaml` entry (or fix the doc citation if the path was a typo). |

### 5. --fix mode (interactive)

For each gap, present:

- **The gap** (one line, with the specific item).
- **The proposed fix** — the exact `/<skill> --<flag> <ID>` invocation
  the user can accept.
- **Wait** for the user to type `apply`, `skip`, or `quit`.
  - `apply` — invoke the proposed skill/command. Surface its result
    before moving to the next gap.
  - `skip` — log the skip and move on. Do not auto-apply later.
  - `quit` — stop the walk; report what was applied vs skipped.

Don't batch. Don't propose fixes the underlying skill doesn't actually
support — verify each proposal against the skill's arguments before
suggesting.

### 6. Closing summary

Always end with:

- N gaps surfaced, K addressed in this run (if `--fix`), L skipped.
- Recommended next step if there are still ✗ items.
- A line noting the script's location so the user can re-run later
  manually: `python3 research-kit/tools/coverage.py --detail`.

## Guardrails

- **Read-only by default.** Only `--fix` proposes changes, and even
  then, only via skills the user accepts per gap.
- **Don't invoke `/next` from here.** Coverage is a static audit. If a
  gap looks like new analysis work (e.g. an uncited artifact that
  *should* be cited), surface it as a `/next` candidate hint, but
  don't start `/next`.
- **Skip ✓ sections in the focused output.** Run the underlying tool
  directly with `--detail` for exhaustive output.
- **Pass through `--detail` truthfully.** If the Python tool truncated
  a list ("… 32 more"), don't pretend the gap is smaller than it is —
  show the truncation marker.
- **Don't try to fix things outside the listed gaps.** The check set
  is bounded; suggesting work outside it is scope creep.

## When to run

- **Before a `/next` session** — clears drift so propagation in step 5
  doesn't compound it.
- **After a parser/data refresh** — sidecar dirty flags, broken
  artifact paths, and stale validation rows surface together.
- **After a script rename or directory move** — broken artifact /
  script paths fire immediately.
- **Weekly** — the signal degrades cleanly when nothing's wrong, so a
  no-news run is a feature, not a problem.

## Common failure modes

- **`coverage.py` not found.** The project may not have `research-kit`
  cloned as a sibling. Tell the user to clone it (or, in the workspace
  layout this skill assumes, `git clone git@github.com:hsigstad/research-kit.git`
  at the workspace root).
- **`pyyaml` missing.** Tell the user to `pip install pyyaml` (or use
  the project's virtualenv). Don't try to install it yourself.
- **Project has no `CLAUDE.md` or no `docs/`/`source/` directories.**
  The auto-detect will fail. Pass `--project <path>` explicitly, or
  the project isn't structured per the workspace conventions —
  surface that, don't try to fix it.
