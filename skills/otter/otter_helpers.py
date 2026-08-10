"""Helpers for the /otter skill.

Two CLI subcommands:
  parse <src>                       parse an Otter "Meeting Summary" email -> JSON
  save  <src> <msg_id> <dest_path>  parse + render the meeting markdown file
  scan-ids [roots...]               {otter_id: path} of every saved Otter meeting

Unlike /tactiq (which pulls Google Docs from Drive), Otter shares meetings as
email. Fetching is done by the model via the Gmail MCP tools; this helper never
touches the network. `parse`/`save` operate on a file the caller has already
saved — either the raw `get_thread` JSON (`{id, messages:[...]}`, camelCase
keys) or a plain-text file containing just the email body.

IMPORTANT: an Otter "Meeting Summary for <title>" email contains only the AI
summary and a few action items — NOT the full transcript. The transcript stays
in the Otter web app behind (auth-gated) links. So the saved meeting file is the
summary + action items, and records how many action items Otter listed vs how
many the email inlined.

Otter email plaintext shape (observed 2026-08):

    <Name> has shared notes from <Title>, <Mon DD> . <summary...>
     Hi <Name>,
     ...tracking links...
     - Otter
    ****************
    <Title>
    ****************
    <Mon DD>, <H:MM am/pm>, <N> min
    <summary paragraph>
    *See full summary -> *
    ------------
    Action items
    ------------
     <Person> - <action> .
     <action> .
    * See <N> action items -> *
    ...footer...
"""

import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

# en dash / hyphen used by Otter between an action-item owner and the action
_DASHES = "–—-"
_BANNER_RE = re.compile(r"^\*{5,}\s*$")
_DATELINE_RE = re.compile(
    r"^([A-Z][a-z]{2,8})\s+(\d{1,2}),\s+(\d{1,2}:\d{2}\s*[ap]m),\s*(\d+)\s*min",
)
_OWNER_RE = re.compile(rf"^([A-Z][\w.]+(?:\s+[A-Z][\w.]+){{0,3}})\s+[{_DASHES}]\s+")
_SEE_N_RE = re.compile(r"See\s+(\d+)\s+action items")
_SHARED_FROM_RE = re.compile(r"shared notes from\s+(.+?),\s")
_STOP_MARKERS = (
    "see full summary", "see all insights", "see 5 action items",
    "action items", "otter.ai,", "email settings", "unsubscribe",
)


def _load(src: str) -> tuple[str, str | None, str | None, str | None]:
    """Return (body_text, email_date_iso, subject, message_id) from src.

    src may be the raw get_thread JSON ({id, messages:[...]}) or a plain-text
    body. For JSON, the Otter message (sender contains 'otter.ai', else the
    first message) supplies plaintextBody / date / subject / id.
    """
    text = Path(src).read_text(encoding="utf-8-sig", errors="replace")
    try:
        obj = json.loads(text)
    except ValueError:
        return text, None, None, None
    if not isinstance(obj, dict) or "messages" not in obj:
        return text, None, None, None
    msgs = obj.get("messages") or []
    msg = next((m for m in msgs if "otter.ai" in (m.get("sender") or "")), None)
    msg = msg or (msgs[0] if msgs else {})
    body = msg.get("plaintextBody") or msg.get("htmlBody") or ""
    date_iso = (msg.get("date") or "")[:10] or None
    return body, date_iso, msg.get("subject"), msg.get("id")


def _clean(raw: str) -> str:
    t = raw.replace("\r", "")
    t = re.sub(r"https?://\S+", " ", t)     # drop tracking URLs
    t = re.sub(r"\(\s*\)", " ", t)          # empty parens left behind
    t = html.unescape(t)                    # &apos; &amp; &rarr; ...
    t = re.sub(r"[ \t]+", " ", t)
    return t


def _title(subject: str | None, body: str, lines: list[str]) -> str | None:
    if subject:
        m = re.match(r"\s*Meeting Summary for\s+(.+?)\s*$", subject)
        if m:
            return m.group(1).strip()
    # banner: line of ***** , then the title, then another *****
    for i, ln in enumerate(lines[:-2]):
        if _BANNER_RE.match(ln) and lines[i + 1].strip() and _BANNER_RE.match(lines[i + 2]):
            return lines[i + 1].strip()
    m = _SHARED_FROM_RE.search(body)
    return m.group(1).strip() if m else None


def _meeting_date(lines: list[str], email_date_iso: str | None) -> tuple[str | None, str | None]:
    """(iso_date, duration) from the '<Mon DD>, <time>, <N> min' line.

    The body line has no year, so the year comes from the email's date. Falls
    back to the email date when the body line is absent.
    """
    year = email_date_iso[:4] if email_date_iso else None
    for ln in lines:
        m = _DATELINE_RE.match(ln.strip())
        if not m:
            continue
        mon, day, _time, mins = m.groups()
        duration = f"{mins} min"
        if year:
            for fmt in ("%b %d %Y", "%B %d %Y"):
                try:
                    iso = datetime.strptime(f"{mon} {day} {year}", fmt).strftime("%Y-%m-%d")
                    return iso, duration
                except ValueError:
                    pass
        return email_date_iso, duration
    return email_date_iso, None


