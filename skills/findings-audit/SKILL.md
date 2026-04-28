---
name: findings-audit
description: "Audit a project's empirical findings against external evidence — anecdotes (news, interviews, court opinions) and aggregate reports (CNJ, IPEA, OECD, FMI). Flags counter-evidence to load-bearing interpretations and surfaces patterns no current finding addresses. Use when the user wants a reality check on findings, before writing up, or after a corpus refresh."
user_invocable: true
---

# /findings-audit — Audit findings against external evidence

Reality-check a project's empirical findings against external evidence the
project has already collected. The audit is **asymmetric by design**: it looks
for counter-evidence to load-bearing interpretations, not confirmation.
Pro-evidence is over-selected (interpretations were authored having seen
supportive evidence) — what tests them is contradictions.

External evidence comes in two families and four source types:

| Family    | Source type        | Typical home                                  | Bias                                              |
|-----------|--------------------|-----------------------------------------------|---------------------------------------------------|
| Narrative | `news`             | `references/news/stories.csv`                 | Over-samples unusual / contested / extreme events |
| Narrative | `interview`        | `references/interviews/*.md`                  | Subject self-selection; contested-case salience   |
| Narrative | `court-opinion`    | `references/cases/*.md`                       | Appellate / published-decision over-representation |
| Aggregate | `aggregate-report` | `references/reports/*.pdf`, `references/cnj/` | Methodology-bound; definitional gaps              |

The procedure is the same in shape but **adjudication and falsification
thresholds differ by type** — see §5 and §6.

Two modes:

- **Targeted (default).** For each finding, derive or accept a falsification
  pattern ("what evidence would contradict this?"), then scan each source
  type for matches.
- **Open-ended (`--open-ended`).** Find evidence patterns that no current
  finding or hypothesis addresses. Surfaces blind spots and new-hypothesis
  candidates. Slower; run quarterly or after a corpus expansion.

## When to invoke

- "sanity check findings against the news / interviews / CNJ reports"
- before drafting a section that leans heavily on a single interpretation
- after a corpus refresh (new articles fetched, new CNJ release, new transcripts)

Don't use it for:

