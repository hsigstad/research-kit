---
name: outlook
description: "Convert Outlook .eml email exports to clean markdown for project docs. Use when the user wants to save email exchanges to a project's docs/emails/ directory."
user_invocable: true
---

# Outlook Email Converter

Convert .eml files exported from Outlook into clean markdown thread files,
following the project email archive convention (see deterrence/docs/emails/).

## Tool

`~/me/bin/fetch_outlook_emails.py` — converts .eml files to dated markdown.

## How the user exports emails from Outlook

In Outlook (web or desktop):
1. Open the thread / last reply in the thread
2. Click "..." → "Save as" or drag the message to a folder
3. Save as `.eml` (not `.msg` — .eml is plain text and portable)

One .eml per thread is enough — save the **latest reply**, which contains
the full quoted history.

## Usage

```bash
# Convert all .eml files in a folder:
python3 ~/me/bin/fetch_outlook_emails.py /path/to/emls/ --outdir project/docs/emails/

# Convert a single file:
python3 ~/me/bin/fetch_outlook_emails.py thread.eml --outdir project/docs/emails/
```

Output naming: `YYYY-MM-DD_subject-slug.md`

## Workflow for saving emails to a project

1. User exports .eml files from Outlook to a temporary location
2. Run the converter to produce markdown files in `docs/emails/`
3. Create a `docs/emails/README.md` index (follow deterrence project convention)
4. Clean up the .eml source files

## Parsing the request

The user may say:
- `/outlook` — process .eml files already present in the current project area
- `/outlook convert the emails in /tmp/soltes/` — explicit path

If no .eml files are found, remind the user how to export from Outlook.
