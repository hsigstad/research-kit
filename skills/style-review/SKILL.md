---
name: style-review
description: LLM-based prose review against the empirical-economics writing style guides. Runs the mechanical linter first, then reads the file against the general baseline and any relevant per-type guides. Use when the user invokes /style-review <file>, asks for a "thorough style review", "polish this for submission", "review for clarity", or wants prose feedback on a paper draft / important email / chapter. For fast deterministic AI-tell scanning, use /style-check; for section-scoped pre-submission validation with ledger writes, use /validate-section.
---

# style-review

Slow, thorough LLM-assisted prose review. Catches what `/style-check`
can't: long/complex sentences, buried verbs, weak topic sentences,
hedging in main claims, paragraph-coherence drift, voice inconsistency,
and formal/informal pairing failures.

Use this for prose that matters: paper drafts, chapters, important
emails, externally-visible blog posts. Don't use it on routine project
docs or working drafts — overkill.

## How to invoke

| Form | What it does |
|------|--------------|
| `/style-review <file>` | Full review. Mechanical linter first, then LLM. Numbered findings; ask which to apply. |
| `/style-review <file> --section <name>` | Restrict the LLM review to one section (intro, abstract, results, etc.). |
| `/style-review <file> --no-fix` | Review only, no edit prompts. |

## Workflow

### 1. Run the mechanical linter

Always start with the deterministic linter:

```bash
python3 ~/research/research-kit/tools/style_lint.py <file> --format json --severity warning
```

If any warning-or-higher violations exist, offer to fix them before the
LLM review. No point reviewing prose the linter would re-flag anyway.

### 2. Resolve section structure

Identify which sections the file contains so the right per-type guides
get loaded. Detection order:

1. **`section_deps.json`** — if the project has
   `build/paper/section_deps.json`, read it. Each entry has a `type`
   field per the convention in
   [`research-kit/rules/section_labels.md`](../../rules/section_labels.md).
2. **LaTeX labels** — if section_deps.json is absent, parse `\label{sec:<type>}`
   directly from the file. The first colon-separated segment after `sec:` is
   the type.
3. **Heading-text heuristic** — if neither is available, infer types
   from heading text per the table in
   [`research-kit/rules/section_labels.md`](../../rules/section_labels.md).

For files without sections (a standalone abstract, a paragraph, an
email): treat the whole file as one section, infer type from filename
or content.

### 3. Load the rule files

Always load the general baseline:

```
research-kit/rules/writing_style.md
```

For each section type encountered, also load the per-type guide:

```
research-kit/rules/writing_style/<type>.md
```

For body-section types (results, methods, data, institutions,
discussion), also load:

```
research-kit/rules/writing_style/body.md
```

If the file is under `~/Dropbox/referee/`, also load:

```
research/referee/style.md
```

If working in the user's workspace, also load the workspace addendum:

```
research/rules/writing_style.md
```

The per-type files state what's specific to each section type; the
general baseline states rules that apply everywhere. Apply both.

### 4. LLM review pass

Read the file. For each section, evaluate against the loaded rules.
Findings to look for:

**General (apply to all sections):**

- Sentence length & structure (default short; flag long sentences that
  could split cleanly).
- Voice (active default; flag passive author actions and unnecessary
  passives).
- Editorializing the data (`starkest`, `most compelling`, `striking`,
  `notable`).
- Topic sentence placement (point buried in sentence 3 or 4).
- Hedging in main claims (caveats that should move to footnotes).
- Adjective stacks, synonym piling.
- Specifics vs. generalities; numbers, not qualifiers.
- Author-coined compounds without inline gloss.
- Formal + informal pairing for technical content.
- Connective overuse (same connective opening multiple paragraphs).
- Signposting bloat ("in this section, we will discuss" when the
  heading already says it).
- Self-categorizing prefaces ("This is a descriptive paper:").

**Per section type:** apply the rules from the loaded per-type file.
Examples:

- Abstract → first sentence states the question; plain-language audience
  test; close with implication.
- Intro → Hook → Question → Why Hard → Setting → Approach → Results →
  Lit → Roadmap; question-first; hook is concrete; lit-contributions
  paragraph near the end.
- Body sections → triangular structure; lead with main result; no
  previews/recalls; economic significance not just statistical.
- Theory → formal+informal pairing; minimum theory required.
- Conclusion → short, no future research, close with implication.

The per-type files are authoritative for type-specific rules. Don't
restate them inline; cite the rule by file:rule-name when reporting.

### 5. Present and apply

For each finding, propose a concrete revision. Format:

```
3. line 47, paragraph on identification:
   buried topic sentence (writing_style.md §5). The point ("we identify
   the effect by …") appears in sentence 4 of 6.
   propose: move sentence 4 to first position; collapse sentences 1-3
   into a one-line setup.

7. line 122 (intro):
   contribution-first opening (writing_style/intro.md hard rules).
   "We construct the first dataset of …"
   propose: open with the research question first; move "We construct…"
   to a later paragraph.

12. line 215 (results):
    "starkest" — editorializing (writing_style.md §2 / writing_style/
    results.md). Replace with direct finding: "the temporal pattern is
    consistent with corruption migrating across margins as oversight
    tightened."
```

Then ask:

```
Respond with:
- "go" or "all"          → apply every proposed revision
- "all except 6,9"       → apply, skip those
- "1,3,5"                → apply only those
- "skip"                 → no edits
```

Apply with the Edit tool. Don't commit automatically.

### 6. Final pass

Re-run the mechanical linter to confirm no new deterministic violations
were introduced.

## When to use vs. the other style skills

| Skill                  | Scope          | Mechanical              | LLM | Ledger |
|------------------------|----------------|-------------------------|-----|--------|
| `/style-check`         | file           | yes (`style_lint.py`)   | no  | no     |
| `/style-review` (this) | file (whole)   | yes (`style_lint.py`)   | yes | no     |
| `/validate-section`    | one section    | yes (`style_lint.py`)   | yes | yes    |
| `/style-revise`        | paragraph      | yes (lints its rewrite) | yes | no     |

Same patterns underneath. This skill is for whole-document review when
the document is worth a thorough pass; `/validate-section` is for
section-scoped pre-submission validation with ledger writes. `/style-revise`
is the earlier-pipeline counterpart: it *reshapes* a rough draft's idea
flow and offers alternative structures, rather than auditing near-final
prose against the guide. Route by draft maturity — rough → `/style-revise`,
near-final → this skill.

## Cost

Reading the file fully and reasoning over every paragraph against the
general baseline plus per-type guides. Long papers take a few minutes of
LLM time. Use `--section <name>` for tighter scope.

## Output discipline

Findings in numbered form, one per item, with:

- Line number(s)
- The current text (short excerpt)
- The proposed revision
- One-sentence justification citing the rule by file/section.

No general praise or summary commentary. The user wants concrete edits.
