#!/usr/bin/env python3
"""PreToolUse hook (MCP tools): stop a peer-driven turn from reaching real people.

pretool_irreversible_guard.py only sees Bash. Sending a Telegram message,
trashing mail, or creating a calendar invite happens through MCP tools with no
shell command to inspect, so those walked straight past it — and idle-wake makes
unattended turns routine.

Scope differs from the Bash guard ON PURPOSE, and this is the one place the
"gate every turn" rule bends: an MCP tool call has no command string, so there
is no ALLOW_IRREVERSIBLE prefix to offer. Blocking these on every turn would
leave no way to proceed at all, and would break the legitimate uses outright
(Valborg IS a Telegram bot; /meet and /zoom create calendar events). So these
are blocked only during a peer turn — one started by stop_inbox.py draining a
message or inbox_waker.py typing into an idle pane, with no human present.

Human turns are unaffected. A peer cannot make this session message a person.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import peer_turn
except Exception:
    peer_turn = None

# Tools that reach a real person or mutate someone's shared record.
OUTWARD = [
    (r"telegram__(reply|edit_message)$", "sends a Telegram message"),
    (r"Gmail__(trash_\w+|mark_\w+_spam|apply_sensitive\w*)$", "mutates real mail"),
    (r"Google_Calendar__(create|delete|update|respond_to)_event$", "changes a real calendar"),
    (r"Google_Drive__(create_file|copy_file)$", "writes to shared Drive"),
    (r"whatsapp", "sends a WhatsApp message"),
]


def outward_reason(tool_name):
    for rx, why in OUTWARD:
        if re.search(rx, tool_name or "", re.IGNORECASE):
            return why
    return None


def main():
    data = json.load(sys.stdin)
    tool = data.get("tool_name") or ""
    why = outward_reason(tool)
    if not why:
        return 0
    sid = data.get("session_id")
    peer = peer_turn.read(sid) if (peer_turn and sid) else None
    if not peer:
        return 0

    print(
        f"Blocked (peer turn): `{tool}` {why}.\n"
        f"This turn was started by a peer session ({peer.get('origin')}), not by a "
        f"human. Peers can make this session work; they cannot make it contact "
        f"anyone.\n"
        f"Reply to the peer with research-kit/tools/send_message.py instead, and say "
        f"plainly that the outward step needs a human.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        sys.exit(0)
