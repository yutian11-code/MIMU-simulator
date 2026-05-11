# MMU Makeup Template Platform Design

## Source Of Truth

This platform design follows the approved **Option C: platform-level build**.

When product documents differ, `docs/MMU模板库标准构建(1).docx` is the
source of truth. `docs/妆容生成搭建模板.docx` is used as supporting context for
the generated-result library and the user-facing makeup generation flow.

The user-facing demo flow remains five executable steps for now. The data
foundation must still preserve MMU's full standard taxonomy and map every
five-step execution block back to MMU standard step codes, so a future
fourteen-step execution mode can be added without rebuilding the platform.

## Product Goal

Build a formal makeup-template platform, not a one-off recommendation feature.
The platform should support:

1. A database-backed MMU standard template library.
2. Model-backed template matching with mandatory embedding and rerank services.
3. User-specific generated makeup results that preserve why and how they were
   generated.
4. Makeup preview tied to the selected template and product slots.
5. AI execution coaching that can detect step completion and move forward.
6. A frontend experience where product, frontend, backend, and model teammates
   can test the full path without guessing hidden state.
7. Evaluation datasets and smoke scripts that prove the platform still works
   after code or model changes.
8. Traceable logs across recommendation, template matching, preview, voice, and
   realtime coaching.

## Non-Goals For This Platform Slice

The platform must be formal, but this slice still avoids unnecessary expansion:

1. No multi-person approval workflow. Review fields are reserved, but publishing
   is allowed by default.
2. No training or fine-tuning new models.
3. No 14-step user-facing execution screen yet.
4. No raw face, audio, video, or ComfyUI output persistence in Git.
5. No external VLM/LLM calls with real user faces unless explicitly configured
   and approved.
6. No GPU scheduler inside NestJS. Backends consume configured service URLs;
   scripts and runbooks own GPU placement.
7. No full BI dashboard. This slice stores enough data and exposes enough traces
   for a future dashboard.

## Platform Architecture

The platform has six bounded domains.

### 1. Model Service Platform

This domain owns model service configuration, availability checks, and runtime
observability for:

- template embedding service.
- template reranker service.
- reference-image VLM service.
- ASR service.
- makeup preview service through ComfyUI or an equivalent Stable Makeup
  workflow.
- AI coach VLM/LLM service.

The backend must expose a health summary that distinguishes:

- configured and healthy.
- configured but unhealthy.
- missing configuration.
- timed out.
- model response invalid.

Template matching must fail clearly if embedding or rerank is unavailable.
Reference-image matching must fail clearly if the user supplied a reference image
and VLM parsing fails. ASR, preview, and coach failures should return explicit
errors or scripted test responses only when the route is documented as a local
test route.

### 2. MMU Standard Template Library

This is the editable source library. It contains:

- style families.
- standard template identities.
- immutable version snapshots.
- step blocks.
- product slot specifications.
- operation areas.
- face-shape rules.
- difficulty rules.
- taxonomy entries and aliases.

Templates are stored in PostgreSQL, not hard-coded as the primary source.
Seed data can still live in code for initialization, but runtime matching reads
published database template versions first.

The library supports:

- create template.
- edit draft.
- publish.
- archive.
- rollback by copying an old version into a new published version.
- reserved review state with default `not_required`.

### 3. Personalized Generated Result Library

This domain stores what the user actually receives. It is separate from the
standard template library.

For every generation, persist:

- original user input.
- normalized intent.
- user profile snapshot.
- user product snapshot.
- selected standard template and version.
- model match trace.
- generated five-step execution template.
- product slot matches, substitutions, and missing products.
- personalization reasons.
- preview job linkage when preview is generated.
- execution events.
- step completion, skip, failure, product replacement, user edits, and
  satisfaction feedback.

This data makes future personalization possible. The product direction is a
generated-result library, not a large static template catalog.

### 4. Matching And Evaluation Platform

The official generated path is:

```text
user input + user profile + owned products + optional reference image
-> intent normalization
-> optional VLM reference-image feature extraction
-> embedding recall
-> rerank
-> MMU constraints and difficulty scoring
-> product-slot matching
-> generated five-step executable template
-> trace and event persistence
```

Embedding and rerank are mandatory. Rule matching may help explain and constrain
results, but it must not silently replace the model path.

Add a dedicated `eval/template-matching/` suite that contains:

