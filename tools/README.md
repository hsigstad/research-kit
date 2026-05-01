# Tools

Workspace-shared command-line utilities consumed by skills, build
scripts, and direct CLI use. Stable interfaces; treat as research-kit's
public surface.

## Style

- **`style_lint.py`** — canonical mechanical prose linter. Single source
  of truth for the regex/heuristic style checks defined in
  `../rules/writing_style.md`. Eighteen rules covering AI-tell vocabulary,
  filler phrases, throat-clearing, editorializing, naked "this", plain-
  word violations, self-categorizing prefaces, forward references,
  hedging openers, sentence length, passive voice density, connective
  openers, stacked adjectives, synonym piling, "significantly"
  non-statistical, decimal precision, abstract first-sentence,
  and cute opening quotations.

  Consumed by:
  - `/style-check` (file-scoped, mechanical only)
  - `/style-review` (whole-document, mechanical pre-pass + LLM review)
  - `/validate-section` (section-scoped, mechanical pre-pass + LLM
    `style_prose` checks + ledger writes)

  All three skills delegate the mechanical layer here. Add new patterns
  in one place; all three pick them up.

  Usage:
  ```bash
  python3 style_lint.py <file_or_dir> [--format json] [--severity warning]
                                       [--rule <name>] [--rule <name>]
  ```

  Exits 1 if any violations exceed the severity threshold; 0 otherwise.

## Other tools in this directory

(Add a one-line summary as new tools land.)
