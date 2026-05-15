#!/usr/bin/env bash
set -u

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${MIMU_BACKEND_URL:-http://127.0.0.1:13001}"
GATEWAY_URL="${MIMU_GATEWAY_URL:-https://127.0.0.1:19443}"
FRONTEND_URL="${MIMU_FRONTEND_URL:-http://127.0.0.1:19006}"
ASR_URL="${MIMU_ASR_URL:-http://127.0.0.1:8020}"
VLM_URL="${MIMU_VLM_URL:-http://127.0.0.1:8010}"
COMFY_URL="${MIMU_COMFY_URL:-http://127.0.0.1:8188}"
TIMEOUT_SECONDS="${MIMU_HEALTH_TIMEOUT_SECONDS:-5}"
WITH_SMOKE=0
FAILED=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-smoke)
      WITH_SMOKE=1
      shift
      ;;
    -h|--help)
      cat <<EOF
Usage: scripts/check-demo-health.sh [--with-smoke]

Environment overrides:
  MIMU_BACKEND_URL   default http://127.0.0.1:13001
  MIMU_GATEWAY_URL   default https://127.0.0.1:19443
  MIMU_FRONTEND_URL  default http://127.0.0.1:19006
  MIMU_ASR_URL       default http://127.0.0.1:8020
  MIMU_VLM_URL       default http://127.0.0.1:8010
  MIMU_COMFY_URL     default http://127.0.0.1:8188
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

pass() {
  printf '[PASS] %s\n' "$1"
}

warn() {
  printf '[WARN] %s\n' "$1"
}

fail() {
  FAILED=1
  printf '[FAIL] %s\n' "$1"
}

check_url() {
  local name="$1"
  local url="$2"
  local required="${3:-required}"
  local curl_args=(-fsS --max-time "$TIMEOUT_SECONDS")

  if [[ "$url" == https://* ]]; then
    curl_args=(-k "${curl_args[@]}")
  fi

  local start elapsed
  start="$(date +%s%3N)"
  if curl "${curl_args[@]}" "$url" >/tmp/mimu-health-check.out 2>/tmp/mimu-health-check.err; then
    elapsed=$(( $(date +%s%3N) - start ))
    pass "$name ${url} ${elapsed}ms"
    return 0
  fi

  local error
  error="$(tr '\n' ' ' </tmp/mimu-health-check.err | sed 's/[[:space:]]\+/ /g' | cut -c1-180)"
  if [[ "$required" == "optional" ]]; then
    warn "$name ${url} unavailable: ${error:-curl failed}"
    return 0
  fi

  fail "$name ${url} unavailable: ${error:-curl failed}"
  return 1
}

check_frontend() {
  local start elapsed
  start="$(date +%s%3N)"
  if curl -fsSI --max-time "$TIMEOUT_SECONDS" "$FRONTEND_URL" >/tmp/mimu-frontend-head.out 2>/tmp/mimu-frontend-head.err ||
     curl -fsS --max-time "$TIMEOUT_SECONDS" "$FRONTEND_URL" >/tmp/mimu-frontend-get.out 2>/tmp/mimu-frontend-head.err; then
    elapsed=$(( $(date +%s%3N) - start ))
    pass "frontend ${FRONTEND_URL} ${elapsed}ms"
    return 0
  fi

  fail "frontend ${FRONTEND_URL} unavailable: $(tr '\n' ' ' </tmp/mimu-frontend-head.err | cut -c1-180)"
}

check_websocket() {
  local ws_url="${BACKEND_URL/http:/ws:}/makeup/coach/realtime/wake"
  ws_url="${ws_url/https:/wss:}"

  MIMU_WS_URL="$ws_url" node <<'NODE'
const WebSocket = require('./backend/node_modules/ws');
const url = process.env.MIMU_WS_URL;
const socket = new WebSocket(url, { rejectUnauthorized: false });
const timeout = setTimeout(() => {
  console.error(`timeout connecting to ${url}`);
  socket.terminate();
  process.exit(1);
}, 5000);

socket.on('open', () => {
  socket.send(JSON.stringify({
    type: 'start',
    payload: {
      scenario: 'demo health',
      stepTitle: '底妆',
      stepInstruction: '少量多次铺开粉底。',
      completedStepTitles: [],
      totalSteps: 5,
      wakeWordMode: true,
      wakeActivationMs: 15000
    }
  }));
});

socket.on('message', (data) => {
  const event = JSON.parse(String(data));
  if (event.type === 'session_ready' || event.type === 'listening') {
    clearTimeout(timeout);
    socket.close();
  }
});

socket.on('close', () => process.exit(0));
socket.on('error', (error) => {
  clearTimeout(timeout);
  console.error(error.message);
  process.exit(1);
});
NODE
  local code=$?
  if [[ $code -eq 0 ]]; then
    pass "websocket ${ws_url}"
  else
    fail "websocket ${ws_url}"
  fi
}

echo "MIMU demo health check"
echo "backend=$BACKEND_URL gateway=$GATEWAY_URL frontend=$FRONTEND_URL"

check_url "backend health" "$BACKEND_URL/health" required
check_url "platform health" "$BACKEND_URL/platform/health" required
check_url "https gateway api" "$GATEWAY_URL/api/health" required
check_frontend
check_url "ASR" "$ASR_URL/health" required
check_url "Qwen-VL models" "$VLM_URL/v1/models" required
check_url "ComfyUI" "$COMFY_URL/system_stats" required
check_websocket

if [[ "$WITH_SMOKE" -eq 1 ]]; then
  if MIMU_BACKEND_URL="$BACKEND_URL" bash "$ROOT_DIR/scripts/smoke-mimu-platform.sh"; then
    pass "platform smoke"
  else
    fail "platform smoke"
  fi
fi

if [[ "$FAILED" -ne 0 ]]; then
  echo "MIMU demo health check failed"
  exit 1
fi

echo "MIMU demo health check passed"
