#!/usr/bin/env python3
"""Send an inter-session message to a concurrent Claude session.

Writes a message file to <workspace>/inbox/messages/ that the UserPromptSubmit
inbox hook (userprompt_inbox.py) auto-delivers to the addressed session(s) on
their next prompt. Handles the filename, UTC timestamp, sender env, and — most
importantly — stamps the sender's own session id as `From-Session:` so the
recipient can reply straight back to THIS session (see To-Session below).

Addressing:
  --to host|sandbox|all   Environment address (default: the OTHER env — so a
                          sandbox session defaults to reaching a host session,
                          and vice versa). Use this when you don't care WHICH
                          session of that type picks it up — the "no clear
                          address" case. If no such session is running yet, the
                          file waits until one starts.
  --to-session <id>       Optional: target ONE specific session by id (e.g. when
                          replying — pass the From-Session you received). This
                          adds a `To-Session:` header the hook honors; only that
                          session gets it, others leave it untouched.

Body comes from --body or stdin. Example:
  echo "Please rebuild rol and deploy." | send_message.py --to host --subject "rol deploy"
  send_message.py --to-session abc123 --subject "done" --body "Rebuilt; site is live."
"""
import argparse
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def workspace() -> Path:
    env = os.environ.get("RESEARCH_WORKSPACE")
    if env:
        return Path(env)
    for cand in (Path("/workspace"), Path.home() / "research"):
        if (cand / "research-kit").exists() and (cand / "inbox").exists():
            return cand
        if (cand / "research-kit").exists():
            return cand
    return Path("/workspace")


def main() -> int:
    here = "sandbox" if Path("/workspace").exists() else "host"
    default_to = "host" if here == "sandbox" else "sandbox"

    ap = argparse.ArgumentParser(description="Send an inter-session message.")
    ap.add_argument("--to", default=default_to,
                    help="Env address: host|sandbox|all (default: the other env).")
    ap.add_argument("--to-session", default=None,
                    help="Target one specific session id (e.g. a reply's From-Session).")
    ap.add_argument("--subject", default=None, help="Optional subject line.")
    ap.add_argument("--body", default=None, help="Message body (else read stdin).")
    args = ap.parse_args()

    to = args.to.lower().strip()
    body = args.body if args.body is not None else sys.stdin.read()
    if not body.strip():
        print("send_message: empty body; nothing sent.", file=sys.stderr)
        return 2

    from_session = os.environ.get("CLAUDE_CODE_SESSION_ID", "unknown")
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    msg_dir = workspace() / "inbox" / "messages"
    msg_dir.mkdir(parents=True, exist_ok=True)
    path = msg_dir / f"{here}-to-{to}_{ts}.md"

    lines = [f"From-Session: {from_session}"]
    if args.to_session:
        lines.append(f"To-Session: {args.to_session}")
    lines.append("")
    if args.subject:
        lines.append(f"# {args.subject}")
        lines.append("")
    lines.append(body.rstrip())
    lines.append("")
    path.write_text("\n".join(lines))

    dest = args.to_session or to
    print(f"sent → {path.relative_to(workspace())}  (from {here} session "
          f"{from_session[:12]}…, to {dest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
