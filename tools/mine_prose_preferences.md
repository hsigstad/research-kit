# Task: mine conversation transcripts for Henrik's prose preferences

**Goal.** Enrich the voice card
(`research/rules/writing_style/henrik_voice.md`) with Henrik's revealed
prose-style preferences harvested from his Claude Code conversation
histories — specifically his own comments on writing, wording, and
voice.

**Source discipline (non-negotiable).** Signal comes ONLY from Henrik's
own words: his hypothes.is annotations and his in-conversation comments
on prose. NEVER model his voice on AI-generated prose he merely
accepted. A mined entry is valid only when it is *his* comment plus the
prose he was reacting to.

## Why this is a committed, per-machine task

Transcripts live under `$HOME/.claude/projects/**/*.jsonl` and are **not
synced between machines** (Henrik runs Claude Code on both a laptop and
the Educloud server). The `research` and `research-kit` repos **are**
synced. So:

1. Run the miner on **each** machine against its local transcript store.
2. It writes a **machine-tagged** output file into the synced repo
   (`research/rules/writing_style/voice_mining/<machine>-<host>.{jsonl,md}`),
   so laptop and Educloud harvests merge instead of overwriting.
3. Distill all harvests into the voice card (one pass, by hand or LLM).

## Run it

```bash
python3 research-kit/tools/mine_prose_preferences.py
```

Outputs a `.jsonl` (structured) and a `.md` digest grouped by session.
The digest shows, for each hit, what Claude had just written and
Henrik's reaction to it.

## Distill into the voice card

Read the `.md` digest. For each candidate, keep it only if it is a
genuine, reusable style preference (not one-off task chatter the keyword
net caught). Fold it into the matching **move** in
`research/rules/writing_style/henrik_voice.md` as his verbatim comment +
the flagged prose. Add a new move section only if a real pattern isn't
already covered. Keep the card tight — it is a few-shot, not an archive.

## Status

- [x] Educloud harvest (`educloud-ic-rhel9-*`) — committed.
- [ ] Laptop harvest — run on the laptop, commit, then distill.
