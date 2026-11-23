# Author voice layer

An optional personal layer on top of [`writing_style.md`](writing_style.md) and
the per-section guides in [`writing_style/`](writing_style/). The baseline
describes how *publishable empirical-economics prose* should read in general.
An author voice pack describes what makes it read like *one specific author*.

This file defines the convention; it carries no author's content itself. A voice
pack is private to its author and lives outside this (public) repo.

## What a voice pack is

Two parts, mirroring the split that actually moves model outputs:

1. **A voice spec** — the author's register as rules: how they open a paper,
   where the headline number goes, which hedges are allowed, a personal ban list
   on top of the baseline's AI-tell list.
2. **Annotated exemplars** — 3–5 short excerpts (≈150–300 words) of the author's
   own best prose, each with a note on *what makes it theirs*. This is the part
   the rule-based baseline lacks, and the part that most reliably pulls a draft
   toward the author's voice: models imitate examples more faithfully than they
   follow abstract descriptions.

Optionally a QA checklist and a small test suite (a fixed set of drafting prompts
scored against a rubric) so changes to the pack can be A/B'd rather than vibed.

## Where the exemplars should come from

Prefer text the author wrote and revised themselves — published papers are ideal
(unambiguously their voice). For authors who now draft with an assistant and
shape the result through instructions rather than typing prose, the voice lives
in the **final text of the passages they corrected most heavily**, not in what
they typed. Select those passages by how much the author pushed on them (e.g. the
density of their editing instructions), not by authorship of the keystrokes.

## How it loads

Graceful degradation is the rule: if no voice pack is configured or the files are
missing, fall back to the baseline silently.

- **Claude Code:** keep the pack at a stable path (e.g. a private repo, or
  `~/.claude/rules/`), and have the drafting/review skills load the spec +
  exemplars on top of the baseline. A one-line pointer in a project `CLAUDE.md`
  (`author voice pack: <path> — load on top of the writing-style baseline when
  drafting prose`) is enough.
- **Chatbot project (Overleaf drafting, etc.):** paste the spec's rule section
  plus 2–3 exemplars into the project instructions.

## Relationship to the baseline

When the voice pack and the baseline agree, the baseline already covers it and the
pack just points at an exemplar. When the pack is more specific (a tighter
sentence-length habit, a signature rhetorical move, an extra banned word), the
pack wins for that author. The pack never loosens a baseline correctness rule
(citations, honest reporting of nulls, no editorializing of results).

## Reference

The examples-beat-rules principle: Anthropic, *Effective context engineering for
AI agents*. The structure here is adapted from the public "voice pack" pattern
(Blattman, Claude Blattman toolkit, 2026).
