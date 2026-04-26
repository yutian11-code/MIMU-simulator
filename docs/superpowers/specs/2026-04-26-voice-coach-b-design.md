# Voice Coach B Design

## Goal

B 版把 A 版“点击录音”升级为路演可用的“连续视频通话”体验。用户进入 AI 视频指导后，可以开启通话，摄像头和麦克风持续接入；系统在用户说完一句话后自动截取当前画面和音频片段，调用已经跑通的本地 ASR 和 32B 视觉教练，并用浏览器 TTS 播报结果。

## Scope

This design implements the quasi-realtime version, not a full streaming WebSocket stack.

Included:
- Frontend continuous call mode.
- Browser-side volume/VAD detection for speech start and speech end.
- Automatic turn submission after a silence window.
- Current frame capture per voice turn.
- Browser TTS playback of model guidance.
- Guarded auto-advance when the user says “下一步/继续/可以了” and the VLM says the current step can proceed.
- A-version manual voice button remains as fallback.

Excluded from B:
- Token-level streaming ASR.
- WebSocket audio transport.
- Cloud realtime multimodal API.
- New large model deployment.

## Architecture

Frontend owns the continuous-call state machine. It uses `getUserMedia({ audio: true })`, `AudioContext`, `AnalyserNode`, and `MediaRecorder`. The analyser calculates a simple RMS level on every animation frame. When speech crosses the configured start threshold, the recorder starts; when silence lasts long enough, the recorder stops and sends one turn.

Backend keeps the A-version `/makeup/coach/voice` endpoint and adds optional turn metadata. It still calls the local Python ASR service and then reuses `MakeupCoachService.guide()`. This keeps GPU use unchanged: ASR stays on the 0.6B Qwen ASR service, VLM stays on the 32B local server.

## Data Flow

1. User taps “开始视频通话”.
2. Frontend starts camera preview if needed and opens microphone.
3. VAD enters `listening`.
4. User speaks; VAD enters `hearing`, starts `MediaRecorder`.
5. Silence window expires; recorder stops.
6. Frontend converts audio to WAV data URL and captures current frame.
7. Frontend POSTs `/makeup/coach/voice` with `interactionMode=conversation`, `clientTurnId`, audio, frame, and current step context.
8. Backend transcribes audio, classifies voice intent, calls the VLM coach, and returns transcript plus coach result.
9. Frontend shows transcript/result and speaks `guidance + nextAction`.
10. If voice intent is confirm-step and `shouldProceed=true`, frontend advances after the response is visible.

## Error Handling

Microphone permission errors show a clear HTTPS/browser-permission message. ASR or VLM failures keep the call active but show a turn-level error and return to listening. Very short or empty recordings are discarded locally. A cooldown prevents duplicate submissions from one utterance.

## Testing

Backend tests cover metadata passthrough and response echo. Frontend verification uses `npx tsc --noEmit`, `npm run lint`, and a live Metro build through the existing HTTPS gateway. Runtime verification checks ASR `/health`, backend `/health`, HTTPS `/api/health`, and one real `/makeup/coach/voice` request.
