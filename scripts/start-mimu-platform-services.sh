#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/var/logs"
MODE="${MIMU_MODEL_MODE:-mock}"
SESSION_NAME="${MIMU_TEMPLATE_MODEL_SESSION:-mimu_template_model_mocks}"

mkdir -p "$LOG_DIR"

if [[ "$MODE" == "mock" ]]; then
  if tmux has-session -t "$SESSION_NAME" 2>/dev/null; then
    echo "Mock template model services already running in tmux session: $SESSION_NAME"
    exit 0
  fi

  tmux new-session -d -s "$SESSION_NAME" \
    "cd '$ROOT_DIR' && node scripts/start-template-model-mock-services.mjs 2>&1 | tee '$LOG_DIR/template-model-mocks.log'"
  echo "Started mock template model services on 8030/8031/8032"
  echo "Logs: $LOG_DIR/template-model-mocks.log"
  exit 0
fi

cat <<'EOF'
Real model mode selected.
Start embedding, rerank, VLM, ASR, ComfyUI, and coach services with the
configured conda environments and ports from docs/team-runbook.md.

Expected backend env examples:
  TEMPLATE_EMBEDDING_BASE_URL=http://127.0.0.1:8030/v1
  TEMPLATE_RERANKER_BASE_URL=http://127.0.0.1:8031/v1
  TEMPLATE_VLM_BASE_URL=http://127.0.0.1:8010/v1
  COACH_ASR_BASE_URL=http://127.0.0.1:8020
  COMFY_UI_BASE_URL=http://127.0.0.1:8188
EOF