- eight MMU family coverage cases.
- with-reference-image and no-reference-image variants.
- user profile fixtures.
- owned product fixtures.
- expected selected template IDs.
- expected broad score ranges.
- expected missing product categories.
- regression output with pass/fail, top candidates, model status, and trace ID.

### 5. Frontend Product Experience

The frontend must expose a complete usable experience:

- template library management.
- template create/edit/publish/rollback.
- generate today's makeup.
- upload optional reference image.
- result page with model evidence and trace ID.
- product checklist with slot status.
- makeup preview with user selfie and template-model preview.
- before/after split and slider comparison.
- execution page with five steps mapped to MMU step codes.
- AI coach and realtime coach entry.
- image-upload test route for step-recognition when camera is unavailable.
- history page for generated user templates.

Frontend error states must be explicit. Empty pages and invisible controls are
not acceptable failure modes. When a required model service is unavailable, the
screen should name the missing service and show the trace ID if one exists.

### 6. AI Execution Loop

Execution uses the five-step demo flow:

1. prep/base.
2. brow.
3. eye.
4. cheek/contour.
5. lip/finish.

Each step stores MMU `standardStepCodes`, completion criteria, common failure
types, detection region, and next-step condition.

The coach response must include:

- current step code.
- detected completion level.
- detected mistakes.
- correction instruction.
- whether the user can move to the next step.
- voice text.
- trace ID.

The same backend evaluator should support:

- camera realtime frames.
- uploaded still image test.
- scripted local test audio.
- voice question plus optional image.

This lets teammates prove the chain is connected even when camera permissions,
browser HTTPS, or simulator behavior are blocking realtime testing.

## Data Design

### Standard Library Tables

The existing formal template-library schema remains the foundation. It should be
extended only where the platform needs stronger traceability or management.

Core objects:

- `StandardMakeupStyle`
- `StandardMakeupTemplate`
- `StandardMakeupTemplateVersion`
- `StandardTemplateStepBlock`
- `StandardProductSlotSpec`
- `TemplateProductCategory`
- `TemplateOperationArea`
- `TemplateFaceShape`
- `TemplateDifficultyRule`

Required template version payload:

- display name.
- style family.
- scene tags.
- effect tags.
- visual description.
- five execution blocks.
- MMU standard step-code mapping.
- product slot requirements.
- operation areas.
- face-shape fit rules.
- difficulty configuration.
- publishing metadata.

### Generated Result Tables

Generated result records should preserve:

- `MakeupGenerationRequest`
- `UserConditionSnapshot`
- `UserProductSnapshot`
- `GeneratedMakeupTemplate`
- `GeneratedTemplateStep`
- `TemplateProductSlot`
- `TemplateMatchTrace`
- `TemplateEvent`

Existing recommendation rows remain as compatibility projections for current
frontend pages, but the generated template is the richer source object.

### Trace And Event Data

Every major flow should have a trace ID:

- `mtrace_...` for template matching.
- `preview_...` for makeup preview jobs.
- `coach_...` for video or image coaching.
- `voice_...` for ASR plus coach.
- `exec_...` for execution sessions.

Trace records store metadata, structured model responses, score breakdowns, and
failure reasons. They do not store raw private images, raw audio, or raw video.

Events should include:

- generated.
- template edited.
- template published.
- template rolled back.
- preview requested.
- preview completed.
- step started.
- step completed.
- step auto-advanced.
- step correction suggested.
- product replaced.
- step skipped.
- feedback submitted.

## Backend API Design

### Model Health

Add a platform health endpoint:

```text
GET /platform/health
```

It returns backend health plus configured model service status:

```json
{
  "backend": "ok",
  "database": "ok",
  "models": {
    "templateEmbedding": {
      "configured": true,
      "healthy": true,
      "baseUrl": "http://127.0.0.1:8030/v1",
      "model": "Qwen3-Embedding-4B",
      "latencyMs": 24
    },
    "templateReranker": {
      "configured": true,
      "healthy": true,
      "baseUrl": "http://127.0.0.1:8031/v1",
      "model": "Qwen3-Reranker-8B",
      "latencyMs": 31
    }
  }
}
```

### Template Library

Keep and complete:

