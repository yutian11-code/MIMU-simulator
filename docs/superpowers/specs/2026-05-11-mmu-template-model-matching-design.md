# MMU Template Model Matching Design

## Decision

This phase follows `docs/MMU模板库标准构建(1).docx` as the source of truth when it conflicts with `docs/妆容生成搭建模板.docx`.

The user-facing execution flow remains 5 steps for now. The backend standard library must still preserve MMU's full standard taxonomy and map each 5-step execution block back to MMU standard step codes, so a future 14-step execution mode can be introduced without changing the data foundation.

The selected approach is a model-backed matching pipeline:

```text
user text + user profile + owned products + optional reference image
-> reference image VLM feature extraction, only when an image is provided
-> embedding recall
-> reranker ranking
-> MMU rule constraints and explanations
-> 5-step executable makeup template
```

Embedding and reranker services are mandatory. The backend must not silently fall back to pure rules when either service is unavailable.

## Scope

In scope:

- Complete the MMU standard taxonomy used by template matching:
  - 8 normalized makeup style families.
  - 9 product standard categories with subcategories, texture tags, function tags, shade tags, aliases, and sort order.
  - 9 face operation areas.
  - 6 standard face shapes.
  - MMU difficulty rule components.
- Keep user-facing templates at 5 execution steps.
- Ensure every 5-step block carries `standardStepCodes` mapping to MMU's 14 standard makeup steps.
- Make embedding and reranker services required for template matching.
- Add reference image parsing through the local VLM service.
- Add face shape, difficulty, product coverage, historical preference, reference image features, embedding score, and rerank score to the final score breakdown.
- Add traceable structured logs for the full matching pipeline.
- Expose enough fields in API responses and frontend UI for teammates to verify what happened.

Out of scope:

- Switching the user-facing execution flow to 14 steps.
- Video makeup parsing.
- Blogger/link parsing.
- Training new models.
- Saving raw face/reference images by default.
- Designing this module as the exclusive owner of all 8 GPUs.

## GPU And Model Service Policy

All GPUs 0-7 may be used, but services must be assigned by actual resource need.

Embedding and reranker services must be healthy before model-backed matching is considered available. These models should use low-overhead deployment and should not occupy a high-memory GPU if their actual memory footprint is small.

Heavy services such as Qwen-VL, ComfyUI, and realtime coach models can use larger GPUs when needed. Reference image parsing calls the existing or configured VLM service only when the user provides an image.

The backend does not directly manage CUDA placement. It depends on model service URLs and health checks. Startup scripts and runbooks own GPU assignment, concurrency, and memory limits.

Required service configuration:

- `TEMPLATE_EMBEDDING_BASE_URL`
- `TEMPLATE_EMBEDDING_MODEL`
- `TEMPLATE_RERANKER_BASE_URL`
- `TEMPLATE_RERANKER_MODEL`
- `TEMPLATE_VLM_BASE_URL`
- `TEMPLATE_VLM_MODEL`
- `TEMPLATE_MODEL_TIMEOUT_MS`

## Backend Data Design

The current standard template library schema remains the foundation. Add or extend fields only where the current schema cannot express MMU requirements or traceability.

### Standard Taxonomy

`TemplateProductCategory` should store MMU product standards with:

- parent category code.
- display name.
- aliases.
- texture tags.
- function tags.
- shade tags.
- sort order.

The seed data must include MMU's 9 standard product groups:

- prep.
- base.
- setting.
- brow.
- eye.
- contour.
- lip.
- remover.
- tool.

It must also include the MMU subcategory vocabulary needed by matching, such as toner, lotion, sunscreen, primer, foundation, cushion, concealer, powder, setting spray, brow pencil, brow powder, eyeshadow, eyeliner, mascara, false lashes, contour, highlight, blush, lip balm, lipstick, lip glaze, lip mud, lip liner, remover, brush, and puff.

`TemplateOperationArea` should contain MMU's 9 operation areas:

- full face.
- T zone.
- U zone.
- eye area.
- brows.
- cheekbone or cheeks.
- jawline.
- nose area.
- lips.

