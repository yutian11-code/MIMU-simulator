# WebSocket Realtime Coach Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build C 版 WebSocket Realtime Coach while keeping A/B voice coach paths intact.

**Architecture:** Add a backend raw WebSocket server mounted at `/makeup/coach/realtime`, backed by a focused realtime session service that performs server-side RMS VAD and calls the existing voice coach only after utterance end. Add a frontend experimental realtime mode that sends PCM16 mono chunks every 250ms and renders backend state events.

**Tech Stack:** NestJS, raw `ws`, Jest, React Native Web/Expo, Web Audio API, browser `speechSynthesis`.

---

## File Map

- `backend/src/makeup/makeup-realtime-session.service.ts`: pure-ish session state, VAD, PCM/WAV packaging, coach invocation, event emission.
- `backend/src/makeup/makeup-realtime-session.service.spec.ts`: tests for silence, speech start, utterance completion, coach result, and malformed audio.
- `backend/src/makeup/makeup-realtime.gateway.ts`: raw WebSocket server attachment and JSON message routing.
- `backend/src/makeup/makeup.module.ts`: register realtime providers.
- `backend/src/main.ts`: attach the realtime gateway after Nest app starts.
- `backend/src/makeup/dto/makeup-coach.dto.ts`: allow `interactionMode: "realtime"`.
- `frontend/services/makeupCoachRealtimeService.ts`: build WebSocket URL and define realtime message helpers.
- `frontend/types/makeup-coach.ts`: add realtime mode and event types.
- `frontend/app/recommendation/coach.tsx`: add experimental realtime switch, audio chunk streaming, event handling, and cleanup.

## Tasks

### Task 1: Backend Realtime Session Core

- [ ] Write `makeup-realtime-session.service.spec.ts` covering:
  - silence chunks emit no speech turn and keep listening;
  - speech chunks emit `speech_started`;
  - speech followed by enough silence emits `recognizing`, `thinking`, and `coach_result`;
  - generated WAV data URL is `audio/wav`;
  - short speech is dropped and returns to listening.
- [ ] Run the spec and confirm it fails because the service does not exist.
- [ ] Implement `makeup-realtime-session.service.ts` with `createSession()`, `start()`, `updateFrame()`, `receiveAudioChunk()`, `stop()`, and deterministic thresholds.
- [ ] Run the new spec until it passes.

### Task 2: Backend WebSocket Gateway

- [ ] Install `ws` and `@types/ws` through npm using a China registry mirror when needed.
- [ ] Write a gateway test or smoke-friendly implementation boundary for JSON parsing and routing.
- [ ] Implement `makeup-realtime.gateway.ts` with `attach(server)` and path guard `/makeup/coach/realtime`.
- [ ] Register providers in `makeup.module.ts`.
- [ ] Attach the gateway from `main.ts` using `app.get(MakeupRealtimeGateway).attach(app.getHttpServer())`.
- [ ] Extend `MakeupCoachInteractionMode` to include `realtime`.
- [ ] Run backend unit tests and build.

### Task 3: Frontend Realtime Client

- [ ] Add `makeupCoachRealtimeService.ts` to resolve `ws://` or `wss://` from the active API base URL.
- [ ] Extend `types/makeup-coach.ts` with realtime event/message types and `interactionMode: "realtime"`.
- [ ] Update `coach.tsx` with separate C 版 state, refs, and cleanup so A/B state remains independent.
- [ ] Add an “实时通话实验版” switch/entry in the existing video call panel.
- [ ] Implement Web Audio chunking: Float32 to PCM16 mono, aggregate roughly 250ms, send `audio_chunk`.
- [ ] Send `start`, periodic `frame`, and `stop` messages.
- [ ] Map backend events to user-visible statuses and reuse existing result/TTS/auto-step behavior on `coach_result`.
- [ ] Run frontend TypeScript and lint.

### Task 4: Integration Verification

- [ ] Restart backend on `0.0.0.0:13000` and frontend on `0.0.0.0:19006` if watch processes do not pick up changes.
- [ ] Confirm `http://127.0.0.1:13000/health`.
- [ ] Confirm `https://127.0.0.1:19443/api/health` through HTTPS gateway.
- [ ] Run a Node WebSocket smoke test against `ws://127.0.0.1:13000/makeup/coach/realtime`.
- [ ] Run a Node WebSocket smoke test against `wss://127.0.0.1:19443/api/makeup/coach/realtime` with `rejectUnauthorized: false`.
- [ ] Commit backend and frontend separately.
