---
name: tactiq
description: "Pull recent Tactiq meeting transcripts from Google Drive, route each to the right project, and save as raw markdown under docs/meetings/. Use when the user runs /tactiq or asks to 'grab the tactiq notes' / 'sync meeting transcripts' / 'save the recent tactiq transcripts'."
disable-model-invocation: true
---

# Tactiq Notes Sync (Tactiq → projects/<slug>/docs/meetings/)

On-demand sync of Tactiq.io meeting transcripts into per-project meeting archives.

Tactiq is a Chrome extension that auto-records Google Meet sessions and saves transcripts to a Google Drive folder named `Tactiq Transcription/` as Google Docs.

The skill writes processed-file IDs to `.tactiq_processed.json` and saves transcripts under `projects/<slug>/docs/meetings/`.

## What this skill does

1. Lists files in `gdrive:"Tactiq Transcription/"` via rclone.
2. For each unprocessed file, exports the Google Doc as plain text via the Drive API.
3. Parses title, date, attendees, and transcript body from the Tactiq format.
4. Routes the meeting to a project via the `## Meetings` block in each project's `CLAUDE.md`.
5. Saves to `projects/<slug>/docs/meetings/YYYY-MM-DD-<title-slug>.md`.
6. Records the Drive file ID in `.tactiq_processed.json` (workspace root) for idempotent re-runs.
7. Anything unmatched goes to `inbox/meetings/` for manual triage.

## Inputs

The user invokes the skill with no required args. Optional:
- A date range (e.g., `/tactiq since 2026-04-01` or `last 7 days`). Default: all unprocessed.
- A specific project slug to limit routing (e.g., `/tactiq procure`).

## Prerequisites

- rclone configured with a `gdrive` remote (see `~/.config/rclone/rclone.conf`).
- Run in a non-sandboxed session — the skill needs network access and the rclone config file.
- Helper script: `research-kit/skills/tactiq/tactiq_helpers.py` (Drive download, Tactiq parser, meeting-file renderer).

## Step 1 — list Tactiq docs

```bash
rclone lsjson gdrive:"Tactiq Transcription/"
```

Returns JSON with one entry per doc, including `ID` (Drive file ID) and `ModTime`. Tactiq names every file `Meeting Transcription.docx` regardless of meeting title — the actual title is inside the doc. **Always dedup by Drive `ID`, never by filename.**

If the call fails with `RATE_LIMIT_EXCEEDED`, wait ~60 seconds and retry. Drive's quota is per-minute; rclone's app credentials hit it easily.

If the user passed a date filter, prune entries whose `ModTime` is before the cutoff.

## Step 2 — load dedup state

Read `.tactiq_processed.json` from the workspace root:

```json
{
  "processed": {
    "<drive_file_id>": {
      "saved_to": "projects/<slug>/docs/meetings/<filename>.md",
      "title": "<meeting title>",
      "date": "YYYY-MM-DD",
      "processed_at": "ISO8601"
    }
  },
  "ignored": {
    "<drive_file_id>": {
      "title": "<meeting title or filename>",
      "date": "YYYY-MM-DD",
      "reason": "<short reason — e.g., 'solo recording', 'not project-relevant'>",
      "ignored_at": "ISO8601"
    }
  }
}
```

Skip any file ID present in either `processed` or `ignored`. If the file is missing or corrupt, treat as `{"processed": {}, "ignored": {}}` and warn the user.

The `ignored` section is for transcripts the user has explicitly marked as not worth saving anywhere (solo test recordings, unrelated calls, etc.). Add entries when the user invokes `/tactiq ignore <file_id>` or asks to mark specific transcripts as ignored. Never auto-populate `ignored` — only the user decides what to ignore.

## Step 3 — fetch each unprocessed doc

rclone alone cannot download two files that share a name in the same Drive folder (its source-side dedup keeps only one), so we use the Drive API export-by-ID directly. The `tactiq_helpers.py` script reads the OAuth access token from rclone's config and calls the Drive API.

```bash
# Refresh rclone's access token as a side effect.
rclone about gdrive: > /dev/null 2>&1

# Download each file by ID.
SKILL_DIR="$HOME/.claude/skills/tactiq"
mkdir -p /tmp/tactiq
python3 "$SKILL_DIR/tactiq_helpers.py" download <FILE_ID> /tmp/tactiq/<FILE_ID>.txt
```

If the Drive call returns 401, run `rclone about gdrive:` again to force a token refresh and retry.

## Step 4 — parse the Tactiq export

```bash
python3 "$SKILL_DIR/tactiq_helpers.py" parse /tmp/tactiq/<FILE_ID>.txt
```

Returns JSON with `title`, `date` (YYYY-MM-DD), `attendees` (list of names), `highlights`, `transcript` (raw lines), and `transcript_lines` (structured `{timestamp, speaker, text}` objects).

The Tactiq plaintext format (observed 2026-05-01):

```
Transcript delivered by Tactiq.io - get it for your Google Meet today!
View the full transcript ...


<DD Month YYYY> | <Title>
Attendees: <name1>, <name2>


Highlights
<highlights or boilerplate>


Transcript
<MM:SS or HH:MM> <Speaker>: <text>
...
```

