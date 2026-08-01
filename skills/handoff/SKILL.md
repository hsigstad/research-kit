---
name: handoff
description: "End-of-session: commit and push all changes across projects touched in this session. Write a handoff note only when there's a cognitive thread the rest of the system doesn't capture (mid-stream WIP, noticed-but-not-acted-on, partial verification). Use when the user is done working and wants to wrap up."
---

# Session Handoff

Wrap up an end-of-session: commit and push the session's changes, plus
optionally write a focused handoff note for the next session.

## Default flow

Always do these:

1. **Identify which projects/pipelines were modified** during the session
   (`git status` in each one that was touched).

2. **For each repo with uncommitted changes**, separately:
   - Review `git status` and `git diff` to inventory the changes.
   - **If the repo has convention-guard scripts (`source/diagnostic/*.py`
     that exit non-zero on a violation), run them and confirm green
     before committing.** These are the project's own drift/lint guards
     (e.g. a canonical-spec or superseded-citation check); a red guard
     means this session introduced a NEW violation to fix first. Run at
     the checkpoint, not as a blocking commit hook — in a shared repo a
     repo-wide guard can go red for another session's change, so read the
     `[FAIL]` line and only act on your own.
   - Stage relevant files — prefer naming specific files over `git add .`
     to avoid sweeping in unrelated WIP.
   - Draft a commit message and confirm with the user.
   - Commit, then push (unless the user asks to hold off).

3. **Move completed `todo.md` items to `done.md`** if the session
   actually completed any. Add new tasks that emerged to `todo.md`.

After step 3, **decide whether a handoff note is needed**.

## When to write a handoff note

A note is worth writing **only** when the rest of the system doesn't
capture what the next session should know. The rest of the system
already gives you commits, `done.md`, `todo.md`, the per-iteration
`/next` reports, `artifacts.yaml`, and `decisions.md` — most "where
did I leave off" questions are answered by those.

A note earns its keep when:

- **Mid-stream work:** a script is half-written, or run but not yet
  propagated to docs. Commit + push captures the bytes; the note
  captures *what's incomplete and why*.
- **Noticed but not acted on:** "Bacenjud hit-rate has a weird drop in
  2022Q4 — not investigated." No commit, no todo, but worth
  surfacing.
- **Partial verification:** "parser fix verified on TJSP-PGE only;
  PGM cohort hasn't been spot-checked." Easy to forget in commits.
- **Cognitive context for the next session** that doesn't fit a
  one-line todo (e.g., "the cross-state merge in H17 is tricky;
  come back to it fresh — the inscrição-year alignment isn't
  trivial").

**Skip the note** when the session finished a clean iteration with
nothing surprising — `/next`'s end-of-iteration report, the commit
message, and an updated `todo.md`/`done.md` cover it.

Ask the user explicitly: *"Anything mid-stream or noticed-but-not-
acted-on that the next session should know? (skip if no)"* — and
write a note only if the answer is yes.

## How to write the note (when warranted)

Write to a **per-session file** under `docs/notes/handoffs/`:

```
docs/notes/handoffs/<ISO-timestamp>_<short-tag>.md
```

- `<ISO-timestamp>`: `YYYY-MM-DDTHH-MM` (filename-safe; colons replaced
  with hyphens). `date +%Y-%m-%dT%H-%M` gives the right value.
- `<short-tag>`: a brief slug derived from the session's primary
  `/next` target if one was set (e.g. `h17-cross-jurisdictional`),
  otherwise from what the user describes (`parser-fix-followup`,
  `paper-companion-s4`).

Content schema (see `research/rules/workspace.md` §Session handoff):

```markdown
# Session handoff — 2026-05-11T15-32 — h17-cross-jurisdictional

- **What's mid-stream / unfinished:** [if anything]
- **Noticed but not acted on:** [if anything]
- **Next session should:** [specific next step that doesn't fit todo.md]
```

Use only the sections that apply — empty sections add noise. Commit
the new file with the rest of the session's work (or as a tail
commit).

## Why per-session files (not append-to-todo.md)

Multiple parallel `/handoff` sessions on the same repo would race on
`todo.md`:
- **Git conflicts** if both commit simultaneously.
- **Overlapping content** with both sessions writing under the same
  date header.

Per-file handoffs sidestep both: distinct filenames, distinct files,
no merge conflict surface, clear ownership.

## Pickup workflow (separate session)

When starting a new session:

1. `ls docs/notes/handoffs/` — enumerate pending handoffs.
2. Read each file (or have Claude summarize).
3. Act on whatever's relevant: open the mid-stream work, investigate
   the noticed-but-not-acted-on flag, run the verification step.
4. After acting, `git rm docs/notes/handoffs/<file>` to clear the
   handoff. Commit the deletion separately or roll into a `/next`
   step 6 close-out commit.

Handoffs that go a week without being consumed are a smell — either
the cognitive thread no longer matters, or it's important enough to
turn into a `todo.md` entry. Either way, don't let them accumulate
indefinitely.

## Rules

- **Always commit + push.** That's the literal "wrap up" — never skip.
- **Always confirm commit messages with the user.** No silent
  commits.
- **One repo at a time** when multiple were touched.
- **No empty handoff notes.** If the session finished cleanly, the
  commit + `done.md` + `todo.md` is the entire handoff. Don't write
  a placeholder.
- **Don't append to `todo.md` for handoffs.** That convention was
  retired — per-session files in `docs/notes/handoffs/` is the
  current pattern (see `research/rules/workspace.md`).
- **No silent overwrites.** Each session writes a uniquely-named file;
  collisions are a bug.

## Common failure modes

- **Wrong filename collision** — two sessions starting in the same
  minute pick the same `<timestamp>_<tag>`. Mitigate by including
  seconds in the timestamp, or appending a short hash:
  `date +%Y-%m-%dT%H-%M-%S`.
- **`docs/notes/handoffs/` doesn't exist yet** — create it as part of
  the first handoff (the directory is just a folder, not a structured
  doc; no template needed).
- **Pending handoff blocks the user's flow** — if a pickup step
  surfaces a noticed-but-not-acted item that the user isn't ready to
  address, *don't* delete the handoff. Leave it pending; better to
  re-encounter it next session than to forget the observation.
