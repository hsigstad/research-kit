---
name: otter
description: "Pull recent Otter.ai meeting-summary emails from Gmail, route each to the right project, and save under docs/meetings/. Use when the user runs /otter or asks to 'grab the otter notes' / 'sync otter meeting summaries' / 'update meeting notes from otter'."
disable-model-invocation: true
---

# Otter Notes Sync (Otter.ai email → projects/<slug>/docs/meetings/)

On-demand sync of Otter.ai meeting summaries into per-project meeting archives.
The Otter → /otter counterpart of Tactiq → /tactiq. Where Tactiq saves Google
Docs to Drive, **Otter shares meetings as email**: for every recorded meeting,
`no-reply@otter.ai` sends a `Meeting Summary for <title>` message containing the
AI summary and a few action items.

**Important — Otter emails are summaries, not transcripts.** The email carries
the AI-written summary plus the first ~3 action items. The **full transcript**
stays in the Otter web app behind auth-gated links; it is not in the email and
cannot be fetched here. So each saved file is the summary + inlined action items,
and records how many action items Otter listed vs how many the email showed. If a
meeting was *also* recorded by Tactiq, prefer `/tactiq` for that one (full
verbatim transcript) — see "Meetings with both Otter and Tactiq" below.

## What this skill does

1. Lists `Meeting Summary for …` emails from `no-reply@otter.ai` via the Gmail MCP tools.
2. Skips any already recorded in `.otter_processed.json` or already saved on disk.
3. Fetches each thread, saves the raw JSON, and parses summary / action items / date / title.
4. Routes the meeting to a project via the `## Meetings` block in each project's `CLAUDE.md` (the same block `/tactiq` uses).
5. Saves to `projects/<slug>/docs/meetings/YYYY-MM-DD-<title-slug>.md`.
6. Records the Gmail message ID in `.otter_processed.json` (workspace root) for idempotent re-runs.
7. Anything unmatched goes to `inbox/meetings/` for manual triage.

## Inputs

Invoked with no required args. Optional:
- A date range (`/otter since 2026-07-01`, `last 14 days`). Default: all unprocessed. Map to a Gmail `newer_than:` / `after:` clause.
- A project slug (`/otter judgeGPT`) to restrict routing.

## Prerequisites

- The Gmail MCP server must be connected (the `mcp__claude_ai_Gmail__*` tools).
  Interactively-authenticated MCP servers can be absent in headless/cron runs —
  this skill is meant to be run interactively, like `/tactiq`.
- Helper script: `research-kit/skills/otter/otter_helpers.py` (email parser +
  meeting-file renderer). It never touches the network — fetching is done by the
  model via the Gmail tools; the helper only parses a file the caller saved.

## Step 1 — list Otter summary emails

Use `mcp__claude_ai_Gmail__search_threads` with:

```
from:no-reply@otter.ai subject:"Meeting Summary for"
```

Append the user's date filter if given (e.g. ` newer_than:14d`). Otter also sends
`Your upcoming meetings` digests from the same address — the `subject:"Meeting
Summary for"` clause excludes them. Each result's `subject` is
`Meeting Summary for <title>`; `id` is the Gmail message/thread ID.

If the first run pulls a long backlog, confirm with the user before processing
more than ~10.

## Step 2 — load dedup state

Read `.otter_processed.json` from the workspace root:

```json
{
  "processed": {
    "<gmail_message_id>": {
      "saved_to": "projects/<slug>/docs/meetings/<file>.md",
      "title": "<meeting title>",
      "date": "YYYY-MM-DD",
      "processed_at": "ISO8601"
    }
  },
  "ignored": {
    "<gmail_message_id>": { "title": "…", "reason": "…", "ignored_at": "ISO8601" }
  }
}
```

Skip any ID in `processed` or `ignored`. Missing/corrupt → treat as
`{"processed": {}, "ignored": {}}` and warn.

**Also reconcile against saved files** — the cache is per-machine and untracked,
so a fresh checkout has no cache even though the meeting files are committed:

```bash
python3 "$SKILL_DIR/otter_helpers.py" scan-ids .   # {otter_id: path} for every saved Otter meeting
```

Treat a message as processed if its ID is in the cache **or** in this scan. This
is what prevents `-2` duplicates when the cache is absent. Optionally backfill
scan-only IDs into `.otter_processed.json`.

Only the user populates `ignored` (e.g. `/otter ignore <message_id>` for a test
recording or a non-project call). Never auto-populate it.

## Step 3 — fetch each unprocessed email

Call `mcp__claude_ai_Gmail__get_thread` with `messageFormat: FULL_CONTENT`.
Otter emails are large (~80–90k chars); the tool usually **saves the result to a
file and prints its path** instead of returning it inline. Use that file path
directly as the parser's `src`. If the result *is* returned inline, write the
JSON to `/tmp/otter/<message_id>.json` yourself and use that.

Either way the parser reads the raw `get_thread` JSON (`{id, messages:[…]}`) and
picks the Otter message on its own — no pre-processing needed.

## Step 4 — parse

```bash
python3 "$SKILL_DIR/otter_helpers.py" parse /path/to/thread.json
```

