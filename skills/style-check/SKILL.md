---
name: style-check
description: Fast deterministic prose-style checker. Wraps research-kit/tools/style_lint.py for file-scoped use. Use when the user invokes /style-check <file>, asks to "check style", "scan for AI tells", "polish before sending", or wants a quick mechanical pass before submission. For LLM whole-document review use /style-review; for section-scoped pre-submission validation use /validate-section.
---

# style-check

Fast, deterministic, file-scoped prose-style scan. Wraps the canonical
linter at `research-kit/tools/style_lint.py`. Runs in milliseconds. No LLM.

## How to invoke

```bash
python3 ~/research/research-kit/tools/style_lint.py <file> [flags]
```

Common flags:

- `--format json` — JSON output
- `--severity warning` — minimum severity (`info | warning | error`)
- `--rule <name>` — only run a named rule (repeatable)
- `<dir>` — pass a directory to lint all `.tex` and `.md` under it

See `python3 style_lint.py --help` for the full surface.

Exits 1 if any violations remain at the requested severity. Useful for
gating submissions in CI.

## What it checks

Eighteen mechanical rules covering the deterministic part of
`research-kit/rules/writing_style.md`:

| Rule                          | Section reference          |
|-------------------------------|----------------------------|
| `ai-tell`                     | §4                         |
| `filler-phrase`               | §17 (Quick reference)      |
| `throat-clearing`             | §2                         |
| `editorializing`              | §2                         |
| `naked-this`                  | §4                         |
| `word-choice`                 | §4 (plain-word table)      |
| `self-categorizing`           | §13                        |
| `forward-reference`           | §16 (robot-body linearity) |
| `hedging-opener`              | §7                         |
| `sentence-length`             | §3                         |
| `clause-stacking`             | §3                         |
| `passive-density`             | §2                         |
| `connective-opener`           | §9                         |
| `stacked-adjectives`          | §4                         |
| `synonym-piling`              | §17                        |
| `non-stat-significantly`      | §17                        |
| `decimal-precision`           | §10                        |
| `abstract-opening`            | §13                        |
| `cute-quotation`              | §14                        |

Skipped automatically: LaTeX comments, math environments, fenced and
inline code, URLs, case/docket numbers, YAML frontmatter.

## When to use

- Before sending anything that matters: papers, drafts, emails, slides.
- Cheap enough to run on every commit if you want it as a gate.

## When to use vs. the other style skills

| Skill                  | Scope          | Mechanical              | LLM | Ledger writes |
|------------------------|----------------|-------------------------|-----|---------------|
| `/style-check` (this)  | file           | yes                     | no  | no            |
| `/style-review`        | file (whole)   | yes (calls `style_lint.py`) | yes | no        |
| `/validate-section`    | one section    | yes (calls `style_lint.py`) | yes | yes       |
| `/style-revise`        | paragraph      | yes (lints its rewrite) | yes | no        |

Same patterns underneath. Different scopes and depths. `/style-revise`
reshapes a rough draft's idea flow rather than auditing finished prose —
use it when the draft is still unpolished, the others when it's near-final.

## Implementation

The mechanical layer lives in `research-kit/tools/style_lint.py` and is
shared across `/style-check`, `/style-review`, and `/validate-section`.
Add new patterns there once and all three skills pick them up.

Severity levels: `info` (FYI, often the right word in context),
`warning` (worth addressing), `error` (blocking — typography violations
in referee mode, abstract-opening violations).
