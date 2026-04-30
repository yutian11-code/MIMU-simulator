#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

clone_or_update() {
  local dir="$1"
  local repo="$2"
  local branch="$3"
  local target="$ROOT/$dir"

  if [[ ! -d "$target" ]]; then
    git clone -b "$branch" "$repo" "$target"
    return
  fi

  if [[ ! -d "$target/.git" ]]; then
    echo "ERROR: $target exists but is not a git repository." >&2
    exit 1
  fi

  if [[ -n "$(git -C "$target" status --porcelain)" ]]; then
    echo "ERROR: $target has uncommitted changes. Commit or stash them before pulling." >&2
    exit 1
  fi

  git -C "$target" fetch origin
  git -C "$target" checkout "$branch"
  git -C "$target" pull --ff-only origin "$branch"
}

clone_or_update "backend" "https://github.com/GreFir/mymakeup-backend.git" "feature-ssf"
clone_or_update "frontend" "https://github.com/GreFir/my-make-up.git" "feature-ssf"

echo "MIMU application repositories are ready."
