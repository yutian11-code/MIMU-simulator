# Voice Coach A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the A-version voice interaction loop for the MIMU roadshow: press to record, transcribe with local ASR, send transcript plus current image to the existing VLM coach, speak the guidance, and optionally advance the current step.

**Architecture:** Keep ASR out of the NestJS process. The backend exposes `/makeup/coach/voice`, calls a local Python ASR service, classifies simple voice intents, then reuses `MakeupCoachService.guide()`. The Expo web frontend records one short clip per interaction with `MediaRecorder`, sends it with the current frame, renders the transcript, and uses browser `speechSynthesis` for the roadshow.

**Tech Stack:** NestJS, Jest, Expo React Native Web, MediaRecorder, browser speech synthesis, Python FastAPI, Qwen/Qwen3-ASR-0.6B through the `qwen-asr` package.

---

### Task 1: Backend Voice Endpoint

**Files:**
- Create: `backend/src/makeup/makeup-voice.service.ts`
- Create: `backend/src/makeup/makeup-voice.service.spec.ts`
- Modify: `backend/src/makeup/dto/makeup-coach.dto.ts`
- Modify: `backend/src/makeup/makeup.controller.ts`
- Modify: `backend/src/makeup/makeup.module.ts`

- [ ] **Step 1: Write the failing service test**

Add `MakeupVoiceService` tests that instantiate the service with a mocked `MakeupCoachService`, set `COACH_ASR_BASE_URL=http://127.0.0.1:8020`, mock `global.fetch`, and verify that a voice request:

```ts
{
  scenario: '通勤淡妆',
  stepTitle: '底妆',
  stepInstruction: '少量多次铺开粉底。',
  completedStepTitles: ['护肤打底'],
  totalSteps: 4,
  audioDataUrl: 'data:audio/webm;base64,AAAA',
  imageDataUrl: 'data:image/jpeg;base64,BBBB'
}
```

calls the ASR service, passes transcript text into `MakeupCoachService.guide()`, returns the coach response plus `transcript` and `voiceAction`, and classifies “下一步” as `confirm_step`.

- [ ] **Step 2: Run the test to verify it fails**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
npm test -- makeup-voice.service.spec.ts --runInBand
```

Expected: FAIL because `makeup-voice.service.ts` does not exist.

- [ ] **Step 3: Implement minimal backend code**

Create `MakeupVoiceService` with:

```ts
async guideWithVoice(request: MakeupCoachVoiceRequestDto): Promise<MakeupCoachVoiceResponseDto>
```

It validates `audioDataUrl`, POSTs `{ audioDataUrl, audioMimeType }` to `${COACH_ASR_BASE_URL}/transcribe`, trims the returned `text`, classifies intent by Chinese keywords, calls `MakeupCoachService.guide({ ...request, userQuestion: transcript })`, and returns the merged DTO.

- [ ] **Step 4: Wire the controller**

Add `POST /makeup/coach/voice` in `MakeupController`, inject `MakeupVoiceService`, and register it in `MakeupModule.providers`.

- [ ] **Step 5: Verify backend**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
npm test -- makeup-voice.service.spec.ts makeup-coach.service.spec.ts --runInBand
npm run build
```

Expected: both test suites pass and Nest builds successfully.

