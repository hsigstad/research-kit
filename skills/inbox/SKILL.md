---
name: inbox
description: >
  Send a message from one Claude session to another concurrent session — typically a
  sandboxed session asking the host (non-sandboxed) session to do something the sandbox
  can't (write via a read-only connector, run a host-only tool), or leaving a note for a
  named session. Delivery is automatic via the inbox hook. Also covers the rare container
  (e.g. ~/me) that can't reach the shared inbox and needs a manual relay.
---

# Inter-session inbox

Concurrent Claude sessions leave messages for each other under
`<workspace>/inbox/messages/`. A `UserPromptSubmit` hook (`userprompt_inbox.py`) injects any
unseen messages addressed to a session at its next prompt, so **delivery is automatic** — nobody
has to relay or be told to "check the inbox".

**Host and sandbox share the SAME `<workspace>` filesystem and git repo.** The sandbox's
`/workspace` and the host's workspace are the same directory on the same machine (see
`[[workspace_shared_filesystem]]`). So the normal case is simple: write the message into the
shared inbox and the other session picks it up. There is no "may not be mounted" problem in the
standard sandbox — that only bites the separate `~/me` container (see Fallback below).

## Just use the sender tool

Don't hand-write message files. Use:

```sh
research-kit/tools/send_message.py --to host --subject "<subject>" --body "<text>"
# body can also come from stdin:
echo "Rebuild rol and deploy." | research-kit/tools/send_message.py --to host --subject "rol deploy"
```

The tool resolves the workspace, writes `<from>-to-<to>_<utc-timestamp>.md` into
`<workspace>/inbox/messages/`, and stamps the machine-parsed headers
(`From-Session:` / `From-Name:` / `To-Session:` / `To-Name:`) so the recipient can **reply
straight back**. Hand-rolling the file loses reply-routing and name targeting.

### Addressing (pick one)

- `--to host | sandbox | all` — environment address. Default is the *other* env (a sandbox
  session defaults to reaching a host session). Use when you don't care which session of that
  type picks it up. If none is running, the file waits until one is.
- `--to-name "<name>"` — target the session a user named with `/rename` (resolved via
  `~/.claude/sessions/`). This is how "message the 'CGU pipeline' session" works. Prints the
  list of named sessions if the name doesn't match.
- `--to-session <id>` — target one specific session id (e.g. a `From-Session` you received in a
  reply).

## Where the workspace is

`send_message.py` and the hook both resolve `<workspace>` the same way, so you rarely need the
literal path — but for reference:

- **Sandbox:** `/workspace`.
- **Host, laptop:** `~/research`.
- **Host, educloud:** `/projects/ec113/henrik/research/` (set via `RESEARCH_WORKSPACE`).

Resolution order: `$RESEARCH_WORKSPACE` if set, else the first of `/workspace` / `~/research`
that contains `research-kit/`. On educloud, `RESEARCH_WORKSPACE` must be set because that path
isn't in the default candidate list.

## Receiving

The hook delivers up to 3 unseen messages per prompt and tracks seen filenames per session in
`~/.claude/state/inbox_seen_<session>.json`. Act only on messages relevant to your current work;
leave targeted messages meant for another session (don't delete them). **Delete (`rm`) only the
messages you actually consumed** — they're git-ignored plain files. Because host and sandbox
share the same `/workspace`, a message another session wrote is already on disk for you — no
`git pull` or re-run needed.

## Fallback: a container without the shared inbox (`~/me`)

The `~/me` container does **not** mount the shared workspace, so `send_message.py` can't write
into `<workspace>/inbox/messages/` and the host cron can't see this container's filesystem (see
`[[inbox_messaging]]`). There, stage the message in the version-controlled `~/me` outbox and tell
the user it needs a manual relay:

1. Preflight — is the shared inbox reachable?
   ```sh
   test -d /workspace/inbox/messages && echo SHARED || echo ISOLATED
   ```
2. If `SHARED`, use `send_message.py` as above — you're done.
3. If `ISOLATED` (the `~/me` case), write the message to `~/me/claude/outbox/sandbox-to-host_<TS>.md`
   and say plainly: *"Message staged in the ~/me outbox; it won't auto-deliver from this
   container — paste the request into a host session, or open a session in ~/me and check
   `claude/outbox/`."*

> Verified against source on 2026-08-04: `research-kit/tools/send_message.py` (sender),
> `research-kit/tools/hooks/userprompt_inbox.py` (delivery hook), `research-kit/tools/drain_outbox.py`
> (host upload-outbox drain — a separate mechanism for Dropbox uploads, not messaging).
