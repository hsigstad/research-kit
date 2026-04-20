# SCons Build Convention

How data pipelines and paper builds are orchestrated. Applies to every
project with a data pipeline and a paper that cites computed numbers,
figures, or tables.

The goal: a single command rebuilds exactly what's stale. No coauthor
should ever compile a paper whose figures, tables, or macros reflect
an older state of the code than `main.tex` currently expects.

---

## Tool

**SCons** is the project build tool. An `SConstruct` file at the
repository root defines the dependency graph from raw inputs through
the paper's final artefacts.

Why SCons over Make, snakemake, or ad-hoc shell scripts:

- Python-native, so dependency graphs live in the same language as
  the pipeline.
- Content-hash change detection by default — edits that don't change
  output don't cascade.
- `-n` (dry run) shows what would rebuild.
- `-jN` parallelises trivially.
- No DSL to learn beyond Python.

---

## Pattern

One `env.Command` call per primary output. The `source=` list
contains the script plus every imported helper from `source/` — SCons
only sees files listed here, so importing a new helper without
adding it to `source=` breaks dependency detection silently.

```python
env.Command(
    target='build/clean/licitacao.parquet',
    source=['source/clean/licitacao.py', 'source/clean/parse.py'],
    action='python3 -m source.clean.licitacao',
)
```

**`action=`**: canonical form is `python3 -m source.<module>`. Using
`-m` so the package's `__init__.py` chain works and imports resolve
from the project root.

**Chaining**: the return value of one `Command` can be a `source=` of
another. SCons then rebuilds the second when the first's target
changes.

```python
court_case = env.Command(
    target='build/clean/court_case.parquet',
    source=['source/clean/court_case.py'],
    action='python3 -m source.clean.court_case',
)

env.Command(
    target='build/clean/court_party.parquet',
    source=['source/clean/court_party.py', court_case],
    action='python3 -m source.clean.court_party',
)
```

**`env.Precious(...)`**: mark outputs that are expensive to recreate
so SCons doesn't delete them before rebuilding (important for large
parquets or long LLM runs).

---

## Layered dependency graph

SCons should cover every layer in `rules/build_layers.md`:

1. **Clean** — `build/clean/*.parquet` targets depending on raw data
   and `source/clean/*.py` scripts.
2. **Intermediate** (if present) — `build/intermediate/*.parquet`
   targets depending on clean-layer outputs.
3. **Assemble** — `build/assemble/*.parquet` targets depending on
   clean and intermediate.
4. **Analysis / figures / tables** — `build/analysis/*.json`,
   `paper/figures/*.{pdf,png}`, `paper/tables/*.tex` each depend on
   assemble outputs (never on clean directly — see `build_layers.md`).
5. **Paper macros** — `paper/numbers.tex` and `paper/numbers.json`
   depend on every analysis JSON the macros read from.
6. **Paper artefacts** — `main.pdf` and the make4ht HTML depend on
   `main.tex`, `references.bib`, `numbers.tex`, all figures, and all
   tables.

Every edge that exists in reality must exist in the SConstruct. A
missing edge means "paper looks up-to-date but isn't".

---

## Paper as a build target

The paper itself is the final SCons target. Use `env.Command` to wrap
the PDF and HTML builds rather than running `pdflatex` / `make4ht` by
hand:

```python
env.Command(
    target='paper/main.pdf',
    source=['paper/main.tex', 'paper/references.bib',
            'paper/numbers.tex'] + figures + tables,
    action='cd paper && latexmk -pdf main.tex',
)

env.Command(
    target='build/make4ht/main.html',
    source=['paper/main.tex', 'paper/numbers.tex'] + figures + tables,
    action='cd paper && make4ht -d ../build/make4ht main.tex "html5,mathjax"',
)
```

With this wiring, `scons paper/main.pdf` guarantees the PDF reflects
the current state of all upstream code — no need for a separate
orchestrator to remember to run the number generator first.

Orchestration scripts (`build.sh`, `deploy.sh`) stay thin: they call
`scons <target>` and then do the non-data work (rsync to gh-pages,
`gh release create`, etc.). They do not re-implement any part of the
dependency graph.

---

## Usage conventions

| Command                           | What it does                                              |
|-----------------------------------|-----------------------------------------------------------|
| `scons`                           | Rebuild the default target (typically `paper/main.pdf`).  |
| `scons -n`                        | Dry run — print the command chain that would execute.     |
| `scons -j4`                       | Parallel build (adjust to machine; memory-heavy scripts may need `-j2`). |
| `scons build/clean/foo.parquet`   | Rebuild one target and its dependencies.                  |
| `scons --clean`                   | Remove generated targets. Ignores `Precious` marks.       |

Long-running scripts (LLM calls, scrapers) should be SCons targets
even though you rarely want them to auto-run. Mark them `Precious`
and rebuild manually when needed (`scons <that target>`). The alias
`scons paper` (a named alias for the paper target) is the usual
default.

---

## Common failure modes

- **Silent staleness.** Adding a new import to a script without
  updating its SCons `source=` list. SCons happily uses the stale
  parquet because it doesn't know the script changed — no error, just
  wrong numbers. Discipline: every `from source.X import Y` has a
  matching entry in `source=`.
- **Double orchestration.** A `build.sh` that runs things SCons
  already tracks, in a different order. The two drift and users stop
  trusting SCons. Fix: `build.sh` only calls `scons <target>` plus
  side-effect commands (deploy, notify); it doesn't invoke
  `python3 -m source.X` directly.
- **Hash-insensitive outputs.** Scripts whose outputs embed
  timestamps or random orderings trigger unnecessary rebuilds because
  SCons sees the parquet as changed. Sort deterministically and avoid
  embedding `datetime.now()` unless semantically required.

---

## Relationship to other conventions

- **Build layers** (`rules/build_layers.md`): SCons edges follow the
  layered chain; don't let `source/figure/` scripts read from
  `build/clean/` even if the SCons graph doesn't forbid it.
- **Paper macros** (`rules/paper_macros.md`): `paper/numbers.tex`
  must be an SCons target whose sources are every analysis JSON the
  macros read from, so editing an upstream script propagates to the
  paper automatically.
- **Validation ledger** (`meta/validation_ledger.md`): the ledger's
  `depends_on` column should mirror the SCons `source=` lists. If the
  two disagree, one of them is wrong.