def _summary(lines: list[str]) -> str:
    """The paragraph between the meeting-date line and the next marker."""
    start = None
    for i, ln in enumerate(lines):
        if _DATELINE_RE.match(ln.strip()):
            start = i + 1
            break
    if start is None:
        return ""
    out: list[str] = []
    for ln in lines[start:]:
        low = ln.strip().lower().lstrip("*").strip()
        if low.startswith(("see full summary", "action items")) or _BANNER_RE.match(ln):
            if out:
                break
            continue
        if ln.strip().startswith("---") and out:
            break
        if ln.strip():
            out.append(ln.strip())
    return " ".join(out).strip()


def _action_items(lines: list[str]) -> tuple[list[str], int | None]:
    """(items, total_count). total_count from 'See N action items ->' if present."""
    items: list[str] = []
    total = None
    in_block = False
    for ln in lines:
        s = ln.strip()
        sm = _SEE_N_RE.search(s)
        if sm:
            total = int(sm.group(1))
        low = s.lower().lstrip("*").strip()
        if low == "action items":
            in_block = True
            continue
        if not in_block:
            continue
        if s.startswith("---"):
            continue
        if low.startswith(("see ", "* see")) or low.startswith(_STOP_MARKERS[3:]):
            break
        item = s.rstrip(" .").strip()
        if item:
            items.append(item)
    return items, (total if total is not None else (len(items) or None))


def _participants(items: list[str]) -> list[str]:
    seen: list[str] = []
    for it in items:
        m = _OWNER_RE.match(it)
        if m and m.group(1) not in seen:
            seen.append(m.group(1))
    return seen


def parse(src: str) -> dict:
    body, email_date_iso, subject, msg_id = _load(src)
    clean = _clean(body)
    lines = clean.split("\n")
    title = _title(subject, clean, lines)
    date_iso, duration = _meeting_date(lines, email_date_iso)
    summary = _summary(lines)
    items, total = _action_items(lines)
    return {
        "title": title,
        "date": date_iso,
        "duration": duration,
        "summary": summary,
        "action_items": items,
        "action_items_total": total,
        "participants": _participants(items),
        "otter_id": msg_id,
    }


def build_markdown(parsed: dict, msg_id: str, attendees: list[str]) -> str:
    out = ["---",
           f"title: {parsed['title']}",
           f"date: {parsed['date']}",
           "attendees: [" + ", ".join(attendees) + "]"]
    if parsed.get("duration"):
        out.append(f"duration: {parsed['duration']}")
    out += [f"otter_id: {msg_id}",
            "source: otter",
            "---",
            "",
            f"# {parsed['title']}",
            ""]
    if parsed.get("summary"):
        out += ["## Summary", "", parsed["summary"], ""]
    items = parsed.get("action_items") or []
    if items:
        out += ["## Action items", ""]
        out += [f"- {it}" for it in items]
        out.append("")
    total = parsed.get("action_items_total")
    shown = len(items)
    if total and total > shown:
        out += [f"*Otter listed {total} action items; {shown} inlined in the email. "
                "The remaining items and the full transcript are in the Otter web app.*", ""]
    else:
        out += ["*Summary and action items are from the Otter email; the full "
                "transcript stays in the Otter web app.*", ""]
    return "\n".join(out).rstrip() + "\n"


def save(src: str, msg_id: str, dest_path: str, attendees: str | None = None) -> str:
    parsed = parse(src)
    if not msg_id or msg_id == "-":
        msg_id = parsed.get("otter_id") or "-"
    if attendees is not None:
        attlist = [a.strip() for a in attendees.split(",") if a.strip()]
    else:
        attlist = parsed["participants"]
    md = build_markdown(parsed, msg_id, attlist)
    p = Path(dest_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        n = 2
        while (p.parent / f"{p.stem}-{n}{p.suffix}").exists():
            n += 1
        p = p.parent / f"{p.stem}-{n}{p.suffix}"
    p.write_text(md, encoding="utf-8")
    return str(p)


_OTTER_ID_RE = re.compile(r"^otter_id:\s*(\S+)\s*$", re.M)


def scan_ids(roots: list[str]) -> dict:
    """Map every saved Otter meeting's otter_id -> its file path.

    Reconstructs the processed set from committed files, so a machine whose
    per-machine, untracked .otter_processed.json cache is empty still skips
    already-routed meetings instead of creating -2 duplicates.
    """
    out: dict[str, str] = {}
    for root in roots or ["."]:
        rp = Path(root)
        seen = list(rp.glob("projects/*/docs/meetings/*.md")) + list(rp.glob("inbox/meetings/*.md"))
        for md in seen:
            m = _OTTER_ID_RE.search(md.read_text(encoding="utf-8", errors="ignore"))
            if m:
                out[m.group(1)] = str(md)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("parse")
    p.add_argument("src", help="get_thread JSON file or raw email body")

    s = sub.add_parser("save")
    s.add_argument("src")
    s.add_argument("msg_id", help="Gmail message id ('-' to read from JSON)")
    s.add_argument("dest_path")
    s.add_argument("--attendees", default=None,
                   help="comma-separated override for the frontmatter attendees list")

    si = sub.add_parser("scan-ids")
    si.add_argument("roots", nargs="*", default=["."])

    args = ap.parse_args()
    if args.cmd == "parse":
        json.dump(parse(args.src), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
    elif args.cmd == "save":
        print(save(args.src, args.msg_id, args.dest_path, args.attendees))
    elif args.cmd == "scan-ids":
        json.dump(scan_ids(args.roots), sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")


if __name__ == "__main__":
    main()
