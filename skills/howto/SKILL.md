---
name: howto
description: Print Henrik's one-page Claude Code cheat sheet (situation -> command).
disable-model-invocation: true
---

# /howto — print the cheat sheet

Read `$ROOT/research/HOWTO-claude.md` (workspace root is `~/research` on
the host, `/workspace` in the sandbox) and print it verbatim as the
response. No commentary, no summarizing.

If the user asks a follow-up ("when do I use X?"), answer from the
cheat sheet first, then from the underlying skill's SKILL.md if needed.
