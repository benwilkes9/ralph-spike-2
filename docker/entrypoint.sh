#!/bin/bash
set -euo pipefail

# ─── Validate required env vars ─────────────────────────────────
missing=()
[ -z "${ANTHROPIC_API_KEY:-}" ] && missing+=("ANTHROPIC_API_KEY")
[ -z "${GITHUB_PAT:-}" ]       && missing+=("GITHUB_PAT")
[ -z "${REPO:-}" ]             && missing+=("REPO")
[ -z "${BRANCH:-}" ]           && missing+=("BRANCH")

if [ ${#missing[@]} -gt 0 ]; then
    echo "Error: missing required env vars: ${missing[*]}" >&2
    exit 1
fi

# ─── Git config ──────────────────────────────────────────────────
git config --global user.name "Claude"
git config --global user.email "noreply@anthropic.com"
git config --global commit.gpgsign false

# ─── Clone repo ──────────────────────────────────────────────────
# /workspace/repo may already exist as a mount point (e.g. logs volume),
# so use git init + fetch instead of clone.
CLONE_URL="https://x-access-token:${GITHUB_PAT}@github.com/${REPO}.git"
cd /workspace/repo
git init
git remote add origin "$CLONE_URL"
git fetch origin "$BRANCH"
git checkout -b "$BRANCH" "origin/$BRANCH"

# ─── Install project dependencies ───────────────────────────────
uv sync --all-extras
uv run pre-commit install
uv run pre-commit install-hooks

# ─── Claude Code settings ────────────────────────────────────────
export DISABLE_AUTOUPDATER=1

# ─── Hand off to loop.sh ────────────────────────────────────────
exec ./docker/loop.sh "$@"
