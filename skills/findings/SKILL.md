---
name: findings
description: "Populate, extend, refresh, or audit a project's docs/findings.md — a curated index of headline empirical findings and interpretations with confidence tags and standardized source footers. Use when the user wants to draft a new findings doc, append new entries from recent build artifacts or audit JSONs, refresh load-bearing numbers against the current data, or check completeness."
---

# /findings — Populate docs/findings.md

Draft, extend, refresh, or audit a project's `docs/findings.md`:
the curated index of *what we have learned* that the project considers
load-bearing for the paper or for downstream interpretation. Each entry is
a confidence-tagged headline with an expanded explanation, anchored to
build artifacts, reports, news, and cross-references through a
standardized Sources footer.

This skill is the *authoring* counterpart to `/findings-audit` (which
audits findings against external evidence — different verb). Use
`/findings` to write or maintain entries; use `/findings-audit` to
stress-test the entries you've written.

## Arguments

- `/findings` — infer project from cwd; default to populate-or-extend mode.
- `/findings <project-slug>` — run against a specific project under `projects/`.
- `/findings --extend` — preserve existing entries; only append new ones suggested by recent build artifacts, audit JSONs, or the user's pointer.
- `/findings --refresh` — recompute the load-bearing numbers in entries against current build artifacts; flag entries whose headline numbers don't match the current data. Critical for catching staleness after pipeline reruns or parser fixes.
- `/findings --audit` — do not write; report completeness gaps (missing source classes, missing confidence tags, dangling cross-refs, sources without page anchors).
- `/findings --footer <slug-or-heading>` — re-format only the Sources footer of one specified entry to the standardized 4-class schema (used to roll out the schema across an existing doc).
- `/findings --update <slug-or-heading> [--artifact <AN-id-or-build-path>]` — **surgical single-entry edit**. Update one finding's body (headline, magnitude, caveat, confidence tag) after a new analysis result. Reads only `CLAUDE.md`, `findings.md`, and the optional triggering artifact. `--artifact` accepts either an AN id (preferred — e.g. `AN-019`; the skill reads `docs/analyses/an-019-*.md` to recover script + target + headline) or a raw `build/<path>` (fallback for runs not yet ledgered). Does not re-derive other findings, does not re-read `stylized-facts.md`/briefs/audits. Use from `/next` step 5 when a run affects exactly one existing finding (re-run with revised magnitude, parser fix that shifts a number, confidence promotion/demotion after replication). Distinct from `--refresh` (which walks all findings) and `--footer` (which touches only the Sources block).

## Finding the workspace root

The workspace root contains `CLAUDE.md` alongside `projects/`, `pipelines/`, `ideas/`, `research/`. If the current directory is inside a project, search upward to find the root. Use `$ROOT` for all paths below. The project root is `$ROOT/projects/<slug>/` — use `$PROJ` for it.

## Locating the findings doc

Discovery order, first hit wins:

1. `$PROJ/docs/findings.md`
2. `$PROJ/docs/findings/index.md` (folder mode — see below)
3. `$PROJ/docs/reference/key-findings.md` (legacy)
4. Project-specific path declared in `$PROJ/CLAUDE.md` or `$PROJ/docs/summary.md`

If none exists, ask the user which location to create. Default suggestion is
`docs/findings.md`. Do not silently create the file at a non-canonical path.

## What to read (in order)

Read these files to build context. If one is missing, note it and move on; never invent its content.

1. `$PROJ/CLAUDE.md` — current focus, key terms, conventions
2. `$PROJ/docs/summary.md` — research question (required)
3. `$PROJ/docs/findings.md` (if exists) — existing entries; match their template exactly
4. `$PROJ/docs/reference/stylized-facts.md` (if exists) — fact-by-fact ledger; findings draws its empirical anchors from here
5. `$PROJ/docs/hypotheses.md` (if exists) — every empirical finding should map to at least one hypothesis or angle
6. `$PROJ/docs/briefs/*.md` — narrative synthesis files; cross-link from findings entries
7. `$PROJ/docs/audits/findings/*.{md,json}` (if exists) — output of `/findings-audit`; this contains anchor quotes and corroborations to fold into entries
8. `$PROJ/build/table/*` and `$PROJ/build/figure/*` — own-analysis artifacts; each load-bearing finding should cite at least one
9. `$PROJ/source/table/*.py` and `$PROJ/source/figure/*.py` — scripts producing the artifacts; cite the script in the Sources footer
10. `$PROJ/references/{cnj,pgfn,ipea,reports,…}/*.pdf` — aggregate reports; needed for `*Reports*` source-class citations with `#page=N` anchors
11. `$PROJ/references/news/stories.csv` and `$PROJ/references/news/texts/*.txt` — news anecdotes; needed for `*News anchors*` source-class citations with anchor quotes
12. `$PROJ/paper/main.tex` (if exists) — load-bearing findings should match what the paper presents; flag drift

