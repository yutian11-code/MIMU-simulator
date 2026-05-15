# Demo Postlaunch P0/P1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the already launched MIMU demo stable for tomorrow's product and operations use by adding health checks, service controls, regression checks, structured coach logs, clearer front-end state cues, and updated runbook coverage.

**Architecture:** Keep changes small and operationally focused. Add root-level scripts that validate the full LAN demo stack without taking over model services, strengthen backend log records at the HTTP/voice/VLM/WebSocket boundaries, and add front-end copy/state affordances where the AI coach can otherwise look idle or confusing.

**Tech Stack:** Bash, Node/NestJS, TypeScript, React Native/Expo, existing Jest and CJS frontend utility tests.

---

### File Structure

- Create `scripts/check-demo-health.sh`: one-command readiness check for backend, platform health, ASR, Qwen-VL, ComfyUI, HTTPS gateway, frontend, WebSocket handshake, and optional smoke regression.
- Create `scripts/restart-demo-services.sh`: conservative tmux restart wrapper for app-facing services only, with model-service protection by default.
- Create `eval/coach/scripts/run_realtime_coach_regression.py`: local regression runner using existing eval images/audio/video frames against HTTP and WebSocket coach APIs.
- Modify `backend/src/common/middleware/request-logging.middleware.ts`: include request IDs and elapsed time consistently.
- Modify `backend/src/makeup/makeup-coach.service.ts`: log step-evaluate decisions and VLM fallback details with request context.
- Modify `backend/src/makeup/makeup-voice.service.ts`: log ASR transcript, voiceAction, and coach decision details.
- Modify `backend/src/makeup/makeup-realtime.gateway.ts`: include canAutoAdvance and compact outcome fields in realtime logs.
- Modify `backend/src/makeup/*.spec.ts`: test the new observable behavior where useful without depending on exact log strings.
- Modify `frontend/app/recommendation/live-coach.native.tsx` and `frontend/app/recommendation/coach.tsx`: make user-visible coach states clearer around waiting, AI-confirmed-but-user-not-confirmed, unclear frame, and wake mode.
- Modify `frontend/utils/__tests__/*.test.cjs`: add text/source assertions for the new UI cues where direct component rendering is not available.
- Modify `docs/team-runbook.md`: tomorrow's operator flow, health checks, restart commands, common failures, demo regression command.

### Task 1: Demo Health Check Script

**Files:**
- Create: `scripts/check-demo-health.sh`
- Modify: `docs/team-runbook.md`

- [ ] **Step 1: Write a failing shell-level validation**

Run:

```bash
test -x scripts/check-demo-health.sh
```

Expected: FAIL because `scripts/check-demo-health.sh` does not exist yet.

- [ ] **Step 2: Implement the script**

Create `scripts/check-demo-health.sh` with executable permissions. It should:

- Use defaults:
  - `MIMU_BACKEND_URL=http://127.0.0.1:13001`
  - `MIMU_GATEWAY_URL=https://127.0.0.1:19443`
  - `MIMU_FRONTEND_URL=http://127.0.0.1:19006`
  - `MIMU_ASR_URL=http://127.0.0.1:8020`
  - `MIMU_VLM_URL=http://127.0.0.1:8010`
  - `MIMU_COMFY_URL=http://127.0.0.1:8188`
- Print PASS/WARN/FAIL lines.
- Check backend `/health`, backend `/platform/health`, gateway `/api/health`, frontend HEAD/GET, ASR `/health`, VLM `/v1/models`, ComfyUI `/system_stats`.
- Probe WebSocket `/makeup/coach/realtime/wake` using a short Node script.
- Support `--with-smoke` to call `scripts/smoke-mimu-platform.sh`.
- Exit non-zero if required checks fail.

- [ ] **Step 3: Verify the script**

Run:

```bash
scripts/check-demo-health.sh
```

Expected: Required checks pass on running services or fail with precise endpoint names.

### Task 2: Conservative Restart Script

