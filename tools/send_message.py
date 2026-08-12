#!/usr/bin/env python3
"""Send an inter-session message to a concurrent Claude session.

Writes a message file to <workspace>/inbox/messages/ that the UserPromptSubmit
inbox hook (userprompt_inbox.py) auto-delivers to the addressed session(s) on
their next prompt. Handles the filename, UTC timestamp, sender env, and stamps
the sender's session id (and name) as `From-Session:` / `From-Name:` so the
recipient can reply straight back.

Addressing (pick one):
  --to host|sandbox|all   Environment address (default: the OTHER env — a
                          sandbox session defaults to reaching a host session).
                          Use this when you don't care WHICH session of that
                          type picks it up — the "no clear address" case. If no
                          such session is running, the file waits until one does.
  --to-name "<name>"      Target the session a user named with /rename (resolved
                          via ~/.claude/sessions/). This is how a user says
                          "message the 'CGU pipeline' session: ...".
  --to-session <id>       Target one specific session by raw id (e.g. replying
                          with a From-Session you received).

Body comes from --body or stdin. Examples:
  echo "Rebuild rol and deploy." | send_message.py --to host --subject "rol deploy"
  send_message.py --to-name "CGU pipeline" --subject "heads up" --body "..."
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def workspace() -> Path:
    env = os.environ.get("RESEARCH_WORKSPACE")
    if env:
        return Path(env)
    # Self-locating: this script lives at <workspace>/research-kit/tools/, so its
    # own path resolves the workspace regardless of cwd or mount point (fixes the
    # host case where neither /workspace nor ~/research exists — educloud is at
    # /projects/ec113/henrik/research). Ordered candidates, first with research-kit/ wins.
    self_root = Path(__file__).resolve().parents[2]
    proj = os.environ.get("CLAUDE_PROJECT_DIR")
    candidates = [Path("/workspace"), Path.home() / "research", self_root]
    if proj:
        candidates.append(Path(proj))
    for cand in candidates:
        if (cand / "research-kit").exists():
            return cand
    return Path("/workspace")


def sessions_registry():
    """All live-session records from ~/.claude/sessions/*.json (best-effort)."""
    out = []
    d = Path.home() / ".claude" / "sessions"
    try:
        files = list(d.glob("*.json"))
    except Exception:
        return out
    for f in files:
        try:
            out.append(json.loads(f.read_text()))
        except Exception:
            pass
    return out


def name_for_session(sid, reg=None):
    reg = reg if reg is not None else sessions_registry()
    best = None
    for s in reg:
        if s.get("sessionId") == sid and s.get("name"):
            if best is None or s.get("updatedAt", 0) > best[0]:
                best = (s.get("updatedAt", 0), s["name"])
    return best[1] if best else None


def session_for_name(name, reg=None):
    """Return (sessionId, [all matches]) for a named session; most-recent wins."""
    reg = reg if reg is not None else sessions_registry()
    nl = name.strip().lower()
    matches = [s for s in reg
               if (s.get("name") or "").strip().lower() == nl and s.get("sessionId")]
    matches.sort(key=lambda s: s.get("updatedAt", 0), reverse=True)
    return (matches[0]["sessionId"] if matches else None), matches


def main() -> int:
    here = "sandbox" if Path("/workspace").exists() else "host"
    default_to = "host" if here == "sandbox" else "sandbox"

    ap = argparse.ArgumentParser(description="Send an inter-session message.")
    ap.add_argument("--to", default=default_to,
                    help="Env address: host|sandbox|all (default: the other env).")
    ap.add_argument("--to-name", default=None,
                    help='Target a /rename-d session by name, e.g. "CGU pipeline".')
    ap.add_argument("--to-session", default=None,
                    help="Target one specific session id (e.g. a reply's From-Session).")
    ap.add_argument("--subject", default=None, help="Optional subject line.")
    ap.add_argument("--body", default=None, help="Message body (else read stdin).")
    args = ap.parse_args()

    reg = sessions_registry()
    body = args.body if args.body is not None else sys.stdin.read()
    if not body.strip():
        print("send_message: empty body; nothing sent.", file=sys.stderr)
        return 2

    to = args.to.lower().strip()
    to_session = args.to_session
    to_name = None
    if args.to_name:
        sid, matches = session_for_name(args.to_name, reg)
        if not sid:
            named = sorted({(s.get("name"), s.get("cwd"), s.get("status"))
                            for s in reg if s.get("name")})
            print(f"send_message: no running session named {args.to_name!r}. "
                  f"Named sessions currently:", file=sys.stderr)
            for nm, cwd, st in named:
                print(f"  - {nm!r}  ({st}, cwd={cwd})", file=sys.stderr)
            return 3
        to_session = sid
        to_name = matches[0].get("name")
        # cosmetic filename env, inferred from the target's cwd
        tcwd = matches[0].get("cwd", "")
        to = "sandbox" if str(tcwd).startswith("/workspace") else "host"
        if len(matches) > 1:
            print(f"send_message: note — {len(matches)} sessions named "
                  f"{args.to_name!r}; targeting the most recently active.",
                  file=sys.stderr)

    from_session = os.environ.get("CLAUDE_CODE_SESSION_ID", "unknown")
    from_name = name_for_session(from_session, reg)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    msg_dir = workspace() / "inbox" / "messages"
    msg_dir.mkdir(parents=True, exist_ok=True)
    path = msg_dir / f"{here}-to-{to}_{ts}.md"

    lines = [f"From-Session: {from_session}"]
    if from_name:
        lines.append(f"From-Name: {from_name}")
    if to_session:
        lines.append(f"To-Session: {to_session}")
    if to_name:
        lines.append(f"To-Name: {to_name}")
    lines.append("")
    if args.subject:
        lines += [f"# {args.subject}", ""]
    lines += [body.rstrip(), ""]
    path.write_text("\n".join(lines))

    dest = (f"{to_name!r} ({to_session[:12]}…)" if to_name
            else to_session[:12] + "…" if to_session else to)
    frm = f"{from_name!r} " if from_name else ""
    print(f"sent → {path.relative_to(workspace())}  (from {here} session "
          f"{frm}{from_session[:12]}…, to {dest})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
