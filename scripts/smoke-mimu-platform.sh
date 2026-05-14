#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_URL="${MIMU_BACKEND_URL:-http://127.0.0.1:13001}"
TOKEN="${MIMU_DEMO_TOKEN:-demo-token}"
USER_IMAGE="${MIMU_SMOKE_USER_IMAGE:-$ROOT_DIR/eval/makeup/assets/users/u001_front_light.jpg}"
TEMPLATE_IMAGE="${MIMU_SMOKE_TEMPLATE_IMAGE:-$ROOT_DIR/eval/makeup/assets/templates/t001_blue_eye.jpg}"

echo "[1/7] Backend health"
curl -fsS "$BACKEND_URL/health" >/tmp/mimu-health.json

echo "[2/7] Platform health"
curl -fsS "$BACKEND_URL/platform/health" | python -m json.tool >/tmp/mimu-platform-health.json

echo "[3/7] Seed standard template library"
curl -fsS -X POST "$BACKEND_URL/makeup-template-library/seed" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | python -m json.tool >/tmp/mimu-template-seed.json

echo "[4/7] Generate recommendation"
curl -fsS -X POST "$BACKEND_URL/recommendations/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scenario":"面试","scenarioDetails":"面试需要轻熟知性优雅妆，不要太浓","requirements":["不要太浓"]}' \
  | python -m json.tool >/tmp/mimu-generation.json

echo "[5/7] Create makeup preview job"
if [[ ! -f "$USER_IMAGE" || ! -f "$TEMPLATE_IMAGE" ]]; then
  echo "Missing smoke preview images: $USER_IMAGE / $TEMPLATE_IMAGE" >&2
  exit 1
fi
curl -fsS -X POST "$BACKEND_URL/makeup/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -F "userImage=@$USER_IMAGE;type=image/jpeg" \
  -F "templateImage=@$TEMPLATE_IMAGE;type=image/jpeg" \
  -F "generatedTemplateId=smoke_generated_template" \
  -F "sourceStandardTemplateVersionId=smoke_standard_version" \
  -F "comparisonMode=slider" \
  -F 'productSlotSummary={"source":"smoke"}' \
  | python -m json.tool >/tmp/mimu-preview-job.json

echo "[6/7] Coach step-evaluate schema"
STEP_IMAGE_DATA_URL="data:image/jpeg;base64,$(base64 "$USER_IMAGE" | tr -d '\n')"
curl -fsS -X POST "$BACKEND_URL/makeup/coach/step-evaluate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"generatedTemplateId":"smoke_generated_template","stepId":"smoke_step_lip","stepCode":"LIP","scenario":"五步演示妆容","stepTitle":"唇妆","stepInstruction":"完成豆沙色唇妆。","completionCriteria":"唇色均匀，边缘清晰。","imageDataUrl":"'"$STEP_IMAGE_DATA_URL"'"}' \
  | python -m json.tool >/tmp/mimu-step-evaluate.json

echo "[7/7] Template matching eval"
python "$ROOT_DIR/eval/template_matching/run_template_matching_eval.py" \
  --backend-url "$BACKEND_URL" \
  --token "$TOKEN" \
  --output /tmp/mimu-template-matching-report.json

echo "MIMU platform smoke passed"
echo "Artifacts:"
echo "  /tmp/mimu-platform-health.json"
echo "  /tmp/mimu-template-seed.json"
echo "  /tmp/mimu-generation.json"
echo "  /tmp/mimu-preview-job.json"
echo "  /tmp/mimu-step-evaluate.json"
echo "  /tmp/mimu-template-matching-report.json"
