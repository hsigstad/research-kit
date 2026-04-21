# Validation Ledger Spec

The mechanics of the validation ledger referenced in stage 8 of
`ai_research_workflow.md`. This is the spec the `/validate-section` skill
follows, and the format every project's `paper/validation.yaml` should
conform to. (Historical note: before 2026-04-21 the script ledger was
markdown at `paper/validation.md`; that file now holds only the prose
narrative ledgers, with the structured state in YAML.)

Companion format: a **section-level** state file
(`paper/validation_sections.yaml`) tracks human sign-off at subsection
granularity. It's optional — use it when a project renders a site view of
the paper with per-section stripes. See the bottom of this doc.

---

## Script ledger: `paper/validation.yaml`

YAML file, one top-level `scripts:` list with one entry per script. A
parallel `hand_coded:` list tracks paper elements without generating
scripts (TikZ figures, LaTeX tables, appendix prose).

Narrative companions (the "AI checks performed" running log, the
draft-reading ledger) live in `paper/validation.md` as prose markdown.
The structured ledger (this file) is what tooling reads.

### Script entry schema

```yaml
scripts:
  - script: source/analysis/overruns.py
    layer: analysis_procurement_outcomes   # cosmetic group for rendering
    produces: build/analysis/overruns.parquet
    depends_on:
      - source/clean/parse.py
      - source/clean/contract.py
    hash: 6faeed2                          # short git hash at validation
    closure_hash: 7bf20ada85f2             # see Closure hash section
    ai_checks:
      - kind: line_by_line_trace
        date: 2026-04-16
        notes: cache-key fix
    human_check: null                      # YYYY-MM-DD once signed off
    reviewer: null
    status: pending                        # pending | ai-verified | human-verified | stale
```

Field notes:

- `script` — repo-relative path. The primary key.
- `layer` — cosmetic grouping string (e.g. `clean_layer`,
  `analysis_court_linking`). Tooling uses it only for display.
- `produces` — string or list of strings. Output path(s).
- `depends_on` — list of upstream script paths (full repo-relative,
  not bare basenames). Edges that conceptually point at an output
  parquet should be rewritten to the producing script's path — the
  graph is between scripts, one entry per script.
- `hash` — short git hash of the script at validation time. Audit
  anchor: `git show <hash>:<path>` recovers the exact bytes that were
  reviewed.
