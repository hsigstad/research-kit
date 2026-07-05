---
name: theory
description: "Populate or expand a project's docs/theory.md — a structured inventory of formal theoretical frameworks relevant to the project, with testable predictions tied to the project's identification strategy. Use when the user wants to draft, update, or audit theory.md."
---

# /theory — Populate docs/theory.md

Draft or extend a project's `docs/theory.md`: a structured inventory of
formal theoretical frameworks that generate testable predictions the
project's empirical design can adjudicate.

## Arguments

- `/theory` — infer project from the current working directory.
- `/theory <project-slug>` — run against a specific project under `projects/`.
- `/theory --audit` — do not write; report coverage, dangling refs, and missing sections.
- `/theory --extend` — preserve existing entries; only append new frameworks suggested by current evidence/literature.
- `/theory --update <framework-id> [--artifact <AN-id-or-build-path>]` — **surgical single-framework edit**. Update one framework entry (prediction, scope, references) when a new analysis result or literature touchpoint changes how it applies to the project. Reads only `CLAUDE.md`, `theory.md`, and the optional triggering artifact. `--artifact` accepts either an AN id (preferred — e.g. `AN-019`; the skill reads `docs/analyses/an-019-*.md` to recover the relevant empirical content) or a raw `build/<path>` fallback. The framework entry's references back to evidence cite the AN id, not the build path. Does not re-derive other frameworks, does not re-walk `literature.md`/`hypotheses.md`. Use from `/next` step 5 when a run refines a single framework's empirical content. The `<framework-id>` argument is the entry number or name as used in `theory.md`. Numbering is sacred — never renumber (paper and hypothesis cross-refs depend on it).

## Finding the workspace root

The workspace root contains `CLAUDE.md` alongside `projects/`, `pipelines/`, `ideas/`, `research/`. If the current directory is inside a project, search upward to find the root. Use `$ROOT` for all paths below. The project root is `$ROOT/projects/<slug>/` — use `$PROJ` for it.

## What to read (in order)

Read these files to build context. If one is missing, note it and move on; never invent its content.

1. `$PROJ/CLAUDE.md` — current focus, key terms, conventions
2. `$PROJ/docs/summary.md` — research question (required)
3. `$PROJ/docs/thinking.md` — candidate angles, open questions
4. `$PROJ/docs/literature.md` — authoritative list of papers the project cites or positions against
5. `$PROJ/docs/institutions.md` — institutional facts (rules, actors, timelines)
6. `$PROJ/docs/data.md` — what variation/outcomes are available (constrains which predictions are testable)
7. `$PROJ/docs/hypotheses.md` (if exists) — hypotheses already written; theory.md should support them
8. `$PROJ/docs/theory.md` (if exists) — existing entries; match their template exactly and preserve content
9. `$PROJ/paper/main.tex` §introduction and §theory/§model if present
10. `$PROJ/paper/*.bib` — existing bibliography
11. `$PROJ/references/reports/**`, `$PROJ/references/pdfs/**` — technical/policy reports (scan titles + abstracts; read the 2–3 most relevant in full)
12. `$PROJ/references/news/stories.csv` — anecdotal evidence; use only to ground institutional claims, never as a lit reference

## Decide the template

If `docs/theory.md` already exists: infer its template from the current entries. **Match it exactly** — same section headers, same ordering, same level of detail. Do not reformat existing content.

If it does not exist, offer the user three templates and ask them to pick:

- **Numbered frameworks** (saude-style): `## N. Framework name` → Core result → Implication for the project → Key references → Testable predictions → Connection to our design. Ends with an "Overarching framing" section comparing polar views. Best when the paper has a clear identification strategy and a theory-vs-theory framing.
- **Mechanism-centric**: group by mechanism rather than framework. `## Mechanism N. Short name` → Formal model reference → What the mechanism predicts → Evidence already suggestive of the mechanism → How our design isolates it. Best when the paper is decomposing a known phenomenon into channels.
- **Minimal inventory**: one short paragraph per framework (name, core claim, ref, one testable prediction). Best for early-stage projects where theory coverage is exploratory.

For early-stage projects (summary.md says "research question not yet fixed" or equivalent), default to **minimal inventory**, organized by candidate angle from thinking.md. Each candidate angle gets its own sub-section listing the 2–4 frameworks most relevant to it.

## Draft protocol

1. Build a **framework candidate list** from literature.md, existing paper cites, and the research question. For each candidate, record: name, core claim, canonical reference (author + year only; never invent the journal/title if not in literature.md).
2. Filter aggressively. Keep only frameworks that (a) generate a directional prediction and (b) the project's data/design can plausibly adjudicate. Drop frameworks that are merely adjacent or fashionable.
3. For each surviving framework, draft the entry matching the chosen template. For each field:
   - **Core result/idea**: state the theoretical claim precisely. Cite author + year from literature.md. If literature.md doesn't contain the reference, write `[ref needed: {author year}]` — do not fabricate.
   - **Implication / prediction**: make it directional and specific. "X increases Y" beats "X affects Y."
   - **Testable predictions**: each must name a variable and a source of variation the project has or could plausibly get. If none, drop the framework — it's not theory for this paper.
   - **Connection to our design**: reference concrete project elements (judge-IV, event study, specific data source). Generic "could be tested" language is a failure mode — cut it.
