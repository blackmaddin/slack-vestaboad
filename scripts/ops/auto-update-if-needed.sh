#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="/opt/vestaboard"
BRANCH="main"
LOG_PREFIX="[vestaboard-auto-update]"

cd "$REPO_DIR"

if ! git fetch origin "$BRANCH" --quiet; then
  echo "$LOG_PREFIX fetch failed (auth/network); skipping"
  exit 0
fi

current_local="$(git rev-parse "$BRANCH")"
current_remote="$(git rev-parse "origin/$BRANCH")"

if [ "$current_local" = "$current_remote" ]; then
  echo "$LOG_PREFIX no update needed ($current_local)"
  exit 0
fi

echo "$LOG_PREFIX updating $current_local -> $current_remote"
git reset --hard "$current_remote"
docker compose up -d --build

echo "$LOG_PREFIX update applied"
