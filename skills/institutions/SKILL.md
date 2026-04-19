---
name: institutions
description: "Populate or audit a project's docs/institutions.md using the shared institutional reference (research/institutions/brazil/ for Brazil projects). Bootstraps from shared topic files and artigos.db; marks gaps for manual curation."
user_invocable: true
---

# /institutions — Populate or audit institutional background

Build or update a project's `docs/institutions.md` by pulling relevant
material from the shared institutional reference and resolving statutory
citations against `artigos.db`.

## Arguments

- `/institutions` — bootstrap from scratch (new project) or audit an
  existing `institutions.md` against the shared reference for gaps
- `/institutions update` — re-check existing file against current shared
  reference; add new sections for topics not yet covered
- `/institutions audit` — verify citations resolve, flag stale claims,
  check coverage against shared reference without adding content

If no project slug is given, infer from the current working directory.

## Pipeline overview

```
1. Find workspace root & project
2. Detect country → select shared reference
3. Read project context
4. Identify relevant institutional domains
5. Read relevant shared-reference topic files
6. Draft / update institutions.md
7. Verify citations
8. Report
```

## Step-by-step

### 1. Find workspace root and project

Locate `$ROOT` by searching upward for `CLAUDE.md` next to `projects/`
and `pipelines/`. Resolve the project path: `$ROOT/projects/{slug}/`.

Set:
- `$INST` = `$ROOT/research/institutions/brazil` (Brazil projects)
- `$CITE` = `$INST/tools/leis_artigos/cite.py`
- `$DB` = `~/research/data/lei/artigos.db`

### 2. Detect country

Read `$PROJECT/CLAUDE.md` and `$PROJECT/docs/summary.md`. If the project
is Brazil-focused (most projects in this workspace are), use
`$ROOT/research/institutions/brazil/` as the shared reference.

For non-Brazil projects: skip the shared reference entirely. Scaffold
`institutions.md` with section headings derived from the project context
and mark every section `**TODO: requires manual curation**`. Report to
the user that no shared reference exists for this country. Stop here.

### 3. Read project context

Read these files to understand what institutional domains matter:

- `docs/summary.md` (required — stop if missing)
- `docs/thinking.md`
- `docs/methods.md`
- `docs/hypotheses.md`
- `docs/institutions.md` (existing content, if any)
- `paper/*.tex` (scan introduction and institutional background sections)
- `CLAUDE.md`

Extract:
- The core research question and identification strategy
- Key institutional actors (courts, agencies, registries, etc.)
- Statutory anchors mentioned or implied
- Procedural details relevant to the research design

### 4. Identify relevant institutional domains

Using the project context, identify which shared-reference topic files
are relevant. Do this by:

1. **Grep the topic keyword lines.** Each file in `$INST/topics/` has a
   `Topics / keywords` line near the top. Search these for project
   keywords (bilingual — Portuguese and English).

2. **Consult the indices.** Grep `$INST/siglas.md` for acronyms found in
   the project context. Each entry points to a topical file.

3. **Check `$INST/README.md`** for the organized index of all 26 topic
   files. Scan section headings to catch domains the keyword search missed.

4. **Check `$INST/quasi-experimentos.md`** if the project uses a
   quasi-experimental design — it indexes identification strategies
   embedded in Brazilian institutions.

5. **Check `$INST/data_pointers.md`** for data sources relevant to the
   project's datasets.

Produce a list of 3–8 relevant topic files, ranked by importance.
Show the list to the user before proceeding unless they said "go ahead".

### 5. Read relevant shared-reference topic files

For each relevant topic file, read it fully. Also read:

- `$INST/leis_index.yaml` — for statutes relevant to the project
- `$INST/glossario.md` — for terms that need precise definition
- `$INST/pitfalls.md` — for common mistakes in this domain
- `$INST/jurisprudencia_index.yaml` — if STF cases matter
- `$INST/sumulas_vinculantes.yaml` — if binding summaries are cited
- Any YAML index entry that references a relevant statute or case

**Do not read all 26 topic files.** Only read the ones identified in
step 4. The shared reference is large; relevance filtering is critical.

### 6. Draft or update institutions.md

#### Mode: bootstrap (no existing file or file is a stub)

Write `docs/institutions.md` following the project docs contract format.
Structure it around the project's institutional needs, not the shared
reference's organization.

For each section:

- **Pull institutional facts** from the shared-reference topic files.
  Rewrite for project relevance — don't copy paragraphs verbatim.
  The project's institutions.md should explain why each fact matters
  *for this project's research design*, not just state the fact.

- **Use backtick citations** for statutory references. For every statute
  cited, use the canonical compact form (`` `CDC.43.§2` ``,
  `` `CF.31.§2` ``). Run `$CITE '<citation>'` to verify it resolves
  before writing it. If it doesn't resolve, use a prose mention with a
  planalto.gov.br link instead.

- **Do not paste statutory text.** The whole point of `artigos.db` is
  that Claude can look up article text on demand. In `institutions.md`,
  characterize what the article says and why it matters; don't quote it.
  Exception: for the 2–3 most load-bearing provisions (the ones that
  define the treatment, the assignment mechanism, or the sample), a
  brief inline quote is acceptable with the backtick citation alongside.

