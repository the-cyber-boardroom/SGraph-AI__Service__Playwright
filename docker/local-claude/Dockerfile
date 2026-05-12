# ═══════════════════════════════════════════════════════════════════════════════
# SG Playwright — docker/local-claude/Dockerfile
#
# Laptop-local twin of `sg lc`: a container that runs Claude Code CLI pointed
# at the host's Ollama (OpenAI-compat endpoint) instead of EC2-hosted vLLM.
# Mirrors the EC2 firstboot pattern from
# sg_compute/platforms/ec2/user_data/Section__Claude_Code__Firstboot.py
# but adapted for Docker on a Mac (host.docker.internal:11434).
# ═══════════════════════════════════════════════════════════════════════════════

FROM node:22-bookworm-slim

# Minimal tooling that the EC2 firstboot effectively gives Claude.
# Keep lean: no build-essential by default (Claude rarely needs to compile).
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        git \
        curl \
        jq \
        ca-certificates \
        python3 \
        python3-pip \
        ripgrep \
        tini \
 && rm -rf /var/lib/apt/lists/*

# Claude Code CLI — official npm distribution
RUN npm install -g @anthropic-ai/claude-code \
 && npm cache clean --force

# Non-root user with a real home dir (Claude writes config under ~/.claude).
# node:22 base ships a `node` user at UID 1000 — drop it so we can claim 1000.
RUN userdel -r node 2>/dev/null || true \
 && useradd --create-home --shell /bin/bash --uid 1000 claude \
 && mkdir -p /home/claude/.claude /workspace \
 && chown -R claude:claude /home/claude /workspace

# Settings template + launcher (mirrors Section__Claude_Code__Firstboot.py)
COPY --chown=claude:claude settings.json        /home/claude/.claude/settings.json
COPY --chown=claude:claude local-llm-claude.sh  /home/claude/local-llm-claude.sh
RUN chmod +x /home/claude/local-llm-claude.sh

USER claude
WORKDIR /workspace

ENV HOME=/home/claude \
    PATH=/home/claude/.local/bin:/home/claude/bin:/usr/local/bin:/usr/bin:/bin

# tini gives clean PID-1 signal handling for the interactive `claude` process
ENTRYPOINT ["/usr/bin/tini", "--", "/home/claude/local-llm-claude.sh"]
CMD ["--dangerously-skip-permissions"]