4. Aim for **8–15 frameworks**. More than 15 means insufficient filtering. Fewer than 6 means the project is under-theorized; flag that in the output.
5. If the template includes a polar-views framing (saude-style), write it last. It should compress the individual frameworks into 2–3 competing overall predictions, each with a list of supporting frameworks.

## Guardrails (these are the quality bar — do not relax)

- **Never fabricate a reference.** If the canonical citation is not in literature.md, paper/*.bib, or the body of an existing doc, write `[ref needed: ...]`. Placeholder refs are fine; fake refs are not.
- **Never state evidence without a source.** Anecdotal evidence must cite a row in `references/news/stories.csv` by id or a report filename. Institutional facts must cite `docs/institutions.md`.
- **Every testable prediction must map to project data.** If `docs/data.md` does not contain a source that can measure the variable in question, either (a) refine the prediction to fit available data, (b) flag the prediction with `[requires: ...]`, or (c) drop it.
- **Preserve existing content.** If `docs/theory.md` exists and you're in extend mode or normal mode, never rewrite or reorder existing entries. Append new entries at the end, marked with a `Status: drafted YYYY-MM-DD` line.
- **No padding.** If a section would only contain generic statements, leave it empty with a brief TODO rather than filling it. Readers can distinguish an honest gap from a disguised one.
- **Theoretical frameworks only, not empirical findings.** Theory.md is for formal models and their predictions. Empirical results belong in hypotheses.md or results.md.

## Output protocol

1. Print a short preview: framework numbers + names + one-line core claim each. Flag any `[ref needed]` or `[requires: ...]` placeholders.
2. Wait for user confirmation unless they said "go ahead" up front.
3. Write `docs/theory.md`. If the file exists, read it first; merge by appending new entries, never rewriting existing ones.
4. Report back: number of frameworks drafted, number of placeholders that need manual resolution, path to the file. Suggest running `/hypothesis` next if `docs/hypotheses.md` is thin or missing.

## Update mode (`--update <framework-id>`)

Surgical single-framework edit. Use when one framework's prediction,
scope, or reference list needs refinement after a `/next` iteration
surfaced something specific (a new test sharpens the prediction, a
result narrows the framework's domain, a citation needs adding).

**Minimal read set:**

1. `$PROJ/CLAUDE.md` — current focus.
2. `$PROJ/docs/theory.md` — locate the target framework, respect its
   template exactly.
3. The `--artifact` argument (if given). If an AN id: read
   `$PROJ/docs/analyses/an-NNN-*.md` to recover the empirical result;
   the framework's evidence citation uses the AN id. If a
   `build/<path>`: read the artifact directly.
4. The triggering script's IAT docstring (from the AN page's
   `script:` field, or the `source/X.py → build/X.*` convention for
   bare-path artifacts) — for context.

Do **not** re-read `literature.md`, `hypotheses.md`, or any external
literature unless the target framework's citation list would change.

**What to edit:** only the target framework's entry. Preserve the
template (Core result, Testable predictions, Connection to our
design). Update only the field affected by the new result.

**What not to touch:** other frameworks, the document header, the
cross-link to hypotheses.md (unless adding a new hypothesis ref to
the target framework).

**Numbering is sacred:** never renumber. Paper and `hypotheses.md`
cross-refs depend on framework-ID stability.

**Output:** edited `theory.md` plus a one-paragraph summary of what
changed. The summary belongs in the `/next` end-of-iteration report.

## Audit mode (`--audit`)

Do not write. Check:
- Every entry has Core result + Testable predictions + Connection to our design filled (per template).
- Every reference cited in the body appears in literature.md or paper/*.bib.
- Every testable prediction's variable appears in data.md.
- Every framework has at least one link to a hypothesis in hypotheses.md (if hypotheses.md exists). Orphan frameworks that no hypothesis uses are flagged.

Report findings as a bulleted list of gaps. Do not attempt to fix them automatically.

## Interaction with /hypothesis

If hypotheses.md exists and references theory frameworks by number (`Theory: #3 + #7`), preserve the numbering of existing entries when extending. Never renumber — it will break hypotheses.md cross-refs.

## Common failure modes to avoid

- **Generic theory dump.** Listing every framework the user has ever heard of. Filter to what the project can actually test.
- **Fake erudition.** Citing Coase, Arrow, Tirole because they sound appropriate. Only cite if the paper genuinely uses the result.
- **Disconnected predictions.** "This predicts X" with no tie to the project's data. Every prediction must say where X would be measured.
- **Polar-views theater.** Writing a "two views" framing when the evidence clearly favors one view. If the honest read is one-sided, say so.
