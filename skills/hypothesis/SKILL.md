---
name: hypothesis
description: "Populate or expand a project's docs/hypotheses.md (or docs/hypotheses/ folder) — testable predictions linking theory (docs/theory.md or docs/literature.md) to evidence and the project's empirical design. Use when the user wants to draft, update, or audit hypotheses."
user_invocable: true
---

# /hypothesis — Populate docs/hypotheses.md

Draft or extend a project's `docs/hypotheses.md` (or `docs/hypotheses/`
folder): a structured mapping of theoretical predictions to pre-existing
evidence and concrete empirical tests the project can run. Each
hypothesis is a single testable claim with its theory, evidence,
specification, and data requirement spelled out.

## Locating the hypotheses doc

Discovery order, first hit wins:

1. `$PROJ/docs/hypotheses.md` (flat file)
2. `$PROJ/docs/hypotheses/index.md` (folder mode)

If neither exists, ask the user which to create. Default to flat file for
<15 hypotheses, folder for 15+.

## Arguments

- `/hypothesis` — infer project from the current working directory.
- `/hypothesis <project-slug>` — run against a specific project under `projects/`.
- `/hypothesis --audit` — do not write; report gaps, dangling refs, and orphan theories.
- `/hypothesis --extend` — preserve existing entries; only append new hypotheses suggested by current evidence/literature.
- `/hypothesis --update <H#> [--artifact <AN-id-or-build-path>]` — **surgical single-entry edit**. Update the status block (or evidence/test fields) of one existing hypothesis after a new analysis result. Reads only `CLAUDE.md`, `hypotheses.md`, and the optional triggering artifact. `--artifact` accepts either an AN id (preferred — e.g. `AN-019`; the skill reads `docs/analyses/an-019-*.md` to recover script + target + headline + confidence) or a raw `build/<path>` (fallback for unledgered runs). Does not re-derive other hypotheses, does not re-read `theory.md`/`literature.md`/etc. Use from `/next` step 5 when a run affects exactly one hypothesis (demotion after null, strengthening after a confirming test, status-block refresh).

## Finding the workspace root

The workspace root contains `CLAUDE.md` alongside `projects/`, `pipelines/`, `ideas/`, `research/`. If the current directory is inside a project, search upward to find the root. Use `$ROOT` for all paths below. The project root is `$ROOT/projects/<slug>/` — use `$PROJ` for it.

## What to read (in order)

Read these files to build context. If one is missing, note it and move on; never invent its content.

1. `$PROJ/CLAUDE.md` — current focus, key terms, conventions
2. `$PROJ/docs/summary.md` — research question (required)
3. `$PROJ/docs/thinking.md` — candidate angles, open questions
4. `$PROJ/docs/theory.md` — formal frameworks; every hypothesis should link to at least one framework here. If missing, suggest running `/theory` first.
5. `$PROJ/docs/literature.md` — empirical literature the paper cites or positions against. Hypotheses should be aware of what's already known.
6. `$PROJ/docs/institutions.md` — institutional facts (rules, actors, timelines)
7. `$PROJ/docs/data.md` — what variation/outcomes are available. Hypotheses without a data home get cut or flagged.
8. `$PROJ/docs/methods.md` (if exists) — identification strategy details
9. `$PROJ/docs/hypotheses.md` or `$PROJ/docs/hypotheses/index.md` (if exists) — existing hypotheses; match their template exactly and preserve content
10. `$PROJ/paper/main.tex` §introduction, §hypotheses, §empirical if present
11. `$PROJ/paper/*.bib` — existing bibliography
12. `$PROJ/references/reports/**`, `$PROJ/references/pdfs/**` — technical/policy reports (scan titles; read the 3–5 most relevant in full)
13. `$PROJ/references/news/stories.csv` — anecdotal evidence; sample the full text of 5–10 rows most relevant to each candidate hypothesis via `texts/NNN.txt`
14. Project-specific evidence files (e.g., `$PROJ/docs/scheme_evidence.md` in procure) — scan for existing evidence a hypothesis can cite

## Decide the template

If `docs/hypotheses.md` already exists: infer its template from the current entries. **Match it exactly** — same section headers, same ordering of fields, same prose style. Do not reformat existing content.