## Document & entry format

Full spec — templates, verbatim confidence-tag scheme, entry schema, headline
rule with examples, Sources footer, path conventions, folder-mode details,
migration, and the validation badge — is in
[`reference/entry-format.md`](reference/entry-format.md). **Read it before
drafting, extending, or updating entries.** The essentials:

- **Default layout is folder mode**: `docs/findings/` with `index.md` (intro +
  confidence scheme + linked overview) and one `<slug>.md` per finding. Flat
  `docs/findings.md` is legacy — maintain existing ones, don't create new.
- **Each entry** = a confidence tag + a self-contained headline sentence (≤40
  words, one declarative claim about the world, with the load-bearing number(s)
  and AN cite(s)), then 1–4 paragraphs of anchored explanation, then a
  four-class **Sources footer** (*Own analysis* / *Reports* / *News anchors* /
  *Cross-refs*, plus *Validation* if the project has a ledger). Absent classes
  read `none direct`, never omitted.
- **Confidence tags** 🟢/🟡/🔴 mean replicated / single-source / provisional for
  empirical findings, and strong / plausible / speculative for interpretations.
- Findings **cite the AN ledger entry** (`AN-NNN`) and take the magnitude from
  the AN page — they don't re-derive numbers.

## Draft protocol

1. Read all inputs (see "What to read"). Build a **finding candidate list** from:
   - Existing entries (preserve as-is in normal/extend mode)
   - `build/table/*.csv` and `build/figure/*.pdf` artifacts not yet cited in any entry — each is a candidate finding
   - `docs/audits/findings/*.json` — anchor quotes and corroborations to fold in
   - The user's pointer if they specified one
2. Filter aggressively. Keep only findings that (a) are *load-bearing* for the paper or for an interpretation, (b) have at least one own-analysis artifact or anchored external source, (c) state a directional claim ("X is rare", "Y rises with Z"). Drop merely descriptive cuts unless they support a specific interpretation downstream.
3. For each finding, draft the entry per the schema:
   - Pick confidence tag honestly per the scheme.
   - Headline sentence carries the load-bearing number.
   - Expanded explanation grounds the number with anchored citations.
   - Sources footer in the four-class format with all four classes (use `none direct` if a class has no entries).
4. Aim for **20–50 entries** in mature projects, **5–15** in early-stage. More than 60 means insufficient curation — split into a separate page or move some to `stylized-facts.md`.
5. The `## Findings overview` index must include every entry with a one-line summary and an anchor link. This is the doc's table of contents and is critical for navigability.

## Update mode (`--update <slug-or-heading>`)

Surgical single-entry edit. Use when one finding's content changed
(magnitude revised, caveat added, confidence tag moved, parser-fix
walk-back) and the rest of `findings.md` should remain untouched.

**Minimal read set** — do not re-read the full briefing pack:

1. `$PROJ/CLAUDE.md` — for current focus and naming conventions.
2. `$PROJ/docs/findings.md` — to locate the target entry
   and respect its template exactly.
3. The `--artifact` argument (if given). If an AN id: read
   `$PROJ/docs/analyses/an-NNN-*.md` to recover the script, target,
   headline, and confidence — the AN page is canonical, do not
   re-derive numbers from the build artifact. If a `build/<path>`:
   read the artifact itself.
4. The triggering script's IAT docstring (via the `source/X.py →
   build/X.*` convention, or the `script:` field on the AN page) —
   for context.

Do **not** re-read `stylized-facts.md`, briefs, audits, or paper.tex
unless the target finding's Sources footer explicitly cites them and
the update would change those citations.

**What to edit:** only the target finding's entry. Preserve the
template (headline, expanded prose, Sources footer four-class schema).
Update only the fields affected — typically the magnitude in the
headline + the prose explanation, optionally the confidence tag.

**What not to touch:** other findings, the `## Findings overview`
table of contents (unless the headline changed materially), the
confidence-tag scheme section, or any cross-cutting structure.

