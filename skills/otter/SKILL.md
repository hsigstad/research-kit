---
name: otter
description: "Pull recent Otter.ai meeting notes from Gmail, route each to the right project, and save as raw markdown under docs/meetings/. Use when the user runs /otter or asks to 'grab the otter notes' / 'sync meeting notes' / 'save the recent meeting transcripts'."
user_invocable: true
---

# Otter Notes Sync (Otter → projects/<slug>/docs/meetings/)

On-demand sync of Otter.ai meeting transcripts from Gmail into per-project meeting archives.

## What this skill does

1. Searches Gmail for recent Otter.ai notification emails.
2. For each unprocessed email, extracts meeting metadata + raw note content.
3. Matches the meeting to one of the user's projects via a `## Meetings` block in each project's `CLAUDE.md`.
4. Saves the raw notes to `projects/<slug>/docs/meetings/YYYY-MM-DD-<title-slug>.md`.
5. Records the Gmail message ID in `~/research/.otter_processed.json` for idempotent re-runs.
6. Anything unmatched goes to `~/research/inbox/meetings/` for manual triage.

## Inputs

The user invokes the skill with no required args. Optional:
- A date range (e.g., `/otter since 2026-04-01` or `last 7 days`). Default: last 30 days.
- A specific project slug to limit routing (e.g., `/otter procure`).

## Step 1 — find Otter emails

Use `mcp__claude_ai_Gmail__search_threads` with a query like:

```
from:noreply@otter.ai newer_than:30d
```

Adjust `newer_than` based on user's date arg. If the user asks for a specific date range, use Gmail's `after:YYYY/MM/DD before:YYYY/MM/DD` syntax.

For each thread, use `mcp__claude_ai_Gmail__get_thread` to retrieve full message bodies.

Otter sender addresses observed in practice include `noreply@otter.ai` and sometimes `notifications@otter.ai`. If the first query returns nothing, broaden to `from:otter.ai`.

## Step 2 — load dedup state

Read `~/research/.otter_processed.json`. Format:

```json
{
  "processed": {
    "<gmail_message_id>": {
      "saved_to": "projects/<slug>/docs/meetings/<filename>.md",
      "title": "<meeting title>",
      "date": "YYYY-MM-DD",
      "processed_at": "ISO8601"
    }
  }
}
```

Skip any message ID already present. Create the file with `{"processed": {}}` if it doesn't exist.

## Step 3 — extract per email

For each unprocessed email, extract:

- **title**: meeting title (Otter usually puts it in the subject, e.g. `Notes from "Procurement Corruption"` or `"Procurement Corruption" - Otter notes`). Strip wrapping quotes, "Notes from", "- Otter notes", etc.
- **date**: the meeting date. Otter notification emails are sent near the meeting end, so the email's internal date is a reasonable proxy. If the body contains a meeting date/time, prefer that.
- **attendees**: names/emails listed in the Otter email body if present.
- **otter_url**: link to the Otter conversation page (usually one prominent link in the body).
- **body**: the email body text (Otter usually includes summary, action items, and sometimes a transcript snippet — keep all of it raw).

Note: Otter emails often include a **summary** and a **link to the full transcript** rather than the entire transcript inline.

### Fetching the full transcript

After extracting the `otter_url` from the email, use Playwright to fetch the full transcript:

1. Navigate to the `otter_url` using `mcp__playwright__browser_navigate`.
2. Wait for the page to load, then take a snapshot with `mcp__playwright__browser_snapshot` to understand the page structure.
3. The transcript is typically in the main content area. Look for the transcript text elements and extract them.
4. If Otter requires login or the page doesn't load the transcript (e.g., paywall, auth wall), fall back to the email summary and note in the output that the full transcript could not be fetched.
5. Include the full transcript in the saved file under a `## Transcript` section, after the email summary.

If Playwright is unavailable or the fetch fails, save the email summary as-is (graceful degradation).

## Step 4 — route to a project

Iterate over `~/research/projects/*/CLAUDE.md`. Each project may contain a `## Meetings` section with a fenced YAML block:

````markdown
## Meetings

```yaml
match:
  - title_contains: ["procurement", "fiscal enforcement"]
  - attendee: coauthor1@example.edu
  - attendee: coauthor2@example.org
```
````

Matching rules:
- `title_contains` is a list; match is case-insensitive substring against the meeting title.
- `attendee` matches if that email appears among the meeting's attendee emails (from the Otter body) **or** the calendar invite (if known — usually you only have what's in the email).
- A project matches if **any** rule matches.
- If multiple projects match, ask the user which one. Show both project slugs and the meeting title.
- If no project matches, save to `~/research/inbox/meetings/` and report this in the summary so the user can update routing rules later.

## Step 5 — save the file

Per-project meeting files:

- Path: `~/research/projects/<slug>/docs/meetings/YYYY-MM-DD-<title-slug>.md`
- `<title-slug>` = lowercase, ASCII-folded, non-alphanumeric → `-`, collapse repeats, trim, truncate to ~50 chars.
- Create `docs/meetings/` if it doesn't exist.
- If the file already exists (rare — title collision on same day), append ` -2`, ` -3` to the slug.

Unmatched files:

- Path: `~/research/inbox/meetings/YYYY-MM-DD-<title-slug>.md`

File contents (markdown):

```markdown
---
title: <meeting title>
date: YYYY-MM-DD
attendees: [<email1>, <email2>, ...]   # if known
otter_url: <url>                         # if present
gmail_message_id: <id>
---

# <meeting title>

<raw email body, preserved verbatim>
```

Keep the body **raw** — do not summarize, restructure, or strip content. The user wants faithful capture.

## Step 6 — update dedup state

After each successful save, append the entry to `~/research/.otter_processed.json` and write back.

If the save fails, do not record it as processed.

## Step 7 — report

Print a summary to the user:

- N notes processed
- Per project: count + list of new files (relative paths)
- Unmatched: count + list of files in inbox
- Skipped (already processed): count

For unmatched items, suggest adding a routing rule to the relevant project's CLAUDE.md.

## Bootstrapping a project's routing block

If the user asks to "set up meeting routing for procure" or similar, add a `## Meetings` block to that project's `CLAUDE.md` with placeholder rules they can edit. Don't add the block proactively — only on request.

## Gotchas

- The first run after a long gap may pull many emails. Confirm with the user before processing more than ~10 at once.
- Otter sometimes sends multiple emails per meeting (e.g., live notes + final notes). Treat each email as its own entry; the dedup is per `gmail_message_id`, not per meeting. If this becomes noisy, we can add per-meeting dedup later.
- Don't auto-create routing rules from observed attendees — that's the user's call.
- The skill does NOT delete or label the Gmail messages. Leave them in place.
- Calendar event attendees are not always present in the Otter email body; routing by `attendee` works best when the user has added attendee patterns explicitly.
- If `~/research/.otter_processed.json` is missing or corrupt, treat as empty (`{"processed": {}}`) and warn the user.
