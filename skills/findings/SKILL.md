---
name: findings
description: "Populate, extend, refresh, or audit a project's docs/reference/key-findings.md — a curated index of headline empirical findings and interpretations with confidence tags and standardized source footers. Use when the user wants to draft a new findings doc, append new entries from recent build artifacts or audit JSONs, refresh load-bearing numbers against the current data, or check completeness."
user_invocable: true
---

# /findings — Populate docs/reference/key-findings.md

Draft, extend, refresh, or audit a project's `docs/reference/key-findings.md`:
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

## Finding the workspace root

The workspace root contains `CLAUDE.md` alongside `projects/`, `pipelines/`, `ideas/`, `research/`. If the current directory is inside a project, search upward to find the root. Use `$ROOT` for all paths below. The project root is `$ROOT/projects/<slug>/` — use `$PROJ` for it.

## Locating the findings doc

Discovery order, first hit wins:

1. `$PROJ/docs/reference/key-findings.md`
2. `$PROJ/docs/key-findings.md`
3. `$PROJ/docs/findings.md`
4. Project-specific path declared in `$PROJ/CLAUDE.md` or `$PROJ/docs/summary.md`

If none exists, ask the user which location to create. Default suggestion is
`docs/reference/key-findings.md`. Do not silently create the file at a
non-canonical path.

## What to read (in order)

Read these files to build context. If one is missing, note it and move on; never invent its content.

1. `$PROJ/CLAUDE.md` — current focus, key terms, conventions
2. `$PROJ/docs/summary.md` — research question (required)
3. `$PROJ/docs/reference/key-findings.md` (if exists) — existing entries; match their template exactly
4. `$PROJ/docs/reference/stylized-facts.md` (if exists) — fact-by-fact ledger; key-findings draws its empirical anchors from here
5. `$PROJ/docs/hypotheses.md` (if exists) — every empirical finding should map to at least one hypothesis or angle
6. `$PROJ/docs/briefs/*.md` — narrative synthesis files; cross-link from findings entries
7. `$PROJ/docs/audits/findings/*.{md,json}` (if exists) — output of `/findings-audit`; this contains anchor quotes and corroborations to fold into entries
8. `$PROJ/build/table/*` and `$PROJ/build/figure/*` — own-analysis artifacts; each load-bearing finding should cite at least one
9. `$PROJ/source/table/*.py` and `$PROJ/source/figure/*.py` — scripts producing the artifacts; cite the script in the Sources footer
10. `$PROJ/references/{cnj,pgfn,ipea,reports,…}/*.pdf` — aggregate reports; needed for `*Reports*` source-class citations with `#page=N` anchors
11. `$PROJ/references/news/stories.csv` and `$PROJ/references/news/texts/*.txt` — news anecdotes; needed for `*News anchors*` source-class citations with anchor quotes
12. `$PROJ/paper/main.tex` (if exists) — load-bearing findings should match what the paper presents; flag drift

## Document structure

Required sections (in order):

```markdown
# Key Findings — <project topic>

<one-paragraph explanation of what this document is and isn't>

This page is the **directory of conclusions**. The companion page
[stylized-facts.md] is the **evidence ledger**. Use this page to scan
what we believe; use that page to look up the raw numbers.

---

## How to read the confidence tags

<confidence-tag scheme — see "Confidence-tag scheme" below; copy verbatim>

---

## Findings overview

<scannable index of every claim with anchored headline links, grouped by
theme: empirical vs interpretive, plus optional sub-themes>

---

## Empirical findings — detail

### <Finding headline 1>

<entry body — see "Entry schema" below>

### <Finding headline 2>

...

---

## Interpretations — detail

<bullet preamble: "The bullets below go beyond pure description — they
are readings of the evidence. Each names the empirical findings it draws
on, so a reader can challenge the inference without challenging the
underlying data.">

### <Interpretation headline 1>

...

---

## Open items for this page

<bulleted list of known gaps, pending replications, confidence-upgrade
candidates>
```

## Confidence-tag scheme (verbatim — copy into `## How to read the confidence tags`)

A traffic-light convention runs across both scales: 🟢 = strongest confidence, 🟡 = middle, 🔴 = weakest. The *meaning* of each color depends on whether the claim is empirical or interpretive.

**Empirical findings** — the color reflects the *source* of confidence, not the size of the effect:

- 🟢 **Replicated** — the finding appears in multiple independent samples or studies that agree in direction and rough magnitude.
- 🟡 **Single source** — one solid study, or one of our own runs, with no independent replication yet.
- 🔴 **Provisional** — one descriptive cut that is parser-dependent, sensitive to sample definition, or flagged with a known caveat. Read the qualifier before quoting.

**Interpretations** — parallel scheme:

- 🟢 **Strong** — multiple converging lines of evidence; alternatives have been considered and rejected.
- 🟡 **Plausible** — consistent with the evidence but other readings remain open.
- 🔴 **Speculative** — suggested by the data but unverified; flagged for follow-up rather than relied on.

## Entry schema

Every empirical finding and interpretation entry must contain, in this order:

1. **Confidence tag + headline sentence.** First non-blank line of the entry's body. Format: `🟢/🟡/🔴 <one-sentence summary with the load-bearing number>`.
2. **Expanded explanation.** Plain prose, 1–4 paragraphs, with inline anchored citations (no bare `[CNJ-DIAG22 p.198]` — use `[CNJ-DIAG22 p.198](../../references/cnj/file.pdf#page=198)` instead).
3. **Optional sub-paragraphs** for updates, robustness, caveats — each prefixed with a bold header like `**Forward-look caveat (added YYYY-MM-DD).**` so the reader can date the addition.
4. **Optional figure embed** with italicized caption underneath.
5. **The Sources footer** — see "Sources footer" below. Required, standardized, four-class.
6. **Optional Draws-on / Cross-refs paragraph** if the entry is an interpretation. Lists the empirical findings the inference rests on, by anchor link.

## Sources footer (the standard schema)

Every entry's footer is structured into four bulleted classes. Missing classes appear as `*<class>*: none direct` rather than being omitted — explicit absence is informative.

```markdown
**Sources.**
- *Own analysis*: <build artifacts and scripts as clickable file paths>
- *Reports*: <aggregate-report citations with `#page=N` deep links>
- *News anchors*: <`texts/NNN.txt` links + anchor quote when load-bearing>
- *Cross-refs*: <stylized-facts §, briefs/, audits/, related findings>
```

Path conventions (when the doc lives at `docs/reference/key-findings.md`):
- Build artifacts: `[`stem.csv`](../../build/table/stem.csv)`
- Scripts: `[`stem.py`](../../source/table/stem.py)`
- Reports with page: `[CNJ-DEF24 p.205](../../references/cnj/justica_em_numeros_2024.pdf#page=205)`
- News texts: `[outlet YYYY-MM-DD (short topic)](../../references/news/texts/NNN.txt)`
- Cross-refs to other docs in `$PROJ/docs/`: `[stylized-facts §X](stylized-facts.md#anchor)` (same dir) or `[briefs/Y §Z](../briefs/Y.md#anchor)` (sibling dir)

For news anchors that carry a load-bearing quote, append the quote inline:
> [Folha 2026-03 (Cucolo, Pesquisa Patrimonial CNJ)](../../references/news/texts/070.txt) — anchor: *"a execução de sentenças judiciais que determinam o pagamento de dívidas seja hoje um dos principais gargalos do Judiciário"*

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
