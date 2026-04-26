# VLM Video Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a roadshow-ready AI video guidance flow backed by OpenAI-compatible VLM calls and local Qwen-VL model downloads.

**Architecture:** Keep model inference behind the backend so the frontend never needs provider keys. Use a best-effort VLM call with deterministic fallback. Implement the frontend as a camera-frame coaching flow rather than continuous WebRTC.

**Tech Stack:** NestJS, Axios, Expo React Native Web, browser `mediaDevices`, OpenAI-compatible chat completions, Hugging Face mirror downloads.

---

### Task 1: Model Download Script

**Files:**
- Modify: `/storage/nvme3/shushanfu/checkpoint/down_load.py`

- [ ] Configure the script to download `Qwen/Qwen2.5-VL-32B-Instruct-AWQ` and `Qwen/Qwen2.5-VL-72B-Instruct-AWQ` into `/storage/nvme3/shushanfu/checkpoint/huggingface`.
- [ ] Run with `HF_ENDPOINT=https://hf-mirror.com`.
- [ ] If mirror connection fails, retry with `HTTP_PROXY=http://127.0.0.1:7890 HTTPS_PROXY=http://127.0.0.1:7890`.
- [ ] Verify both model directories contain `config.json`, tokenizer files, and safetensors shards.

### Task 2: Backend Coach Service

**Files:**
- Create: `backend/src/makeup/dto/makeup-coach.dto.ts`
- Create: `backend/src/makeup/makeup-coach.service.ts`
- Create: `backend/src/makeup/makeup-coach.service.spec.ts`
- Modify: `backend/src/makeup/makeup.controller.ts`
- Modify: `backend/src/makeup/makeup.module.ts`

- [ ] Write a failing unit test for no-key fallback response.
- [ ] Write a failing unit test for the OpenAI-compatible request body with text plus optional image data URL.
- [ ] Implement DTOs and service methods.
- [ ] Add `POST /makeup/coach` controller route.
- [ ] Run `npm test -- makeup-coach.service.spec.ts`.
- [ ] Run `npm run build`.
- [ ] Commit backend changes.

### Task 3: Frontend Coach Service

**Files:**
- Create: `frontend/types/makeup-coach.ts`
- Create: `frontend/services/makeupCoachService.ts`
- Modify: `frontend/types/index.ts`

- [ ] Add typed request/response models matching backend DTOs.
- [ ] Add `requestCoachGuidance()` using the shared API client.
- [ ] Run `npx tsc --noEmit`.

### Task 4: Frontend Video Coach Screen

**Files:**
- Create: `frontend/app/recommendation/coach.tsx`
- Modify: `frontend/app/recommendation/execution.tsx`

- [ ] Add an `AI 视频指导` action on execution page.
- [ ] Build the coach screen around current execution draft and recommendation steps.
- [ ] On web, start camera preview with `navigator.mediaDevices.getUserMedia`.
- [ ] Capture a compressed frame to a canvas and submit it with current-step context.
- [ ] Provide text-only guidance fallback if camera permission fails.
- [ ] Run `npx tsc --noEmit` and `npm run lint`.
- [ ] Commit frontend changes.

### Task 5: Runtime Wiring

**Files:**
- Modify or create: `backend/.env.example`
- Modify or create: `docs/team-runbook.md`

- [ ] Document local vLLM env variables.
- [ ] Document DashScope env variables.
- [ ] Document sample vLLM serve commands for 32B and 72B AWQ.
- [ ] Restart backend and frontend services.
- [ ] Smoke test `/makeup/coach` with fallback mode.
- [ ] Commit documentation changes.
