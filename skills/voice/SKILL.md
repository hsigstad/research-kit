---
name: voice
description: "Draft or revise a paper section in the author's voice. Loads that section's voice examples + rules FIRST, then writes. Invoke as /voice <section> [what to write], e.g. /voice results, /voice abstract, /voice intro. Sections: abstract, intro, theory, methods, data, results, conclusion."
---

# Voice-draft a paper section

Write or revise paper prose in Henrik's voice by loading the matching section's
**examples** and **rules** before drafting — never draft a section without reading
its examples first. This is the whole point of the skill: the examples must be in
context before you write a word of that section.

## Step 1 — Resolve the voice pack

Find the voice-pack directory `research/meta/voice/`. From a project repo (e.g.
`projects/monotone/`) it is usually `../../research/meta/voice/`; from the research
repo it is `meta/voice/`. If neither is obvious, locate it:

```
find . ../.. ../../.. -maxdepth 4 -type d -path '*research/meta/voice/examples' 2>/dev/null | head -1
```

If no voice pack is found, tell the user and fall back to the general baseline
(`research-kit/rules/writing_style.md`); do not invent a voice.

## Step 2 — Parse the section

Read `$ARGUMENTS`. The first token is the section; the rest (if any) is what to
write or the file/text to revise. Normalize aliases to one of the seven files in
`<voicepack>/examples/`:

| Section file | Aliases |
|---|---|
| `abstract.md` | abstract |
| `intro.md` | intro, introduction |
| `theory.md` | theory, model, framework |
| `methods.md` | methods, method, empirical, empirical-strategy, identification, design, strategy |
| `data.md` | data, setting, institutions, institutional |
| `results.md` | results, findings, main-results |
| `conclusion.md` | conclusion, conclusions, discussion |

If no section is given, ask which one (don't guess). If the section is given but the
file is missing, say so and load the closest match plus `PAPER_VOICE.md`.

## Step 3 — Load examples + rules (REQUIRED, before writing)

1. **Read `<voicepack>/examples/<section>.md` in full.** These verbatim passages are
   the model to imitate.
2. **Read `<voicepack>/PAPER_VOICE.md`** — at least §1–§4 (the invariant rules and
   ban list) and any section the example file's header points to (e.g. results →
   §2.12 and §8).
3. The general baseline `research-kit/rules/writing_style.md` still applies
   underneath; the voice pack wins on any conflict.

## Step 4 — State the moves (make the read visible)

Before drafting, list in 2–4 short lines the specific moves from the examples you
will follow for this section (e.g. for results: "numbers per group then the
contrast; evidence before interpretation; robustness in one sentence tagged to
tables"). This confirms the examples are loaded and anchors the draft.

## Step 5 — Draft or revise

Write the requested text in the section's voice. Imitate the **sentence shapes and
structure** of the examples, not their topic. Hard rules:

- Match the register to authorship: solo → "I", coauthored → "we".
- Evidence before interpretation, always (PAPER_VOICE §2.12).
- Numbers over adjectives; hedges carry a reason; no editorializing; no words on the
  ban list.
- When revising existing prose, prefer deletion to addition; change the fewest words
  that fix the issue.

Then show the draft. If you deviated from an example's move for a good reason, say so
in one line.

## Step 6 — Self-lint and hand off

After writing, run the mechanical linter on what you produced to catch AI-tells the
examples should have ruled out:

```bash
python3 ~/research/research-kit/tools/style_lint.py <file> --format json --severity warning
```

(Resolve the path if that location is absent: try `research-kit/tools/style_lint.py`
or `../../research-kit/tools/style_lint.py`.) Fix any warning-or-higher violations in
what you just wrote. Then point the user at the deep audit:

> Drafted. For a thorough pass, run `/style-review <file> --section <section>` — it
> audits against this same voice pack plus the full style guides.

`/voice` drafts; `/style-review` audits. Same voice pack, two modes.

## Arguments

`$ARGUMENTS` — `<section> [instruction or file path]`. Examples:

```
/voice results                 # load results examples, then draft the results from context
/voice abstract                # draft/revise the abstract
/voice intro revise paper/draft.tex intro to open on the stakes
/voice methods write the identification subsection from the design notes above
```

## Notes

- The per-section split keeps context lean: load only the section you're writing.
- This skill is author-agnostic. It reads whatever voice pack sits at
  `research/meta/voice/`; the convention is documented in
  `research-kit/rules/writing_style_author_voice.md`.
