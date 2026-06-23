---
name: fetch-annotations
description: Pull hypothes.is annotations left by coauthors on a project's rendered site, map each one back to its source .md file, walk the user through applying (or skipping) each as an edit, write a response log, and optionally post condensed replies back as threaded annotations on hypothes.is. Use when the user wants to incorporate feedback left as web annotations.
user_invocable: true
---

# /fetch-annotations — Pull coauthor annotations from hypothes.is and apply them

Coauthors annotate the rendered project site via hypothes.is (sidebar on every
doc page and the paper). This skill fetches those annotations, maps each one
to the corresponding source `.md` file using the quoted text, walks the
user through applying each as an edit to the repo, writes a response log,
and (optionally) posts condensed replies back to hypothes.is so each thread
shows what was done.

## Arguments

- `/fetch-annotations` — target the current project (auto-detected)
- `/fetch-annotations [project-slug]` — target a specific project
- `/fetch-annotations --since 2026-04-01` — only annotations updated since date

## What you do

### 1. Locate project and site URL

Find workspace root by searching upward for `CLAUDE.md` next to `projects/`
and `pipelines/`. Resolve the project: `$ROOT/projects/{slug}/`.

Determine the site URL prefix:
- Look at `build.sh` for a `deploy_site` target pushing to `gh-pages`. If the
  repo is `hsigstad/{slug}`, the URL is `https://hsigstad.github.io/{slug}/`.
- If unclear, ask the user once.

### 2. Get the group ID (first time per project)

Private annotations live in a hypothes.is group. Check for a cached group ID:

- `$PROJECT/.claude/fetch-annotations.json` with `{"group": "..."}`

If not cached, ask the user for the group ID (visible in the group page URL:
`https://hypothes.is/groups/{ID}/{slug}`). Optionally cache it. For public
annotations only, no group is needed.

### 3. Fetch annotations

Run the shared tool:

```bash
python3 $ROOT/research/tools/fetch_annotations.py \
    --url-prefix https://hsigstad.github.io/{slug}/ \
    --group {GROUP_ID} \
    [--since YYYY-MM-DD] \
    --json > /tmp/annotations.json
```