**Files:**
- Create: `scripts/restart-demo-services.sh`
- Modify: `docs/team-runbook.md`

- [ ] **Step 1: Write a failing validation**

Run:

```bash
test -x scripts/restart-demo-services.sh
```

Expected: FAIL because the script does not exist yet.

- [ ] **Step 2: Implement restart wrapper**

Create `scripts/restart-demo-services.sh`. It should:

- Restart only app-facing tmux sessions by default:
  - `mimu-backend-13000`
  - `mimu-backend-13001`
  - `mimu-frontend-19006`
  - `mimu-https-gateway-19443`
- Never kill ASR, VLM, ComfyUI unless `--include-models` is explicitly passed.
- Use existing commands and environment defaults where discoverable.
- Write logs to `var/logs`.
- Print a final health-check command.

- [ ] **Step 3: Verify script help/dry-run**

Run:

```bash
scripts/restart-demo-services.sh --dry-run
```

Expected: Lists planned sessions and commands without killing anything.

### Task 3: Coach Regression Runner

**Files:**
- Create: `eval/coach/scripts/run_realtime_coach_regression.py`
- Modify: `docs/team-runbook.md`

- [ ] **Step 1: Write a failing validation**

Run:

```bash
python eval/coach/scripts/run_realtime_coach_regression.py --help
```

Expected: FAIL because the script does not exist yet.

- [ ] **Step 2: Implement regression runner**

Create a Python script that:

- Accepts `--backend-url`, `--token`, `--image-limit`, `--video-dir`, `--audio-dir`, `--output`.
- Calls `/makeup/coach/step-evaluate` for images under `eval/data/评测集` when present, otherwise uses `eval/makeup/assets/users`.
- Exercises `/makeup/coach/voice` for audio samples under `eval/coach/assets/audio`.
- Performs a WebSocket wake handshake and can send a `start` then close cleanly.
- Writes JSON report with `passed`, `failed`, `cases`, `endpoint`, `latencyMs`, `voiceAction`, `canAutoAdvance`, and error messages.
- Does not upload real private video content to external services; it only calls the local backend.

- [ ] **Step 3: Verify help and a small run**

Run:

```bash
python eval/coach/scripts/run_realtime_coach_regression.py --help
python eval/coach/scripts/run_realtime_coach_regression.py --backend-url http://127.0.0.1:13001 --image-limit 2 --output /tmp/mimu-coach-regression.json
```

Expected: Help prints options; small run writes a JSON report and exits 0 when required local services are healthy.

### Task 4: Structured Backend Logs

**Files:**
- Modify: `backend/src/common/middleware/request-logging.middleware.ts`
- Modify: `backend/src/makeup/makeup-coach.service.ts`
- Modify: `backend/src/makeup/makeup-voice.service.ts`
- Modify: `backend/src/makeup/makeup-realtime.gateway.ts`
- Modify tests under `backend/src/makeup/*.spec.ts` as needed.

- [ ] **Step 1: Add failing tests for observable decisions**

Add tests that assert:

- Voice response preserves `voiceAction`, `canAutoAdvance`, and transcript for noisy next-step input.
- Step evaluation returns the canAutoAdvance schema when VLM is available or fallback occurs.
- Realtime event logs include `canAutoAdvance` in the event payload.

Run:

```bash
cd backend && npm test -- --runInBand src/makeup/makeup-voice.service.spec.ts src/makeup/makeup-realtime-session.service.spec.ts
```

Expected: At least one new assertion fails before implementation if a field is missing from observable payloads.

- [ ] **Step 2: Implement logs**

Add compact structured log messages, not large image/audio payloads:

- `coach_step_evaluate`: stepCode, stepTitle, completionLevel, shouldProceed, canAutoAdvance, qualityScore, provider, elapsedMs.
- `coach_voice`: transcript, voiceAction, shouldProceed, canAutoAdvance, model, elapsedMs.
- `realtime_event`: sessionId, turnId, event type, voiceAction, shouldProceed, canAutoAdvance, reason.
- `http_request`: method, path, statusCode, elapsedMs, requestId.

