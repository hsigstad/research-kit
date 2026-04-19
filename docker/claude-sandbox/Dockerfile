FROM debian:bookworm-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl git ca-certificates nodejs npm \
    python3 python3-pip python3-venv \
    chromium chromium-driver \
  && rm -rf /var/lib/apt/lists/*

# Install Claude Code
RUN npm install -g @anthropic-ai/claude-code

# Match host user
RUN useradd -m -u 1000 henrik
USER henrik

# Python env with common scraping/analysis packages
RUN python3 -m venv /home/henrik/venv
ENV PATH="/home/henrik/venv/bin:$PATH"
RUN pip install --no-cache-dir \
    requests beautifulsoup4 lxml \
    newspaper3k trafilatura \
    pandas pyarrow \
    numpy scipy statsmodels matplotlib \
    PyMuPDF mistune \
    linearmodels pydantic python-dotenv html2text \
    openai anthropic

# Memory monitor
COPY monitor_memory.sh /usr/local/bin/monitor_memory.sh

WORKDIR /workspace
