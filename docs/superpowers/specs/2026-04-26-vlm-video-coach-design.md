# VLM Video Coach Design

## Goal

Build a roadshow-ready AI video guidance flow from the existing execution page. The first version must run without a paid API key, then switch to DashScope `qwen-vl-plus-latest` or `qwen-vl-max-latest` by changing environment variables.

## Model Strategy

Download two local fallback models:

- `Qwen/Qwen2.5-VL-32B-Instruct-AWQ`
- `Qwen/Qwen2.5-VL-72B-Instruct-AWQ`

The 32B model is the first smoke-test target because it is faster and easier to serve. The 72B AWQ model is the higher-quality local target for the 4x4090 48G machine. Hosted DashScope remains the recommended roadshow quality path once a key is available.

## Backend Design

Add a makeup coach endpoint under the existing makeup domain:

- `POST /makeup/coach`
- Request includes scenario, current step, completed steps, optional user question, and optional captured camera frame as a data URL.
- Response includes provider, model, guidance text, next action, risk reminder, and whether the result is fallback guidance.

The service uses OpenAI-compatible chat completions:

- Local vLLM: `COACH_LLM_BASE_URL=http://127.0.0.1:8010/v1`, `COACH_LLM_API_KEY=EMPTY`
- DashScope: `COACH_LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1`, `COACH_LLM_API_KEY=<key>`

If no key/base URL is configured, or if the model call fails, the backend returns deterministic fallback guidance so the demo flow never breaks.

## Frontend Design

The execution page keeps the existing checklist flow and adds an `AI 视频指导` entry. The new page presents a call-like coaching interface:

- Shows current scenario, current step, and completed-step count.
- On web, opens browser camera with `navigator.mediaDevices.getUserMedia`.
- Captures a single frame when the user asks for guidance.
- If camera permission fails, the user can still ask a text-only question.
- Sends the captured frame and step context to `POST /makeup/coach`.

This is intentionally not continuous WebRTC. For the roadshow, frame-by-frame VLM guidance is more reliable, cheaper, and easier to run locally.

## Error Handling

- Missing execution context redirects the user back to the execution page.
- Camera errors are shown as recoverable UI state.
- Backend model errors degrade to fallback guidance.
- Oversized images are avoided by capturing a compressed 512px JPEG frame.

## Testing

- Backend unit tests cover fallback guidance and OpenAI-compatible payload construction.
- Frontend TypeScript and lint verify service/page integration.
- Manual smoke test checks execution page -> AI video guide -> text guidance, and camera permission fallback.