Returns JSON: `title`, `date` (YYYY-MM-DD), `duration`, `summary`,
`action_items` (list), `action_items_total` (int — from "See N action items →"),
`participants` (best-effort: the owners named on action items), `otter_id`
(Gmail message id).

Notes on the fields:
- **title** comes from the subject (`Meeting Summary for <title>`) — reliable.
- **date** is the meeting date: month/day from the email body's `<Mon DD>, <time>, <N> min` line, year from the email's `Date`. Falls back to the email date.
- **participants** is only the action-item owners — Otter emails have no attendee list. Expect it to be partial; pass `--attendees` to `save` to correct it (names are visible in the summary text, e.g. "X and Y discussed …").

## Step 5 — route to a project

Iterate `projects/*/CLAUDE.md` for a `## Meetings` block (the same block
`/tactiq` reads):

````markdown
## Meetings

```yaml
match:
  - title_contains: ["procurement", "fiscal enforcement"]
  - attendee_name: ["Andrei Leite", "Lucas Mariani"]
```
````

Matching rules:
- `title_contains` — case-insensitive substring against the Otter meeting title. **This is the reliable signal for Otter** (the title is exact).
- `attendee_name` — case-insensitive match against the parsed `participants` **and** the `summary` + `action_items` text (Otter has no attendee list, so match against the notes text, not just `participants`).
- A project matches if **any** rule matches. Multiple matches → ask the user.
- `/otter <slug>` restricts routing to those slugs.
- No match → save to `inbox/meetings/` and surface it so the user can add a rule.

## Step 6 — save the file

Do not hand-write the markdown — the `save` subcommand is the single source of
truth for the format.

Destination: `projects/<slug>/docs/meetings/YYYY-MM-DD-<title-slug>.md`
(unmatched → `inbox/meetings/…`). Slug rules: lowercase, ASCII-fold,
non-alphanumeric → `-`, collapse repeats, trim, ~50 chars.

```bash
python3 "$SKILL_DIR/otter_helpers.py" save \
  /path/to/thread.json <gmail_message_id> \
  projects/<slug>/docs/meetings/YYYY-MM-DD-<title-slug>.md
```

Pass `-` as the message id to read it from the JSON. Pass
`--attendees "Name One,Name Two"` to set the frontmatter attendee list from the
summary text. The subcommand appends `-2`, `-3`, … on collision and prints the
final path. Record that path in `.otter_processed.json`.

Rendered file:

```markdown
---
title: <meeting title>
date: YYYY-MM-DD
attendees: [<name>, ...]
duration: <N min>
otter_id: <gmail_message_id>
source: otter
---

# <meeting title>

## Summary

<AI summary, verbatim>

## Action items

- <item>
- <item>

*Otter listed N action items; M inlined in the email. The remaining items and
the full transcript are in the Otter web app.*
```

The summary and action items are kept **verbatim** — the helper never
re-summarizes or translates. (Otter's transcription occasionally garbles proper
nouns like model names or acronyms; leave the body as-is and note corrections in
the project's curated `docs/meetings.md` if the user maintains one.)

## Step 7 — update dedup state and report

After each successful save, append to `.otter_processed.json` and write back.
On failure, do not record it.

Report:
- N summaries processed
- Per project: count + new files (relative paths)
- Unmatched: count + files in inbox (suggest a routing rule)
- Skipped (already processed): count
- Any meeting whose `action_items_total` > items shown (so the user knows to open Otter for the rest)

## Meetings with both Otter and Tactiq

The same meeting can be captured by both tools (Otter for the summary, Tactiq for
the full transcript). When you know a meeting has both:
- Prefer the **Tactiq** file — the full verbatim transcript is higher fidelity.
- Skip the Otter twin, or save it alongside and note the Tactiq file is the
  primary record. Don't silently produce two competing files for one meeting
  without flagging it.
Detecting the overlap is by (date, title) — check `docs/meetings/` for a
`source: tactiq` file on the same date before saving an Otter one.

## Bootstrapping a project's routing block

The `## Meetings` block is shared with `/tactiq`. If a project has one already,
`/otter` uses it as-is. If the user asks to "set up otter routing for <project>",
add the block (only on request) with placeholder `title_contains` /
`attendee_name` rules to edit.

## Gotchas

- Address and dedup by **Gmail message ID**, never by subject — Otter reuses the
  identical subject `Meeting Summary for <title>` for every instance of a
  recurring meeting.
- `get_thread` on an Otter email usually exceeds the inline size limit and is
  saved to a file — use that path; don't fight to read it inline.
- Otter emails are mostly tracking-link boilerplate; the parser strips URLs and
  HTML entities. If a future email layout changes and `summary`/`action_items`
  come back empty, the banner/marker regexes in `otter_helpers.py` need updating.
- `participants` is best-effort (action-item owners only). Use `--attendees` to
  fix the frontmatter when it matters.
- The full transcript is never in the email. Do not imply the saved file is a
  transcript — it is a summary.
- If `.otter_processed.json` is missing or corrupt, treat as empty and warn
  before reprocessing a backlog.