Notes on the format:

- Tactiq uses the Google Meet event title; if the meeting had no title, it falls back to the literal string `Meeting Transcription`. Flag those for the user — routing on a generic title is fragile.
- Attendees are display names from Google Meet, not email addresses.
- Long meetings are sometimes truncated by Tactiq. If `transcript` ends abruptly mid-sentence, note it in the report.

## Step 5 — route to a project

Iterate over `projects/*/CLAUDE.md` and look for a `## Meetings` block:

````markdown
## Meetings

```yaml
match:
  - title_contains: ["procurement", "fiscal enforcement"]
  - attendee_name: ["Andrei Leite", "Lucas Mariani"]
```
````

Matching rules:

- `title_contains` — case-insensitive substring against the meeting title.
- `attendee_name` — case-insensitive match against any attendee display name. (Tactiq does not provide emails, so email-based `attendee:` rules will never match a Tactiq export.)
- A project matches if **any** rule matches.
- If multiple projects match, ask the user.
- If the user passed project slugs (e.g., `/tactiq procure`), restrict routing to those.
- If no project matches, save to `inbox/meetings/` and surface this in the summary so the user can update routing rules.

## Step 6 — save the file

Decide the destination path, then let the helper render and write it. Do **not**
hand-write the markdown — the `save` subcommand is the single source of truth for
the file format, so the layout never drifts between runs.

Destination path: `projects/<slug>/docs/meetings/YYYY-MM-DD-<title-slug>.md`
(unmatched meetings go to `inbox/meetings/YYYY-MM-DD-<title-slug>.md`).

Slug rules: lowercase, ASCII-fold, non-alphanumeric → `-`, collapse repeats, trim,
truncate to ~50 chars.

```bash
python3 "$SKILL_DIR/tactiq_helpers.py" save \
  /tmp/tactiq/<FILE_ID>.txt <FILE_ID> \
  projects/<slug>/docs/meetings/YYYY-MM-DD-<title-slug>.md
```

The subcommand parses the transcript, renders the frontmatter + transcript
markdown, appends `-2`, `-3`, ... if the path already exists, and prints the
final path written. Record that printed path in `.tactiq_processed.json`.

Pass `--attendees "Name One,Name Two"` to override the frontmatter attendee list
when the Tactiq `Attendees:` line is ambiguous — e.g. a single `Lastname, First`
name that the comma-split parser reads as two people.

The rendered file looks like:

```markdown
---
title: <meeting title>
date: YYYY-MM-DD
attendees: [<name1>, <name2>, ...]
tactiq_id: <drive_file_id>
source: tactiq
---

# <meeting title>

## Highlights

<highlights section, verbatim — omitted when empty or default boilerplate>

## Transcript

[MM:SS] **<Speaker>**: <text>

[MM:SS] **<Speaker>**: <text>

...
```

The body is kept **raw** — the helper never summarizes, restructures, translates,
or strips content.

## Step 7 — update dedup state and report

After each successful save, append the entry to `.tactiq_processed.json` and write back. If the save fails, do not record it.

Report a summary to the user:

- N transcripts processed
- Per project: count + list of new files (relative paths)
- Unmatched: count + list of files in inbox
- Skipped (already processed): count
- Any meetings whose title is the literal `Meeting Transcription` — flag so the user can rename in Drive or set a Meet event title next time
- Any transcripts that look truncated

For unmatched items, suggest adding a routing rule to the relevant project's `CLAUDE.md`.

## Bootstrapping a project's routing block

If the user asks to "set up tactiq routing for procure" or similar, add a `## Meetings` block to that project's `CLAUDE.md` with placeholder `title_contains` and `attendee_name` rules they can edit. Don't add the block proactively — only on request.

## Gotchas

- Tactiq names every doc `Meeting Transcription.docx` — never dedup or address by filename, always by Drive file ID.
- The first run after a long gap may pull many transcripts. Confirm with the user before processing more than ~10.
- The Drive access token in `rclone.conf` is short-lived (~1 hour). Run `rclone about gdrive: > /dev/null 2>&1` before reading the token to trigger an rclone-managed refresh.
- Drive API quota errors (`RATE_LIMIT_EXCEEDED`) happen surprisingly often with rclone's app credentials. Sleep ~60s and retry.
- Tactiq exports do not include attendee emails. Email-based `attendee:` routing rules will never match a Tactiq export — use `attendee_name:` instead.
- Tactiq sometimes uses the literal title `Meeting Transcription` when the Meet event had no name. The slugged filename will collide if multiple such meetings happen on the same day; the `-2`, `-3` suffix logic handles it, but flag the user so they set Meet titles up front.
- The skill does NOT delete or move docs in Drive. Files stay in `Tactiq Transcription/` indefinitely.
- If `.tactiq_processed.json` is missing or corrupt, treat as empty and warn the user before reprocessing.
- This skill must run in a non-sandboxed session; rclone needs network and the config file.