If it does not exist, offer the user three templates:

- **Tiered by evidence strength** (saude-style): group by `## Tier 1: Very Strong Pre-Existing Evidence`, `## Tier 2: Strong, Directly Testable`, `## Tier 3: Plausible, Partially Testable`. Each entry: Theory → Prediction → Pre-existing evidence (bulleted with sources) → Evidence strength + justification → Empirical test → Data → Priority. Best when there's a rich pre-existing empirical literature to assess against.
- **Clustered by paper section** (procure-style): group by `## Cluster A: ...`, mapping each cluster to a paper section. Each entry: Statement (bold sentence) → Theoretical motivation (paragraph with refs) → Case evidence (paragraph with refs) → Empirical test (outcome / variation / specification / fixed effects) → Data requirements and limitations. Best when hypotheses map cleanly to distinct paper sections with concrete empirical specs.
- **Exploration-first**: group by candidate angle from thinking.md. Each angle gets 2–4 hypotheses with a looser template (Prediction → Why it matters → What evidence already exists → How we'd test it → What data we'd need). Best for early-stage projects without a fixed research question.

For early-stage projects (summary.md says "research question not yet fixed" or equivalent), default to **exploration-first**.

## Draft protocol

1. Build a **hypothesis candidate list**. For each framework in theory.md (or each mechanism in the relevant literature if theory.md is missing), enumerate the directional predictions that the project's data could adjudicate. For each candidate, record: short name, theory ref, prediction (1 sentence), variable(s) it touches.
2. Filter aggressively. Drop candidates where (a) no variation in the project's data can identify the prediction, (b) the prediction is already established well enough in the literature that another test adds nothing, or (c) two candidates collapse into the same empirical spec — keep the tighter framing.
3. For each surviving hypothesis, draft the entry matching the chosen template. If the project's existing entries have a `**Slug:**` field, assign a slug to each new entry (lowercase, hyphenated, 2-4 words, e.g., `value-interaction`, `recusal-selective`). Slugs must be unique and stable — they are used as identifiers in analysis tracking systems. For each field:
   - **Theory / Theoretical motivation**: name the framework from theory.md (by number or name). If the theory isn't in theory.md, either add a stub there or write `[theory: {author year} — not yet in theory.md]`.
   - **Prediction / Statement**: directional and specific. "Higher X causes higher Y in subgroup Z" beats "X is related to Y."
   - **Pre-existing evidence / Case evidence**: every bullet must cite a specific source. Sources can be:
     - A news row: `[stories.csv #NNN]` with a short description
     - A report: `[{filename.pdf}, p. N]`
     - A lit entry: `[Author Year]` where the entry exists in literature.md or paper/*.bib
     - An institutional fact: `[institutions.md §N]`
     - Never cite from memory — only from materials actually in the project.
   - **Evidence strength**: rate honestly (Very strong / Strong / Moderate / Weak) and justify in one sentence. If mixed, say so.
   - **Empirical test**: specify the concrete specification — outcome variable, source of variation, the statistical form (OLS / IV / event study / density test / etc.), fixed effects. Reference data.md for data sources.
   - **Data requirements / limitations**: name datasets and flag any the project does not yet have access to. Note threats to identification.
   - **Priority** (if template includes it): rank by (evidence strength) × (testability with current data) × (distinctiveness — does this test something no one else can?).
4. Aim for **8–14 hypotheses**. More means insufficient filtering. Fewer than 6 means the project is under-developed or the filtering was too aggressive.
5. If the template includes a summary table, write it after all entries. It should make the whole hypothesis space scannable in one screen.

## Folder mode (`docs/hypotheses/`)

When the project has 15+ hypotheses or individual entries grow long
(accumulating evidence blocks, robustness notes, status updates),
promote to a folder:

```
docs/hypotheses/
  index.md           # intro + field schema + cluster index + summary table
  <slug>.md          # one file per hypothesis, named by slug field
```

### index.md structure

- Title and intro paragraph
- "How to read this document" field descriptions
- Cluster sections with brief descriptions and bulleted links to
  individual files: `- [H1: Headline](slug.md)`
- Cross-cluster notes (e.g., mechanisms taxonomy references)
- Summary table at the end

### Per-hypothesis file (`<slug>.md`)

```markdown
# H<N>: <Title>

- **Slug:** <slug>
- **Theory:** ...
- **Prediction:** ...
- **Competing prediction:** ...
- **Pre-existing evidence:** ...
- **Evidence strength:** ...
- **Empirical test:** ...
- **Data requirements:** ...
```

### File naming

Use the **Slug** field as the filename (e.g., `plaintiff-awards.md`).
No numeric prefixes — ordering lives in `index.md`, not filenames.

### Path conventions

Since files live at `docs/hypotheses/<slug>.md`:
- Theory: `[theory.md](../theory.md)`
- Mechanisms: `[mechanisms.md](../reference/mechanisms.md)`
- Build artifacts: `[stem.csv](../../build/table/stem.csv)`
- Cross-refs between hypotheses: `[H<N>](other-slug.md)`

### Skill behavior in folder mode

- `/hypothesis` (populate): creates `index.md` + one file per hypothesis.
- `/hypothesis --update <slug>`: edits only `docs/hypotheses/<slug>.md`.
- `/hypothesis --extend`: appends new files and adds entries to index.
- `/hypothesis --audit`: checks each file for schema compliance and
  verifies index links resolve.

## Guardrails (these are the quality bar — do not relax)

- **Never fabricate a reference.** If the citation is not in literature.md, paper/*.bib, or the body of an existing doc, write `[ref needed: ...]`. Placeholder refs are fine; fake refs are not.
- **Never state evidence without a specific source.** Every bullet in "pre-existing evidence" must end with a bracketed source pointer. A bullet without a source is a failure — delete or source it.
- **Every hypothesis must be testable with project data.** If `docs/data.md` does not contain a source that can measure the outcome and variation involved, either (a) refine the hypothesis to fit available data, (b) flag with `[requires: dataset X — not yet accessed]`, or (c) drop it.
- **Every hypothesis must reference a theory.** Either an entry in theory.md or a formal citation to a paper. "We expect X" without theoretical backing is a prior, not a hypothesis — cut it.
- **Preserve existing content.** If `docs/hypotheses.md` exists, read it first. In extend/normal mode, never rewrite existing entries. Append new entries after the last existing one, marked with a `Status: drafted YYYY-MM-DD` line.
- **No padding.** If a section would be generic, leave it empty with a brief TODO.
- **Honest tier assignment.** Pushing a weakly-supported hypothesis into Tier 1 because it's the paper's central claim is a failure mode. Tier reflects *existing* evidence, not the paper's ambition.

## Output protocol

1. Print a short preview: hypothesis numbers + short names + one-line predictions, grouped by tier/cluster. Flag any `[ref needed]`, `[theory: not yet in theory.md]`, or `[requires: ...]` placeholders.
2. If more than 3 placeholders appear, pause and ask the user whether to proceed, revise inputs first, or run `/theory` and `/literature` first.
3. Wait for confirmation unless the user said "go ahead."
4. Write `docs/hypotheses.md`. Read first if it exists; merge by appending, never rewriting.
5. Report back: number of hypotheses drafted, number of placeholders, path to the file. Cross-reference theory.md (which frameworks were used, which were orphaned).

## Update mode (`--update <identifier>`)

Surgical single-entry edit. The identifier can be a **slug**
(e.g., `value-interaction`) or a legacy H-number (e.g., `H13`).
Slugs are preferred — they are stable across reordering. If the
project's hypotheses.md has a `**Slug:**` field, always match on
that. Fall back to H-number only if no slugs exist.

**Citation convention:** Cross-references to hypotheses in any doc
use the `H:<slug>` notation (e.g., `H:plaintiff-awards`,
`H:value-interaction`). This is greppable, unambiguous, and stable.
When writing or updating any document that references a hypothesis,
use this notation instead of bare H-numbers.

Use when one hypothesis's status changed (demoted after a null,
strengthened after a confirming test, evidence list refreshed,
priority retiered) and the rest of `hypotheses.md` should remain
untouched.

**Minimal read set** — do not re-read the full briefing pack:

1. `$PROJ/CLAUDE.md` — for current focus and naming conventions.
2. `$PROJ/docs/hypotheses.md` or `$PROJ/docs/hypotheses/<slug>.md` — to
   locate the target entry and respect its template exactly.
3. The `--artifact` argument (if given). If an AN id: read
   `$PROJ/docs/analyses/an-NNN-*.md` to recover the script, target,
   headline, and confidence — cite the AN id (e.g. `AN-019`) in the
   evidence row, not the build path. If a `build/<path>`: read the
   artifact itself.
4. The triggering script's IAT docstring (derived from the AN page's
   `script:` field, or from the `source/X.py → build/X.*` convention
   for bare-path artifacts) — for context.

Do **not** re-read `theory.md`, `literature.md`, `institutions.md`,
`data.md`, or any other context unless the target hypothesis's text
explicitly cites them and the update would change those citations.

**What to edit:** only the target hypothesis's entry. Preserve the
template (fields, order, prose style) inferred from neighboring
entries. Add or update only the fields the new result affects —
typically the status block, the evidence list, or the priority tag.
Evidence-table rows that point at this hypothesis should use the AN
id (`AN-019`) as the anchor, not a bare build path.

**Back-link to the AN page.** When --artifact is an AN id and the AN
page's `hypothesis:` frontmatter field is null or different from
this hypothesis's slug, update the AN page's `hypothesis:` field to
match. Both sides of the link should agree.

**What not to touch:** other hypotheses, the document header, the
summary table (if present), or any cross-cutting structure.

**Identifiers are sacred:** never renumber or rename slugs. Paper
cross-refs and analysis-index.yaml tags depend on their stability.

**Output:** the edited `hypotheses.md` plus a one-paragraph summary
of what changed (which fields, before → after, what artifact was
cited). The summary belongs in the `/next` end-of-iteration report.

## Audit mode (`--audit`)

Do not write. Check:
- Every hypothesis has all required template fields filled.
- Every reference in the body exists in literature.md, paper/*.bib, institutions.md, or references/news/stories.csv.
- Every outcome variable named in "empirical test" is covered by data.md.
- Every theory cited exists in theory.md.
- Every theory in theory.md is used by at least one hypothesis (flag orphans).
- Priority/tier fields are filled and consistent (no "Very strong evidence" hypotheses in Tier 3, etc.).

Report findings as a bulleted list of gaps. Do not fix them automatically.

## Interaction with /theory

- If `docs/theory.md` is missing or has fewer than 3 entries, stop and suggest running `/theory` first. Do not draft hypotheses against an empty theoretical frame.
- If new frameworks emerge while drafting hypotheses (an implied theory that isn't in theory.md yet), collect them and emit a final note recommending the user run `/theory --extend` with those framework names.
- Preserve existing identifiers when extending. Never renumber H-numbers or rename slugs — analysis-index.yaml tags and paper cross-refs depend on their stability.

## Early-stage projects

When summary.md signals "research question not yet fixed" (or the project is genuinely exploratory), do not force hypotheses into tiers. Instead, for each candidate angle in thinking.md:

1. Write a brief angle header with 1–2 sentences on why it's a candidate direction.
2. List 2–4 hypotheses under each angle using the exploration-first template.
3. End with a "Comparison table" that lets the user see at a glance which angle has the richest evidence, the cleanest identification, and the tightest predictions. This helps the user commit to an angle.

The file's purpose in this mode is to *inform the choice of research question*, not to lock in a test plan. Label it as such in the document's header.

## Common failure modes to avoid

- **Unsourced evidence.** Writing "X is well-documented" without a citation. Every evidence claim cites something the reader can open.
- **Fake erudition.** Citing Kleven, Pomeranz, Galanter because they sound appropriate. Only cite if the paper actually uses the result and the reference exists in project materials.
- **Untestable predictions.** "Firms respond strategically to enforcement" — unmeasurable. "Firms close the targeted CNPJ within 18 months of an execução fiscal filing, more so when the firm has a related CNPJ receiving worker transfers" — measurable.
- **Theory-free hypotheses.** A prior masquerading as a hypothesis. Every hypothesis earns its place by connecting theory to a testable prediction.
- **Copy-paste from other projects.** Hypotheses from saude or procure do not transfer. Each project's hypotheses must be grounded in its own evidence and data.
