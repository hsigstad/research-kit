# Paper Section Label Convention

LaTeX label convention for paper sections, used by `validate-section`
and other tooling to identify section types automatically. The first
colon-separated segment after `sec:` is the **section type**;
type-conditional checks key off this segment.

---

## Convention

Every `\section{…}` and `\subsection{…}` carries a label:

```
\label{sec:<type>}              % top-level
\label{sec:<type>:<slug>}       % subsection
```

The `<slug>` is freeform, identifying the subsection within its type.

## Recommended types

| Type            | Use for                                                |
|-----------------|--------------------------------------------------------|
| `intro`         | Paper introduction                                     |
| `institutions`  | Institutional / legal / political background          |
| `data`          | Data section                                           |
| `theory`        | Theoretical framework, model setup                    |
| `methods`       | Identification strategy, empirical strategy           |
| `results`       | Main empirical results (and sub-types)                |
| `discussion`    | Mechanisms, interpretation, robustness narrative      |
| `welfare`       | Welfare analysis, policy implications                 |
| `conclusion`    | Conclusion                                              |
| `appendix`      | Appendix sections                                      |

The vocabulary is open — projects may add their own types. Tools that
don't recognize a type fall back to body-section defaults (skip
intro-ordering, conclusion-brevity, etc.; apply universal checks).

## Example

```latex
\section{Introduction}\label{sec:intro}
\section{Institutional Background}\label{sec:institutions}
\section{Data}\label{sec:data}
\section{Identification}\label{sec:methods}
\section{Theory}\label{sec:theory}
\section{Results}\label{sec:results}
  \subsection{Main results}\label{sec:results:main}
  \subsection{Robustness}\label{sec:results:robustness}
  \subsection{Heterogeneity}\label{sec:results:heterogeneity}
\section{Discussion}\label{sec:discussion}
\section{Welfare}\label{sec:welfare}
\section{Conclusion}\label{sec:conclusion}
\section*{Appendix A: Proofs}\label{sec:appendix:proofs}
```

## Build integration

The build script that produces `build/paper/section_deps.json` parses
each section's label and stores the first segment as `type:`:

```json
{
  "results:main": {
    "type": "results",
    "title": "Main results",
    "label": "sec:results:main",
    "macros": [...],
    "figures": [...],
    "backing_scripts": [...]
  }
}
```

Downstream tools (`validate-section`, `style-review --section`,
type-conditional style checks) read `section_deps.json[slug].type`
rather than re-parsing main.tex on every invocation.

## Fallback heuristic (when labels are missing)

For sections without a type-prefixed label, tools infer the type from
heading text using these word matches (case-insensitive):

| Heading contains                                          | Inferred type   |
|-----------------------------------------------------------|-----------------|
| `introduction`                                            | `intro`         |
| `institutional`, `legal background`, `setting`, `context` | `institutions`  |
| `data`                                                    | `data`          |
| `theory`, `model`, `framework`                            | `theory`        |
| `identification`, `empirical strategy`, `method`          | `methods`       |
| `result`, `estimate`, `finding`                           | `results`       |
| `discussion`, `mechanism`, `interpretation`               | `discussion`    |
| `welfare`, `policy`, `implication`                        | `welfare`       |
| `conclusion`                                              | `conclusion`    |
| `appendix`                                                | `appendix`      |

If neither label nor heading determines a type, treat as a generic
body section: skip type-conditional checks; apply universal checks
(topic sentences, triangular structure, robot-body persuasion,
caption self-containment, every-number-discussed).

## Adoption

The convention is recommended, not enforced. Existing papers without
type-prefixed labels still pass through the heading-text heuristic.
New papers should adopt it from the start; existing papers can adopt
gradually as labels are added or sections renamed.
