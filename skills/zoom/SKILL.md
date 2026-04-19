---
name: zoom
description: "Create a Zoom meeting as a Google Calendar event. Use when the user wants to schedule a meeting, e.g. 'set up zoom meeting with Darcio Tue 2pm'."
user_invocable: true
---

# Zoom Meeting

Create a Google Calendar event with the user's personal Zoom room link.

## Configuration

Read `$RESEARCH/contacts.yaml` for:
- **defaults**: Zoom link, passcode, default duration, timezone, organizer email
- **contacts**: name/nickname → email lookup

`$RESEARCH` is the `research/` directory inside the workspace root (i.e. the directory containing `rules/`, `skills/`, `contacts.yaml`).

## Parsing the request

The user may say things like:
- `/zoom Darcio Tue 2pm`
- `/zoom Gui and Daniel Friday 10am 1h`
- `set up zoom meeting with Sergio tomorrow 3pm`

Extract:
1. **Who** — one or more contact names/nicknames → resolve via contacts.yaml
2. **When** — day and time → resolve relative to today's date and the default timezone
3. **Duration** — if specified (e.g., "1h", "45 min"); otherwise use default from contacts.yaml

## Creating the event

Use `mcp__claude_ai_Google_Calendar__gcal_create_event` with:

- **summary**: "{OrganizerFirstName} and {Name1}" for one attendee, or "{OrganizerFirstName}, {Name1}, {Name2}, ..." for multiple (or a custom title if the user provides one). Use first names only. The organizer's first name comes from contacts.yaml defaults or the organizer email.
- **start**: resolved datetime in RFC3339 with timezone from defaults
- **end**: start + duration
- **location**: Zoom link from defaults
- **description**:
  ```
  Join Zoom Meeting
  {zoom_link}

  Passcode: {zoom_passcode}
  ```
- **attendees**: resolved email(s) + organizer email (with `organizer: true`)
- **sendUpdates**: `"all"` (so attendees get the invite)

## Before sending

Show the user a summary of what will be created:
- Title, attendees (name + email), date/time, duration
- Ask for confirmation before creating

## After creating

Show the event link and confirm it was sent.

## Gotchas

- If a contact name is ambiguous or not found in contacts.yaml, ask the user.
- If a contact has multiple emails, use `default_email` unless the user specifies otherwise.
- Resolve "tomorrow", "Tuesday", "next week" etc. relative to today's date.
- "Tue" means the next upcoming Tuesday (today or later).
- If no time is given, ask for it — don't guess.