`TemplateFaceShape` should contain MMU's 6 standard face shapes:

- oval.
- narrow.
- round.
- long.
- short.
- square round.

`TemplateDifficultyRule` should support the MMU formula:

```text
total difficulty = step difficulty score + product count weight + special technique bonus
```

Special technique bonus is 3 points when a marked special technique is present.

### Step Mapping

The user-facing execution template stays 5 steps:

- base/prep.
- brow.
- eye.
- cheek/contour.
- lip/finish.

Each step block must carry `standardStepCodes` mapping to MMU's 14 standard steps:

- skin prep.
- sunscreen or primer.
- concealer.
- foundation.
- setting.
- eyeshadow.
- brow.
- contour.
- highlight.
- blush.
- lash.
- eyeliner.
- lip.
- second setting.

The API response must return these codes so the frontend and tests can prove the 5-step experience is backed by MMU's standard structure.

### Match Trace

Extend `TemplateMatchTrace` or its payload to record:

- `templateTraceId`.
- raw input length and normalized intent.
- embedding model, status, latency, vector dimension.
- reranker model, status, latency, candidate count.
- VLM model, status, latency, only when a reference image is provided.
- reference image features, without raw image data.
- selected template ID and version ID.
- candidate top K summary.
- score breakdown.
- face shape adjustments.
- difficulty breakdown.
- product coverage breakdown.
- history preference score.
- failure reason when matching fails.

## Matching Algorithm

The matching algorithm has four stages.

### 1. Input Normalization

Parse user text into:

- scene.
- style tags.
- effect tags.
- constraints.
- requested time.
- skill level.

Build user profile features from current user data and generated snapshots:

- skin type.
- face shape, when available.
- skill level.
- preferred style signals.
- avoid style signals.
- owned product categories and subcategories.
- recent product usage and preference data, where available.

### 2. Mandatory Model Retrieval

Embedding service computes the query representation and, where supported, candidate template representations.

If embedding service is unavailable or returns an invalid response, stop the request and return:

```text
TEMPLATE_EMBEDDING_UNAVAILABLE
```

Reranker service receives the query and candidate template descriptions. If reranker service is unavailable or invalid, stop the request and return:

```text
TEMPLATE_RERANKER_UNAVAILABLE
```

Rules can help prepare candidates and explain results, but they must not replace the embedding/reranker path.

### 3. Optional Reference Image Features

When the user uploads a reference image, call the local VLM service and ask for structured JSON:

```json
{
  "baseFinish": "dewy",
  "eyeIntensity": 2,
  "blushPlacement": "upper_cheek",
  "lipColorFamily": "bean_paste",
  "styleSignals": ["clean", "soft_eye", "low_saturation"]
}
```

Do not save raw images by default. Persist only structured features and model status in the match trace.

If a reference image was provided and VLM parsing fails, return:

```text
REFERENCE_IMAGE_PARSE_FAILED
```

If no image is provided, skip VLM and continue.

### 4. Rule Constraints And Final Score

Final score combines:

- embedding similarity.
- reranker relevance.
- style match.
- scene match.
- reference image fit.
- product coverage.
- face shape fit.
- user profile fit.
- history preference.
- difficulty penalty.
- missing required slot penalty.

The response must include a score breakdown and human-readable reasons.

Face shape affects contour, blush, highlight, and brow/eye emphasis. For example, round face profiles can receive higher weight for lifted cheek placement and natural contour slots.

Difficulty uses MMU's formula and should expose:

- step score.
- product count contribution.
- special technique bonus.
- final difficulty score.
- mapped difficulty level.

History preference should use existing execution, product usage, and feedback data where available. If insufficient data exists, the score is explicit zero with reason `insufficient_history`.

## API Design

Enhance existing endpoints instead of adding parallel flows.

### `POST /makeup-templates/generate`

Accepts:

- text input.
- requirements.
- optional `referenceImage`.
- generation source.

Returns:

