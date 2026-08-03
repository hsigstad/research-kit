# findings-audit — output schemas

Loaded at the persist step (§8) of `/findings-audit`. Holds the exact templates
for the three durable outputs and the source-bias disclaimer block that heads
every report.

## Persist three outputs

### a) Tagged corpus (durable annotation)

- `stories.csv` — append `audit_flag` column. Values:
  `strong:<finding-slug>:<source-type>` or `weak:...` or empty. Pipe-separated
  for multi-flag rows.
- Free-form `.md` — sidecar `<corpus-path>.audit.json` keyed by file +
  paragraph index.
- `aggregate-report` — sidecar `references/reports/<report-name>.audit.json`
  with per-table flags.

Re-audits confirm, upgrade weak→strong, or downgrade strong→weak (note
in report). Never delete prior tags silently.

### b) Audit report

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
[per-type disclaimers; see the disclaimer block below]

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

### c) `last_audited_sha` cache + machine-readable JSON

`docs/audits/findings/state.yaml`:

```yaml
findings_path: docs/findings.md
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

## Source-bias disclaimers

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
