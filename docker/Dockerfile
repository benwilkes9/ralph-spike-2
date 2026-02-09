FROM node:22-bookworm

# ═════════════════════════════════════════════════════════════════
# Universal layers — same across all repos using this pattern
# ═════════════════════════════════════════════════════════════════

# System packages
RUN apt-get update && apt-get install -y --no-install-recommends \
        git jq bc curl ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code@latest

# uv (Python/general package manager)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Non-root user
RUN useradd -m -s /bin/bash claude \
    && mkdir -p /home/claude/.claude /workspace/repo \
    && chown -R claude:claude /home/claude /workspace

# ═════════════════════════════════════════════════════════════════
# Project-specific layers — customise per repo
# ═════════════════════════════════════════════════════════════════

COPY docker/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

USER claude
WORKDIR /workspace
ENV PATH="/home/claude/.local/bin:$PATH"

RUN uv python install 3.12

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
