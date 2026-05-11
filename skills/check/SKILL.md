---
name: check
description: "Audit a project or pipeline against workspace conventions AND propose fixes for everything found. Three modes: docs (doc-contract + source/build naming), ledgers (artifacts.yaml + validation.yaml + .run.json + cross-refs), cite (citation tokens against the registry + anchors + .bib). All three are fast and deterministic. Default runs all three and proposes changes. Use when the user invokes /check, /check <mode>, /check <slug>, or asks to 'lint the docs', 'audit conventions', 'check citations', 'check the ledgers', 'clean up the docs'."
user_invocable: true
---

# /check — Workspace convention audit (with proposed fixes)

Orchestrates the three **fast deterministic** project audits, **proposes
fixes for every finding**, and lets the user approve before any change
lands. Thin wrapper over the underlying tools — the skill's job is
**sequence, unified reporting, and the propose-then-apply interaction
shape**.

The default behavior is *propose-and-apply*, not read-only. Pass `--json`
when you want a raw report for tooling or CI.

| Mode | What it audits | Backing |
|---|---|---|
| `docs` | doc-contract presence, todo/done hygiene, thinking.md sections, source/build naming (incl. multi-output folder), pandas merge validate=, archive.md leakage, idea frontmatter | `research-kit/tools/check_docs.py` (deterministic, <2s workspace-wide) |
| `ledgers` | `artifacts.yaml` ↔ disk drift, `validation.yaml` pending/stale rows, `.run.json` sidecar provenance, doc ↔ artifacts.yaml cross-refs | `research-kit/tools/coverage.py` (deterministic; requires pyyaml) |
| `cite` | `[ns:key]` citation tokens against the workspace registry, internal anchors, and `.bib` files | `research-kit/tools/citations.py` (deterministic; lint only — no manifest sync) |

For IAT (INTENT / REASONING / ASSUMES / SOURCE) comment compliance, see
`/iat` — that audit is LLM-driven and slower, kept as its own skill so
`/check` stays fast.

For manifest regeneration (`docs/refs/manifest.toml`), see `/cite-sync` —
that's a write action, not an audit.

## How to invoke

| Form | What it does |
|------|--------------|
| `/check` | All three modes for the current project (inferred from cwd) or workspace-wide; **propose fixes and ask before applying** |
| `/check <slug>` | All three modes against a single project/pipeline |
| `/check docs` | Docs mode only |
| `/check ledgers` | Ledgers mode only |
| `/check cite` | Citation mode only |
| `/check <mode> <slug>` | One mode, one repo |
| `/check --full` | Show every instance in the report (not the grouped summary) |
| `/check --json` | Raw JSON output, no proposals — for CI, tooling, or "just tell me how dirty it is" |

## Finding the workspace root

Workspace root contains `CLAUDE.md` alongside `projects/`, `pipelines/`,
`ideas/`, `research/`. Search upward from cwd; project root is
`$ROOT/projects/<slug>/`. If neither cwd nor an explicit slug resolves, fail
with a useful message.

## Procedure

### 1. Resolve mode and scope

- Mode: `docs`, `ledgers`, `cite`, or `all` (default). If the first
  positional arg matches a mode keyword, treat it as the mode; otherwise
  treat it as a slug and use mode `all`.
- Scope: explicit slug, cwd's project, or workspace-wide if neither.

### 2. Run the underlying tool(s)

For each requested mode:

```bash
# docs
python3 $ROOT/research-kit/tools/check_docs.py [<slug>] --json

# ledgers (project-scoped only — no workspace-wide rollup)
python3 $ROOT/research-kit/tools/coverage.py --project $PROJ --json

# cite (lint mode; --sync is /cite-sync's responsibility)
python3 $ROOT/research-kit/tools/citations.py [<slug>] --json
```

If any tool errors, surface the traceback — do not silently fall back. If
`coverage.py` is missing, surface a hint to clone `research-kit`. If
`pyyaml` is missing, tell the user to `pip install pyyaml`; don't try to
install it yourself.

### 3. Render the focused report

Open with a one-line summary: `N gaps across {docs, ledgers, cite}` and
the totals.

For each mode, group findings by code and show counts + first 3 examples,
truncating with `… +N more`. `--full` enumerates every instance.

Use the underlying tool's grouped output for all three modes.

### 4. Propose fixes

This is the default. For every finding, derive a concrete fix (or a routed
follow-up). The interaction shape differs by mode because the work differs:

**Docs (`/check docs`): enter plan mode with the full fix list.**

Each finding gets a templated fix from `fixes.md` (sibling file). Build the
complete plan as a numbered list grouped by repo, then call `EnterPlanMode`
with the plan. The user sees every change at once and approves or redirects
before any edit lands. On approval, execute the file ops (renames, moves,
new files, merge `validate=` insertions) and commit per repo with the
message format in `fixes.md`. Findings without a templated fix
(`.merge() validate=` value choice, `archive.leakage`) go in a
**Manual review** section at the end
of the plan — surfaced but not auto-applied. Common fixes:

