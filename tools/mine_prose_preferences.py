#!/usr/bin/env python3
"""Mine Henrik's Claude Code conversation transcripts for prose-style
preferences — his own comments on writing, wording, and voice.

WHY: the voice card (research/rules/writing_style/henrik_voice.md) is a
few-shot of Henrik's revealed prose preferences. Its source discipline
is strict: signal comes ONLY from Henrik's own words — his hypothes.is
annotations and his in-conversation comments on prose — never from
AI-generated prose he happened to accept. This script harvests the
second source: messages HE typed that react to or direct prose.

Transcripts live per-machine under $HOME/.claude/projects/**/*.jsonl and
are NOT synced. So each machine runs this against its own local store
and writes a machine-tagged output file into the (synced) research repo;
the distillation step then folds all machines' harvests into the card.

USAGE
    python3 research-kit/tools/mine_prose_preferences.py
    # optional: --projects DIR   (default $HOME/.claude/projects)
    #           --out-dir DIR     (default research/rules/writing_style/voice_mining)

OUTPUT (into --out-dir, tagged by machine+hostname so harvests merge):
    <machine>-<host>.jsonl   one record per candidate (file, ts, context, text)
    <machine>-<host>.md      human-readable digest grouped by session

Then DISTILL by hand/LLM into henrik_voice.md — keep only genuine
style preferences, phrased as his verbatim comment + the prose he was
reacting to. Discard task chatter the keyword net caught.
"""
import argparse, glob, json, os, re, socket

# --- Henrik's typed messages only -------------------------------------
# Exclude tool_result blocks, hook output, and harness-injected wrappers.
_WRAPPER_PREFIXES = (
    "<system-reminder", "<command-", "<local-command", "<user-prompt-submit",
    "[peer-wake", "Caveat:", "Stop hook feedback", "act as Valborg",
    "SessionStart", "## Live sessions", "## Nightly convention sweep",
)

def _texts(content):
    if isinstance(content, str):
        return [content]
    if isinstance(content, list):
        return [b.get("text", "") for b in content
                if isinstance(b, dict) and b.get("type") == "text"]
    return []

def henrik_texts(obj):
    if obj.get("type") != "user":
        return []
    msg = obj.get("message") or {}
    if not isinstance(msg, dict) or msg.get("role") != "user":
        return []
    out = []
    for t in _texts(msg.get("content")):
        if not t or len(t.strip()) < 4:
            continue
        s = t.lstrip()
        if s.startswith(_WRAPPER_PREFIXES):
            continue
        if "tool_use_id" in t or "<function_results" in t:
            continue
        out.append(t.strip())
    return out

def assistant_text(obj):
    if obj.get("type") != "assistant":
        return ""
    msg = obj.get("message") or {}
    if not isinstance(msg, dict):
        return ""
    return " ".join(_texts(msg.get("content"))).strip()

# --- prose-signal keywords (high recall; distillation adds precision) --
KW = re.compile(r'''\b(
    prose|sentence|paragraph|wording|rephrase|reword|rewrite|wordy|verbose|
    concise|throat.?clear|em.?dash|hedg|editorializ|passive\ voice|active\ voice|
    topic\ sentence|opener|flowery|fancy|jargon|cryptic|plain\ language|plainly|
    too\ complicated|simpler|keep\ it\ simple|too\ long|awkward|clunky|
    AI\ generated|AI.?tell|sounds?\ (very\ )?ai|academically|overclaim|
    (not|un).?back(ed|able)|too\ strong|conclusions?\ up\ front|lead\ with|
    dont\ say|don.t\ say|dont\ write|don.t\ write|dont\ use|don.t\ use|
    dont\ mention|don.t\ mention|voice|tone|signpost|parallelism|
    state\ (it\ )?plainly|just\ say|too\ many\ words|say\ less|shorten
)\b''', re.I | re.X)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--projects", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--out-dir", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "research", "rules", "writing_style", "voice_mining"))
    ap.add_argument("--max-len", type=int, default=2000,
                    help="skip candidate messages longer than this (likely pastes)")
    args = ap.parse_args()

    machine = "educloud" if os.path.expanduser("~").startswith("/fp/homes01/") else "laptop"
    host = socket.gethostname().split(".")[0]
    tag = f"{machine}-{host}"
    os.makedirs(args.out_dir, exist_ok=True)

    files = sorted(glob.glob(os.path.join(args.projects, "*", "*.jsonl")))
    hits, n_msgs = [], 0
    for f in files:
        prev_assistant = ""
        try:
            fh = open(f, encoding="utf-8")
        except OSError:
            continue
        with fh:
            for line in fh:
                try:
                    o = json.loads(line)
                except (json.JSONDecodeError, ValueError):
                    continue
                a = assistant_text(o)
                if a:
                    prev_assistant = a
                for t in henrik_texts(o):
                    n_msgs += 1
                    if len(t) <= args.max_len and KW.search(t):
                        hits.append({
                            "file": os.path.relpath(f, args.projects),
                            "ts": o.get("timestamp", ""),
                            "reacting_to": prev_assistant[:600],
                            "text": t,
                        })

    jpath = os.path.join(args.out_dir, f"{tag}.jsonl")
    with open(jpath, "w", encoding="utf-8") as out:
        for h in hits:
            out.write(json.dumps(h, ensure_ascii=False) + "\n")

    mpath = os.path.join(args.out_dir, f"{tag}.md")
    by_file = {}
    for h in hits:
        by_file.setdefault(h["file"], []).append(h)
    with open(mpath, "w", encoding="utf-8") as out:
        out.write(f"# Prose-preference mining — {tag}\n\n")
        out.write(f"{len(hits)} candidate messages from {n_msgs} Henrik-typed "
                  f"messages across {len(files)} transcripts.\n\n")
        out.write("Each entry: what Claude had just written (→ reacting to), then "
                  "Henrik's comment. Distill genuine style preferences into "
                  "`../henrik_voice.md`; discard task chatter.\n\n")
        for fn, items in sorted(by_file.items()):
            out.write(f"\n## {fn}\n\n")
            for h in items:
                if h["reacting_to"]:
                    out.write(f"> _reacting to:_ {h['reacting_to'][:280]}\n>\n")
                out.write(f"**Henrik:** {h['text']}\n\n")

    print(f"[{tag}] {len(hits)} candidates / {n_msgs} typed messages / "
          f"{len(files)} transcripts")
    print(f"  -> {jpath}")
    print(f"  -> {mpath}")

if __name__ == "__main__":
    main()