```text
GET  /makeup-template-library/taxonomy
GET  /makeup-template-library/templates
POST /makeup-template-library/templates
GET  /makeup-template-library/templates/:templateId
PUT  /makeup-template-library/templates/:templateId/draft
POST /makeup-template-library/templates/:templateId/publish
POST /makeup-template-library/templates/:templateId/archive
POST /makeup-template-library/templates/:templateId/rollback
GET  /makeup-template-library/templates/:templateId/versions
POST /makeup-template-library/seed
POST /makeup-template-library/match-debug
```

`match-debug` is for authenticated internal testing. It must return candidates,
score breakdown, model status, selected template, and trace ID.

### Generation And Recommendation

The user-facing path remains:

```text
POST /recommendations/generate
```

It should internally create or reuse generated-template records, then return the
existing recommendation response enriched with:

- generated template ID.
- source standard template ID.
- source version ID.
- template trace ID.
- model status.
- score breakdown.
- product coverage.
- missing products.
- standard step codes.
- generated reasons.

Add direct generated-result endpoints for management and history:

```text
GET  /makeup-templates/generated
GET  /makeup-templates/generated/:templateId
POST /makeup-templates/generated/:templateId/events
POST /makeup-templates/generated/:templateId/feedback
```

### Makeup Preview

Complete the preview path:

```text
POST /makeup/jobs
GET  /makeup/jobs/:jobId
GET  /makeup/result
```

Preview requests should carry:

- generated template ID.
- selected standard template version ID.
- selfie image.
- optional template model image.
- selected product slot metadata.
- comparison mode.

Response should support:

- user generated preview.
- template-model preview.
- before image URL.
- after image URL.
- trace ID.
- job status and error reason.

### AI Coach

Complete and standardize:

```text
POST /makeup/coach
POST /makeup/coach/voice
POST /makeup/coach/step-evaluate
WebSocket /makeup/coach/realtime
```

`step-evaluate` is the still-image test route. It accepts a generated template
ID, step ID or step code, and image data URL. It returns the same completion
schema as realtime coaching.

## Frontend Design

### Template Management

The management page should let an authenticated teammate:

- seed initial MMU templates.
- search and filter templates.
- open detail.
- edit core metadata.
- edit five step blocks.
- edit MMU standard step-code mappings.
- edit product slots.
- edit difficulty and operation areas.
- save draft.
- publish.
- view version history.
- rollback.

Fields should be form controls, not JSON textareas, for the common path. Advanced
raw payload viewing can be read-only at first.

### Recommendation Flow

The user journey is:

```text
home -> generate today's makeup -> scenario/profile/reference image
-> loading -> result -> product checklist -> preview or execution
```

Result page must show:

- selected template name and family.
- standard template ID.
- generated template ID.
- trace ID with copy action.
- model status.
- score breakdown.
- five steps.
- MMU standard step codes.
- product coverage.
- missing products.
- personalization reasons.

### Preview Flow

The preview screen must support:

- upload selfie.
- generate preview from selected template.
- view template model preview when available.
- before/after split comparison.
- slider comparison.
- retry when preview service fails.
- trace ID display.

The first formal version may use product-slot metadata rather than exact product
image/color extraction. The API shape should preserve room for future real
product images, shade IDs, and finish values.

### Execution And Coach Flow

Execution page must show:

- current step.
- completion criteria.
- common mistakes.
- correction tips.
- linked product slots.
- AI detection area.
- manual next and skip.
- auto-next when coach returns completion.

Coach page must support:

- camera realtime path.
- still-image upload test path.
- voice test path.
- text question path.

This avoids blocking demonstrations on camera or microphone permissions.

## Model Service And GPU Policy

All GPUs can be used when the machine is dedicated to this work, but services
must use resource-appropriate placement:

- embedding and rerank should use the smallest viable GPU footprint or CPU if
  latency is acceptable.
- VLM, ComfyUI, and realtime coach can use high-memory GPUs.
- ASR should run in the existing conda-managed voice environment.
- scripts must document `CUDA_VISIBLE_DEVICES`, port, model path, and log path.

Required model configuration:

```env
TEMPLATE_EMBEDDING_BASE_URL=
TEMPLATE_EMBEDDING_MODEL=
TEMPLATE_RERANKER_BASE_URL=
TEMPLATE_RERANKER_MODEL=
TEMPLATE_VLM_BASE_URL=
TEMPLATE_VLM_MODEL=
COACH_LLM_BASE_URL=
COACH_LLM_MODEL=
COACH_ASR_BASE_URL=
COMFY_UI_BASE_URL=
```