For private groups, `HYPOTHESIS_API_TOKEN` (or `HYPOTHESIS_TOKEN`) must be
exported (get one at https://hypothes.is/account/developer). If the call
fails with 401, prompt the user to set it. The user may keep the token in
`~/.bashrc` for future invocations.

### 4. Map each annotation to a source file

Each annotation has:
- `url` — rendered page, e.g. `.../institutions.html`
- `quote` — exact text selected in the browser
- `text` — coauthor's comment
- `user`, `updated`, `tags`

Mapping rules:
- `{prefix}/institutions.html` → `$PROJECT/docs/institutions.md`
- `{prefix}/paper.html` → `$PROJECT/paper/paper.tex`
- `{prefix}/` (root) → `$PROJECT/README.md` (best guess; ask if unsure)

For each annotation, grep the `quote` in the mapped source file to locate the
line. If the quote matches multiple places or none, flag it and show what was
found. Quotes are rendered HTML text, so whitespace/line breaks in the source
may differ — fall back to matching the first 5–8 significant words.

### 5. Present the plan and walk through each annotation

Show a numbered summary first:

```
Found 7 annotations (5 with suggested edits, 2 pure comments):
  [1] docs/institutions.md:42  — Lucas  "the SPC registry was ..."
  [2] docs/methods.md:88       — Pedro  "typo: 'judgue' → 'judge'"
  ...
```

Then for each annotation, propose a concrete action:
- **Pure comment / question** → offer to append a note under a TODO section
  in the file, or skip.
- **Suggested edit** (typo fix, rewording, factual correction) → propose the
  specific Edit operation (old_string / new_string) based on the quote and
  comment text. Show the diff.
- **Ambiguous** → show the annotation and ask the user what to do.

For each one, ask: apply / skip / edit-my-version / stop. Apply approved
edits with the Edit tool one at a time so the user can see each change.

### 6. Write the response log

As you walk through annotations (Step 5), maintain a markdown log at
`$PROJECT/docs/responses_{author}_{YYYY-MM-DD}.md`, one entry per
annotation in numeric order. Each entry should have:

- The annotation number and source location (e.g. `paper/4OLS.tex:42`).
- A blockquote of the coauthor's selected text.
- The coauthor's note (verbatim, prefixed with their name).
- A short response from us — what we agreed/disagreed with, what we did.
- An `**Action:**` line stating the concrete change (which file edited,
  what TODO logged, or "none — superseded by #X").

This is the document we can hand to the coauthor offline (email, Drive,
WhatsApp) AND it's the source the posting step (Step 8) will condense
into hypothes.is replies. Keep entries faithful to the conversation;
don't paper over disagreements.

If multiple annotations are addressed by a single edit (e.g. "#10 + #27
both ask for X"), give them one combined entry under the lowest number,
and reference it from the higher number (e.g. "#27 — handled under #10").

### 7. Harvest style-flavored feedback to the workspace log (optional)

After the response log is complete, classify each annotation by *kind*:

- **content** — factual correction, methodological pushback, missing
  citation, "this number is wrong", scope/framing decisions about what
  to claim. Skip.
- **style** — rewording, clarity, sentence length, "buries the lede",
  "too jargony", "intro doesn't motivate", register, punctuation. Append.
- **mixed** — append the style part only; the content part is already
  captured in the project response log.
- **typo** — pure typo/spelling. Skip (noise).
- **meta** — about the process, not the text ("let's discuss on a call").
  Skip.

For each `style` and `mixed` entry, append one record to
`$ROOT/research/rules/writing_feedback_log.md` below the
`<!-- /fetch-annotations appends below this line -->` marker, in the format
documented at the top of that file. Use exactly one tag from the fixed
vocab listed there. Mark `Status: raw`.

Do NOT edit `research/rules/writing_style.md` or the research-kit baseline
here. The log is harvest; distillation is a separate, manual
`/distill-style` pass (not yet implemented at time of writing). If you find
the same annotation keeps appearing across projects and the rule is
obvious, mention it to the user rather than auto-promoting — they decide
what becomes a rule.

If the `other` bucket is taking on entries that share a pattern, surface
that to the user at the end of this step — emerging clusters are the
trigger to update the vocab in `writing_feedback_log.md`.

### 8. Post condensed replies to hypothes.is (optional)

After the response log is complete, offer the user the option to post
each response as a threaded reply back to the original annotation. This
keeps the conversation discoverable on the rendered site and lets the
coauthor respond again.

Workflow:

1. **Get a token.** Auth requires `HYPOTHESIS_API_TOKEN` (or
   `HYPOTHESIS_TOKEN`) in env. If not set, ask the user — they can
   create one at https://hypothes.is/account/developer. Suggest saving
   to `~/.bashrc` for reuse.

2. **Build a mapping file.** Generate a JSON list at
   `$PROJECT/.claude/annotation_replies_{YYYY-MM-DD}.json`:

   ```json
   [
     {
       "n": 1,
       "parent_id": "<annotation id>",
       "parent_url": "<rendered page URL>",
       "group": "<group id, or __world__>",
       "reply_text": "Condensed 2–4 sentence reply.",
       "reply_id": null
     }
   ]
   ```

   The `reply_text` is the **condensed** version of the response-log
   entry — 2–4 sentences max. Hypothes.is reply threads read terribly
   when stuffed with multi-paragraph prose. Aim for: what we agreed
   with, what we did, where to find detail. The full response log is
   the long form; this is the conversational acknowledgement.

3. **Dry-run, then post.** Run:

   ```bash
   python3 $ROOT/research-kit/tools/post_annotations.py \
       --mapping $PROJECT/.claude/annotation_replies_{date}.json \
       --dry-run                          # sanity-check first
   python3 $ROOT/research-kit/tools/post_annotations.py \
       --mapping $PROJECT/.claude/annotation_replies_{date}.json
   ```

   The script writes each posted reply's id back into the mapping file
   so it's safe to re-run (already-posted entries are skipped). Replies
   land in the same group as the parent annotation (inherited per-entry).

4. **Editing or deleting replies.** If we change our mind later — before
   the coauthor responds — use `edit_annotations.py` rather than posting
   a follow-up:

   ```bash
   python3 $ROOT/research-kit/tools/edit_annotations.py \
       --mapping $PROJECT/.claude/annotation_replies_{date}.json --list
   python3 $ROOT/research-kit/tools/edit_annotations.py \
       --mapping $PROJECT/.claude/annotation_replies_{date}.json \
       --n 7 --text "Revised reply."
   python3 $ROOT/research-kit/tools/edit_annotations.py \
       --mapping $PROJECT/.claude/annotation_replies_{date}.json \
       --n 7 --delete
   ```

   PATCH leaves the thread intact; the UI shows an "edited" timestamp.
   Only the reply's author can PATCH/DELETE it — so this only works if
   the same user-token owns both the original post and the edit.

   If the coauthor has *already replied* to our reply, do NOT PATCH —
   it edits in place and may misrepresent what they were responding to.
   Instead, post a fresh reply that references our previous reply ID
   (use `post_annotations.py` with a new entry whose `parent_id` is the
   prior reply's id).

5. **Summarise back to the user.** Report ok/fail counts and the
   mapping-file path. Do not attempt to "resolve" or close annotations
   via the API — that's the coauthor's call.

## Notes and gotchas

- **Orphaned annotations:** if the site has been rebuilt and the quoted text
  no longer exists verbatim, the annotation still returns from the API but
  the grep will miss. Surface these explicitly rather than silently dropping.
- **HTML vs markdown:** hypothes.is selects rendered text, so markdown syntax
  (`**bold**`, `[link](url)`) won't appear in the quote. Match the visible
  text, then find the corresponding markdown in the source.
- **Paper annotations** map to `paper/paper.tex` but the quote is HTML text
  from make4ht output — expect LaTeX macros in the source around the match.
- **Never delete the coauthor's annotations** via the API. You can only
  delete your own replies (Step 8), and only with the user's go-ahead.
- **Don't batch applies.** Walk the user through one at a time; a wrong
  auto-apply on a paragraph is painful to undo.
- **Token names vary.** Two conventions exist in this workspace:
  `HYPOTHESIS_API_TOKEN` (used by `projects/procure/source/feedback/`)
  and `HYPOTHESIS_TOKEN` (used by the original `fetch_annotations.py`).
  The new posting tools accept either. If asking the user to source a
  token file, run `. /path/to/file` from a shell session and verify with
  `curl -H "Authorization: Bearer $TOKEN" https://api.hypothes.is/api/profile`
  — a `userid` field set to something other than `null` means the token
  authenticates.
- **Token-owner identity.** Replies are posted as the account that owns
  the token. If the user's token is theirs, replies appear from them
  (their coauthor pseudonym); confirm this is the intended sender before
  posting in bulk.
- **Group inheritance.** A reply lands in whatever group the parent
  annotation is in (`__world__` for public, an ID for private groups).
  The script inherits this per entry; don't override unless you mean to.
- **Condensed-reply rule.** When posting (Step 8), each reply must be
  2–4 sentences. The full response log is the long form; hypothes.is
  reply threads read terribly when stuffed with multi-paragraph prose.
