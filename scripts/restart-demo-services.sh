#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/var/logs"
DRY_RUN=0
INCLUDE_MODELS=0

mkdir -p "$LOG_DIR"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --include-models)
      INCLUDE_MODELS=1
      shift
      ;;
    -h|--help)
      cat <<EOF
Usage: scripts/restart-demo-services.sh [--dry-run] [--include-models]

Default restarts only app-facing services:
  mimu-backend-13000, mimu-backend-13001, mimu-frontend-19006, mimu-https-gateway-19443

Model services are not touched unless --include-models is passed.
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

run() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] %s\n' "$*"
    return
  fi

  eval "$@"
}

kill_session() {
  local session="$1"
  if tmux has-session -t "$session" 2>/dev/null; then
    run "tmux kill-session -t '$session'"
  elif [[ "$DRY_RUN" -eq 1 ]]; then
    printf '[dry-run] tmux session not running: %s\n' "$session"
  fi
}

start_backend() {
  local port="$1"
  local session="mimu-backend-$port"
  kill_session "$session"
  run "tmux new-session -d -s '$session' \"cd '$ROOT_DIR/backend' && PORT=$port HOST=0.0.0.0 node dist/src/main 2>&1 | tee '$LOG_DIR/backend-$port.log'\""
}

start_frontend() {
  local session="mimu-frontend-19006"
  kill_session "$session"
  run "tmux new-session -d -s '$session' \"cd '$ROOT_DIR/frontend' && npx expo start --web --host lan --port 19006 2>&1 | tee '$LOG_DIR/frontend-19006.log'\""
}

start_gateway() {
  local session="mimu-https-gateway-19443"
  kill_session "$session"
  kill_session "mimu_https_gateway"
  run "tmux new-session -d -s '$session' \"cd '$ROOT_DIR' && MIMU_BACKEND_ORIGIN=http://127.0.0.1:13001 bash scripts/start-https-lan-gateway.sh 2>&1 | tee '$LOG_DIR/https-lan-gateway.log'\""
}

restart_models() {
  kill_session "mimu_asr_8020"
  kill_session "mimu_qwen_vl_8010"
  kill_session "mimu_comfy_8188"
  echo "Model sessions were stopped. Restart model services with the project-specific conda commands in docs/team-runbook.md."
}

echo "Restarting MIMU demo app services from $ROOT_DIR"
start_backend 13000
start_backend 13001
start_frontend
start_gateway

if [[ "$INCLUDE_MODELS" -eq 1 ]]; then
  restart_models
else
  echo "Model services left untouched. Pass --include-models only during a planned model maintenance window."
fi

echo "Run health check:"
echo "  $ROOT_DIR/scripts/check-demo-health.sh"
