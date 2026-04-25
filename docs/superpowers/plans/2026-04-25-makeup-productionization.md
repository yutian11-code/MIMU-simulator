# Makeup Productionization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the five remaining core tasks for a stable internal MIMU demo.

**Architecture:** Keep the existing synchronous `/makeup` API compatible, route makeup generation through an in-memory single-GPU queue, add async job endpoints for the frontend, expand deterministic regression data, and document reproducibility/privacy rules.

**Tech Stack:** NestJS, TypeScript, Expo React Native Web, Python/Pillow evaluation scripts, git patch files.

---

### Task 1: Backend Makeup Queue

**Files:**
- Create: `backend/src/makeup/dto/makeup-job-response.dto.ts`
- Create: `backend/src/makeup/makeup-job.service.ts`
- Modify: `backend/src/makeup/makeup.service.ts`
- Modify: `backend/src/makeup/makeup.controller.ts`
- Modify: `backend/src/makeup/makeup.module.ts`
- Modify: `backend/src/makeup/dto/makeup-response.dto.ts`
- Modify: `backend/.env.example`
- Modify: `backend/README.md`
- Test: `backend/src/makeup/makeup-job.service.spec.ts`

- [ ] Write tests for queued, running, completed, failed, retry, and cleanup behavior.
- [ ] Implement the in-memory queue service with one active worker by default.
- [ ] Split direct ComfyUI generation into a raw generation method used by the queue.
- [ ] Add async job endpoints and keep synchronous `/makeup` by waiting for a queued job.
- [ ] Run backend build, unit tests, and e2e tests.
- [ ] Commit backend changes.

### Task 2: Frontend Async Try-On

**Files:**
- Modify: `frontend/types/virtual-try-on.ts`
- Modify: `frontend/services/virtualTryOnService.ts`
- Modify: `frontend/components/recommendation/makeup-try-on-panel.tsx`
- Modify: `frontend/docs/virtual-try-on-api.md`
- Test: TypeScript and lint checks

- [ ] Add job status types and async service methods.
- [ ] Update the try-on panel to enqueue jobs and poll status.
- [ ] Show queued/running/retrying/progress/failure states.
- [ ] Run frontend type check and lint.
- [ ] Commit frontend changes.

### Task 3: Expanded Evaluation Set

**Files:**
- Modify: `eval/makeup/scripts/mimu_eval/assets.py`
- Modify: `eval/makeup/scripts/prepare_seed_assets.py`
- Modify: `eval/makeup/tests/test_assets.py`
- Create: `eval/makeup/manifests/regression_90.jsonl`
- Modify: `eval/makeup/README.md`

- [ ] Extend deterministic asset variant generation to 30 user variants and 3 template variants.
- [ ] Generate `regression_90.jsonl`.
- [ ] Update tests to verify the 90-case manifest.
- [ ] Run evaluation unit tests and a 90-case pipeline run.
- [ ] Commit evaluation changes.

### Task 4: Stable Makeup Patch Reproducibility

**Files:**
- Create: `patches/stable-makeup/README.md`
- Create: `patches/stable-makeup/0001-diffusers-controlnet-import.patch`
- Modify: `docs/team-runbook.md`

- [ ] Export the current Stable Makeup compatibility commit as a patch.
- [ ] Document how to apply and verify the patch.
- [ ] Commit reproducibility docs.

### Task 5: Privacy And Internal Test Documentation

**Files:**
- Create: `docs/internal-test-and-privacy.md`
- Modify: `docs/team-runbook.md`

- [ ] Document allowed image sources for internal testing.
- [ ] Document cleanup rules for uploads, outputs, and eval artifacts.
- [ ] Document that external VLM/LLM use requires explicit approval for face images.
- [ ] Commit documentation.

### Task 6: Final Verification

**Commands:**
- `cd backend && npm run build && npm run test && npm run test:e2e`
- `cd frontend && npx tsc --noEmit && npm run lint`
- `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest discover -s eval/makeup/tests -v`
- backend, frontend, and ComfyUI health checks
- synchronous `/makeup` smoke
- async `/makeup/jobs` smoke

- [ ] Run all verification commands fresh.
- [ ] Confirm git status for top-level, backend, frontend, and stable-makeup.
- [ ] Report completed commits, verification evidence, and remaining product risks.