- collecting new evidence (that's `/anecdotes` for news; manual for the rest)
- checking prose against scripts (that's `/validate-section`)
- pure literature lookup — that's `WebFetch`/research

## Args

```
/findings-audit [--findings <path>] [--corpus <path>...] [--mode targeted|open-ended]
                [--finding <slug-or-heading>] [--types news,interview,court-opinion,aggregate-report]
                [--full] [--max-rows N] [--auto]
```

- `--findings` — findings doc to audit. Default: discovered (§1).
- `--corpus` — one or more evidence sources. Default: discovered (§2).
- `--mode` — `targeted` (default) or `open-ended`.
- `--finding` — restrict to one finding (heading slug or phrase).
- `--types` — restrict to a subset of source types. Default: all that exist.
- `--full` — ignore `last_audited_sha` cache.
- `--max-rows` — cap rows examined per flag (cost guardrail).
- `--auto` — skip the §0 confirmation gate. Use for autonomous / scheduled runs.

**Default behavior on bare invocation (`/findings-audit` with no args):**
discover findings doc and sources, derive a plan, **present the plan and ask
the user to confirm or edit before any classification work runs**. See §0.

## Procedure

### 0. Plan and confirm (default; skip with `--auto`)

On bare invocation, run §1, §2, and §3 first as a *plan-only pass* — no
classification, no LLM cost — then present the plan and wait for the user.

The plan should include:

```
Findings audit — plan

Findings doc:    <path> (<N> entries; sha <short>)
Mode:            targeted   [pass --mode open-ended for residual sweep]
Cache:           last audit on <date> at sha <short>; <K> findings changed,
                 <M> sources changed since   [or: no prior audit]

Sources detected:
  [x] news               <N> rows         <path>
  [x] aggregate-report   <N> documents    <paths>
  [ ] interview          (none found)
  [ ] court-opinion      (none found)

Restrict to one finding?   no  [pass --finding <slug> to restrict]
Candidates to read (after keyword/theme filter):
  news               <N1> rows across <K> findings
  aggregate-report   <N2> tables across <K> findings
  ...
  Total:             <N> snippets (warn if >300; see Cost guardrails)

Derived falsification patterns (per finding × source family):
  - <finding-slug-1>:
      narrative:  "..."
      aggregate:  "..."
  - <finding-slug-2>:
      narrative:  "..."
      aggregate:  "..."   [or: n/a — finding has no numeric form]
  ...
```

Then ask:

> Proceed as shown? Or edit:
> (1) findings doc, (2) mode, (3) source types,
> (4) restrict to one finding, (5) falsification patterns, (6) cancel.

If the user picks an edit option, revise that piece and re-show the plan.
Loop until the user confirms or cancels.

If `--auto` is passed, skip this section and proceed to §4.

If args were partially specified (e.g. `--mode open-ended` but no
`--findings`), fill in defaults via discovery, show the plan, and confirm
once. Don't re-prompt on individual fields the user already pinned.

If discovery comes up empty for a load-bearing input (no findings doc;
no evidence sources at all), stop here and ask — don't show a plan you
can't execute.

### 1. Locate the findings doc

Default-discovery order, first hit wins:

1. `docs/reference/key-findings.md`
2. `docs/key-findings.md`
3. `docs/findings.md`
4. `docs/hypotheses.md` (audit the evidence-so-far blocks under each hypothesis)
5. Project-specific path declared in `CLAUDE.md` or `docs/summary.md`

If `--findings` is passed, use it directly. If nothing is found, ask the user
where the load-bearing interpretations live — do not invent.

### 2. Locate evidence sources

Default detection — read `CLAUDE.md` and `docs/summary.md` first since
projects often flag non-default paths. Then probe the canonical locations:

| Source type        | Canonical paths                                      | Format               |
|--------------------|------------------------------------------------------|----------------------|
| `news`             | `references/news/stories.csv` + `texts/NNN.txt`      | newsbr CSV + text   |
| `interview`        | `references/interviews/*.md`                         | free-form markdown  |
| `court-opinion`    | `references/cases/*.md`, `references/cases/*.pdf`    | free-form / PDF     |
| `aggregate-report` | `references/reports/*.pdf`, `references/cnj/*.csv`, `references/oecd/`, `references/ipea/` | PDF / structured |

Build a typed source list before auditing. Show the user what you found and
confirm — especially if the list crosses into aggregate reports, since those
need different prompts than narrative sources.

If a source type is empty, skip it; don't fail. If everything is empty, stop
and recommend `/anecdotes` (for news) or manual collection (for the rest).

### 3. Extract findings + falsification patterns

Parse the findings doc into a list of `(finding_slug, claim, falsification)`.

For **narrative sources** (news, interview, court-opinion), falsification
patterns are short descriptions of a story-shaped contradiction. Examples:

- "A leilão succeeded for a case under R$50k where the debtor had no other
  attached assets." (negates "small-case enforcement rarely fires")
- "A redirecionamento order triggered the named sócios moving assets or
  fleeing jurisdiction." (negates "sócio-loyalty")

For **aggregate-report sources**, falsification patterns are **numeric
ranges or named statistics that contradict the finding**. Examples:

- Finding: "PGFN recovers <1% of stock judicially" → falsification:
  "any CNJ/PGFN-published recovery rate >5% on judicially-pursued stock,
  same year, comparable definition."
- Finding: "Embargos rate is 16% (INSPER)" → falsification: "CNJ Justiça
  em Números or PGFN annual report quoting embargos incidence outside
  the 10-25% band on a comparable population."

Patterns are best derived **per source type per finding** — what would
falsify this finding *in news* vs. *in CNJ data* are different prompts.

If the findings doc declares falsification patterns explicitly (some
projects use a `<!-- falsified-by: ... -->` comment), use those verbatim.
Otherwise derive them, **show the derived list to the user before
auditing, let them edit**. Bad falsification patterns produce garbage flags.

Calibration: a good falsification pattern is **specific and observable in
a single piece of evidence**. Bad patterns ("markets are inefficient")
are too abstract to test.

### 4. Narrow the candidate set (mechanical, no LLM dispatch)

Adjudication in §5 is done by **you, the calling assistant**, reading each
candidate directly — not delegated to a helper LLM call. Project context
(which findings are load-bearing, which caveats already exist, which
interpretations have been softened) is what makes the call accurate, and
that context lives in this conversation, not in a prompt to a sub-model.

So §4 is purely mechanical filtering — narrow the set down to what's
worth reading, then read it.

For each (finding, source type) cell:

1. **Keyword/theme filter.** Each falsification pattern has natural keywords.
   For `stories.csv`, filter rows whose `theme` / `title` / `summary` match
   (regex / substring; no LLM). For free-form `.md`, `grep` paragraphs.
   For `aggregate-report` PDFs/CSVs, locate the relevant table or section
   by ToC / heading match before reading.
2. Cap each cell's candidate set at `--max-rows` (default: no cap; warn if
   any cell exceeds 200 — that's a lot of reading).
3. **If after mechanical filtering the candidate set is still very large**
   (>200 in a single cell), narrow further by:
   - tightening the keyword filter,
   - splitting the falsification pattern into a more specific sub-pattern,
   - or asking the user to broaden `--max-rows` knowingly.

   Do NOT introduce a separate LLM triage pass. If the set is too big to
   read, the falsification pattern is too broad — fix the pattern, not the
   pipeline.

### 5. Adjudicate counter-evidence

You, the calling assistant, read each candidate that survived §4 and
classify it. Do not dispatch a sub-LLM call per candidate — your project
context is what catches the calibration cases (jurisdiction-out-of-scope,
self-reference to the source the finding was derived from, caveats already
declared in the finding). Sub-models won't have it.

The adjudication procedure **dispatches by source type**.

#### 5a. Narrative sources (`news`, `interview`, `court-opinion`)

For each candidate, classify as:

- **counter-evidence-strong** — explicitly describes the falsification
  pattern with named actors / amounts / outcomes.
- **counter-evidence-weak** — consistent with the negation but ambiguous.
- **on-pattern** — consistent with the finding (don't record).
- **off-topic** — not about this finding's domain.

Each `counter-evidence-*` MUST include:

- **anchor quote** — verbatim from the article / transcript / opinion.
- **finding it counters** — slug + exact claim text.
- **why non-trivial** — one line; not trivially explained by source bias
  or by the finding's own caveats.

Without an anchor quote, don't record.

##### Calibration (narrative)

Should NOT be flagged:

- One rare success that the finding already calls "rare" (finding: "leilão
  succeeds in <5% of cases"; story: a successful leilão; that's *consistent*
  unless the finding said "never").
- Story is about a regime/jurisdiction outside the finding's stated scope.
- Story uses the finding's vocabulary loosely.
- Story is the source the finding was derived from (self-reference).

Should be flagged:

- Story describes a category the finding claims doesn't exist.
- Story names actors/amounts directly contradicting the finding's scope.
- Story describes a mechanism the finding rules out.

#### 5b. Aggregate reports (`aggregate-report`)

For each report:

1. Locate the table/section that bears on the finding (use ToC, heading,
   chapter index). If not found, record `not-applicable`.
2. Extract the relevant value(s) — number, year, definition, denominator.
3. Compare against the finding's claim:
   - **counter-evidence-strong** — value contradicts the finding outside
     its stated uncertainty range, AND the definition is comparable.
   - **counter-evidence-weak** — value contradicts but with definition
     mismatch (different denominator, different population, different year)
     that could explain the gap.
   - **on-pattern** — value is consistent with the finding.
   - **definition-incompatible** — record but don't count toward verdict;
     flag as a *measurement reconciliation* follow-up instead.

Each `counter-evidence-*` MUST include:

- **source citation** — report name, year, page/table number.
- **value extracted** — the number with units.
- **definition note** — denominator, population, time window, methodology.
- **finding it counters** — slug + exact claim text.
- **why non-trivial** — one line; specifically: why this isn't a
  definition mismatch.

Without a value and a definition note, don't record.

##### Calibration (aggregate)

Should NOT be flagged:

- Report value differs from finding's value but uses a different
  denominator (e.g., "all processos" vs "EFs only").
- Report's coverage window doesn't overlap the finding's window.
- Finding is a TJSP-only claim; report covers all-Brazil. Reporting the
  delta is fine; flagging as counter-evidence is not, unless the all-Brazil
  number is *inconsistent with TJSP being a typical state*.

Should be flagged:

- Report value contradicts the finding using *the same definition*
  (same denominator, comparable window).
- Report contains a methodology disclosure that invalidates an
  assumption the finding rests on.
- Report's published rate falls outside the finding's stated uncertainty
  range and the denominator difference is too small to explain it.

### 6. Aggregate per-finding verdict (type-weighted)

For each finding, compute counter-evidence weighted by source type:

| Source type        | Weight per `strong` | Weight per `weak` |
|--------------------|---------------------|-------------------|
| `aggregate-report` | 3                   | 1                 |
| `court-opinion`    | 1.5                 | 0.5               |
| `interview`        | 1                   | 0.3               |
| `news`             | 1                   | 0.3               |

Verdict thresholds (sum of weighted counter-evidence):

- **robust** — total weight ≤ 1
- **soft** — total weight 1–3, or any single aggregate-report at strong
  with definition mismatch under review
- **contradicted** — total weight ≥ 3, OR any single aggregate-report at
  strong with confirmed comparable definition

The weighting reflects population-vs-anecdote: one CNJ table is much more
load-bearing than three news anecdotes. Adjust by `--weights` if a project
has a reason to override (rare).

The verdict is a *signal*, not a ruling. The user adjudicates using the
anchor quotes and value extracts.

### 7. Open-ended residual mode (`--mode open-ended`)

Skip §3-6. Instead:

1. Sample (or take all, if corpus < 200) entries per source type.
2. For each, ask: does this fit naturally under any current finding /
   hypothesis? If yes, name it. If no, why — what new pattern does it
   suggest?
3. Cluster the "no" entries. Patterns that recur across ≥ 3 entries are
   candidate hypotheses.

Output: orphan-entry clusters with representative examples, candidate
hypothesis, and recommended next test. Aggregate-report findings here
often surface measurement gaps the project hasn't noticed (e.g., "CNJ
publishes a recovery-by-tribunal table that the project hasn't used").

### 8. Persist results

Three outputs:

#### a) Tagged corpus (durable annotation)

- `stories.csv` — append `audit_flag` column. Values:
  `strong:<finding-slug>:<source-type>` or `weak:...` or empty. Pipe-separated
  for multi-flag rows.
- Free-form `.md` — sidecar `<corpus-path>.audit.json` keyed by file +
  paragraph index.
- `aggregate-report` — sidecar `references/reports/<report-name>.audit.json`
  with per-table flags.

Re-audits confirm, upgrade weak→strong, or downgrade strong→weak (note
in report). Never delete prior tags silently.

#### b) Audit report

Write to `docs/audits/findings/<YYYY-MM-DD>-<mode>.md`. **This is git-tracked
on purpose** — the report is part of the project's reasoning record, not a
build artifact, and the project's `.gitignore` typically excludes `build/`.
A reviewer reading the project history should be able to see what was
audited, when, and what counter-evidence surfaced.

Structure:

```markdown
# Findings audit — YYYY-MM-DD (mode: targeted)

**Findings doc:** path (sha at audit)
**Sources audited:** news (N rows), interviews (N), court-opinions (N),
                    aggregate-reports (N reports)

## Source-bias disclaimer
[per-type disclaimers; see §9]

## Findings × counter-evidence

### <finding-slug-1> — <verdict> (weight: X.X)
**Claim:** <one line>
**Falsification patterns:** narrative: <...>; aggregate: <...>

#### Counter-evidence by source type

**news** — N candidates, S strong, W weak
- [story-id, outlet, date]: "anchor quote" (why non-trivial: ...)

**aggregate-report** — N reports examined
- CNJ Justiça em Números 2024, p. 142, Table 4.3:
  value <X>, definition <Y>. Counters claim <Z>.
  Why non-trivial: <comparable denominator established>

**court-opinion / interview** — ...

[repeat per finding]

## Suggested follow-ups
- ...

## Skipped findings
- <slug>: <reason>
```

#### c) `last_audited_sha` cache + machine-readable JSON

`docs/audits/findings/state.yaml`:

```yaml
findings_path: docs/reference/key-findings.md
findings_sha: <git short sha>
sources:
  - type: news
    path: references/news/stories.csv
    signature: <sha256 or row-count + last-modified>
  - type: aggregate-report
    path: references/reports/cnj_justica_em_numeros_2024.pdf
    signature: <sha256>
last_audited_at: YYYY-MM-DD
mode: targeted
```

`docs/audits/findings/<date>-<mode>.json`:

```json
{
  "audit_date": "YYYY-MM-DD",
  "mode": "targeted",
  "findings_path": "...",
  "findings_sha": "...",
  "sources": [{"type": "news", "path": "...", "n": 523}],
  "findings": [
    {
      "slug": "...",
      "claim": "...",
      "falsifications": {"narrative": "...", "aggregate": "..."},
      "form": "dominant",
      "verdict": "robust",
      "weight": 0.0,
      "counter_evidence": [
        {
          "source_type": "news",
          "strength": "weak",
          "id": "stories.csv:312",
          "anchor_quote": "...",
          "why_non_trivial": "...",
          "outlet": "jota",
          "date": "2025-03-14"
        },
        {
          "source_type": "aggregate-report",
          "strength": "strong",
          "report": "CNJ Justiça em Números 2024",
          "page": 142,
          "table": "4.3",
          "value": "8.2%",
          "definition": "embargos / EFs filed, federal courts, 2023",
          "why_non_trivial": "comparable denominator to finding's INSPER 16%"
        }
      ]
    }
  ],
  "suggested_follow_ups": [{"finding": "...", "next_step": "..."}]
}
```

Scope subsequent audits using the cache:

- Findings unchanged + sources unchanged → no work; report "no re-check
  needed; last audit <date>".
- Findings changed → audit changed/new findings against full corpus.
- Source signature changed → audit new entries against all findings.
- Both → union.

### 9. Source-bias disclaimers

Emit at the top of every report. Project-specific paths can override.

> **Counter-evidence is informative; absence is not confirmation.** Each
> source type has its own bias. Read the verdict against the bias.
>
> - **News.** Over-samples unusual / extreme events. A finding that says
>   "X is rare" cannot be confirmed by absence of X-news. A finding that
>   says "X never happens" can be falsified by a single named X-story.
> - **Interviews.** Over-samples contested cases and articulate respondents.
>   A finding about routine practice cannot be confirmed by interview
>   absence; one transcript describing the contradicted pattern is
>   suggestive but not load-bearing alone.
> - **Court opinions.** Over-samples appellate and published decisions.
>   Trial-level outcomes are largely invisible. A finding about
>   first-instance practice should not be falsified by appellate outliers.
> - **Aggregate reports.** Methodology-bound. Definitions can shift across
>   editions. A reported value contradicts a finding only if the
>   denominator, population, and window are comparable. Definition
>   mismatches are *measurement reconciliation* tasks, not contradictions.

## Falsification-threshold rules (per finding form)

Findings differ in how counter-evidence should affect them.

| Finding form                                     | Counter-evidence load                                                                          |
|--------------------------------------------------|------------------------------------------------------------------------------------------------|
| "X never happens" / "no Y under Z"               | 1 strong (any source) → contradicted                                                            |
| "X is dominant" / "X explains most of Y"         | aggregate-report ≥1 strong, OR narrative ≥3 distinct strong → soft; aggregate-report counter with same denominator → contradicted |
| "X is rare ~N%"                                  | aggregate-report value outside N±band → contradicted; narrative needs counter-rate to exceed N substantially; otherwise robust  |
| "Mechanism: X drives Y"                          | narrative ≥1 strong showing Y without X → soft; aggregate report contradicting → contradicted   |
| Hedged ("data are consistent with X")            | counter-evidence raises follow-ups, not rules out                                               |

If the finding doesn't declare its form, infer from the prose and note the
inference. Strong-form claims should rarely sit in a findings doc without
explicit caveats; flag any that do.

## Cost guardrails

The cost is your reading time, not external API calls — there are no
sub-model dispatches in this skill. Guardrails accordingly:

- Stop and confirm if total post-filter candidates exceed **300 across
  all (finding × source) cells**. Reading 300 short snippets is feasible;
  reading 1,000 is not, and the audit becomes shallow.
- For `--mode open-ended`, sample at most 200 entries per source type per
  pass unless the user asks for full corpus.
- For `aggregate-report` PDFs > 50 pages, locate the relevant
  table/section by ToC / heading **before reading**. Don't read whole PDFs
  end to end — the table is the load-bearing part; the surrounding prose
  is context only.
- Surface the candidate-count breakdown as part of §0's plan so the user
  sees scope before confirming.

## Scope guards

- **Don't edit the findings doc.** The audit reports; the human revises.
- **Don't drop "on-pattern" entries silently.** Header should state how
  many were examined and how many were on-pattern.
- **Don't claim a finding is "confirmed" by absence.** Verdict vocabulary
  is *robust / soft / contradicted* — never "confirmed."
- **Don't audit findings with no quantitative backing.** If a finding is
  itself anecdote-derived, the audit becomes circular. Skip with a note.
- **Don't propose new collection during an audit.** If a (finding, source-type)
  cell has zero candidates, that goes in the report ("no evidence either
  way; consider running `/anecdotes` with queries X, Y" or "consider
  fetching CNJ Justiça em Números 2024") — not a side trip.
- **Don't blur source types.** A weighted total of 3.0 driven entirely by
  one aggregate-report is a different signal than the same total driven by
  10 news anecdotes. The report should always show the per-type breakdown.

## Composition with other skills

- Upstream: `/anecdotes` (collects news for the corpus this audit consumes).
- Sibling: `/validate-section` (audits prose against scripts; this audits
  interpretations against external evidence — same spirit, different axis).
- Downstream: findings flagged `contradicted` should trigger a hypothesis
  revision or follow-up test in the project's todo / hypotheses doc.

## Common failure modes

- **Overflag (narrative).** Without good calibration anchors, every story
  mentioning the domain looks like counter-evidence. Re-read §5a if the
  strong-counter rate exceeds ~5% of news candidates on a mature findings
  doc.
- **Underflag (aggregate).** Definition mismatch dismissals can become a
  blanket excuse. Confirm denominators / windows / populations explicitly;
  if they're comparable, the report value is binding.
- **Drift to confirmation.** The skill is asymmetric. If you find yourself
  recording supportive entries, stop — that belongs elsewhere.
- **Stale falsification patterns.** Findings doc edited but derived
  patterns not refreshed → auditing yesterday's claims. The
  `last_audited_sha` cache catches doc edits; derived patterns should
  refresh on every doc change.
- **Whole-PDF reads.** Reading a full report end to end before locating
  the table that bears on the finding wastes context and tempts
  hallucinated values. Always locate the table first via ToC / heading;
  quote with page + table number.
