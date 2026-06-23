---
name: distill-style
description: Read raw entries in research/rules/writing_feedback_log.md, cluster them by tag, propose concrete edits to writing_style.md (general baseline + workspace overlay + per-section files), and let the user approve a batch. Flips status of consumed entries to distilled or rejected. Use when the log has accumulated enough raw entries to be worth turning into rules.
user_invocable: true
---

# /distill-style — Turn raw style-feedback entries into rule edits

The companion to `/fetch-annotations` Step 7. That step *harvests* coauthor
feedback as raw entries; this skill *distills* accumulated raw entries into
proposed edits to the writing-style rule files, with user approval.

## Arguments

- `/distill-style` — process all `Status: raw` entries in
  `research/rules/writing_feedback_log.md`.
- `/distill-style --since YYYY-MM-DD` — only entries appended after that date.
- `/distill-style --tag <tag>` — only one tag's cluster.

## Targets

The rules live in three places. Decide per cluster:

1. `research-kit/rules/writing_style.md` — general baseline (public,
   sibling repo). Edit when the rule is general-purpose empirical-econ
   writing advice that any project would benefit from.
2. `research/rules/writing_style.md` — workspace overlay (banned phrases,
   referee carve-out, workspace-specific tics). Edit when the rule is
   workspace- or author-specific. Banned-phrase swaps land here.
3. `research-kit/rules/writing_style/<section>.md` — per-section files
   (`intro.md`, `methods.md`, `results.md`, `data.md`, `discussion.md`,
   `conclusion.md`, `theory.md`, `institutions.md`, `abstract.md`,
   `body.md`, `appendix.md`). Edit only when the entries explicitly
   address a section-specific concern.

**Default = general.** Route to a per-section file only when the coauthor's
note explicitly speaks to a section-level concern (e.g., "the intro
doesn't motivate the outcome", "literature review should be near the end",
"data section needs to define ACIA in table notes"). Source-file path
alone is NOT enough — a jargon complaint in `5Methods.tex` is still a
general jargon rule unless the note frames it as a methods-section
concern.

## Workflow

### 1. Read the log and the rule files

- Read `research/rules/writing_feedback_log.md` to collect all
  `Status: raw` entries (or filtered by `--since` / `--tag`).
- Read the current text of `research-kit/rules/writing_style.md`,
  `research/rules/writing_style.md`, and each section file in
  `research-kit/rules/writing_style/`. Knowing the current text lets the
  proposals say "amend this paragraph" instead of "add some general
  guidance".

### 2. Cluster and route

Group entries by tag. For each tag's entries:

- **Judge target.** Default = general. Route to a section file only when
  the coauthor's note clearly says so. Route to the workspace overlay
  when the lesson is a specific phrase swap or author-specific tic.
- **Split if needed.** A tag cluster may produce >1 proposal if the
  entries split into distinct rules (e.g., `jargon` entries split into
  "define acronyms on first use" + "no internal pipeline labels in
  prose").
- **Singleton clusters are allowed** but flagged "n=1" so the user knows
  the rule rests on one data point.
- **Drop noise.** If a cluster is too thin or too scattered to support a
  rule, mark its entries `Status: rejected — insufficient signal`.

### 3. Write the proposal report

Produce `research/rules/writing_feedback_proposals_YYYY-MM-DD.md` with
sections per target file. Each proposal must have:

- A number (`P1`, `P2`, …).
- Target file + the specific paragraph/section it amends (or "new
  section").
- A `**Current text:**` block (verbatim) if amending, or "new" if adding.
- A `**Proposed text:**` block — the exact text to insert/replace. Write
  it as if it will be pasted verbatim into the rule file.
- A `**Supporting entries:**` list — short quote+note excerpts from the
  raw entries that justify the rule, with the source location and
  coauthor for each. This is what the user uses to decide whether the
  rule generalizes.
- A `**Cluster size:**` line (n=X).
- Each supporting entry references the log entry by date+source so
  status flipping is unambiguous later.

### 4. Hand the report to the user

Tell the user the report path and ask them to reply with approvals.
Acceptable approval forms:

- "approve all"
- "approve P1, P3, P5"
- "approve all except P2, P7"
- "approve P3 with edit: <new text>"
- "reject P4 — <reason>"
- "defer P6"

Don't walk through them one at a time. The user reviews the file
holistically and replies with a list.

### 5. Apply approved edits

For each approved proposal:

- Edit the target file (use Edit tool).
- Find the supporting raw entries in
  `research/rules/writing_feedback_log.md` and flip
  `Status: raw` → `Status: distilled → {target_file}:{section_or_anchor}`.
- For rejected proposals, flip supporting entries to
  `Status: rejected — {reason}`.
- For deferred proposals, leave entries as `raw` and note the proposal
  number in the report file.

### 6. Final report

Summarise back to the user:

- Number of proposals approved / rejected / deferred.
- Number of log entries flipped to distilled / rejected / left raw.
- The rule files that changed (so they can re-read for coherence).
- Any emerging `other`-tag clusters worth promoting to a new tag.

## Rules and gotchas

- **Never auto-edit.** Every rule-file change requires user approval.
- **Never delete log entries.** Status flip only.
- **Banned-phrase swaps go to the workspace overlay's table**, not the
  baseline — they may be coauthor- or workspace-specific.
- **AI-voice patterns** typically go to baseline §3 (Sentences) or §2
  (Voice), not the workspace overlay.
- **n=1 attribution-leak / causal-language** are legitimate even at small
  n because the principle is sharp. Flag for the user, don't auto-reject.
- **Vocab gap detection.** If the `other` tag has grown ≥3 entries that
  share a theme, propose a new tag in `writing_feedback_log.md`'s
  `## Tags` section as a separate P (proposal) — same approval workflow.
- **Don't touch existing distilled / rejected entries.** They're frozen
  history.
- **If a proposal contradicts existing text**, surface that in the
  proposal block explicitly so the user can see the conflict.
- **The proposal file is intermediate.** After application, the user can
  delete it; the durable record is the log's status field + the rule
  files.
