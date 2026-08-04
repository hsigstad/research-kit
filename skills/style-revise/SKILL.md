---
name: style-revise
description: Revise a rough draft paragraph by fixing idea flow before wording, then offer alternative shapes. Use when the user shares unpolished prose and asks for comments, says a paragraph "feels awkward", wants "better flow", restructuring, wording alternatives, or help finding the right shape for ideas they've already drafted. For auditing a near-final document against the style guide use /style-review; for a fast mechanical AI-tell scan use /style-check.
---

# style-revise

Take a rough draft and get the ideas into the right order before touching
the words. The other style skills *audit finished prose against the
rulebook*; this one *reshapes an unfinished draft*. Different job, earlier
in the pipeline.

Use it when the user hands you a messy paragraph and wants to find the
right shape — not when they want a compliance pass on a document that's
already close to done. That's `/style-review`.

## Stance

Assume the user has the right ideas and needs the best structure for
them. Revise aggressively at the level of order, emphasis, sentence
boundaries, transitions, and paragraph shape — but preserve the
substantive claims, notation, and technical language.

Don't add or drop ideas by default. Add a missing idea, cut one, or move
one out of the paragraph only when the paragraph can't work otherwise —
and say so explicitly when you do.

Treat an awkward sentence as evidence of an idea-flow problem, not a
bad-English problem. It's usually awkward because it's doing two jobs at
once, because the sentence before it didn't set it up, or because the
paragraph's logical order isn't right yet.

## Workflow

### 1. Load the rulebook first

Your rewrites have to survive the same standards the rest of the stack
enforces. Before proposing anything, load the general baseline:

```
research-kit/rules/writing_style.md
```

If working in the user's workspace, also load the overlay (banned
phrases, referee carve-out, author tics):

```
research/rules/writing_style.md
```

If you can tell the paragraph's section type (intro, results, theory,
abstract, …), load the per-type guide too:

```
research-kit/rules/writing_style/<type>.md
```

This is what keeps a "smoother" rewrite from quietly reintroducing an
AI-tell or a banned phrase.

### 2. Diagnose flow before wording

Read the target prose and enough context to understand the local
argument. Identify the paragraph's job: the claim, contrast, mechanism,
qualification, implication, or transition it needs to deliver.

Then look for the structural problems, in this order:

- Ideas in the wrong order.
- The main claim buried below the setup.
- A sentence doing multiple logical jobs.
- Missing connective tissue between ideas.
- A qualification that lands before the claim it qualifies.
- A final sentence that belongs earlier.

If the idea structure is what's blocking good flow, name that first.
Don't try to fix structural confusion with surface polish.

### 3. Rearrange, then smooth

Repack the *existing* ideas into a clearer sequence. Only once the order
is right, make the language cleaner and more economical:

- Put the main point where it can organize the paragraph.
- Split sentences doing multiple logical jobs; combine ones whose
  separation makes the logic choppy.
- Move qualifications after the claim, unless accuracy demands otherwise.
- Add a transition only after the underlying relation is clear.
- Replace vague connectives with the actual relation: contrast,
  mechanism, implication, caveat, example, consequence.

### 4. Lint your own rewrite

Before presenting a revision, run it through the mechanical linter so you
don't hand back prose the rest of the stack would immediately re-flag:

```bash
python3 ~/research/research-kit/tools/style_lint.py <tmpfile-or-source> --severity warning
```

If a proposed rewrite trips a rule, fix it before showing it. A rewrite
that reads well but reintroduces a banned phrase is a regression, not an
improvement.

### 5. Apply, if asked

If the user wants the edit applied, edit the **source file**, not a
generated build output. Preserve notation, citations, `[ns:key]` tokens,
`\label`s, author notes, and technical claims unless the user explicitly
asks to change them. Don't commit automatically.

## Output style

For a short interactive request, usually:

1. A one- or two-line diagnosis of what's limiting the flow.
2. Two or three revised versions, when alternatives actually help —
   e.g. conservative vs. more aggressive restructuring.
3. A short note on the tradeoff between them.

Keep line-level proofreading comments out unless they materially affect
flow. For a long document, give a structured revision report rather than
inline rewrites, unless the user asks for direct edits.

## When to use vs. the other style skills

| Skill | Job | Draft maturity | Output |
|-------|-----|----------------|--------|
| `/style-check` | mechanical AI-tell scan | any | linter findings |
| `/style-review` | audit against the style guide | near-final | rule-citing findings |
| `/validate-section` | section-scoped pre-submission gate | near-final | findings + ledger |
| `/style-revise` (this) | reshape idea flow | rough / unpolished | diagnosis + alternative rewrites |

The dividing line: **rough draft you're still shaping → `/style-revise`;
document that's basically done and needs a compliance pass →
`/style-review`.** When the user says "polish," disambiguate by draft
maturity, not the word itself.

## Cost

One LLM pass over a paragraph or short passage, plus a linter run on the
rewrite. Cheap for interactive paragraph-level work. For a whole document,
prefer `/style-review` (which is built for that scope) unless the user
specifically wants structural reshaping rather than a guide-compliance
audit.