- [ ] **Step 6: Commit backend**

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
git add src/makeup
git commit -m "feat: add voice coach endpoint"
```

### Task 2: Local ASR Service

**Files:**
- Create: `services/asr_service/server.py`
- Create: `services/asr_service/requirements.txt`
- Create: `services/asr_service/README.md`
- Modify: `docs/team-runbook.md`

- [ ] **Step 1: Create a testable FastAPI service**

Implement `/health` and `/transcribe`. `/transcribe` accepts:

```json
{"audioDataUrl":"data:audio/webm;base64,...","audioMimeType":"audio/webm"}
```

It calls `Qwen3ASRModel.from_pretrained()` once at startup/lazy first request, transcribes the base64 audio, and returns:

```json
{"text":"下一步","provider":"qwen-asr","model":"Qwen/Qwen3-ASR-0.6B"}
```

- [ ] **Step 2: Add startup docs using Chinese mirrors**

Document the conda environment, PyPI mirror, HF mirror, and tmux command:

```bash
conda create -n mimu-voice python=3.12 -y -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main
conda run -n mimu-voice pip install -r services/asr_service/requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
HF_ENDPOINT=https://hf-mirror.com python /storage/nvme3/shushanfu/checkpoint/down_load.py --repo-id Qwen/Qwen3-ASR-0.6B --save-path /storage/nvme3/shushanfu/checkpoint/huggingface/Qwen/Qwen3-ASR-0.6B
```

- [ ] **Step 3: Verify service syntax**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
python -m py_compile services/asr_service/server.py
```

Expected: no syntax errors.

- [ ] **Step 4: Commit top-level ASR files**

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
git add services/asr_service docs/team-runbook.md docs/superpowers/plans/2026-04-26-voice-coach-a.md
git commit -m "feat: add local asr service plan"
```

### Task 3: Frontend Voice Controls

**Files:**
- Modify: `frontend/types/makeup-coach.ts`
- Modify: `frontend/services/makeupCoachService.ts`
- Modify: `frontend/app/recommendation/coach.tsx`

- [ ] **Step 1: Add frontend types and service method**

Define `MakeupCoachVoiceRequest` and `MakeupCoachVoiceResponse`, then add:

```ts
requestVoiceGuidance(params: MakeupCoachVoiceRequest)
```

which POSTs to `/makeup/coach/voice`.

- [ ] **Step 2: Add recording state**

In `coach.tsx`, add `recordingState`, `voiceError`, `voiceTranscript`, `voiceAutoAdvanceNotice`, `mediaRecorderRef`, and `audioChunksRef`.

- [ ] **Step 3: Implement record/stop/send**

Use `navigator.mediaDevices.getUserMedia({ audio: true })`, `MediaRecorder`, and `FileReader` to create an audio data URL. On stop, capture/upload the current image frame, send the voice request, set the transcript, and call `speechSynthesis.speak()` with `guidance + nextAction`.

- [ ] **Step 4: Implement guarded auto-advance**

When the backend returns `voiceAction === 'confirm_step'` and `shouldProceed === true`, call `handleConfirmCurrentStep()` after the response has rendered. If `shouldProceed === false`, do not advance; show a short notice that the model recommends fixing the current step first.

- [ ] **Step 5: Verify frontend**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/frontend
npx tsc --noEmit
npm run lint
```

Expected: TypeScript and lint pass.

- [ ] **Step 6: Commit frontend**

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/frontend
git add app/recommendation/coach.tsx services/makeupCoachService.ts types/makeup-coach.ts
git commit -m "feat: add voice coach controls"
```

### Task 4: Runtime Verification

**Files:**
- No required source changes unless verification exposes a defect.

- [ ] **Step 1: Install and download**

Use Chinese mirrors first. If HF mirror download fails, retry with the user-approved `http://127.0.0.1:7890` proxy.

- [ ] **Step 2: Start ASR service**

Start tmux session `mimu_asr_8020` on `0.0.0.0:8020` with the `mimu-voice` environment and `CUDA_VISIBLE_DEVICES=1` unless GPU memory requires another card.

- [ ] **Step 3: Restart backend with ASR enabled**

Set:

```bash
COACH_ASR_BASE_URL=http://127.0.0.1:8020
```

and keep the existing VLM variables pointing at the 32B vLLM server.

- [ ] **Step 4: Smoke test**

Check:

```bash
curl http://127.0.0.1:8020/health
curl http://127.0.0.1:13000/makeup/coach/voice ...
```

Expected: `/health` returns loaded ASR metadata and the backend voice endpoint returns `transcript`, `voiceAction`, and a normal coach response.

- [ ] **Step 5: Roadshow URL**

Confirm `https://10.246.1.70:19443` still opens the frontend and proxies `/api/*` to the backend.