- **Mark gaps.** For project-specific institutional facts that can't be
  derived from the shared reference (e.g., court-specific assignment
  mechanics, agency-specific data practices, sample-specific
  empirical facts), write a placeholder:
  `**PROJECT-SPECIFIC — needs manual curation:** [description of what's needed]`

- **Mark unverified claims.** For facts pulled from the shared reference
  that the reference itself flags as time-volatile or unverified:
  `**NEEDS PRIMARY SOURCE:** [what needs checking]`

- **Cross-reference the paper.** Where possible, note which paper
  section each institutional section feeds (e.g., "Key for §2.1").
  This maintains the serasa-style table of contents.

#### Mode: update (existing file, `--update` or default for non-empty file)

Read the existing `institutions.md`. For each section in the shared
reference that the project context suggests is relevant:

- If the section is already covered: leave it alone (do not rewrite
  existing content — the human curated it for a reason)
- If the section is missing: draft it and append, clearly marked as
  `**[NEW — from shared reference, needs review]**`
- If the section exists but the shared reference has newer information
  (check `Snapshot as of` dates): add a note
  `**[shared reference updated YYYY — check for changes]**`

#### Mode: audit (`--audit`)

Do not add content. Only:
1. Run `$CITE --find-in docs/institutions.md` to check all citations
2. Flag citations that don't resolve
3. Check coverage: list shared-reference topics that seem relevant but
   aren't covered in the file
4. Check for `**NEEDS PRIMARY SOURCE**` markers that are still open
5. Report findings

### 7. Verify citations

After writing or updating, run:

```bash
python3 $CITE --find-in $PROJECT/docs/institutions.md
```

Review the output:
- Every backtick citation should resolve. If any don't, either fix the
  citation form or revert to prose mention.
- Report the resolution rate to the user.

### 8. Report

Output a structured summary:

- **File:** `docs/institutions.md`
- **Mode:** bootstrap / update / audit
- **Shared-reference topics used:** list of topic files consulted
- **Sections written/updated:** list
- **Citations:** total / resolved / failed
- **Gaps marked:** count of `**PROJECT-SPECIFIC**` and `**NEEDS PRIMARY SOURCE**` markers
- **Coverage notes:** any relevant shared-reference topics not yet in the file

## Principles

### What institutions.md is for

The audience is Claude in future sessions. The file grounds the agent on
institutional details so it can:
- Write accurate paper prose without hallucinating institutional facts
- Make research-design suggestions that respect institutional constraints
- Understand why the data looks the way it does

It is **not** a paper draft and not a copy of the shared reference. It's
a project-specific selection of institutional facts, attributed and
citation-linked, that Claude should trust as the source of truth for
this project.

### Relationship to the shared reference

The shared reference (`research/institutions/brazil/`) is the canonical,
cross-project repository of institutional knowledge. Project-level
`institutions.md` files select from it and add project-specific context.

- Shared reference = general, authoritative, cross-cutting
- Project institutions.md = project-specific, curated, design-oriented

The skill bridges the two. It should never duplicate the shared reference
wholesale — only pull what this project needs.

### Citation conventions

- **Statutes:** Use backtick form (`` `CDC.43.§2` ``) for all statutory
  references. Always verify via `cite.py` before writing.
- **STF cases:** Use backtick form (`` `Tema1199` ``, `` `ADI4650` ``)
  when the case is in `jurisprudencia_index.yaml`.
- **Súmulas:** Use backtick form (`` `SV14` ``, `` `STSE38` ``).
- **Non-cataloged sources:** Use prose with a URL or full citation.
- **Don't paste article text.** Characterize and cite; let `artigos.db`
  serve the text on demand.

### What NOT to put in institutions.md

- Verbatim statute text (use `artigos.db`)
- Generic procedure that applies to any case type (cross-reference
  the shared reference instead)
- Empirical results (those go in `results.md`)
- Speculation (goes in `thinking.md`)
- Literature citations (go in `literature.md`)

## Gotchas

- **cite.py must be run for every new backtick citation.** Don't guess
  whether a citation resolves — verify. Non-cataloged laws won't resolve
  and need prose mentions instead. Currently 37 laws are cataloged.
- **The shared reference is large (~300KB+ across all files).** Don't
  read everything — use the keyword/index strategy in step 4 to
  narrow down to 3–8 topic files.
- **Project-specific facts are the hard part.** The skill can pull
  general institutional background from the shared reference, but
  facts like "TJSP assigns cases by sorteio eletrônico within
  foro-vara" or "plaintiff win-rate is ~80%" come from the project's
  own research. Mark these gaps clearly.
- **Existing content is sacred.** In update mode, never rewrite sections
  the human has already curated. The human's version is better than
  what the skill would produce — it has project-specific nuance.
- **Don't create a table of contents prematurely.** The serasa-style
  TOC with paper-section mappings is valuable but only makes sense
  when the paper structure is settled. For early-stage projects,
  skip the TOC and organize by institutional domain instead.
- **Check snapshot dates.** Shared-reference topic files have
  `Snapshot as of YYYY` lines. If a topic file hasn't been updated
  since before a major reform, flag the staleness rather than
  silently trusting old content.
- **artigos.db must exist.** If `~/research/data/lei/artigos.db` is
  missing, tell the user to download it from Dropbox (see
  `$INST/tools/leis_artigos/README.md`) and stop. Don't proceed
  without citation verification.
