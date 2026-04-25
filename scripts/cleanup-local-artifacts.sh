#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="${ROOT_DIR:-/storage/nvme3/shushanfu/MIMU-colleague}"
MODE="${1:---dry-run}"

TARGETS=(
  "$ROOT_DIR/ComfyUI/input"
  "$ROOT_DIR/ComfyUI/output/stable_makeup"
  "$ROOT_DIR/eval/makeup/runs"
)

if [[ "$MODE" != "--dry-run" && "$MODE" != "--apply" ]]; then
  echo "Usage: $0 [--dry-run|--apply]" >&2
  exit 2
fi

echo "Mode: $MODE"
for target in "${TARGETS[@]}"; do
  if [[ ! -e "$target" ]]; then
    echo "skip missing: $target"
    continue
  fi

  echo "target: $target"
  find "$target" -mindepth 1 -maxdepth 2 -type f | sort | sed -n '1,80p'

  if [[ "$MODE" == "--apply" ]]; then
    find "$target" -mindepth 1 -maxdepth 2 -type f -delete
  fi
done

if [[ "$MODE" == "--dry-run" ]]; then
  echo "No files were deleted. Re-run with --apply to delete listed files."
else
  echo "Cleanup finished."
fi
