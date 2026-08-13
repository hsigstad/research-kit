---
name: gmail
description: "Draft an email for Henrik in his house style AND record the draft so the sent-vs-draft diff can teach the style. Use when any session drafts/prepares an email for Henrik to send (to a coauthor, colleague, admin, etc.), or when the user says 'draft an email', 'reply to <person>'."
user_invocable: true
---

# /gmail — draft an email + record it for the style-learning loop

Any session that prepares an email for Henrik uses this, so (a) the draft follows his house style and
(b) it is **recorded at draft time** — which lets Saga diff Henrik's *sent* version against the draft
and learn his edits, **no matter which session drafted it**. (The `outlook` skill only archives *already
sent* .eml threads; this records the draft *before* it's sent.)

## 1. Draft to the house style
Read **`research/meta/email_style.md`** first and draft to it (short · link-don't-inline · Gmail-default ·
no em dashes · terse concrete scheduling · don't over-explain an accept · …). Do not invent a different
style; that file is canonical and is what the learning loop tunes.

## 2. Record the draft (the important part)
Write the draft to **`research/meta/email_drafts/YYYY-MM-DD_<session>_<slug>.md`** — one file per draft,
frontmatter + body:

```markdown
---
date: 2026-08-13
session: <your session name>        # e.g. Saga, deterrence, judgeGPT — the attribution + context key
to: <recipient email>
subject: <subject>
thread_id: <gmail thread id if replying, else "">
project: <slug or "">               # e.g. deterrence, vague, "" for admin/general
why: <one line of context NOT obvious from the email — what prompted it / what it's really about>
sent: false                          # Saga flips this after diffing against Henrik's sent mail
---

<the exact draft body>
```

The `why` line is also the cross-session context record — so a later reader (usually Saga during
reconcile) isn't guessing why the email exists or who drafted it.

## 3. Create the actual draft — only if you can
- **If you have the Gmail MCP** (Saga does): create the Gmail draft (`create_draft`, `replyToMessageId`
  when replying; `htmlBody` `<a>` anchor for any link per email_style rule 10), and add its draft id to
  the recorded file (`draft_id: r-…`). Leave a `Saga/handled` label if that's your convention.
- **If you don't** (most research/teaching sessions): just record the file (step 2) and hand Henrik the
  body to send himself. **Never send** — the outward act is always Henrik's.

## 4. The learning loop (Saga runs this — you don't)
Saga's nightly/triage scans `meta/email_drafts/` for records whose thread now has a **SENT** message
from Henrik, diffs sent-vs-draft, appends the delta to `meta/email_feedback_log.md`, sets `sent: true`,
and periodically distills recurring deltas into `meta/email_style.md`. So every session's draft feeds the
same house-style improvement — the whole point of recording here rather than in a per-session file.

## Notes
- Sensitive routing (site-password allowlists, delivery quirks like a UiO spam-reject, WhatsApp-only
  contacts) is **Saga's** overlay in its private repo — not in this shared file. Draft addresses come from
  `contacts.yaml` `default_email`.
- Keep drafts out of any *public* repo body if they contain private personal info; `research/` (this
  meta-repo) is private, which is why the archive lives here and not in a project's shared repo.
