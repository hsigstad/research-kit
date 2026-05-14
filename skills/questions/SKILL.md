---
name: questions
description: "Populate or update a project's docs/questions.md — the 3-5 policy-relevant research questions the project answers, each synthesizing evidence from multiple hypotheses. Use when the user wants to draft, update, or audit questions.md."
user_invocable: true
---

# /questions — Populate docs/questions.md

Draft or maintain a project's `docs/questions.md`: the small set of
policy-relevant questions the research answers. Each question aggregates
evidence from multiple hypotheses and maintains a current working answer
that evolves as new results come in.

These are **synthesis** questions — the "so what?" that motivates the
paper and frames the contribution. They sit above the hypothesis layer:
hypotheses are testable predictions; questions are what the predictions
collectively tell us.

## What questions.md is NOT

- Not a staging area for half-formed ideas (that's `thinking.md`)
- Not a list of descriptive queries ("what share of cases have X?")
- Not a restatement of hypotheses (those have their own doc)
- Not a research agenda (keep it to what THIS project answers)

## Arguments

- `/questions` — infer project from CWD
- `/questions <project-slug>` — run against a specific project
- `/questions --update <Q:slug> [--artifact <path>]` — update one
  question's working answer after new evidence (e.g., from `/connect-results`)
- `/questions --audit` — check for stale answers, missing hypothesis refs,
  orphan questions with no tested hypotheses
- `/questions --extend` — propose a new question (requires justification)

## Finding the workspace root

The workspace root contains `CLAUDE.md` alongside `projects/`, `pipelines/`,
`ideas/`, `research/`. If inside a project, search upward. `$ROOT` for paths;
`$PROJ = $ROOT/projects/<slug>/`.

## What to read

1. `$PROJ/CLAUDE.md` — current focus
2. `$PROJ/docs/summary.md` — the main research question (required)
3. `$PROJ/docs/questions.md` — existing questions (if any; match template)
4. `$PROJ/docs/hypotheses.md` — all hypotheses with evidence strengths
5. `$PROJ/docs/findings.md` — empirical results (if exists)
6. `$PROJ/docs/reference/analysis-index.yaml` — what's been tested (if exists)

Do NOT read theory.md, literature.md, institutions.md unless a specific
question's answer needs institutional context. Questions synthesize from
hypotheses, not from primary sources.

## Entry template

Each question follows this structure:

```markdown
### Q:<slug>: <Question in natural language?>

**Relevant hypotheses:** H:<slug1>, H:<slug2>, ...

**Current working answer:**
<2-5 sentences synthesizing what the tested hypotheses tell us.
Cite specific numbers from results. Note where evidence is strong
vs suggestive. Write as you would for a non-specialist.>

**Open:** <What remains untested or ambiguous. Reference specific
H: slugs with their status (not tested / queued / interpreted).>
```

## Conventions

### Slugs

Each question has a stable slug prefixed with `Q:` (e.g.,
`Q:does-favoritism-exist`, `Q:how-circumvented`). Slugs are:
- Lowercase, hyphenated, 2-5 words
- Unique within the project
- Never renamed once created (same stability rule as H: slugs)
- Used for cross-referencing in analysis files, index tags, and prose

### Scope

- Aim for **around 5 questions** per project. This is a soft limit —
  adding a 6th or 7th is fine if genuinely warranted, but each new
  question should pass the bar: "would a policymaker or seminar
  audience ask this?" If not, it's probably a hypothesis or a
  thinking.md note, not a research question.
- Questions must be answerable (at least partially) by the project's
  data and design. Aspirational questions belong in thinking.md.
- Questions should be policy-relevant or have clear "so what?" value.
  Pure mechanism questions ("through which channel?") are fine if the
  channel has policy implications.

### Working answers

- Write for a non-specialist. No jargon, no regression notation.
- Cite specific numbers from results (coefficients, percentages).
- Be honest about uncertainty. "The evidence suggests..." not
  "We have shown..."
- Update after each `/connect-results` (or equivalent) run that
  changes the evidence base for any relevant hypothesis.
- Date-stamp is NOT needed — git history tracks when answers changed.

### Relationship to other docs

- **summary.md** states the main research question in 1-2 sentences.
  questions.md decomposes it into answerable sub-questions.
- **hypotheses.md** contains the testable predictions. questions.md
  groups them and synthesizes their answers.
- **findings.md** records individual empirical results.
  questions.md interprets what they mean collectively.
- **thinking.md** holds open-ended speculation. When a thinking.md
  note matures into something the project can answer, it may become
  a question. Most won't.

## Draft protocol (new file)

1. Read summary.md to identify the paper's core motivation.
2. Read hypotheses.md to understand what's testable.
3. Identify 3-5 questions that a seminar audience or policymaker would
   ask, such that the hypotheses collectively address them.
4. For each question: list the relevant H: slugs, draft a working
   answer from current evidence, note what's still open.
5. Present the list to the user for confirmation before writing.

## Update mode (`--update Q:<slug>`)

Surgical edit of one question's working answer. Triggered when new
evidence arrives (typically after `/connect-results` interprets a
returned analysis).

**Minimal read set:**
1. `$PROJ/docs/questions.md` — locate the target entry
2. `$PROJ/docs/hypotheses.md` — read the updated hypothesis/hypotheses
3. The triggering analysis file (if referenced)

**What to edit:** Only the target question's `Current working answer`
and `Open` sections. Do not touch other questions.

**Output:** The edited questions.md plus a one-sentence summary of
what changed in the working answer.

## Audit mode (`--audit`)

Check without writing:
- Every H: slug referenced in questions.md exists in hypotheses.md
- Every question has at least one hypothesis with evidence strength
  above "Not tested"
- Working answers are consistent with current evidence strengths in
  hypotheses.md (e.g., don't claim "strong evidence" if all relevant
  hypotheses say "Moderate" or "Weak")
- No orphan questions (all hypotheses mapped to at least one question)
  — orphan hypotheses are fine (not every test maps to a big question)

Report findings as a bulleted list.

## Integration with other skills

- `/connect-results` should suggest a `/questions --update` when an
  interpreted result changes the evidence base for a question
- `/next` proposal mode can reference open items in questions.md
- `/hypothesis --update` should note if the change affects a question's
  working answer
