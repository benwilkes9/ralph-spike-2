#!/bin/bash
set -euo pipefail

ENV_FILE=".env"

# ─── Auto-detect repo and branch ────────────────────────────────
REPO=$(git remote get-url origin | sed -E 's#.*github\.com[:/]([^/]+/[^/.]+)(\.git)?$#\1#')
BRANCH=$(git branch --show-current)

echo "Repo:   $REPO"
echo "Branch: $BRANCH"

# ─── Load .env if present ────────────────────────────────────────
if [ -f "$ENV_FILE" ]; then
    set -a
    # shellcheck source=/dev/null
    source "$ENV_FILE"
    set +a
fi

# ─── Validate secrets ───────────────────────────────────────────
missing=()
[ -z "${ANTHROPIC_API_KEY:-}" ] && missing+=("ANTHROPIC_API_KEY")
[ -z "${GITHUB_PAT:-}" ]       && missing+=("GITHUB_PAT")

if [ ${#missing[@]} -gt 0 ]; then
    echo "Error: missing required env vars: ${missing[*]}" >&2
    echo "Add them to .env or export them before running." >&2
    exit 1
fi

# ─── Build and run ───────────────────────────────────────────────
DOCKER_BUILDKIT=1 docker build -t claude-loop -f docker/Dockerfile .

LOCAL_LOGS="$(pwd)/logs"
mkdir -p "$LOCAL_LOGS"

docker run --rm -it \
    -e ANTHROPIC_API_KEY \
    -e GITHUB_PAT \
    -e REPO="$REPO" \
    -e BRANCH="$BRANCH" \
    -v "$LOCAL_LOGS:/workspace/repo/logs" \
    claude-loop "$@"

# ─── Sync local branch with remote pushes from container ────────
echo ""
echo "Syncing local branch with remote..."
git pull --rebase origin "$BRANCH" 2>/dev/null && echo "Local branch up to date." || echo "Warning: failed to sync with remote."
