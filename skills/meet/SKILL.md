---
name: meet
description: "Create a Google Meet meeting as a Google Calendar event. Use when the user wants to schedule a meeting with a Google Meet link, e.g. 'set up meet with Darcio Tue 2pm' or '/meet Gui Friday 10am'."
user_invocable: true
---

# Google Meet Meeting

Create a Google Calendar event with an auto-generated Google Meet link.

## Configuration

Read `$RESEARCH/contacts.yaml` for:
- **defaults**: default duration, timezone, organizer email and name
- **contacts**: name/nickname → email lookup

`$RESEARCH` is the `research/` directory inside the workspace root (i.e. the directory containing `rules/`, `skills/`, `contacts.yaml`).

The Zoom-specific fields in defaults (`zoom_link`, `zoom_passcode`) are not used by this skill.

## Parsing the request

The user may say things like:
- `/meet Darcio Tue 2pm`
- `/meet Gui and Daniel Friday 10am 1h`
- `set up google meet with Sergio tomorrow 3pm`

Extract:
1. **Who** — one or more contact names/nicknames → resolve via contacts.yaml
2. **When** — day and time → resolve relative to today's date and the default timezone
3. **Duration** — if specified (e.g., "1h", "45 min"); otherwise use default from contacts.yaml

## Creating the event

Use `mcp__claude_ai_Google_Calendar__create_event` with:

- **summary**: "{OrganizerFirstName} and {Name1}" for one attendee, or "{OrganizerFirstName}, {Name1}, {Name2}, ..." for multiple (or a custom title if the user provides one). Use first names only. Organizer first name comes from contacts.yaml `defaults.organizer_name`.
- **startTime**: resolved datetime in ISO 8601
- **endTime**: start + duration
- **timeZone**: from `defaults.timezone`
- **attendeeEmails**: resolved attendee email(s). The organizer is added automatically by the calendar when the event is on their primary calendar.
- **addGoogleMeetUrl**: `true` — this generates a fresh Meet link attached to the event.
- **notificationLevel**: `"ALL"` so attendees get the invite email with the Meet link.

Do **not** set `location` or write the Meet link into `description` — Calendar attaches the auto-generated link as a structured conference field, visible to attendees in the event and in the invite email.

## Before sending

Show the user a summary of what will be created:
- Title, attendees (name + email), date/time, duration

Ask for confirmation before creating.

## After creating

Show the event link and confirm the invite was sent. Mention that Otter will auto-join if the meeting falls on the configured calendar (Otter is set up to auto-record all calendar meetings).

## Gotchas

- If a contact name is ambiguous or not found in contacts.yaml, ask the user.
- If a contact has multiple emails, use `default_email` unless the user specifies otherwise.
- Resolve "tomorrow", "Tuesday", "next week" etc. relative to today's date.
- "Tue" means the next upcoming Tuesday (today or later).
- If no time is given, ask for it — don't guess.
- If `addGoogleMeetUrl` silently fails to attach a link (rare; happens if Meet is disabled for the account), warn the user and offer to fall back to `/zoom`.
