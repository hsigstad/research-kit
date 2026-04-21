# Build-time invariant tests

Convention for pytest-style property assertions that replace
`property_assertions` AI checks for any clean-layer or analysis table
whose invariants have been crystallized.

The goal: a number or a schema constraint that AI verified once stays
verified forever, mechanically, on every build — not "when someone
next runs the validation skill".

---

## Why move this out of the AI vocabulary

The AI-check version of `property_assertions` has two phases:
authoring the invariants (genuinely AI work — a human + AI conversation
about what the table should satisfy) and re-checking them (mechanical
assertion evaluation). Only the first phase needs judgment. Running
the assertions is what pytest is for.

Failure mode the AI-only version leaves open: invariants drift out of
sync with reality between AI passes. A silent bug that drops 5% of
rows is caught only when someone re-runs the skill. A build-time
pytest catches it on the next commit.

---

## Layout

Per project, under a top-level `tests/` directory:

```
tests/
  conftest.py              # shared fixtures: clean_dir, load_parquet
  clean/                   # invariants for build/clean/*.parquet
    test_licitacao.py
    test_contract.py
    ...
  analysis/                # invariants for build/analysis/*
    test_enforcement_outcomes.py
    ...
```

One file per target artefact. Each file asserts schema, grain, and
domain properties of a single parquet/JSON.

---

## What belongs in an invariant file

Three buckets, in this order (most-portable to most-domain-specific):

1. **Schema.** Required columns present; key columns have expected dtypes;
   date columns are datetimes and not strings.
2. **Grain.** Primary key is unique on the documented grain (one row per
   `<entity, dimension>`); expected row-count bounds that would trip
   on silent data loss.
3. **Domain.** Column values in expected ranges or categorical sets;
   non-negative monetary amounts; municipality IDs from the right
   vocabulary; years in a plausible window.

Each test must carry a docstring with the *why* — the business
meaning or the incident the test would have caught. An invariant
whose rationale no reader can reconstruct is a time bomb.

---

## Bounds: tight vs. tripwire

When writing a row-count or coverage assertion, two styles are
useful:

- **Tight bound**: when you know the exact value, assert it.
  `assert df.codigo_licitacao.nunique() == len(df)` (true by
  definition of the grain).
- **Tripwire bound**: when the value is a dataset fact you expect to
  drift slowly, allow a wide range.
  `assert 200_000 < len(df) < 500_000` for a 2015–2024 procurement
  table — fires on bulk data loss or accidental double-load, lets
  normal quarterly growth through without upkeep.

Tripwires should have a comment with the rationale for the range.
A test that fails because the real data genuinely crossed the bound
should be *updated*, not ignored — but the update is a conscious
edit, not a silent rubberstamp.

---

## Running

From project root:

```
pytest tests/                              # everything
pytest tests/clean/                        # clean layer only
pytest tests/clean/test_licitacao.py -v    # one file, verbose
pytest -k primary_key                      # anything named primary_key
```

Missing parquets should cause the test to *skip*, not fail — this
keeps the suite green in downstream-mode checkouts that don't have
every clean artefact on disk. The shared `load_parquet` fixture in
`conftest.py` should handle this uniformly.

---

## Hooking into the build

For projects using SCons (`rules/scons_builds.md`): add a marker
target gating any critical downstream step (paper build, site
deploy):

```python
env.Command(
    target='build/tests/invariants.ok',
    source=[
        'tests/conftest.py',
        'tests/clean/test_licitacao.py',
        'build/clean/licitacao.parquet',
        # + every test file and the parquet(s) it reads
    ],
    action='python3 -m pytest tests/ -q && mkdir -p build/tests && touch $TARGET',
)
```

Then add `'build/tests/invariants.ok'` to the paper / site build's
source list. A failing test breaks `scons paper`, so you learn
about schema drift before shipping.

The marker pattern (touch a file on success) lets SCons cache the
result: if no source has changed, pytest doesn't re-run.

---

## Relationship to the validation ledger

The AI vocabulary's `property_assertions` entry covers *authoring*
new invariants. Once in a test file:

- The pytest suite is the source of truth for what the table
  guarantees.
- The ledger row for the script can record the initial authoring
  pass (`property_assertions 2026-04-21; N invariants moved to
  tests/clean/test_licitacao.py`).
- Subsequent edits to invariants are regular code changes (git
  diff), not ledger entries.
- The `pending` → `ai-verified` transition for property_assertions
  is driven by existence of a passing test file, not by an AI
  re-check event.

Section-level validation (`skills/validate-section/`) treats
scripts whose invariants live in pytest as already-covered for the
`property_assertions` floor — no AI re-check needed.
