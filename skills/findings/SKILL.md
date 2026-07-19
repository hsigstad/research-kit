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

## Document structure

**Default: folder mode** (`docs/findings/`, one file per finding). It matches the
canonical `project_docs_contract.md` §5 and the sibling `docs/hypotheses/` layout, and
is what nearly every project uses. Create it for new projects regardless of entry
count. The flat-file mode below is **legacy**: keep maintaining existing flat
`docs/findings.md` files, but do not create new ones — migrate them to a folder when
convenient (see "Migrating from flat to folder").

### Flat-file mode (`docs/findings.md`) — legacy

Required sections (in order):

```markdown
# Findings — <project topic>

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

### Folder mode (`docs/findings/`) — the default

Use one file per finding — this is the default layout for every project (see the
note under "Document structure"). See the "Folder mode" section below for the full
specification. The `index.md` carries the overview and links; each `<slug>.md`
carries one entry.

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

1. **Confidence tag + headline sentence.** First non-blank line of the entry's body. Format: `🟢/🟡/🔴 <one declarative sentence stating the finding as a claim about the world, with the load-bearing number(s) and AN cite(s)>`. See "Headline rule" below — this is the most quoted line in the doc and the bar is high.
2. **Expanded explanation.** Plain prose, 1–4 paragraphs, with inline anchored citations (no bare `[CNJ-DIAG22 p.198]` — use `[CNJ-DIAG22 p.198](../../references/cnj/file.pdf#page=198)` instead).
3. **Optional sub-paragraphs** for updates, robustness, caveats — each prefixed with a bold header like `**Forward-look caveat (added YYYY-MM-DD).**` so the reader can date the addition.
4. **Optional figure embed** with italicized caption underneath.
5. **The Sources footer** — see "Sources footer" below. Required, standardized, four-class.
6. **Optional Draws-on / Cross-refs paragraph** if the entry is an interpretation. Lists the empirical findings the inference rests on, by anchor link.

## Headline rule

The 🟢/🟡/🔴 line directly under the title is the single most-quoted unit in the doc — it gets linked, screenshotted, and dropped into emails out of context. It has to stand on its own.

1. **One declarative sentence stating the finding as a claim about the world.** Lead with the conclusion. Not a setup sentence, not a meta-introduction.
2. **Self-contained.** A reader landing here from a deep link must be able to parse the sentence without looking at the title or surrounding text. Spell out what "the asymmetry" / "the settlement effect" / "the gap" actually refers to — whose, between what, in what direction. Project-specific terms must be unpacked or replaced.
3. **Flesh out the title, don't echo it.** The title is the same claim in headline form; the sentence adds the load-bearing numbers, units, and scope. If the sentence reads like the title plus a comma, it's wasted space.
4. **Ground load-bearing magnitudes in numbers + AN cites.** Not "substantial" or "large". Significance markers (`*`, `**`, `***`) attach to the numbers they qualify.
5. **No evidence-as-subject, no meta-predicate, no hedged lead.** Confidence comes from the colored dot, not the verb. Avoid:
   - *"The asymmetry is the strongest evidence for X…"* (evidence as subject)
   - *"Three findings converge: …"* / *"Two patterns suggest…"* (meta-predicate)
   - *"X suggests that…"* / *"…is consistent with…"* (hedged lead)
   State the claim, then say why in the explanatory paragraph.
6. **Hard ceiling: 40 words, one sentence.** If you can't fit it in 40 words, the claim is compound — split it, or move secondary clauses into the explanatory paragraph below.

The headline rule applies equally to empirical and interpretation entries. Interpretations are still claims about the world — they just rest on multiple empirical premises (named in the `Draws on:` paragraph).

**Failing headlines look like:**

- *"The settlement effect tripled after the 2017 labor reform."* → what settlement effect, of what on what?
- *"Three findings converge: …"* → meta-predicate; the reader has to assemble the claim.
- *"The inverse value gradient combined with the flat dose-response suggests…"* → evidence-as-subject + hedged lead.
- *"Recusal reform intended to extend recusal to colleagues. Instead, …"* → setup-then-claim; the first sentence carries no information.

**Passing headlines look like:**

- *"Connected-judge assignment moves plaintiff awards by 30–40% (AN-044) but leaves defendant outcomes unchanged across every connection type tested (AN-031) — an asymmetry that contingency-paid plaintiff lawyers vs fixed-wage defendant lawyers can produce, but implicit bias cannot."*
- *"Connected-judge assignment raised the probability of settlement by 2.3pp (ns) before the 2017 labor reform and 7.1pp\*\*\* after — the settlement channel of favoritism roughly tripled (AN-038)."*

## Sources footer (the standard schema)

Every entry's footer is structured into four bulleted classes. Missing classes appear as `*<class>*: none direct` rather than being omitted — explicit absence is informative.

```markdown
**Sources.**
- *Own analysis*: <build artifacts and scripts as clickable file paths>
- *Reports*: <aggregate-report citations with `#page=N` deep links>
- *News anchors*: <`texts/NNN.txt` links + anchor quote when load-bearing>
- *Cross-refs*: <stylized-facts §, briefs/, audits/, related findings>
- *Validation*: <verification status per backing script>   <!-- only when project has validation.yaml -->
```

Path conventions (when the doc lives at `docs/findings.md`):
- Build artifacts: `[`stem.csv`](../build/table/stem.csv)`
- Scripts: `[`stem.py`](../source/table/stem.py)`
- Reports with page: `[CNJ-DEF24 p.205](../references/cnj/justica_em_numeros_2024.pdf#page=205)`
- News texts: `[outlet YYYY-MM-DD (short topic)](../references/news/texts/NNN.txt)`
- Cross-refs to same-dir docs: `[stylized-facts §X](reference/stylized-facts.md#anchor)` or `[briefs/Y §Z](briefs/Y.md#anchor)`

**Analysis ledger.** Every project maintains an analysis ledger
(`docs/analyses/` with `AN-NNN` entries indexed in
`docs/reference/analysis-index.yaml`). Cite the ledger entry in
`*Own analysis*` — e.g. `AN-026` — rather than raw build artifacts.
The ledger entry is the canonical record: it links to the backing
script and holds the results table and interpretation. Bare `AN-NNN`
tokens auto-link on the rendered site.

The finding's headline number must match the AN page's `headline:`
frontmatter (or `## Results` body) at write time. If they disagree,
the AN page wins — finding entries cite the AN; they do not
re-derive the magnitude. Drift between the two is a `--refresh`
target.

For news anchors that carry a load-bearing quote, append the quote inline:
> [Folha 2026-03 (Cucolo, Pesquisa Patrimonial CNJ)](../references/news/texts/070.txt) — anchor: *"a execução de sentenças judiciais que determinam o pagamento de dívidas seja hoje um dos principais gargalos do Judiciário"*

## Folder mode (`docs/findings/`)

The default layout — one file per finding (used for every new project and by
nearly all existing ones):

```
docs/findings/
  index.md           # overview + confidence scheme + linked index + open items
  <slug>.md          # one file per finding
```

### When to use folder vs flat file

- **Folder** (`docs/findings/`): **the default.** One file per finding — per-finding
  pages on the site, cleaner diffs, and you can edit one entry without touching
  others. Use it for every new project and any project going forward, regardless of
  entry count (it matches `project_docs_contract.md` §5 and `docs/hypotheses/`).
- **Flat file** (`docs/findings.md`): **legacy only.** A few early projects still use
  it; migrate to a folder when convenient. Do not create new flat findings docs.

### index.md structure

```markdown
# Findings — <project topic>

<intro paragraph, same as flat-file mode>

---

## How to read the confidence tags

<confidence-tag scheme — identical to flat-file mode>

---

## Findings overview

**<Theme 1>** *(empirical)*

- 🟢 [Headline sentence](slug.md) — one-line summary
- 🟡 [Another headline](another-slug.md) — one-line summary

**Interpretations**

- 🟢 [Interpretation headline](interp-slug.md) — one-line summary

---

## Open items

<bulleted list of gaps, same as flat-file mode>
```

### Per-finding file structure (`<slug>.md`)

Each finding file is standalone:

```markdown
# <Finding headline>

🟡 <Confidence tag + headline sentence with the load-bearing number.>

<Expanded explanation, 1–4 paragraphs.>

**Sources.**
- *Own analysis*: ...
- *Reports*: ...
- *News anchors*: ...
- *Cross-refs*: ...
```

- Heading is `#` (top-level) since the file is standalone.
- Entry schema and Sources footer are identical to flat-file mode.
- For interpretations, include the `**Draws on:** [...]` paragraph
  linking to the empirical findings it depends on, using relative file
  links: `[headline](other-slug.md)`.

### Path conventions in folder mode

Since files live at `docs/findings/<slug>.md`:
- Build artifacts: `[`stem.csv`](../../build/table/stem.csv)`
- Scripts: `[`stem.py`](../../source/table/stem.py)`
- Reports with page: `[CNJ-DEF24 p.205](../../references/cnj/file.pdf#page=205)`
- News texts: `[outlet YYYY-MM-DD](../../references/news/texts/NNN.txt)`
- Sibling docs: `[stylized-facts §X](../reference/stylized-facts.md#anchor)`
- Cross-refs between findings: `[other headline](other-slug.md)`

### File naming

- Slugs are lowercase, hyphens only, ≤40 characters.
- Derive from the heading: "Most exfis do not recover the debt" →
  `most-exfis-do-not-recover.md`.
- Avoid redundant prefixes like `finding-` — the directory provides context.

### Skill behavior in folder mode

- `/findings` (populate): creates `index.md` + one file per finding.
- `/findings --update <slug>`: edits only `docs/findings/<slug>.md` — the
  minimal-read-set is the same as flat-file `--update` mode.
- `/findings --extend`: appends new files and adds entries to
  `index.md`'s overview.
- `/findings --refresh`: walks all `docs/findings/*.md` files, compares
  numbers to build artifacts, reports drift per file.
- `/findings --audit`: checks each file for schema compliance and
  verifies `index.md` links resolve.
- `/findings --footer <slug>`: operates on one file.

### Migrating from flat to folder

When a flat `docs/findings.md` crosses ~20 entries:

1. Create `docs/findings/` directory.
2. Extract `index.md` (intro + confidence scheme + overview + open items).
3. Extract each `### ` entry into `<slug>.md`, promoting heading to `#`.
4. Rewrite overview links from `#anchor` to `slug.md`.
5. Fix relative paths (`../build/` → `../../build/`, etc.).
6. Delete the original `docs/findings.md`.
7. Update `artifacts.yaml` cited_in paths if the project has one.

### Validation badge (only when project has a validation ledger)

The *Validation* line renders per-script status from
`docs/validation.yaml` (or legacy `paper/validation.yaml`). Skip the
line entirely if neither location exists — the project hasn't opted
into the ledger. Schema: `research-kit/meta/validation_ledger.md`.

Format — one line per backing script cited in *Own analysis*:

```markdown
- *Validation*:
  - `h4_pgfn_filtering_break.py` — 🛡 ai-verified (2026-05-08, hash f311796)
  - `h4_cross_exequente_did.py` — ⏳ pending
  - `cnpj_firm_descriptives.py` — ⚠ stale (hash drift since 2026-04-29 sign-off)
```

Status glyph vocabulary (matches `validation.yaml::status`):

- 🛡 **`ai-verified`** — at least one AI check recorded; required-method floor met.
- ✅ **`human-verified`** — human reviewer signed off; hash matches reviewed bytes.
- ⏳ **`pending`** — row exists but no checks have run yet.
- ⚠ **`stale`** — script hash (or closure hash) has drifted since the recorded check date.

**Don't fabricate.** If a backing script isn't in `validation.yaml`,
omit it from the *Validation* block rather than guessing. Missing
script in the ledger means /next step 5d didn't add it, which is
itself a flag — log it in the entry's body, not as a fake validation
status.

**Confidence tag vs validation status are different axes** —
*confidence* (🟢/🟡/🔴) is about source robustness (replicated vs
single-source vs provisional); *validation* (🛡/✅/⏳/⚠) is about
verification of the analysis code. A finding can be 🟢 single-source
ai-verified, 🟡 single-source pending, or 🟢 replicated stale —
all meaningful.

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