Startup scripts should write logs under `var/logs/` and avoid committing logs.

## Evaluation Design

Add:

```text
eval/template-matching/
  cases/
  fixtures/
  scripts/
  reports/
```

Case schema:

```json
{
  "caseId": "tm_elegant_interview_001",
  "name": "Interview elegant makeup",
  "input": "面试需要轻熟知性优雅妆，不要太浓",
  "profile": {
    "skinType": "combination",
    "faceShape": "oval",
    "skillLevel": "normal"
  },
  "ownedProducts": [
    {
      "category": "base",
      "subCategory": "foundation",
      "finish": "natural"
    }
  ],
  "referenceImage": null,
  "expected": {
    "templateId": "std_elegant_luxury",
    "family": "ELEGANT_LUXURY",
    "requiredStepCodes": ["SKIN_PREP", "FOUNDATION", "BROW", "LIP"]
  }
}
```

Evaluation output:

- overall pass rate.
- per-family pass rate.
- selected template.
- expected template.
- top candidates.
- model status.
- trace ID.
- failure reason.
- generated HTML or Markdown report.

## Logging And Observability

Backend logs should be structured and include:

- trace ID.
- user ID when safe.
- route.
- template ID.
- generated template ID.
- model name.
- model latency.
- error code.
- failure reason.

Frontend should show and copy trace IDs for:

- recommendation generation.
- preview.
- coach.
- voice.

The runbook should document how to search logs by trace ID.

## Privacy Rules

The platform handles face images and voice data as sensitive data.

Rules:

- Do not commit uploaded selfies, generated face outputs, audio, video, logs, or
  evaluation runs.
- Store structured model features and IDs, not raw images or audio.
- Keep generated test assets under ignored output directories unless they are
  approved synthetic fixtures.
- Avoid sending real user faces to external services by default.
- Redact large base64 payloads from logs.

## Testing Strategy

Backend verification:

- unit tests for model health client.
- unit tests for mandatory embedding/rerank failures.
- unit tests for VLM reference image parsing.
- unit tests for template version publish and rollback.
- unit tests for generated-result event persistence.
- unit tests for coach step-evaluate completion schema.
- e2e tests for seed -> generate -> evidence -> event persistence.

Frontend verification:

- TypeScript check.
- lint.
- route smoke for template management, result, preview, execution, and coach.
- component tests where the project test setup supports them.
- manual LAN smoke using HTTPS gateway for camera/microphone path.

Evaluation verification:

- `eval/template-matching` mock service mode for CI-like local smoke.
- real model mode for server acceptance.
- report checked into ignored run output, not Git.

## Acceptance Criteria

The platform slice is acceptable when all of the following are true:

1. Standard MMU templates can be seeded into PostgreSQL.
2. A teammate can edit, publish, and rollback a template from the frontend.
3. Recommendation generation reads published DB templates.
4. Embedding and rerank are required for authenticated generated matching.
5. Model unavailability produces explicit backend and frontend errors.
6. Generated recommendations include model evidence, trace ID, MMU step codes,
   product slots, missing products, and personalization reasons.
7. Generated result records persist user input, snapshots, template provenance,
   slot matching, events, and feedback.
8. Makeup preview can run from a selected generated template and display
   before/after comparison.
9. Template-model preview is supported when template model media is present.
10. AI coach can evaluate a still image for a selected step and return
    completion, errors, correction, voice text, and auto-next decision.
11. Realtime coach uses the same completion schema as still-image evaluation.
12. `eval/template-matching` can run at least one case per MMU family.
13. Logs and frontend screens expose trace IDs for recommendation, preview, and
    coach flows.
14. Backend build, backend tests, backend e2e tests, frontend typecheck, and
    frontend lint pass before pushing implementation.

## Implementation Decomposition

Because this is a platform-level build, implementation should be split into
separate commits and preferably separate worker tasks:

1. Model health and observability foundation.
2. Standard template library completion.
3. Generated-result persistence and event closure.
4. Model-backed matching evaluation suite.
5. Frontend template management completion.
6. Frontend recommendation evidence and generated history.
7. Makeup preview binding and comparison UI.
8. Coach step-evaluate and auto-next loop.
9. Runbook, smoke scripts, and acceptance documentation.

Each task should include focused tests before production code and should avoid
rewriting unrelated modules.