| Gap | Default fix |
|---|---|
| `doc.missing` | Create the file with the canonical heading template |
| `doc.unallowed` | Rename to canonical (e.g. `todos.md` → `todo.md`) or move to `briefs/`/`notes/`/`reference/` based on content |
| `*.naming-violation` | `mkdir` the script-named folder and `git mv` the sibling outputs into it |
| `*.orphan` / `*.orphan-folder` | Either rename the script to match, or delete the orphan (ask which) |
| `source.no-output` (data layers) | No fix — surface as manual ("build may be unbuilt") |
| `source.merge.no-validate` | Manual review — pick `one_to_one`, `many_to_one`, etc. per call |
| `project.no-claude-md` | Create `CLAUDE.md` at project root with a one-line summary + pointer to `docs/summary.md` |
| `gitignore.no-build` | Add `build/` to `.gitignore` (create the file if missing) |
| `decisions.bad-header` | Rewrite the header to `## YYYY-MM-DD — <title>` (em-dash). Auto-fix if the date is parseable; manual otherwise |
| `handoff.bad-filename` | `git mv` to `<ISO-timestamp>_<short-tag>.md` (manual: pick the right tag) |
| `source.underscore-cited` | Manual review — either rename the script to drop the underscore (and let it be a real artifact) or rewrite the citing doc to point elsewhere |

**Ledgers (`/check ledgers`): numbered list, per-gap apply/skip/quit.**

Plan mode is a bad fit here because most ledger gaps route to *other gated
skills* (`/findings --update`, `/hypothesis --extend`, `/validate-section`).
Wrapping those in plan mode means double-gating. Instead, present a
numbered list of suggested follow-ups; the user picks which to invoke, and
each child skill runs its own approval flow. Common routes:

| Gap | Routed follow-up |
|---|---|
| entries with missing artifact on disk | Fix the `path` field (or delete the entry) — surface diff |
| entries with missing producing script | Fix the `script` field |
| entries with empty `cited_in` (load-bearing) | `/findings --extend` |
| `build/{table,figure}` files not indexed | Append to `artifacts.yaml` |
| scripts missing IAT | `/iat <script>` |
| pending validation rows older than 60d | `/validate-section` |
| stale validation rows (hash drift) | `/validate-section` |
| sidecars with `commit_dirty: true` | Commit and re-run, or document the dirty state |

**Cite (`/check cite`): enter plan mode for auto-fixable; manual review for the rest.**

Mix of deterministic and judgment-call findings. Build the plan from the
deterministic ones; surface the others in a **Manual review** section.

| Code | Auto / manual | Default proposal |
|---|---|---|
| `cite.malformed` | Auto | Deterministic transform: lowercase ns, kebab-case key. Show old → new diff per occurrence |
| `cite.orphan-manifest` | Auto | Run `/cite-sync <slug>` — regenerates the manifest from the live cited set, so the orphan entry drops out atomically (don't hand-edit the TOML) |
| `cite.missing-from-manifest` | Auto | Run `/cite-sync <slug>` — adds the missing entry by regenerating from the live cited set. Group multiple `cite.missing-from-manifest` + `cite.orphan-manifest` findings for the same project into a single `/cite-sync` invocation |
| `cite.unresolved-external` | Manual | Surface the missing `[ns:key]`; ask the user to add a registry entry (title, description, optional path) |
| `cite.unresolved-internal` | Manual | Show the expected anchor (`- id: ns:key` or `\label{ns:key}`) and point at the doc where the citation lives |
| `cite.unresolved-bib` | Manual | Show the `[cite:key]` and ask for a `.bib` stub |
| `cite.unknown-namespace` | Manual | Either a typo (suggest closest valid one) or a new namespace proposal — surface for review |
| `cite.registry-dangling` | Manual | The registry entry's `path` no longer exists. Ask the user to update or remove |
| `anchor.duplicate` | Manual | Two anchors with the same ID in the same scope (docs/ globally, or a single .tex file). Ask the user which to rename — show both occurrences |

For manifest regeneration use `/cite-sync` (write action, not part of the
audit flow).

### 5. Closing summary

Always end with:

- N gaps surfaced; K approved & applied; L skipped or routed; M flagged as
  manual review.
- Per-repo commit summary (if docs-mode applied any fixes).
- Recommended next step if any ✗ items remain.
- The raw commands so the user can re-run for a passive view:
  - `python3 research-kit/tools/check_docs.py [<slug>] --json`
  - `python3 research-kit/tools/coverage.py --project <path> --json`
  - `python3 research-kit/tools/citations.py [<slug>] --json`

## Guardrails

- **Always propose, never auto-apply.** `--json` is the only mode that skips proposals; even there, exit on a non-zero error count for CI gating.
- **Use plan mode for docs and the auto-fixable cite findings.** A unified plan beats per-gap walking — the user sees the whole shape and can redirect in one step.
- **Don't wrap routed skills in plan mode.** When a ledger gap routes to `/findings --update`, let that child skill handle its own approval — chaining plan-mode invocations confuses the gate.
- **Don't invoke `/next` from here.** `/check` is a static audit. If a gap reads like new analysis work, surface it as a `/next` candidate hint, but don't start `/next`.
- **Don't try to fix things outside the listed gaps.** Scope is bounded.
- **For IAT, route to `/iat`.** It's kept separate so `/check` stays fast.

## When to run

- **Before a `/next` session** — clears drift so propagation in step 5 doesn't compound it.
- **After a parser/data refresh** — sidecar dirty flags, broken artifact paths, and stale validation rows surface together.
- **After a script rename or directory move** — broken artifact/script paths and naming violations fire immediately.
- **Weekly** — the signal degrades cleanly when nothing's wrong, so a no-news run is a feature, not a problem.

## Common failure modes

- **`coverage.py` not found.** The project may not have `research-kit` cloned as a sibling. Tell the user to clone it.
- **`pyyaml` missing.** Tell the user to `pip install pyyaml` (or use the project's virtualenv).
- **Project has no `CLAUDE.md` or `docs/`/`source/` directories.** Auto-detect fails. Pass `<slug>` explicitly, or surface that the project isn't structured per the workspace conventions.
