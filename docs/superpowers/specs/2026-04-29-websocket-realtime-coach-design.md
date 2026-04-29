# C 版 WebSocket Realtime Coach Design

## Goal

C 版在现有 A 版“语音问 AI”和 B 版“连续视频通话”之外，新增一个“实时通话实验版”入口。前端在通话期间持续推送 200-300ms 的音频 chunk，后端通过 WebSocket 维护 session、turn 和状态事件，并在服务端完成 VAD/分句后再调用现有 Qwen3-ASR 与 Qwen-VL 教练链路。

## Non-goals

- 不替换 A/B 版入口。A/B 仍作为路演兜底。
- 不做每帧 VLM 推理。VLM 只在一句话结束后调用，避免 32B 模型被音视频流打爆。
- 不做真正流式 TTS。C 版继续使用浏览器 `speechSynthesis` 播报完整回复。
- 不新增模型下载。C 版复用已部署的 Qwen3-ASR 与 32B VLM 服务。

## Architecture

后端新增 raw WebSocket 入口 `/makeup/coach/realtime`。HTTPS LAN gateway 已支持 `/api/*` upgrade 转发，因此浏览器可通过 `wss://<host>/api/makeup/coach/realtime` 访问，后端实际收到 `/makeup/coach/realtime`。

后端 session 服务负责：

- 保存 session context：当前步骤、已完成步骤、总步骤数、最近一帧图片。
- 接收 `audio_chunk`：PCM16 mono base64、sampleRate、durationMs。
- 基于 RMS 做 server-side VAD：静音保持 listening，超过阈值进入 speech_started，检测到足够静音后结束一句话。
- 将缓冲的 PCM16 包装为 WAV data URL。
- 复用 `MakeupVoiceService.guideWithVoice()` 调用 Qwen3-ASR 与现有 VLM coach。
- 向前端发送状态事件：`session_ready`、`listening`、`speech_started`、`recognizing`、`thinking`、`coach_result`、`error`、`stopped`。

前端新增“实时通话实验版”开关。开启后：

- 使用 `AudioContext` 采集麦克风，使用 ScriptProcessor 按约 250ms 聚合 PCM16 mono chunk。
- WebSocket 连接同源 HTTPS gateway 或本地 backend。
- `start` 消息发送当前步骤上下文；`frame` 消息按约 1s 发送当前摄像头画面或上传画面；`audio_chunk` 持续发送音频。
- 收到状态事件后显示“正在听 / 正在识别 / AI 判断中 / AI 回复中”。
- 收到 `coach_result` 后复用现有结果卡、语音转写、自动进入下一步逻辑和浏览器 TTS。

## Client Message Contract

```json
{ "type": "start", "payload": { "scenario": "通勤淡妆", "stepTitle": "底妆", "stepInstruction": "...", "completedStepTitles": [], "totalSteps": 4, "imageDataUrl": "data:image/jpeg;base64,..." } }
{ "type": "frame", "payload": { "imageDataUrl": "data:image/jpeg;base64,..." } }
{ "type": "audio_chunk", "payload": { "pcm16Base64": "...", "sampleRate": 16000, "durationMs": 250 } }
{ "type": "stop" }
```

## Server Event Contract

```json
{ "type": "session_ready", "sessionId": "rt-...", "status": "listening" }
{ "type": "listening", "sessionId": "rt-...", "status": "listening" }
{ "type": "speech_started", "sessionId": "rt-...", "turnId": "rt-...-turn-1", "status": "listening" }
{ "type": "recognizing", "sessionId": "rt-...", "turnId": "rt-...-turn-1", "status": "recognizing" }
{ "type": "thinking", "sessionId": "rt-...", "turnId": "rt-...-turn-1", "status": "thinking" }
{ "type": "coach_result", "sessionId": "rt-...", "turnId": "rt-...-turn-1", "status": "replying", "payload": { "...": "MakeupCoachVoiceResponseDto" } }
{ "type": "error", "sessionId": "rt-...", "message": "..." }
{ "type": "stopped", "sessionId": "rt-...", "status": "stopped" }
```

## Error Handling

- WebSocket 收到非法 JSON 或未知消息类型时返回 `error`，不断开可恢复连接。
- `start` 缺少步骤上下文时返回 `error` 并拒绝处理音频。
- 音频过短或只有噪声时丢弃该 turn 并回到 `listening`。
- ASR/VLM 失败时发送 `error`，session 保持可继续监听。
- 前端连接断开或用户关闭实验版时停止麦克风、关闭音频节点、取消浏览器 TTS。

## Testing

- 后端单测覆盖 RMS/VAD、静音不触发、语音结束触发 coach、WAV data URL 生成和错误恢复。
- 后端 build 和 e2e 保持通过。
- 前端 TypeScript 与 lint 保持通过。
- 使用 Node WebSocket smoke test 连接后端与 HTTPS gateway，验证 session_ready/listening/error 或合成音频事件流。
