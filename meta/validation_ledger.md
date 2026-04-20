# Validation Ledger Spec

The mechanics of the validation ledger referenced in stage 8 of
`ai_research_workflow.md`. This is the spec the `/validate-section` skill
follows, and the format every project's `paper/validation.md` should
conform to.

Companion format: a **section-level** state file
(`paper/validation_sections.yaml`) tracks human sign-off at subsection
granularity. It's optional — use it when a project renders a site view of
the paper with per-section stripes. See the bottom of this doc.

---

## Script ledger: `paper/validation.md`

Markdown file with grouped tables (by pipeline layer). Grouping is
cosmetic; tooling only reads the table rows.

### Row format

One row per script. Eight columns, in this order:

| Column        | Contents |
|---------------|----------|
| `script`      | Backticked path relative to repo root, e.g. `` `source/analysis/overruns.py` ``. |
| `produces`    | Backticked output path or artifact name. |
| `depends_on`  | Comma-separated upstream script names (backticked or bare). |
| `hash`        | Backticked short git hash of the script at validation time. |
| `ai_checks`   | Free text listing applied AI checks with dates and notes (see vocabulary below). Empty = no AI checks recorded. |
| `human_check` | YYYY-MM-DD of human review. Empty = not yet reviewed. |
| `reviewer`    | Initials or name of the human reviewer (relevant on joint projects). |
| `status`      | `pending` \| `ai-verified` \| `human-verified` \| `stale`. |

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

1. Reads every row of `paper/validation.md`.
2. Recomputes each script's current git short hash.
3. If the current hash differs from the row's `hash`, flips `status` to
   `stale` and clears `human_check` (but keeps a record of the prior
   reviewer for provenance).
4. Propagates `stale` transitively through `depends_on`: if a dependency
   is `stale` or `pending`, the dependent is effectively `stale` for
   sign-off purposes, even if its own hash is unchanged.
5. Emits a non-zero exit code if anything on the **critical path** is
   `pending` or `stale`. Critical path = scripts producing headline
   results plus all upstream scripts in their dependency closure.

The checker lives per project (no portable implementation yet) but must
follow this contract.

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
| `property_assertions`     | AI generates invariants (row counts, key uniqueness, distributions) and checks them.    | Cleaning / join scripts.    |
| `output_sanity`           | AI compares script outputs against ex-ante priors (signs, magnitudes, sample sizes).    | Estimation scripts.         |
| `reproduction_run`        | AI re-runs the script from a clean state and diffs outputs against the committed build. | Any script.                 |
| `text_table_consistency`  | AI checks every number quoted in the text matches the corresponding table cell.         | Full draft (stage 8).       |
| `spec_grid`               | AI runs the pre-specified multiverse and reports the full distribution.                 | Estimation (p-hacking).     |

Extensible: add a new row here when a new check earns its keep. Until
then, use `other:<slug>` in the ledger — existing tooling will treat the
slug as opaque.

### Required-method floors

Load-bearing scripts should carry **multiple methods**. Minimum floors
by script type:

- Cleaning / join script → `property_assertions` + `line_by_line_trace`.
- Estimation script → `line_by_line_trace` + `output_sanity` +
  (eventually) `reproduction_run`.
- Table/figure generator → `text_table_consistency` once numbers appear
  in the draft.

Below the floor: the row stays `pending`. AI may record partial checks,
but `status` doesn't flip to `ai-verified` until the floor is met.

---

## Updating a row

Procedure when recording a new AI check:

1. Compute the script's current short git hash (`git log -n 1 --format=%h <path>`).
2. If that hash differs from the row's `hash` column, update the hash.
3. Append `<check_kind> YYYY-MM-DD[; notes]` to the `ai_checks` cell.
4. If the required-method floor is now met **and** `human_check` is
   empty, set `status` to `ai-verified`.
5. Commit the ledger change in the same commit as any code fixes that
   resulted from the check — the audit trail should be one commit per
   state transition.

Procedure when recording a human review:

1. Confirm the hash matches. If not, re-run the AI checks on the new
   hash first — don't sign off on a version you didn't read.
2. Set `human_check` to today's date and `reviewer` to your initials.
3. Set `status` to `human-verified`.

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

Sign-off rule carries over: no section submits with `level: unreviewed`
on the critical path (or `disputed` without resolution).
