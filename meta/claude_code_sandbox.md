# Claude Code: Autonomous Mode & Sandboxing

How to run Claude Code without permission prompts safely. Updated 2026-04-03.

---

## Quick reference

| Mode | Safety | Setup effort | Use case |
|------|--------|-------------|----------|
| `--enable-auto-mode` | High (safety classifier) | None | Day-to-day autonomous work |
| Built-in sandbox (`/sandbox`) | Medium-high | Install bubblewrap | Local work with filesystem/network isolation |
| Docker + `--dangerously-skip-permissions` | Highest | Dockerfile | Long-running unattended tasks |

---

## Option 1: Auto Mode (recommended default)

```bash
claude --enable-auto-mode -p "your task"
```

- Uses a background safety classifier that reviews each action before execution.
- Blocks: code downloads (`curl | bash`), mass deletion, production deploys,
  credential exfiltration, IAM permission changes.
- Allows: local file operations, dependency installation, reading `.env` files.
- Falls back to prompting after 3 consecutive denials or 20 total in a session.
- Requires Team, Enterprise, or API plan with Sonnet 4.6 or Opus 4.6.

---

## Option 2: Built-in Sandboxing

Claude Code has native OS-level sandboxing.

### Setup (Linux/WSL2)

```bash
sudo apt install bubblewrap socat   # Ubuntu/Debian
sudo dnf install bubblewrap socat   # Fedora
```

macOS uses Apple Seatbelt (built-in, no install needed).

### Configuration (`settings.json`)

```json
{
  "sandbox": {
    "enabled": true,
    "filesystem": {
      "allowWrite": ["./workspace"]
    },
    "network": {
      "allowedDomains": ["github.com", "api.github.com", "registry.npmjs.org"]
    }
  }
}
```

### What it does

- **Filesystem isolation**: Write access limited to current working directory
  (plus any paths in `allowWrite`).
- **Network isolation**: All traffic routed through proxy with domain allowlist.
- **Process isolation**: All child processes inherit sandbox boundaries.

---

## Option 3: Docker Container (strongest isolation)

For fully autonomous `--dangerously-skip-permissions` mode, run inside a container.

### Minimal example

```bash
docker run --rm -it \
  -v $(pwd):/workspace \
  -w /workspace \
  --memory=4g --cpus=2 \
  --user 1000:1000 \
  claude-sandbox \
  claude -p "your task" --dangerously-skip-permissions
```

### Dockerfile template

```dockerfile
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ca-certificates nodejs npm bubblewrap socat \
  && rm -rf /var/lib/apt/lists/*

# Install Claude Code
RUN curl https://code.claude.com/install.sh | bash

# Non-root user
RUN useradd -m -u 1000 claude
USER claude
WORKDIR /workspace
```

### Hardening checklist

- [ ] Run as non-root user
- [ ] Mount project directory only (not home or root)
- [ ] Set memory and CPU limits
- [ ] Restrict network (no host network, explicit port exposure only)
- [ ] Use `--read-only` filesystem where possible
- [ ] Do not mount `.ssh`, `.git-credentials`, or other secrets

### Our setup

See `research/docker/claude-sandbox/` in this repo. The `run.sh` script
auto-detects Docker (laptop) or Apptainer/Singularity (RHEL server) and uses
the appropriate image format:

| Environment | Runtime | Image format | Config file |
|---|---|---|---|
| Laptop (Ubuntu) | Docker | Built from `Dockerfile` | `Dockerfile` |
| Server (RHEL) | Apptainer | Built from `.def` → `.sif` | `claude-sandbox.def` |

```bash
# Interactive session
./research/docker/claude-sandbox/run.sh

# Non-interactive task
./research/docker/claude-sandbox/run.sh "collect news stories about corruption from Brazilian media"

# Or use the alias (add to .bashrc):
#   alias cs="/path/to/research/docker/claude-sandbox/run.sh"
cs "collect news stories"
```

The container has full internet but only the current working directory is mounted.
No SSH keys, git credentials, or home directory exposed.

**Note:** The `.sif` image file is large (~1.5 GB) and should not be committed.
It is listed in `.gitignore`.

### Community containers

- [nezhar/claude-container](https://github.com/nezhar/claude-container) -- Docker
  Compose integration with logging proxy.
- [tintinweb/claude-code-container](https://github.com/tintinweb/claude-code-container)
  -- built for bypass-permissions mode.
- [RchGrav/claudebox](https://github.com/RchGrav/claudebox) -- pre-configured dev
  profiles.

---

## Risk assessment

**What Docker isolation prevents:**
- Reading/writing anything on your host outside the mounted `output/` dir
- Accessing SSH keys, git credentials, `.env` files, etc.
- Persisting anything after the container exits (except `output/`)

**What risks remain:**
- Can delete/overwrite files inside `output/` — commit or back up important results
- Full internet access means it could hit arbitrary URLs (acceptable for scraping)
- Claude could make bad judgment calls — always review output before using it
- Container escape exploits exist but are rare and require kernel vulnerabilities

**Practical advice:**
- Always `git commit` before launching autonomous tasks
- Review what lands in `output/` before trusting it
- Don't put secrets in the output directory

---

## Key security principle

From Anthropic's documentation:

> Effective sandboxing requires **both** filesystem AND network isolation.
> Without network isolation, a compromised agent could exfiltrate SSH keys.
> Without filesystem isolation, it could escape the sandbox and gain network access.

---

## CLI flags reference

| Flag | Effect |
|------|--------|
| `--dangerously-skip-permissions` | Disables ALL permission prompts. Use only in containers/VMs. |
| `--permission-mode bypassPermissions` | Same as above (more explicit name). |
| `--enable-auto-mode` | Unlocks auto mode with safety classifier. |
| `--allow-dangerously-skip-permissions` | Adds bypass to the mode cycle without starting in it. |
| `--permission-mode plan` | Read-only exploration mode. |
| `--permission-mode dontAsk` | Only pre-approved tools execute (fully non-interactive). |

Even in bypass mode, writes to `.git`, `.vscode`, `.idea`, `.husky`, and `.claude`
(except `.claude/commands`, `.claude/agents`, `.claude/skills`) still prompt.

---

## Sources

- [Claude Code Permission Modes](https://code.claude.com/docs/en/permission-modes.md)
- [Claude Code Sandboxing](https://code.claude.com/docs/en/sandboxing.md)
- [Anthropic: Claude Code Auto Mode Engineering](https://www.anthropic.com/engineering/claude-code-auto-mode)
- [Anthropic: Claude Code Sandboxing Engineering](https://www.anthropic.com/engineering/claude-code-sandboxing)
- [Docker: Run Claude Code Safely](https://www.docker.com/blog/docker-sandboxes-run-claude-code-and-other-coding-agents-unsupervised-but-safely/)
