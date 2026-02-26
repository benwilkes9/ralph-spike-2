FROM node:22-bookworm

# ═════════════════════════════════════════════════════════════════
# Universal layers — same across all repos using this pattern
# ═════════════════════════════════════════════════════════════════

# System packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        git jq bc curl ca-certificates iptables \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code@latest

# Ralph CLI (loop orchestrator)
COPY --from=golang:1.25-bookworm /usr/local/go /usr/local/go
ENV PATH="/usr/local/go/bin:$PATH"
RUN go install github.com/benwilkes9/ralph-cli/cmd/ralph@latest \
    && cp /root/go/bin/ralph /usr/local/bin/ralph

# ═════════════════════════════════════════════════════════════════
# Language runtime layers
# ═════════════════════════════════════════════════════════════════

# uv (Python package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Non-root user (entrypoint drops to this user after firewall setup)
RUN useradd -m -s /bin/bash claude \
    && mkdir -p /home/claude/.claude /workspace \
    && chown -R claude:claude /home/claude /workspace

# Onboarding marker required for OAuth token authentication
RUN echo '{"hasCompletedOnboarding":true}' > /home/claude/.claude.json \
    && chown claude:claude /home/claude/.claude.json

# ═════════════════════════════════════════════════════════════════
# Project-specific layers
# ═════════════════════════════════════════════════════════════════

COPY --chown=root:claude .ralph/docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 750 /usr/local/bin/entrypoint.sh

WORKDIR /workspace
ENV PATH="/home/claude/.local/bin:$PATH"
ENV UV_LINK_MODE=copy
RUN runuser -u claude -- uv python install 3.12

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
