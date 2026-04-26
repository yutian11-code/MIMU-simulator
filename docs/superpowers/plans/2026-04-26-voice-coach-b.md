# Voice Coach B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade A-version tap-to-talk into a roadshow-ready continuous voice/video coach mode.

**Architecture:** The frontend owns continuous-call behavior with browser VAD, `MediaRecorder`, current-frame capture, and TTS playback. The backend keeps the existing ASR/VLM pipeline and adds optional turn metadata so the frontend can correlate conversation turns without introducing WebSockets.

**Tech Stack:** Expo React Native Web, MediaRecorder, AudioContext/AnalyserNode, browser speech synthesis, NestJS, Jest, Qwen3-ASR-0.6B FastAPI service, local Qwen2.5-VL-32B vLLM.

---

### Task 1: Backend Voice Turn Metadata

**Files:**
- Modify: `backend/src/makeup/dto/makeup-coach.dto.ts`
- Modify: `backend/src/makeup/makeup-voice.service.ts`
- Modify: `backend/src/makeup/makeup-voice.service.spec.ts`

- [ ] **Step 1: Write failing Jest test**

Add a test that sends `interactionMode: 'conversation'` and `clientTurnId: 'turn-001'` to `MakeupVoiceService.guideWithVoice()`. Verify the returned object includes `interactionMode`, `clientTurnId`, and non-empty `turnStartedAt` / `turnCompletedAt`.

- [ ] **Step 2: Run red test**

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
npm test -- makeup-voice.service.spec.ts --runInBand
```

Expected: FAIL because metadata fields are not returned yet.

- [ ] **Step 3: Implement metadata fields**

Add optional `interactionMode?: 'tap' | 'conversation'` and `clientTurnId?: string` to request DTO. Add matching optional response fields plus `turnStartedAt` and `turnCompletedAt`. Populate them in `MakeupVoiceService`.

- [ ] **Step 4: Verify backend**

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
npm test -- makeup-voice.service.spec.ts makeup-coach.service.spec.ts --runInBand
npm run build
```

Expected: PASS.

- [ ] **Step 5: Commit backend**

```bash
git add src/makeup
git commit -m "feat: add voice coach turn metadata"
```

### Task 2: Frontend Continuous Call Mode

**Files:**
- Modify: `frontend/types/makeup-coach.ts`
- Modify: `frontend/app/recommendation/coach.tsx`

- [ ] **Step 1: Add types**

Add `interactionMode`, `clientTurnId`, `turnStartedAt`, and `turnCompletedAt` to voice request/response types.

- [ ] **Step 2: Add call state**

Add `CallState = 'idle' | 'starting' | 'listening' | 'hearing' | 'thinking' | 'speaking' | 'blocked' | 'unsupported'`. Add refs for call stream, analyser, recorder, animation frame, silence timestamp, speech timestamp, and client turn sequence.

- [ ] **Step 3: Start/stop call**

`startConversationCall()` starts camera if needed, opens microphone, creates `AudioContext`, `AnalyserNode`, and enters `listening`. `stopConversationCall()` stops media tracks, cancels animation frame and TTS, clears call state.

- [ ] **Step 4: Browser VAD loop**

Every animation frame, compute RMS. Start a recorder when RMS crosses the speech threshold. Stop it when silence lasts about 950 ms after at least 600 ms of speech. Discard audio shorter than 500 ms.

- [ ] **Step 5: Submit automatic turns**

When a conversation recorder stops, send one `/makeup/coach/voice` request with `interactionMode: 'conversation'`, a generated `clientTurnId`, current frame, current step context, and WAV audio. Show transcript/result and speak response.

- [ ] **Step 6: Guarded auto-advance**

Reuse A-version auto-advance behavior. If the transcript asks to continue but VLM says not ready, keep the call active and show a notice.

- [ ] **Step 7: Verify frontend**

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/frontend
npx tsc --noEmit
npm run lint
```

Expected: PASS.

- [ ] **Step 8: Commit frontend**

```bash
git add app/recommendation/coach.tsx types/makeup-coach.ts
git commit -m "feat: add continuous voice coach mode"
```

### Task 3: Runtime Verification

**Files:**
- Modify docs only if runtime command changes.

- [ ] **Step 1: Restart frontend and backend tmux sessions**

Keep ASR on `mimu_asr_8020` and VLM on `mimu_qwen_vl_32b`. Restart frontend/backend only if hot reload does not pick up changes.

- [ ] **Step 2: Check services**

```bash
curl -fsS http://127.0.0.1:8020/health
curl -fsS http://127.0.0.1:13000/health
curl -k -fsS https://127.0.0.1:19443/api/health
```

Expected: all return healthy JSON.

- [ ] **Step 3: Smoke voice endpoint**

POST a generated WAV data URL to `/makeup/coach/voice` with `interactionMode=conversation` and verify the response includes transcript, voiceAction, clientTurnId, and turn timestamps.

- [ ] **Step 4: Manual browser test**

Open `https://10.246.1.70:19443`, enter AI 视频指导, click “开始视频通话”, speak a short instruction, and verify the UI automatically shows the transcript and speaks the model response.