- generated template.
- standard template IDs.
- model status.
- reference image features.
- score breakdown.
- face shape adjustments.
- difficulty breakdown.
- history preference score.
- standard step codes.
- `templateTraceId`.

### `POST /makeup-template-library/match-debug`

Accepts the same matching inputs and optional reference image. This endpoint is for developer and QA visibility. It should not create a generated template unless explicitly requested.

### Errors

Use explicit error codes and include `templateTraceId` where possible:

- `TEMPLATE_EMBEDDING_UNAVAILABLE`
- `TEMPLATE_RERANKER_UNAVAILABLE`
- `REFERENCE_IMAGE_PARSE_FAILED`
- `TEMPLATE_TAXONOMY_EMPTY`
- `TEMPLATE_NO_CANDIDATES`

## Logging Design

Add a template matching logger that emits structured logs with `templateTraceId`.

Log events:

- request received.
- input normalized.
- embedding request started/completed/failed.
- reranker request started/completed/failed.
- VLM parse started/completed/failed.
- rule scoring completed.
- template selected.
- database write completed.
- response returned.

Log fields:

- trace ID.
- user ID.
- has reference image.
- input text length, not full raw private text.
- model names.
- latency.
- candidate counts.
- selected template.
- score summary.
- error code and stack for failures.

Do not log:

- base64 image data.
- raw uploaded images.
- full sensitive free-text input.
- audio or video payloads.

## Frontend Design

Update the recommendation entry flow to support an optional reference makeup image upload.

Update result and product pages to show:

- selected MMU style family.
- standard template ID/version.
- embedding and reranker status.
- VLM feature summary, when an image was provided.
- product coverage.
- face shape adjustment explanation.
- difficulty breakdown.
- 5 execution steps with MMU standard step codes.
- `templateTraceId` for debugging.

Update model error UI:

- If embedding/reranker is unavailable, show a clear blocking message.
- Show `templateTraceId`.
- Do not fall back to local mock recommendations in this path.

Update template management UI:

- Show and edit standard step codes.
- Show and edit operation areas.
- Show and edit product slot subcategory tags.
- Show difficulty score fields.
- Preserve publish, archive, and rollback behavior.

## Testing Plan

Backend unit tests:

- seed data includes MMU style families, product categories, operation areas, face shapes, and difficulty rules.
- 5-step templates contain MMU standard step codes.
- embedding unavailable returns `TEMPLATE_EMBEDDING_UNAVAILABLE`.
- reranker unavailable returns `TEMPLATE_RERANKER_UNAVAILABLE`.
- reference image VLM failure returns `REFERENCE_IMAGE_PARSE_FAILED`.
- successful model-backed matching writes `TemplateMatchTrace`.
- face shape changes score breakdown.
- difficulty formula includes product count and special technique bonus.
- history preference is scored or explicitly marked insufficient.

Backend e2e tests:

- mock embedding, reranker, and VLM services.
- generate with text only.
- generate with reference image.
- verify generated recommendation keeps 5 user-facing steps.
- verify standard step codes and score breakdown are returned.
- verify database rows are written.

Frontend tests:

- no-reference-image generation path.
- reference-image upload path.
- blocking model error display.
- result page displays model status, score breakdown, trace ID, and standard step codes.
- template management edits MMU fields and publishes a version.

Manual smoke tests:

- run seed.
- start backend.
- start embedding and reranker services.
- start VLM service for reference image testing.
- open frontend and generate a template with and without a reference image.
- confirm logs can be searched by `templateTraceId`.

## Acceptance Criteria

- MMU standard taxonomy is seeded into the database and queryable.
- User-facing generated templates still contain 5 steps.
- Each 5-step template maps back to MMU standard step codes.
- Matching requires embedding and reranker services.
- No silent pure-rule fallback is used when those services fail.
- Reference image parsing works through local VLM and affects score breakdown.
- Face shape, difficulty, product coverage, and history preference are visible in trace and response.
- Frontend displays enough evidence for teammates to verify the algorithm path.
- Structured logs make failures traceable by `templateTraceId`.
