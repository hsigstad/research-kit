---
name: memory-audit
description: Audit Claude's persistent auto-memory (MEMORY.md + memory files) against current workspace state; propose stale-entry updates, merges, and deletions for user approval, then apply the approved batch. Use periodically (e.g. when MEMORY.md grows past ~30 entries or quarterly) or when recalled memories keep contradicting the repo.
user_invocable: true
---

# /memory-audit — Prune and refresh Claude's persistent memory

The memory counterpart of `/distill-style`. Auto-memory is an
append-mostly store: entries are written when something non-obvious is
learned, but nothing verifies them later. Entries rot in three ways —
the fact changes (a bug gets fixed, a file moves, a decision is
superseded), the fact gets absorbed into durable docs (rules, findings,
decisions logs), or two entries accumulate that cover the same thing.
Rotten memories are worse than none: they are recalled with the
authority of "what I know" and contradict the repo.

## Arguments

- `/memory-audit` — audit the current session's memory directory (the
  one whose `MEMORY.md` loads into context).
- `/memory-audit --all` — audit every store under
  `~/.claude/projects/*/memory/`.
- `/memory-audit --dry` — produce the report only; skip the
  apply step even if the user approves inline.

## Workflow

### 1. Inventory

Read `MEMORY.md` and every memory file it indexes. Also list memory
files NOT indexed in `MEMORY.md` (orphans) and index lines whose file
is missing (dead pointers) — both are findings by themselves.

### 2. Verify each entry against the workspace

For each memory file, extract its checkable claims: file paths, flags,
numbers, states ("X is pending", "Y is broken", "use Z workaround").
Check them against the current repo state — read the referenced files,
grep for the flags, check dates. Delegate this to cheap subagents in
batches when the store is large; each verifier returns
entry → {holds | changed | absorbed | unverifiable} with one-line
evidence. Classify:

- **current** — claims hold; keep unchanged.
- **stale** — a checkable claim no longer holds (file moved, bug fixed,
  number superseded). Propose an update or deletion.
- **absorbed** — the content now lives in a durable artifact (a rule
  file, decisions.md, findings.md, a method note). Propose deletion,
  citing where it lives now. Memory duplicating docs is recall noise.
- **duplicate/overlap** — two entries cover one fact. Propose a merge
  into the better-named file.
- **unverifiable** — states a preference or event the repo cannot
  confirm (e.g. user preferences, conversations). Keep unless the user
  says otherwise; flag only if it contradicts another entry.

Session-scoped trivia that should never have been saved (one-off task
state, things fully derivable from the repo) is proposed for deletion
regardless of freshness.

### 3. Write the proposal report

One numbered proposal (`M1`, `M2`, …) per action, grouped by action
type (delete / update / merge / index-repair). Each proposal shows the
entry's name, its current one-line description, the evidence (what was
checked, what came back), and — for updates — the exact replacement
text. Put the report in the conversation directly if it is short
(≤ ~15 proposals); otherwise write it to the scratchpad and give the
path.

### 4. User approval

Same protocol as `/distill-style`: the user replies "approve all",
"approve M1, M3", "approve all except M2", "reject M4 — <reason>".
Never apply without approval.

### 5. Apply

For approved proposals: edit or delete the memory files, update
`MEMORY.md` index lines to match (every file change has a matching
index change), fix `[[...]]` links that pointed at deleted/renamed
entries. Deletion is real deletion — memory is a working cache, not
history; the git-tracked repos are the archive.

### 6. Final report

Entries kept / updated / merged / deleted; store size before and after;
any recurring rot pattern worth a note (e.g. "session-state entries
keep appearing — stop saving those").

## Rules and gotchas

- **Never auto-apply.** Every mutation requires explicit approval.
- **Bias toward deletion.** The index is read every session; each line
  must earn its context cost. When in doubt between "update" and
  "delete because the repo now records it", delete.
- **Don't churn `user`/`feedback` entries** on repo evidence alone —
  preferences aren't falsified by code. Flag contradictions between
  them instead.
- **Keep name slugs stable** on update so inbound `[[links]]` survive.
- **`--all` mode:** audit each store against its own project root, not
  the workspace root.
- **Cadence:** worth running when `MEMORY.md` passes ~30 lines, after
  a big refactor/migration, or when a recalled memory is caught wrong
  twice in one week.
