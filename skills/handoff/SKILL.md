---
name: handoff
description: "End-of-session: commit and push all changes across projects touched in this session. Use when the user is done working and wants to wrap up."
user_invocable: true
---

# Session Handoff

Commit and push changes from the current session.

## Steps

1. **Identify which projects/pipelines were modified.** Check git status in each one that was touched during the session.

2. **For each repo with uncommitted changes:**
   - Run `git status` and `git diff` to review changes.
   - Stage relevant files (prefer naming specific files over `git add .`).
   - Draft a commit message and confirm with the user.
   - Commit and push.

3. **Update todo.md/done.md** if any tasks were completed during the session:
   - Move completed tasks from `docs/todo.md` to `docs/done.md`.
   - Add any new tasks that emerged to `docs/todo.md`.

## Rules

- Always confirm commit messages with the user before committing.
- If multiple projects were touched, handle them one at a time.
- If there are no changes to commit, say so and skip.