- [ ] **Step 3: Verify backend**

Run:

```bash
cd backend && npm test -- --runInBand
cd backend && npm run build
```

Expected: All tests and build pass.

### Task 5: Frontend Coach State Cues

**Files:**
- Modify: `frontend/app/recommendation/live-coach.native.tsx`
- Modify: `frontend/app/recommendation/coach.tsx`
- Modify: `frontend/utils/__tests__/webPerformanceAssets.test.cjs` or `frontend/utils/__tests__/makeupCoachProgress.test.cjs`

- [ ] **Step 1: Add failing source assertions**

Add frontend utility/source tests asserting the UI contains visible user-facing states:

- `等待用户确认`
- `画面不清晰`
- `AI 已确认`
- `唤醒后再说`

Run:

```bash
cd frontend && node --test utils/__tests__/*.test.cjs
```

Expected: FAIL until the strings are present in relevant coach files.

- [ ] **Step 2: Implement UI cues**

Update coach screens so:

- When AI thinks the step can proceed but user has not confirmed: show “AI 已确认，等待用户确认”.
- When confidence/quality is low or `detectedIssues` include image quality: show “画面不清晰，请重新对准后再问 AI”.
- In wake realtime mode: show “唤醒后再说：我完成了，下一步 / 帮我看一下”.
- When both user and AI confirm: keep existing auto-advance behavior and success voice text.

- [ ] **Step 3: Verify frontend**

Run:

```bash
cd frontend && node --test utils/__tests__/*.test.cjs
cd frontend && npx tsc --noEmit
cd frontend && npm run lint
```

Expected: All pass.

### Task 6: Runbook Update

**Files:**
- Modify: `docs/team-runbook.md`

- [ ] **Step 1: Add postlaunch operating section**

Document:

- Official LAN URL.
- One-command health check.
- Restart commands and model-service warning.
- Regression commands.
- Common failures and first response:
  - blank page
  - camera/mic blocked
  - ASR no transcript
  - VLM token/model error
  - WebSocket cannot connect
  - AI says complete but user did not confirm
- Template-library operations note: P1/P2/P3, source media, manual review.

- [ ] **Step 2: Verify docs mention commands**

Run:

```bash
rg -n "check-demo-health|restart-demo-services|run_realtime_coach_regression|https://10.246.1.70:19443" docs/team-runbook.md
```

Expected: All key commands and URL are present.

### Task 7: Full Verification and Push

**Files:**
- All modified files.

- [ ] **Step 1: Run full verification**

Run:

```bash
scripts/check-demo-health.sh
scripts/check-demo-health.sh --with-smoke
python eval/coach/scripts/run_realtime_coach_regression.py --backend-url http://127.0.0.1:13001 --image-limit 4 --output /tmp/mimu-coach-regression.json
cd backend && npm test -- --runInBand && npm run build
cd frontend && node --test utils/__tests__/*.test.cjs && npx tsc --noEmit && npm run lint
```

Expected: All pass. If model services are offline but app code is correct, record the exact unavailable service and still complete code/test verification.

- [ ] **Step 2: Commit and push each repo**

Root:

```bash
git add scripts eval docs
git commit -m "chore: add demo postlaunch operations checks"
git push origin main
```

Backend:

```bash
cd backend
git add src test
git commit -m "chore: improve coach observability"
git push origin master
```

Frontend:

```bash
cd frontend
git add app utils
git commit -m "chore: clarify coach runtime states"
git push origin main
```

Expected: Each repo with changes has one pushed commit; repos without changes remain clean.

---

### Self-Review

- P0 coverage: health checks, restart script, regression test pack, logs, runbook are covered by Tasks 1-4, 6-7.
- P1 coverage: front-end state cues, safer wake/confirmation explanation, template-ops documentation, data/logging hooks are covered by Tasks 4-6.
- No placeholders remain. Exact paths and commands are included.
- Scope is operational stabilization, not a new template algorithm or model deployment rewrite.
