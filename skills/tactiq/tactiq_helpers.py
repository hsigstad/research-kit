"""Helpers for the /tactiq skill.

Three CLI subcommands:
  download <file_id> <out_path>          export a Google Doc as text/plain via Drive API
  parse <txt_path>                       parse a Tactiq plaintext export → JSON
  save <txt_path> <file_id> <dest_path>  parse + render the meeting markdown file

The `save` subcommand is the deterministic format-and-write step. It takes the
downloaded text, parses it, renders the frontmatter + transcript markdown, and
writes it to dest_path (appending -2, -3, ... on collision). It prints the final
path written. Routing dest_path to the right project is the caller's job; pass
--attendees to override the parsed attendee list when the Tactiq export's
comma-separated "Attendees:" line is ambiguous (e.g. a single "Lastname, First"
name that parses as two people).

The Drive access token is read from rclone's config (~/.config/rclone/rclone.conf,
section [gdrive]). Run any rclone command first (e.g. `rclone about gdrive:`) so
rclone refreshes the token before this script reads it.

Tactiq plaintext format (observed 2026-05-01):

    Transcript delivered by Tactiq.io - get it for your Google Meet today!
    View the full transcript ...


    <DD Month YYYY> | <Title>
    Attendees: <name1>, <name2>


    Highlights
    <highlights or boilerplate>


    Transcript
    <MM:SS or HH:MM> <Speaker>: <text>
    ...
"""

import argparse
import configparser
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

RCLONE_CONF = Path(os.environ.get("RCLONE_CONFIG", Path.home() / ".config/rclone/rclone.conf"))
GDRIVE_REMOTE = os.environ.get("TACTIQ_GDRIVE_REMOTE", "gdrive")


def access_token() -> str:
    cp = configparser.ConfigParser()
    cp.read(RCLONE_CONF)
    if GDRIVE_REMOTE not in cp:
        raise SystemExit(f"no [{GDRIVE_REMOTE}] section in {RCLONE_CONF}")
    tok = json.loads(cp[GDRIVE_REMOTE]["token"])
    return tok["access_token"]


def download(file_id: str, out_path: str) -> None:
    token = access_token()
    url = (
        "https://www.googleapis.com/drive/v3/files/"
        + urllib.parse.quote(file_id, safe="")
        + "/export?mimeType=text/plain"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as resp:
        data = resp.read()
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_bytes(data)


_DATE_TITLE_RE = re.compile(r"^(\d{1,2}\s+\w+\s+\d{4})\s*\|\s*(.+?)\s*$")
_TRANSCRIPT_LINE_RE = re.compile(r"^(\d{1,2}:\d{2}(?::\d{2})?)\s+([^:]+?):\s*(.*)$")


def parse(txt_path: str) -> dict:
    text = Path(txt_path).read_text(encoding="utf-8-sig")
    lines = text.splitlines()

    title = None
    date_iso = None
    attendees: list[str] = []
    highlights_lines: list[str] = []
    transcript_lines: list[str] = []

    section = "header"
    for raw in lines:
        line = raw.rstrip()

        if section == "header":
            m = _DATE_TITLE_RE.match(line)
            if m:
                date_str, title = m.group(1), m.group(2).strip()
                for fmt in ("%d %B %Y", "%d %b %Y"):
                    try:
                        date_iso = datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        date_iso = None
                section = "after_title"
                continue

        if section == "after_title":
            if line.startswith("Attendees:"):
                attendees = [a.strip() for a in line.split(":", 1)[1].split(",") if a.strip()]
                section = "pre_highlights"
                continue

        if section in ("pre_highlights", "after_title"):
            if line.strip() == "Highlights":
                section = "highlights"
                continue

        if section == "highlights":
            if line.strip() == "Transcript":
                section = "transcript"
                continue
            highlights_lines.append(line)
            continue

        if section == "transcript":
            transcript_lines.append(line)
            continue

    highlights = _trim_block(highlights_lines)
    transcript = _trim_block(transcript_lines)

    default_highlights = (
        "Use the highlighting tool in Tactiq during the meeting to collect "
        "all highlights in this section."
    )
    if highlights.strip() == default_highlights:
        highlights = ""

    return {
        "title": title,
        "date": date_iso,
        "attendees": attendees,
        "highlights": highlights,
        "transcript": transcript,
        "transcript_lines": _structured_transcript(transcript_lines),
    }


def _trim_block(lines: list[str]) -> str:
    while lines and not lines[0].strip():
        lines.pop(0)
    while lines and not lines[-1].strip():
        lines.pop()
    return "\n".join(lines)


def _structured_transcript(lines: list[str]) -> list[dict]:
    out = []
    for line in lines:
        m = _TRANSCRIPT_LINE_RE.match(line.strip())
        if m:
            out.append({"timestamp": m.group(1), "speaker": m.group(2).strip(), "text": m.group(3).strip()})
    return out


def build_markdown(parsed: dict, file_id: str, attendees: list[str]) -> str:
    """Render a parsed Tactiq transcript as the meeting markdown file.

    Matches the layout in SKILL.md Step 6: YAML frontmatter, an H1 title, an
    optional Highlights section (omitted when empty/boilerplate), and the
    transcript as `[MM:SS] **Speaker**: text` lines separated by blank lines.
    """
    out = ["---",
           f"title: {parsed['title']}",
           f"date: {parsed['date']}",
           "attendees: [" + ", ".join(attendees) + "]",
           f"tactiq_id: {file_id}",
           "source: tactiq",
           "---",
           "",
           f"# {parsed['title']}",
           ""]
    highlights = (parsed.get("highlights") or "").strip()
    if highlights:
        out += ["## Highlights", "", highlights, ""]
    out += ["## Transcript", ""]
    for t in parsed.get("transcript_lines", []):
        out.append(f"[{t['timestamp']}] **{t['speaker']}**: {t['text']}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def save(txt_path: str, file_id: str, dest_path: str, attendees: str | None = None) -> str:
    """Parse txt_path and write the rendered meeting markdown to dest_path.

    Appends -2, -3, ... to the filename if dest_path already exists. Returns the
    final path written. `attendees`, if given, is a comma-separated override for
    the frontmatter attendee list.
    """
    parsed = parse(txt_path)
    if attendees is not None:
        attlist = [a.strip() for a in attendees.split(",") if a.strip()]
    else:
        attlist = parsed["attendees"]
    md = build_markdown(parsed, file_id, attlist)

    p = Path(dest_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        n = 2
        while (p.parent / f"{p.stem}-{n}{p.suffix}").exists():
            n += 1
        p = p.parent / f"{p.stem}-{n}{p.suffix}"
    p.write_text(md, encoding="utf-8")
    return str(p)


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    d = sub.add_parser("download")
    d.add_argument("file_id")
    d.add_argument("out_path")

    p = sub.add_parser("parse")
    p.add_argument("txt_path")

    s = sub.add_parser("save")
    s.add_argument("txt_path")
    s.add_argument("file_id")
    s.add_argument("dest_path")
    s.add_argument("--attendees", default=None,
                   help="comma-separated override for the frontmatter attendees list")

    args = ap.parse_args()
    if args.cmd == "download":
        download(args.file_id, args.out_path)
    elif args.cmd == "parse":
        json.dump(parse(args.txt_path), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    elif args.cmd == "save":
        print(save(args.txt_path, args.file_id, args.dest_path, args.attendees))


if __name__ == "__main__":
    main()