**`@claim` registry:** if the entry uses `@claim` tokens, update the
token values rather than free-text edits where possible. That keeps
`--refresh` cycles cheap on subsequent re-runs.

**Output:** the edited `findings.md` plus a one-paragraph summary
(which entry, before → after, what artifact was cited). The summary
belongs in the `/next` end-of-iteration report.

Distinct from:
- `--refresh` (walks **all** findings, recomputes from artifacts,
  flags drift — for post-pipeline-rerun bulk verification).
- `--footer` (touches only the Sources footer schema, no body edits).
- `--extend` (appends new findings; doesn't edit existing ones).

## Refresh mode (`--refresh`)

This is the most valuable mode and the one most often skipped. After any pipeline rerun or parser fix:

1. For each entry, identify the load-bearing numbers in the headline and body. Patterns to look for: percentages, R$ amounts, counts, ratios.
2. Locate the underlying build artifact (typically the first `*Own analysis*` link in the Sources footer). Read it.
3. Compare current numbers to the entry's stated numbers. Flag any discrepancy >2pp on percentages or >5% on counts.
4. For each flagged entry, present:
   - The entry headline + stated number
   - The current build-artifact number
   - The likely source of drift (parser fix, new data, recompute)
   - A suggested edit (corrected number + a "refreshed YYYY-MM-DD" parenthetical)
5. Do not auto-edit. Show the user the diff and let them confirm each fix. Stale numbers are often the result of an earlier curated narrative the user wants to preserve while flagging drift.

This is the mode that catches problems like a "50% of payments are ghost" headline that was never updated after a parser fix moved 20% of cases to a different bucket.

## Audit mode (`--audit`)

Do not write. Check:

- Every entry has confidence tag, headline sentence, expanded explanation, Sources footer.
- Every Sources footer has all four classes (or explicit `none direct`).
- Every report citation has a `#page=N` anchor (not just stem+page in plain text).
- Every news citation links to a `texts/NNN.txt` file that exists.
- Every own-analysis artifact path resolves (file exists in `build/`).
- Every cross-ref anchor resolves (heading exists in the linked doc).
- Every interpretation entry has a Draws-on / Cross-refs paragraph naming at least one empirical finding it depends on.
- Every empirical finding tagged 🟢 names at least two independent samples or studies in the body.

Report findings as a bulleted list of gaps, grouped by entry. Do not auto-fix.

## Extend mode (`--extend`)

1. Preserve every existing entry verbatim.
2. Compute the diff between current `build/table/*` and the artifacts already cited across existing entries. Identify orphan artifacts (built but never cited) that look load-bearing.
3. For each orphan, propose a new entry headline + a one-line summary. Wait for user pick before drafting full entries.
4. Append new entries after the last existing one, marked with a `Status: drafted YYYY-MM-DD` line if the project's template uses status fields.

## Footer-only mode (`--footer <slug>`)

For migrating an existing doc into the standardized footer schema without touching the prose. Useful as a one-time roll-out tool.

1. Locate the entry by anchor slug or by phrase match in headlines.
2. Parse the existing Sources line (which may have been single-line or in a `Draws on:` form).
3. Re-format into the four-class structure. Auto-classify each existing reference:
   - Paths starting with `build/` → *Own analysis*
   - Paths starting with `references/` and matching `.pdf` → *Reports* (and add page anchor if a page is mentioned in body or stem)
   - Paths starting with `references/news/` or text matching news pattern → *News anchors*
   - Internal anchor links (`#...`) or cross-doc links → *Cross-refs*
4. Add `none direct` for any class that has no existing references.
5. Show the user the diff and confirm before writing.

## Interaction with `/findings-audit`

The two skills are complementary:

- `/findings` produces and maintains the doc.
- `/findings-audit` reads the doc and stress-tests its claims against external evidence (news, reports), producing a JSON+MD audit at `docs/audits/findings/YYYY-MM-DD-targeted.{md,json}`.

When `/findings-audit` finds a corroboration or weak counter-evidence, the audit JSON contains anchor quotes that should be folded back into the relevant `/findings` entries. The `--extend` mode of `/findings` should look for any audit JSON newer than the doc's last edit, and surface its corroborations as candidate new bullets in existing entries.

## Interaction with adjacent skills

- **`/hypothesis`**: every empirical finding tagged 🟢 or 🟡 should map to at least one hypothesis. The audit-mode check for "every interpretation has Draws-on cross-refs" is the symmetric check.
- **`/theory`**: interpretations in key-findings draw on theory.md frameworks. Cross-refs from interpretations to theory.md are encouraged.
- **`/literature`**: when a finding's headline number is being compared across studies (e.g., INSPER 16% vs IPEA 6.5% vs own 1.6%), the supporting studies should appear in literature.md. The Sources footer's `*Reports*` and `*News anchors*` classes are not a substitute for academic literature — they're the institutional and current-events parallel.
- **`/anecdotes`**: when a finding leans on news anecdotes, those rows must exist in `references/news/stories.csv` (populated by `/anecdotes`). Don't cite news that isn't in the curated corpus.

## Guardrails (these are the quality bar — do not relax)

- **Never fabricate a number.** Every load-bearing number in the body must be traceable to a build artifact or an external source linked in the Sources footer. If a number from memory doesn't appear in any artifact, drop it or run the analysis first.
- **Never invent a page number.** Report citations with `#page=N` must be verified — open the PDF or grep its plaintext for the cited content. Better to write `[CNJ-DEF24 — page tbd]` than to invent.
- **Anchor every quote.** News-anchor quotes must be exact substrings of the linked `texts/NNN.txt`. Paraphrases are not anchor quotes — drop the italics or paraphrase elsewhere.
- **Date every update.** Sub-paragraphs, footer changes, confidence upgrades — all carry a parenthetical `(added YYYY-MM-DD)` or `(refreshed YYYY-MM-DD)` so future readers can date the claim.
- **Preserve prior versions of changed numbers.** When refreshing, write the new number first, then a brief note: "*(refreshed YYYY-MM-DD; previously stated as X under <pre-fix universe>)*". This keeps the audit trail without burying the current truth.
- **No padding.** A finding without anchored evidence is not a finding — it's a hypothesis or a guess. Move it to `hypotheses.md` or delete it.
- **Honest confidence tags.** Do not push a 🟡 to 🟢 because the paper needs it. Do upgrade only when independent replication actually arrives.

## Output protocol

1. **Populate/extend:** print a preview — entry count, new vs existing entries, count of placeholder `[ref needed]` or `[page tbd]` markers. Wait for confirmation unless the user said "go ahead." Write the file. Report the path and any unresolved placeholders.
2. **Refresh:** print a per-entry diff showing stated vs current numbers. Wait for confirmation per entry before applying. Refreshed entries get a parenthetical date stamp.
3. **Audit:** print a bulleted list of gaps. Suggest next mode (`--refresh` if numbers drifted, `--extend` if new artifacts orphaned, `/findings-audit` if external corroboration is the gap).
4. **Footer:** show the diff for the one entry; confirm; write.

## Common failure modes to avoid

- **Number drift.** A pipeline rerun changes the headline number in build/, but the entry text isn't refreshed. Catch this with `--refresh` after every pipeline change.
- **Stale parser-fix artifacts.** A paragraph documenting "fix moved X% to Y%" gets carried through subsequent runs even though X and Y no longer match the current data. Either update both the prose and the parser-fix-note, or move the parser-fix audit trail to `done.md` once superseded.
- **Sources without page anchors.** "[CNJ-DIAG22 p.198]" without a clickable PDF link forces the reader to open the PDF and find p.198 manually. Always use `#page=N` deep links when citing reports.
- **News anchors without quotes.** A news citation like "[stories.csv #310]" tells the reader the row exists but not what it says. For load-bearing news anchors, include the anchor quote inline.
- **Interpretation without empirical anchor.** Interpretations that don't draw on specific empirical findings are op-ed, not analysis. Every interpretation entry must list its empirical premises in the Draws-on / Cross-refs paragraph.
- **Index drift.** New entries are added to the body but the `## Findings overview` index isn't updated, so the entry is unreachable from the top of the page. Always update the index when adding entries.
- **Empirical findings filed as interpretations.** A descriptive cut of the data ("X is 27% of cases") is empirical, not interpretive. The interpretation is the *reading* ("this implies X is the modal channel"). Keep the partition clean.