- `closure_hash` — closure hash at validation time (script + all
  first-party Python modules it transitively imports). Drift detector:
  `stale` fires when this differs from the closure hash at HEAD,
  catching helper-module drift the leaf git hash misses. See
  [Closure hash](#closure-hash-drift-detector).
- `ai_checks` — list of structured entries, each with `kind`, `date`,
  and optional `notes`. Vocabulary listed below.
- `human_check` — ISO date once the row is signed off.
- `reviewer` — initials / name.
- `status` — one of the four states.

### Status semantics

- `pending` — no AI checks recorded. Default for new rows.
- `ai-verified` — at least one AI check recorded with a date. `human_check`
  is empty.
- `human-verified` — `human_check` and `reviewer` are set; the script
  hash matches what was reviewed.
- `stale` — script hash has changed since the recorded `human_check`
  (or since any `ai_checks` date, if no human review). Produced by the
  pre-submission checker; do not set by hand.

State machine:

```
pending ──(ai check recorded)──▶ ai-verified ──(human sign-off)──▶ human-verified
   ▲                                 │                                  │
   │                                 └──(hash changes)──▶ stale ◀───────┘
   └─ (new script added) ─
```

### Pre-submission checker

A script that:

1. Reads every entry under `scripts:` in `paper/validation.yaml`.
2. Recomputes each script's current closure hash (see
   [Closure hash](#closure-hash-drift-detector)) at HEAD.
3. If the current closure hash differs from the row's `closure_hash`,
   flips `status` to `stale` and clears `human_check` (but keeps a record
   of the prior reviewer for provenance). This catches both leaf
   drift *and* helper-module drift — the common case where the
   reviewed script itself is unchanged but a module it imports has
   been edited.
4. Propagates `stale` transitively through `depends_on`: if a dependency
   is `stale` or `pending`, the dependent is effectively `stale` for
   sign-off purposes, even if its own closure is unchanged.
5. Emits a non-zero exit code if anything on the **critical path** is
   `pending` or `stale`. Critical path = scripts producing headline
   results plus all upstream scripts in their dependency closure.

The checker lives per project but must follow this contract.
`scripts/check_validation_ledger.py` in `procure` is the reference
implementation.

### Closure hash (drift detector)

`closure_hash` is the deterministic hash of a script's source PLUS all
first-party Python modules it transitively imports. It exists because
the leaf git hash misses a common failure mode: a helper module
(`source/summary/config.py`, `source/clean/parse.py`, a shared figure
style module) is edited, every downstream script silently changes
behavior, but none of their leaf git hashes move — so `stale` doesn't
fire under a leaf-only check.

Contract for the per-project implementation:

- **Inputs**: a script's repo-relative path and (optionally) a git ref.
- **Closure membership**: the script itself, plus every file reached
  by recursively following `import` / `from X import Y` statements
  that resolve to first-party paths in the repo. First-party roots
  are project-defined (e.g., `source/`, `scripts/`). External
  packages (numpy, pandas, llmkit) are excluded — their drift is
  handled separately via package pinning.
- **Not followed**: relative imports, `importlib` dynamic imports,
  file reads of non-`.py` assets (prompt templates, config JSON).
  Projects that depend on such assets must list them in `depends_on`
  or extend the closure tool with an `--extra` mechanism.
- **Output**: a short hex digest (≥12 chars) of a sha256 over
  `(sorted_path, content)` pairs for every file in the closure.
- **Determinism**: the hash depends only on file contents and
  repo-relative paths. Byte order and pair delimiters are defined by
  the implementation but must be stable across runs.
- **Ref support**: the tool must accept a git ref and compute the
  closure at that revision (via `git show <ref>:<path>`), to support
  migrations that populate historical `closure_hash` values.

Reference implementation: `scripts/closure_hash.py` in `procure`.

### Sign-off rule

Nothing submits with `pending` or `stale` rows on the critical path.
Exceptions go in a paper-level comment in the ledger, signed and dated.

---

## AI check-kind vocabulary

The `ai_checks` column records *which* methods were applied — not just
"AI looked at it". A thin list is itself a warning.

### Format within the cell

Each recorded check: `<check_kind> YYYY-MM-DD[; notes]`. Multiple checks
separated by `;`. Example:

```
line_by_line_trace 2026-04-16; text_table_consistency 2026-04-16; code fixes 2026-04-17 (HIGH cache-key collision fixed)
```

The `<check_kind>` token must be one of the identifiers below, or
`other:<slug>` for new methods that haven't yet been added to the
vocabulary. Tooling parses the token that directly precedes the date.

### Vocabulary (current)

| Kind                      | What it does                                                                            | Used at                     |
|---------------------------|-----------------------------------------------------------------------------------------|-----------------------------|
| `lean`                    | Formal proof in Lean.                                                                   | Stage 3 (proofs).           |
| `adversarial_proof`       | Second AI tries to break the proof.                                                     | Stage 3.                    |
| `adversarial_referee`     | Skeptical-referee read of the full draft.                                               | Stage 6.                    |
| `citation_claim_check`    | AI reads the cited PDF and verifies the attributed claim is actually in it.             | Stage 2.                    |
| `line_by_line_trace`      | AI walks each line of a script and explains the logic, flagging surprises.              | Data / coding scripts.      |
| `property_assertions`     | AI generates invariants (row counts, key uniqueness, distributions) once; once crystallized, prefer a pytest-style suite that runs on every build (see `rules/build_invariants.md`). The AI vocabulary entry then covers the authoring step only, not the per-build rerun. | Cleaning / join scripts.    |
| `cache_key_completeness`  | AI enumerates every input that can change the output of a cached computation (prompt content, model, decoding params — temperature, top_p, max_tokens — schema version, truncation thresholds, pre-processing). For each input, verifies one of: (a) included in the cache key itself, (b) checked by the `is_stale()` path AND the pipeline refuses to proceed without refresh (not just flags `stale=True` and serves the old value), or (c) intentionally excluded and documented. Flags anything that falls into none of these. Named separately from `line_by_line_trace` because the lens is cross-cutting — it reads the code asking "if an analyst edits X tomorrow, does the cache refresh?" rather than in document order. | LLM extraction, memoized scraping, simulation replay, any script with a content-addressable cache. |
| `output_sanity`           | AI compares script outputs against ex-ante priors (signs, magnitudes, sample sizes).    | Estimation scripts.         |
| `reproduction_run`        | Clean rebuild + output diff. SCons form: `scons --clean <target> && scons <target>`. Prefer running this as a build hook or CI step (mechanical, no AI judgment). Catches incomplete `source=[...]` declarations and script-level nondeterminism that SCons's normal dependency tracking misses. | Any script.                 |
| `text_table_consistency`  | AI checks non-macroized numbers in prose + table/figure contents match the backing script's output. | Full draft (stage 8).       |
| `macro_provenance`        | AI checks each `\MacroName{}` resolves (via paper numbers sidecar) to an existing JSON path and the rendered value matches. Purely mechanical — projects with a SCons-regenerated macro system (see `rules/paper_macros.md`) should automate this as a build lint (`source/paper/check_macros.py`-style) rather than carrying it in the AI vocabulary. Keep the entry for portability. | Sections citing macros (when not automated). |
| `interpretation_code_alignment` | AI checks each macro's declared `interpretation` in `paper/numbers.json` actually matches what the source script computes at the referenced JSON path (denominator, numerator, filter, aggregation). Script-side; once per macro definition. | Script with macros pointing at it. |
| `interpretation_prose_alignment` | AI checks the prose around each macro invocation is consistent with the macro's declared interpretation — denominator, direction, qualifier words, claim context. Section-side; per section. | Sections citing macros.     |
| `qualifier_alignment`     | AI checks scale-words and magnitude adjectives around *non-macro* numbers (narrative literals kept as prose) match the value. For macros, this is subsumed by `interpretation_prose_alignment`. | Full draft (stage 8).       |
| `narrative_claim_check`   | AI checks each section's conclusions follow from the cited numbers — flags overstated "demonstrate/prove" language, missing caveats, unsupported "therefore" moves, bad evidence pointers, cross-section inconsistency. | Full draft (stage 8).       |
| `institutional_claim_check` | AI extracts every institutional claim (laws, thresholds, dates, modalities, enforcement bodies) from a section and classifies each as BACKED / UNBACKED / CONTRADICTED against the project's institutional-background reference (e.g. `docs/institutions.md`). Typically backed by a dedicated project script (procure: `source/paper/check_institutional_claims.py`) rather than a hand-walk. | Sections stating institutional facts (typically Institutional Background). |
| `spec_grid`               | AI runs the pre-specified multiverse and reports the full distribution.                 | Estimation (p-hacking).     |

Extensible: add a new row here when a new check earns its keep. Until
then, use `other:<slug>` in the ledger — existing tooling will treat the
slug as opaque.

**Note on `text_table_consistency` scope.** Projects that use the paper
numeric macro system (`research-kit/rules/paper_macros.md`) get
mechanical text-JSON alignment for free: every cited pipeline number
resolves through a macro and can't drift from its source. The check
still applies to (a) narrative literals kept as prose (e.g. "nearly
three years"), (b) numbers inside tables/figures that come from their
own generating scripts, and (c) any non-macro literal whose value came
from a dataset. The newer `macro_provenance` + `qualifier_alignment`
checks cover the complementary failure modes the macro system cannot
prevent on its own.

### Required-method floors

Load-bearing scripts should carry **multiple methods**. Minimum floors
by script type:

- Cleaning / join script → `property_assertions` + `line_by_line_trace`.
- Estimation script → `line_by_line_trace` + `output_sanity` +
  (eventually) `reproduction_run`.
- Table/figure generator → `text_table_consistency` once numbers appear
  in the draft.
- LLM extraction / memoized-computation script →
  `line_by_line_trace` + `cache_key_completeness`. Without the
  latter, prompt, decoding-param, or schema edits can silently serve
  stale cached entries rather than refreshing them.

For section-level passes (rows marked as section prose rather than a
single script), the floor is `macro_provenance` +
`interpretation_prose_alignment` when the section cites macro-backed
numbers, plus `narrative_claim_check` once the section is out of first
draft. Include `qualifier_alignment` when the section has non-macro
literal numbers (narrative rounding, etc). Add `citation_claim_check`
when the section introduces or modifies an external citation; stale
citations rarely re-check themselves. Add `institutional_claim_check`
when the section states institutional facts (legal thresholds, named
enforcement bodies, modality rules, statutory dates); these claims
rarely drift but when they do, they drift silently and legal
reviewers catch the mismatch.

Scripts that a section's macros point at carry an extra floor item:
`interpretation_code_alignment` — the declared interpretation must
match what the script actually computes. This is a one-time check
per macro definition; it does not re-fire on every pass, only when
the script's referenced field or the interpretation text changes.

Below the floor: the row stays `pending`. AI may record partial checks,
but `status` doesn't flip to `ai-verified` until the floor is met.

---

## Updating a row

Procedure when recording a new AI check:

1. Compute the script's current short git hash
   (`git log -n 1 --format=%h <path>`). If it differs from the entry's
   `hash:`, update it.
2. Compute the script's current closure hash
   (e.g. `python3 scripts/closure_hash.py <path>`). If it differs from
   the entry's `closure_hash:`, update it. Both fields should be
   updated together on sign-off.
3. Append to `ai_checks:`:
   ```yaml
   - kind: <check_kind>
     date: YYYY-MM-DD
     notes: <optional one-line note>
   ```
4. If the required-method floor is now met **and** `human_check:` is
   null, set `status:` to `ai-verified`.
5. Commit the ledger change in the same commit as any code fixes that
   resulted from the check — the audit trail should be one commit per
   state transition.

Procedure when recording a human review:

1. Confirm the `hash:` matches the current leaf git hash AND
   `closure_hash:` matches the current closure hash. If either differs,
   re-run the AI checks on the new hashes first — don't sign off on a
   version you didn't read, and don't sign off on a closure whose
   helpers have drifted since review.
2. Set `human_check:` to today's date and `reviewer:` to your initials.
3. Set `status:` to `human-verified`.

---

## Section-level state (optional): `paper/validation_sections.yaml`

When a project renders the paper on a site with per-section stripes
(see procure's `source/site/validation.py` for the reference
implementation), add a YAML file keyed by section anchor:

```yaml
sections:
  <section-slug>:
    level: unreviewed | reviewed | signed-off | disputed
    reviewer: <initials> | null
    date: YYYY-MM-DD | null        # auto-filled on form submit
    backing_scripts:               # paths matching the script ledger
      - source/analysis/foo.py
    ai_checks: ""                  # same vocabulary as script ledger
    last_ai_pass_sha: null         # short git SHA at last AI pass
    comment: ""
```

Design intent:

- `level` captures only what a human can judge (does the claim follow
  from the data; is the interpretation reasonable). AI-verifiable
  checks like "numbers match table" are already tracked in the script
  ledger's `ai_checks` column and surfaced next to each backing script.
- `backing_scripts` is the bridge between section-level prose state and
  script-level code state: the site renders the worst-of-deps status
  from the script ledger as the section's "code stripe".
- `date` is set on form submit, not manually — avoids stale dates when
  a reviewer forgets to update.
- `ai_checks` records section-level AI work (macro_provenance,
  qualifier_alignment, narrative_claim_check) using the same
  `<kind> YYYY-MM-DD[; notes]` format as the script ledger.
- `last_ai_pass_sha` enables incremental rechecks: the `/validate-section`
  skill diffs `paper/main.tex` between that SHA and HEAD, plus detects
  backing-script hash drift, and scopes the pass to only the changed
  macros and hunks. Set this to the current short HEAD SHA whenever a
  check is recorded. A full re-pass (e.g. via `--full`) also rewrites
  the SHA.

Sign-off rule carries over: no section submits with `level: unreviewed`
on the critical path (or `disputed` without resolution).
