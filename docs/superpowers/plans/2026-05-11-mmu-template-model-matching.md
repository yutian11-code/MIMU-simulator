# MMU Template Model Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build MMU-standard, model-backed makeup template matching with mandatory embedding/reranker services, optional reference-image VLM parsing, traceable logs, and frontend evidence UI while keeping the user execution flow at 5 steps.

**Architecture:** Keep the existing NestJS `makeup-templates` and Expo recommendation flows. Extend the standard template taxonomy, add focused matching support services for trace IDs, model availability, VLM parsing, difficulty scoring, and response evidence, then surface that evidence through existing recommendation APIs and screens. Matching must fail clearly when embedding or reranker services are unavailable.

**Tech Stack:** NestJS 11, Prisma 7, PostgreSQL, Jest, Expo React Native, TanStack Query, Zustand, TypeScript.

---

## File Structure

### Backend

- Modify `backend/prisma/schema.prisma`
  - Add trace/evidence fields to `TemplateMatchTrace`.
  - Add `standardStepCodes` and `difficultyScore` to generated template steps.
- Create `backend/prisma/migrations/<timestamp>_extend_template_match_trace/migration.sql`
  - Database migration for trace/evidence columns.
- Modify `backend/src/makeup-templates/makeup-template-id.util.ts`
  - Ensure match trace IDs and model log IDs have stable prefixes.
- Modify `backend/src/makeup-templates/template-library/standard-template-library.types.ts`
  - Add model status, reference image, difficulty, history, and trace types.
- Modify `backend/src/makeup-templates/template-library/template-library.seed-data.ts`
  - Expand MMU product subcategory taxonomy and difficulty rules.
- Modify `backend/src/makeup-templates/template-library/standard-template-library.data.ts`
  - Keep 5-step templates but ensure every step maps to MMU 14-step codes and uses MMU slots.
- Modify `backend/src/makeup-templates/template-library/template-model-client.service.ts`
  - Add health checks, mandatory error behavior, model metadata, latency, and VLM parsing.
- Create `backend/src/makeup-templates/template-library/template-model-unavailable.exception.ts`
  - Domain-specific HTTP exceptions for model availability errors.
- Create `backend/src/makeup-templates/template-library/template-match-logger.service.ts`
  - Structured logs with `templateTraceId`.
- Create `backend/src/makeup-templates/template-library/template-difficulty.service.ts`
  - MMU difficulty formula.
- Create `backend/src/makeup-templates/template-library/template-history-preference.service.ts`
  - History preference score from existing events/executions.
- Modify `backend/src/makeup-templates/template-library/template-match-profile.service.ts`
  - Carry face shape, uploaded reference image features, and history signals.
- Modify `backend/src/makeup-templates/template-library/template-matching.service.ts`
  - Enforce mandatory embedding/reranker and add final score breakdown.
- Modify `backend/src/makeup-templates/template-library/template-blueprint-adapter.service.ts`
  - Preserve standard step codes and difficulty on generated steps.
- Modify `backend/src/makeup-templates/makeup-template-generation.service.ts`
  - Create trace ID early, pass reference image/VLM features, persist evidence.
- Modify `backend/src/makeup-templates/makeup-template.mapper.ts`
  - Return model/evidence fields and standard step codes.
- Modify `backend/src/makeup-templates/dto/generate-makeup-template.dto.ts`
  - Add optional reference image data URL for JSON path.
- Modify `backend/src/makeup-templates/dto/makeup-template-response.dto.ts`
  - Add evidence response DTOs.
- Modify `backend/src/makeup-templates/template-library/template-library.controller.ts`
  - Update `match-debug` request/response and model-required error behavior.
- Modify `backend/src/recommendations/recommendations.service.ts`
  - Include generated template evidence when creating/fetching recommendations.
- Modify `backend/src/recommendations/recommendation.mapper.ts`
  - Return evidence fields in recommendation responses.
- Modify `backend/src/recommendations/dto/recommendation-response.dto.ts`
  - Document evidence fields.
- Modify `backend/.env.example`
  - Add required template model service variables.
- Modify `docs/team-runbook.md`
  - Add model service startup and log trace notes.

### Frontend

- Modify `frontend/types/recommendation.ts`
  - Add model status, score breakdown, reference features, difficulty, trace ID, and standard step code types.
- Modify `frontend/services/recommendationService.ts`
  - Remove backend-error local fallback for generated model path and pass optional reference image.
- Modify `frontend/hooks/use-demo-queries.ts`
  - Include reference image in recommendation query key and request.
- Modify `frontend/store/demo-store.ts`
  - Persist optional reference image URI/data URL for the scenario flow.
- Modify `frontend/app/recommendation/scenario.tsx`
  - Add reference image picker/upload control and send it to generation.
- Modify `frontend/app/recommendation/result.tsx`
  - Display model status, score breakdown, trace ID, reference features, difficulty, and standard step codes.
- Modify `frontend/app/recommendation/products.tsx`
  - Show product slot evidence and standard step codes.
- Modify `frontend/app/template-library/detail.tsx`
  - Surface/edit standard step codes, operation areas, product slot tags, and difficulty fields clearly.

### Tests

- Modify/add backend Jest specs:
  - `backend/src/makeup-templates/template-library/template-model-client.service.spec.ts`
  - `backend/src/makeup-templates/template-library/template-matching.service.spec.ts`
  - `backend/src/makeup-templates/template-library/template-difficulty.service.spec.ts`
  - `backend/src/makeup-templates/template-library/template-history-preference.service.spec.ts`
  - `backend/src/makeup-templates/makeup-template-generation.service.spec.ts`
  - `backend/src/recommendations/recommendations.service.spec.ts`
  - `backend/test/app.e2e-spec.ts`
- Modify/add frontend type/lint validation through existing TypeScript and Expo lint commands.

---

## Task 1: Extend Match Trace Schema And Response Types

**Files:**
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/prisma/migrations/20260511100000_extend_template_match_trace/migration.sql`
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.types.ts`
- Modify: `backend/src/makeup-templates/dto/makeup-template-response.dto.ts`
- Modify: `backend/src/recommendations/dto/recommendation-response.dto.ts`
- Test: `backend/src/makeup-templates/makeup-template-generation.service.spec.ts`
- Test: `backend/src/recommendations/recommendations.service.spec.ts`

- [ ] **Step 1: Write failing backend type/mapper tests for evidence fields**

Add expectations in `backend/src/makeup-templates/makeup-template-generation.service.spec.ts` to the existing successful generation test. The generated response should include:

```ts
expect(result.matchTraceId).toMatch(/^mtrace_/);
expect(result.modelStatus).toEqual({
  embedding: 'configured',
  reranker: 'configured',
  vlm: 'skipped',
});
expect(result.scoreBreakdown).toEqual(
  expect.objectContaining({
    embeddingSimilarity: expect.any(Number),
    rerankerRelevance: expect.any(Number),
    productCoverage: expect.any(Number),
    difficultyPenalty: expect.any(Number),
  }),
);
expect(result.difficultyBreakdown).toEqual(
  expect.objectContaining({
    stepScore: expect.any(Number),
    productCountWeight: expect.any(Number),
    specialTechniqueBonus: expect.any(Number),
    totalDifficultyScore: expect.any(Number),
    level: expect.stringMatching(/^L[1-5]$/),
  }),
);
expect(result.steps[0].standardStepCodes).toEqual(
  expect.arrayContaining(['SKIN_PREP', 'FOUNDATION']),
);
```

Add expectations in `backend/src/recommendations/recommendations.service.spec.ts` for mapped recommendations:

```ts
expect(result.templateTraceId).toBe('mtrace_20260511_abcd1234');
expect(result.modelStatus).toEqual({
  embedding: 'configured',
  reranker: 'configured',
  vlm: 'skipped',
});
expect(result.steps[0].standardStepCodes).toContain('FOUNDATION');
expect(result.scoreBreakdown?.rerankerRelevance).toBeGreaterThan(0);
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd backend
npm test -- makeup-template-generation.service.spec.ts recommendations.service.spec.ts --runInBand
```

Expected: FAIL because `modelStatus`, `scoreBreakdown`, `difficultyBreakdown`, `standardStepCodes`, and `templateTraceId` are not in DTOs/mappers yet.

- [ ] **Step 3: Extend Prisma schema**

In `backend/prisma/schema.prisma`, update `GeneratedTemplateStep`:

```prisma
  standardStepCodes String[] @map("standard_step_codes") @default([])
  difficultyScore   Float?   @map("difficulty_score")
```

Update `TemplateMatchTrace` to include structured evidence. Keep existing fields and add these if missing:

```prisma
  templateTraceId         String? @unique @map("template_trace_id") @db.VarChar(60)
  embeddingModel          String? @map("embedding_model") @db.VarChar(120)
  embeddingStatus         String? @map("embedding_status") @db.VarChar(30)
  embeddingLatencyMs      Int?    @map("embedding_latency_ms")
  embeddingVectorDim      Int?    @map("embedding_vector_dim")
  rerankerModel           String? @map("reranker_model") @db.VarChar(120)
  rerankerStatus          String? @map("reranker_status") @db.VarChar(30)
  rerankerLatencyMs       Int?    @map("reranker_latency_ms")
  vlmModel                String? @map("vlm_model") @db.VarChar(120)
  vlmStatus               String? @map("vlm_status") @db.VarChar(30)
  vlmLatencyMs            Int?    @map("vlm_latency_ms")
  referenceImageFeatures  Json?   @map("reference_image_features")
  faceShapeAdjustments    Json?   @map("face_shape_adjustments")
  difficultyBreakdown     Json?   @map("difficulty_breakdown")
  productCoverageBreakdown Json?  @map("product_coverage_breakdown")
  historyPreferenceScore  Float?  @map("history_preference_score")
  failureReason           String? @map("failure_reason") @db.VarChar(500)
```

If `TemplateMatchTrace` already has some JSON fields (`profile`, `scoreBreakdown`, `modelStatus`), preserve them and add only the explicit columns above.

- [ ] **Step 4: Create migration SQL**

Create `backend/prisma/migrations/20260511100000_extend_template_match_trace/migration.sql`:

```sql
ALTER TABLE "generated_template_steps"
  ADD COLUMN IF NOT EXISTS "standard_step_codes" TEXT[] DEFAULT ARRAY[]::TEXT[],
  ADD COLUMN IF NOT EXISTS "difficulty_score" DOUBLE PRECISION;

ALTER TABLE "template_match_traces"
  ADD COLUMN IF NOT EXISTS "template_trace_id" VARCHAR(60),
  ADD COLUMN IF NOT EXISTS "embedding_model" VARCHAR(120),
  ADD COLUMN IF NOT EXISTS "embedding_status" VARCHAR(30),
  ADD COLUMN IF NOT EXISTS "embedding_latency_ms" INTEGER,
  ADD COLUMN IF NOT EXISTS "embedding_vector_dim" INTEGER,
  ADD COLUMN IF NOT EXISTS "reranker_model" VARCHAR(120),
  ADD COLUMN IF NOT EXISTS "reranker_status" VARCHAR(30),
  ADD COLUMN IF NOT EXISTS "reranker_latency_ms" INTEGER,
  ADD COLUMN IF NOT EXISTS "vlm_model" VARCHAR(120),
  ADD COLUMN IF NOT EXISTS "vlm_status" VARCHAR(30),
  ADD COLUMN IF NOT EXISTS "vlm_latency_ms" INTEGER,
  ADD COLUMN IF NOT EXISTS "reference_image_features" JSONB,
  ADD COLUMN IF NOT EXISTS "face_shape_adjustments" JSONB,
  ADD COLUMN IF NOT EXISTS "difficulty_breakdown" JSONB,
  ADD COLUMN IF NOT EXISTS "product_coverage_breakdown" JSONB,
  ADD COLUMN IF NOT EXISTS "history_preference_score" DOUBLE PRECISION,
  ADD COLUMN IF NOT EXISTS "failure_reason" VARCHAR(500);

CREATE UNIQUE INDEX IF NOT EXISTS "template_match_traces_template_trace_id_key"
  ON "template_match_traces"("template_trace_id");
```

- [ ] **Step 5: Extend backend TypeScript types**

In `backend/src/makeup-templates/template-library/standard-template-library.types.ts`, add:

```ts
export type TemplateModelState = 'configured' | 'unavailable' | 'failed' | 'skipped';

export type TemplateModelCallEvidence = {
  model: string;
  status: TemplateModelState;
  latencyMs: number;
  errorMessage?: string;
};

export type ReferenceImageFeatures = {
  baseFinish?: string;
  eyeIntensity?: number;
  blushPlacement?: string;
  lipColorFamily?: string;
  styleSignals: string[];
};

export type TemplateDifficultyBreakdown = {
  stepScore: number;
  productCountWeight: number;
  specialTechniqueBonus: number;
  totalDifficultyScore: number;
  level: 'L1' | 'L2' | 'L3' | 'L4' | 'L5';
};

export type TemplateFaceShapeAdjustment = {
  faceShape?: string;
  target: string;
  scoreDelta: number;
  reason: string;
};

export type TemplateProductCoverageBreakdown = {
  requiredSlots: number;
  matchedRequiredSlots: number;
  coverageRate: number;
  missingRequiredSlotCodes: string[];
};
```

Extend `TemplateMatchResult`:

```ts
  templateTraceId: string;
  referenceImageFeatures?: ReferenceImageFeatures;
  faceShapeAdjustments: TemplateFaceShapeAdjustment[];
  difficultyBreakdown: TemplateDifficultyBreakdown;
  productCoverageBreakdown: TemplateProductCoverageBreakdown;
  historyPreferenceScore: number;
```

Extend `StandardStepBlock` and generated blueprint types so `standardStepCodes` and `difficultyScore` flow through.

- [ ] **Step 6: Extend response DTOs**

In `backend/src/makeup-templates/dto/makeup-template-response.dto.ts`, add DTO classes:

```ts
class TemplateModelStatusResponseDto {
  @ApiProperty({ example: 'configured' })
  embedding!: string;

  @ApiProperty({ example: 'configured' })
  reranker!: string;

  @ApiProperty({ example: 'skipped' })
  vlm!: string;
}

class TemplateScoreBreakdownResponseDto {
  @ApiProperty({ example: 0.82 })
  embeddingSimilarity!: number;

  @ApiProperty({ example: 0.91 })
  rerankerRelevance!: number;

  @ApiProperty({ example: 0.7 })
  styleMatch!: number;

  @ApiProperty({ example: 1 })
  sceneMatch!: number;

  @ApiProperty({ example: 0.8 })
  productCoverage!: number;

  @ApiProperty({ example: 0.5 })
  userProfileFit!: number;

  @ApiProperty({ example: 0.2 })
  historyPreference!: number;

  @ApiProperty({ example: 0 })
  difficultyPenalty!: number;

  @ApiProperty({ example: 0.1 })
  missingRequiredSlotPenalty!: number;
}

class TemplateDifficultyBreakdownResponseDto {
  @ApiProperty({ example: 1.8 })
  stepScore!: number;

  @ApiProperty({ example: 0.4 })
  productCountWeight!: number;

  @ApiProperty({ example: 0 })
  specialTechniqueBonus!: number;

  @ApiProperty({ example: 2.2 })
  totalDifficultyScore!: number;

  @ApiProperty({ example: 'L2' })
  level!: string;
}
```

Add to `GeneratedTemplateStepResponseDto`:

```ts
  @ApiProperty({ example: ['SKIN_PREP', 'FOUNDATION'], type: [String] })
  standardStepCodes!: string[];

  @ApiPropertyOptional({ example: 1.2 })
  difficultyScore?: number;
```

Add to `MakeupTemplateResponseDto`:

```ts
  @ApiPropertyOptional({ example: 'mtrace_20260511_ab12cd34' })
  templateTraceId?: string;

  @ApiPropertyOptional({ type: TemplateModelStatusResponseDto })
  modelStatus?: TemplateModelStatusResponseDto;

  @ApiPropertyOptional({ type: TemplateScoreBreakdownResponseDto })
  scoreBreakdown?: TemplateScoreBreakdownResponseDto;

  @ApiPropertyOptional({ type: TemplateDifficultyBreakdownResponseDto })
  difficultyBreakdown?: TemplateDifficultyBreakdownResponseDto;

  @ApiPropertyOptional({ example: { styleSignals: ['clean'] } })
  referenceImageFeatures?: Record<string, unknown>;

  @ApiPropertyOptional({ example: [{ target: 'CHEEK', scoreDelta: 0.04 }] })
  faceShapeAdjustments?: Array<Record<string, unknown>>;

  @ApiPropertyOptional({ example: 0.2 })
  historyPreferenceScore?: number;
```

Mirror these optional fields in `backend/src/recommendations/dto/recommendation-response.dto.ts`.

- [ ] **Step 7: Update minimal mappers so the new fields compile**

In `backend/src/makeup-templates/makeup-template.mapper.ts`, add the optional fields to `TemplateWithIncludes`:

```ts
matchTrace?: {
  templateTraceId?: string | null;
  modelStatus?: unknown;
  scoreBreakdown?: unknown;
  difficultyBreakdown?: unknown;
  referenceImageFeatures?: unknown;
  faceShapeAdjustments?: unknown;
  historyPreferenceScore?: number | null;
} | null;
```

Add `standardStepCodes` and `difficultyScore` to each step type:

```ts
standardStepCodes: string[];
difficultyScore?: number | null;
```

Return safe optional values:

```ts
templateTraceId: template.matchTrace?.templateTraceId ?? template.matchTraceId ?? undefined,
modelStatus: template.matchTrace?.modelStatus as MakeupTemplateResponseDto['modelStatus'],
scoreBreakdown: template.matchTrace?.scoreBreakdown as MakeupTemplateResponseDto['scoreBreakdown'],
difficultyBreakdown: template.matchTrace?.difficultyBreakdown as MakeupTemplateResponseDto['difficultyBreakdown'],
referenceImageFeatures: template.matchTrace?.referenceImageFeatures as Record<string, unknown> | undefined,
faceShapeAdjustments: template.matchTrace?.faceShapeAdjustments as Array<Record<string, unknown>> | undefined,
historyPreferenceScore: template.matchTrace?.historyPreferenceScore ?? undefined,
```

Inside the step mapper return:

```ts
standardStepCodes: step.standardStepCodes,
difficultyScore: step.difficultyScore ?? undefined,
```

In `backend/src/recommendations/recommendation.mapper.ts`, return optional evidence fields using the same pattern:

```ts
templateTraceId:
  recommendation.generatedTemplate?.matchTrace?.templateTraceId ??
  recommendation.generatedTemplate?.matchTraceId ??
  undefined,
modelStatus: recommendation.generatedTemplate?.matchTrace?.modelStatus,
scoreBreakdown: recommendation.generatedTemplate?.matchTrace?.scoreBreakdown,
difficultyBreakdown:
  recommendation.generatedTemplate?.matchTrace?.difficultyBreakdown,
referenceImageFeatures:
  recommendation.generatedTemplate?.matchTrace?.referenceImageFeatures,
faceShapeAdjustments:
  recommendation.generatedTemplate?.matchTrace?.faceShapeAdjustments,
historyPreferenceScore:
  recommendation.generatedTemplate?.matchTrace?.historyPreferenceScore ??
  undefined,
```

For each recommendation step, return:

```ts
standardStepCodes: generatedStep?.standardStepCodes,
difficultyScore: generatedStep?.difficultyScore ?? undefined,
```

In `backend/src/recommendations/recommendations.service.ts`, extend `GENERATED_TEMPLATE_INCLUDE` to select `matchTraceId`, `matchTrace`, `standardStepCodes`, and `difficultyScore` as shown in Task 4 Step 7.

- [ ] **Step 8: Run Prisma generate and targeted tests**

Run:

```bash
cd backend
npm run prisma:generate
npm test -- makeup-template-generation.service.spec.ts recommendations.service.spec.ts --runInBand
```

Expected: Prisma generation succeeds and targeted tests pass.

- [ ] **Step 9: Commit schema and DTO foundation**

```bash
cd backend
git add prisma/schema.prisma prisma/migrations/20260511100000_extend_template_match_trace/migration.sql src/makeup-templates/template-library/standard-template-library.types.ts src/makeup-templates/dto/makeup-template-response.dto.ts src/recommendations/dto/recommendation-response.dto.ts src/makeup-templates/makeup-template.mapper.ts src/recommendations/recommendation.mapper.ts src/recommendations/recommendations.service.ts src/makeup-templates/makeup-template-generation.service.spec.ts src/recommendations/recommendations.service.spec.ts
git commit -m "feat: add template matching evidence schema"
```

---

## Task 2: Add Mandatory Model Client Health, Errors, VLM Parsing, And Structured Logs

**Files:**
- Modify: `backend/src/makeup-templates/template-library/template-model-client.service.ts`
- Create: `backend/src/makeup-templates/template-library/template-model-unavailable.exception.ts`
- Create: `backend/src/makeup-templates/template-library/template-match-logger.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-model-client.service.spec.ts`
- Modify: `backend/src/makeup-templates/makeup-templates.module.ts`
- Modify: `backend/.env.example`

- [ ] **Step 1: Write failing model client tests**

In `backend/src/makeup-templates/template-library/template-model-client.service.spec.ts`, replace the unavailable-as-success expectation with explicit mandatory behavior tests:

```ts
it('reports embedding unavailable when base URL is missing', async () => {
  const service = new TemplateModelClientService();

  await expect(service.embedText('清透通勤妆')).resolves.toEqual(
    expect.objectContaining({
      status: 'unavailable',
      vector: [],
      model: 'Qwen3-Embedding-4B',
      latencyMs: expect.any(Number),
      errorMessage: 'TEMPLATE_EMBEDDING_BASE_URL is not configured',
    }),
  );
});

it('parses reference image features from configured VLM service', async () => {
  process.env.TEMPLATE_VLM_BASE_URL = 'http://127.0.0.1:8010/v1';
  process.env.TEMPLATE_VLM_MODEL = 'Qwen2.5-VL-32B-Instruct-AWQ';
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: () =>
      Promise.resolve({
        choices: [
          {
            message: {
              content:
                '{"baseFinish":"dewy","eyeIntensity":2,"blushPlacement":"upper_cheek","lipColorFamily":"bean_paste","styleSignals":["clean","soft_eye"]}',
            },
          },
        ],
      }),
  });

  const service = new TemplateModelClientService();

  await expect(
    service.parseReferenceImage('data:image/png;base64,AAAA'),
  ).resolves.toEqual(
    expect.objectContaining({
      status: 'configured',
      features: {
        baseFinish: 'dewy',
        eyeIntensity: 2,
        blushPlacement: 'upper_cheek',
        lipColorFamily: 'bean_paste',
        styleSignals: ['clean', 'soft_eye'],
      },
    }),
  );
});
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd backend
npm test -- template-model-client.service.spec.ts --runInBand
```

Expected: FAIL because current result does not include model/latency/error metadata and has no `parseReferenceImage`.

- [ ] **Step 3: Create domain exception**

Create `backend/src/makeup-templates/template-library/template-model-unavailable.exception.ts`:

```ts
import { ServiceUnavailableException } from '@nestjs/common';

export class TemplateModelUnavailableException extends ServiceUnavailableException {
  constructor(
    readonly code:
      | 'TEMPLATE_EMBEDDING_UNAVAILABLE'
      | 'TEMPLATE_RERANKER_UNAVAILABLE'
      | 'REFERENCE_IMAGE_PARSE_FAILED'
      | 'TEMPLATE_TAXONOMY_EMPTY'
      | 'TEMPLATE_NO_CANDIDATES',
    message: string,
    readonly templateTraceId?: string,
  ) {
    super({
      code,
      message,
      templateTraceId,
    });
  }
}
```

- [ ] **Step 4: Add structured logger service**

Create `backend/src/makeup-templates/template-library/template-match-logger.service.ts`:

```ts
import { Injectable, Logger } from '@nestjs/common';

type TemplateMatchLogPayload = {
  templateTraceId: string;
  userId?: string;
  event:
    | 'request_received'
    | 'input_normalized'
    | 'embedding_started'
    | 'embedding_completed'
    | 'embedding_failed'
    | 'reranker_started'
    | 'reranker_completed'
    | 'reranker_failed'
    | 'vlm_started'
    | 'vlm_completed'
    | 'vlm_failed'
    | 'rule_scoring_completed'
    | 'template_selected'
    | 'db_write_completed'
    | 'response_returned';
  data?: Record<string, unknown>;
};

@Injectable()
export class TemplateMatchLoggerService {
  private readonly logger = new Logger('TemplateMatching');

  log(payload: TemplateMatchLogPayload) {
    this.logger.log(JSON.stringify(redact(payload)));
  }

  warn(payload: TemplateMatchLogPayload) {
    this.logger.warn(JSON.stringify(redact(payload)));
  }
}

function redact(payload: TemplateMatchLogPayload): TemplateMatchLogPayload {
  const data = { ...(payload.data ?? {}) };
  delete data.base64;
  delete data.imageDataUrl;
  delete data.referenceImageDataUrl;
  delete data.rawImage;

  if (typeof data.rawUserInput === 'string') {
    data.rawUserInputLength = data.rawUserInput.length;
    delete data.rawUserInput;
  }

  return { ...payload, data };
}
```

- [ ] **Step 5: Extend model client result types and VLM call**

In `template-model-client.service.ts`, update result types:

```ts
export type TemplateEmbeddingResult = {
  status: TemplateModelStatus;
  model: string;
  latencyMs: number;
  vector: number[];
  errorMessage?: string;
};

export type TemplateRerankResult = {
  status: TemplateModelStatus;
  model: string;
  latencyMs: number;
  scores: number[];
  errorMessage?: string;
};

export type TemplateReferenceImageResult = {
  status: TemplateModelStatus | 'skipped';
  model: string;
  latencyMs: number;
  features?: ReferenceImageFeatures;
  errorMessage?: string;
};
```

Add constructor fields:

```ts
private readonly vlmBaseUrl: string;
private readonly vlmModel: string;
```

Initialize them from `TEMPLATE_VLM_BASE_URL` and `TEMPLATE_VLM_MODEL`.

Wrap `embedText`, `rerank`, and `parseReferenceImage` with `const startedAt = Date.now()` and return `latencyMs: Date.now() - startedAt`.

Add:

```ts
async parseReferenceImage(imageDataUrl?: string): Promise<TemplateReferenceImageResult> {
  const startedAt = Date.now();
  if (!imageDataUrl) {
    return { status: 'skipped', model: this.vlmModel, latencyMs: 0 };
  }
  if (!this.vlmBaseUrl) {
    return {
      status: 'unavailable',
      model: this.vlmModel,
      latencyMs: Date.now() - startedAt,
      errorMessage: 'TEMPLATE_VLM_BASE_URL is not configured',
    };
  }

  try {
    const payload = await this.withTimeout(async (signal) => {
      const response = await fetch(`${this.vlmBaseUrl}/chat/completions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal,
        body: JSON.stringify({
          model: this.vlmModel,
          messages: [
            {
              role: 'user',
              content: [
                {
                  type: 'text',
                  text: 'Analyze this makeup reference image. Return only compact JSON with baseFinish, eyeIntensity, blushPlacement, lipColorFamily, styleSignals.',
                },
                { type: 'image_url', image_url: { url: imageDataUrl } },
              ],
            },
          ],
          max_tokens: 256,
          temperature: 0,
        }),
      });
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return (await response.json()) as unknown;
    });

    return {
      status: 'configured',
      model: this.vlmModel,
      latencyMs: Date.now() - startedAt,
      features: parseReferenceImageFeatures(payload),
    };
  } catch (error) {
    return {
      status: 'failed',
      model: this.vlmModel,
      latencyMs: Date.now() - startedAt,
      errorMessage: formatError(error),
    };
  }
}
```

Implement `parseReferenceImageFeatures(payload)` by extracting `choices[0].message.content`, parsing JSON, and normalizing `styleSignals` to a string array.

- [ ] **Step 6: Register logger service**

In `backend/src/makeup-templates/makeup-templates.module.ts`, add `TemplateMatchLoggerService` to providers.

- [ ] **Step 7: Add env examples**

In `backend/.env.example`, add:

```dotenv
TEMPLATE_EMBEDDING_BASE_URL=http://127.0.0.1:8030/v1
TEMPLATE_EMBEDDING_MODEL=Qwen3-Embedding-4B
TEMPLATE_RERANKER_BASE_URL=http://127.0.0.1:8031/v1
TEMPLATE_RERANKER_MODEL=Qwen3-Reranker-8B
TEMPLATE_VLM_BASE_URL=http://127.0.0.1:8010/v1
TEMPLATE_VLM_MODEL=Qwen2.5-VL-32B-Instruct-AWQ
TEMPLATE_MODEL_TIMEOUT_MS=5000
```

- [ ] **Step 8: Run tests**

Run:

```bash
cd backend
npm test -- template-model-client.service.spec.ts --runInBand
```

Expected: PASS.

- [ ] **Step 9: Commit model client and logger**

```bash
cd backend
git add src/makeup-templates/template-library/template-model-client.service.ts src/makeup-templates/template-library/template-model-client.service.spec.ts src/makeup-templates/template-library/template-model-unavailable.exception.ts src/makeup-templates/template-library/template-match-logger.service.ts src/makeup-templates/makeup-templates.module.ts .env.example
git commit -m "feat: require template model services"
```

---

## Task 3: Implement MMU Difficulty, History Preference, And Scoring Evidence

**Files:**
- Create: `backend/src/makeup-templates/template-library/template-difficulty.service.ts`
- Create: `backend/src/makeup-templates/template-library/template-difficulty.service.spec.ts`
- Create: `backend/src/makeup-templates/template-library/template-history-preference.service.ts`
- Create: `backend/src/makeup-templates/template-library/template-history-preference.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-matching.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-matching.service.spec.ts`
- Modify: `backend/src/makeup-templates/makeup-templates.module.ts`

- [ ] **Step 1: Write failing difficulty tests**

Create `backend/src/makeup-templates/template-library/template-difficulty.service.spec.ts`:

```ts
import { TemplateDifficultyService } from './template-difficulty.service';

describe('TemplateDifficultyService', () => {
  it('calculates MMU total difficulty from step score, product count, and special bonus', () => {
    const service = new TemplateDifficultyService();

    expect(
      service.calculate({
        stepScores: [1.2, 1.8, 2.2],
        productSlotCount: 6,
        specialTechniqueCount: 1,
      }),
    ).toEqual({
      stepScore: 2.2,
      productCountWeight: 0.6,
      specialTechniqueBonus: 3,
      totalDifficultyScore: 5.8,
      level: 'L5',
    });
  });

  it('maps easy five-step template to L2 without special techniques', () => {
    const service = new TemplateDifficultyService();

    expect(
      service.calculate({
        stepScores: [1.2, 1.5, 1.8],
        productSlotCount: 4,
        specialTechniqueCount: 0,
      }),
    ).toEqual({
      stepScore: 1.8,
      productCountWeight: 0.4,
      specialTechniqueBonus: 0,
      totalDifficultyScore: 2.2,
      level: 'L2',
    });
  });
});
```

- [ ] **Step 2: Write failing history preference tests**

Create `backend/src/makeup-templates/template-library/template-history-preference.service.spec.ts`:

```ts
import { TemplateHistoryPreferenceService } from './template-history-preference.service';

describe('TemplateHistoryPreferenceService', () => {
  it('returns insufficient history when user has no prior template events', async () => {
    const prisma = {
      templateEvent: {
        findMany: jest.fn().mockResolvedValue([]),
      },
    };
    const service = new TemplateHistoryPreferenceService(prisma as never);

    await expect(
      service.score({
        userId: 'user-001',
        styleFamily: 'DAILY_COMMUTE',
        productSubCategories: ['foundation'],
      }),
    ).resolves.toEqual({
      score: 0,
      reason: 'insufficient_history',
    });
  });

  it('scores matching completed history higher than unrelated history', async () => {
    const prisma = {
      templateEvent: {
        findMany: jest.fn().mockResolvedValue([
          {
            eventName: 'template_feedback_submitted',
            payload: {
              styleFamily: 'DAILY_COMMUTE',
              satisfaction: 'satisfied',
              usedProductSubCategories: ['foundation', 'lip'],
            },
          },
          {
            eventName: 'template_feedback_submitted',
            payload: {
              styleFamily: 'WESTERN',
              satisfaction: 'unsatisfied',
              usedProductSubCategories: ['eyeliner'],
            },
          },
        ]),
      },
    };
    const service = new TemplateHistoryPreferenceService(prisma as never);

    await expect(
      service.score({
        userId: 'user-001',
        styleFamily: 'DAILY_COMMUTE',
        productSubCategories: ['foundation'],
      }),
    ).resolves.toEqual({
      score: 0.75,
      reason: 'matched_positive_history',
    });
  });
});
```

- [ ] **Step 3: Run tests and verify they fail**

Run:

```bash
cd backend
npm test -- template-difficulty.service.spec.ts template-history-preference.service.spec.ts --runInBand
```

Expected: FAIL because services do not exist.

- [ ] **Step 4: Implement difficulty service**

Create `backend/src/makeup-templates/template-library/template-difficulty.service.ts`:

```ts
import { Injectable } from '@nestjs/common';
import type { TemplateDifficultyBreakdown } from './standard-template-library.types';

@Injectable()
export class TemplateDifficultyService {
  calculate(input: {
    stepScores: number[];
    productSlotCount: number;
    specialTechniqueCount: number;
  }): TemplateDifficultyBreakdown {
    const stepScore = round1(Math.max(0, ...input.stepScores));
    const productCountWeight = round1(Math.max(0, input.productSlotCount) * 0.1);
    const specialTechniqueBonus = Math.max(0, input.specialTechniqueCount) * 3;
    const totalDifficultyScore = round1(
      stepScore + productCountWeight + specialTechniqueBonus,
    );

    return {
      stepScore,
      productCountWeight,
      specialTechniqueBonus,
      totalDifficultyScore,
      level: toLevel(totalDifficultyScore),
    };
  }
}

function toLevel(score: number): TemplateDifficultyBreakdown['level'] {
  if (score <= 1.5) return 'L1';
  if (score <= 2.5) return 'L2';
  if (score <= 3.5) return 'L3';
  if (score <= 4.5) return 'L4';
  return 'L5';
}

function round1(value: number) {
  return Math.round(value * 10) / 10;
}
```

- [ ] **Step 5: Implement history preference service**

Create `backend/src/makeup-templates/template-library/template-history-preference.service.ts`:

```ts
import { Injectable } from '@nestjs/common';
import type { PrismaService } from '../../prisma/prisma.service';

@Injectable()
export class TemplateHistoryPreferenceService {
  constructor(private readonly prisma: PrismaService) {}

  async score(input: {
    userId: string;
    styleFamily: string;
    productSubCategories: string[];
  }): Promise<{ score: number; reason: string }> {
    const events = await this.prisma.templateEvent.findMany({
      where: {
        userId: input.userId,
        eventName: {
          in: [
            'template_feedback_submitted',
            'template_execution_completed',
            'template_generation_completed',
          ],
        },
      },
      orderBy: { createdAt: 'desc' },
      take: 20,
    });

    if (events.length === 0) {
      return { score: 0, reason: 'insufficient_history' };
    }

    let score = 0;
    for (const event of events) {
      const payload = event.payload as Record<string, unknown>;
      if (payload.styleFamily === input.styleFamily) {
        score += 0.45;
      }
      if (payload.satisfaction === 'satisfied') {
        score += 0.2;
      }
      if (payload.satisfaction === 'unsatisfied') {
        score -= 0.2;
      }
      const used = Array.isArray(payload.usedProductSubCategories)
        ? payload.usedProductSubCategories.filter(
            (item): item is string => typeof item === 'string',
          )
        : [];
      if (
        used.some((category) => input.productSubCategories.includes(category))
      ) {
        score += 0.1;
      }
    }

    const normalized = Math.max(0, Math.min(1, Math.round(score * 100) / 100));
    return {
      score: normalized,
      reason:
        normalized > 0 ? 'matched_positive_history' : 'history_not_aligned',
    };
  }
}
```

- [ ] **Step 6: Update matching service tests for mandatory model behavior and scoring**

In `template-matching.service.spec.ts`:

- Replace `selects clear commute template with no-model fallback` with:

```ts
it('throws when embedding service is unavailable', async () => {
  embedTextSpy.mockResolvedValue({
    status: 'unavailable',
    model: 'Qwen3-Embedding-4B',
    latencyMs: 1,
    vector: [],
    errorMessage: 'missing',
  });
  rerankSpy.mockResolvedValue({
    status: 'configured',
    model: 'Qwen3-Reranker-8B',
    latencyMs: 1,
    scores: [1],
  });

  await expect(
    service.match(buildProfile('清透通勤妆')),
  ).rejects.toMatchObject({
    response: expect.objectContaining({
      code: 'TEMPLATE_EMBEDDING_UNAVAILABLE',
    }),
  });
});
```

- Add reranker unavailable equivalent.
- Update successful tests so `embedTextSpy` returns `{ status: 'configured', model, latencyMs, vector }` and `rerankSpy` returns configured scores.
- Assert:

```ts
expect(result.degraded).toBe(false);
expect(result.templateTraceId).toMatch(/^mtrace_/);
expect(result.difficultyBreakdown.level).toMatch(/^L[1-5]$/);
expect(result.historyPreferenceScore).toBeGreaterThanOrEqual(0);
expect(result.productCoverageBreakdown.requiredSlots).toBeGreaterThan(0);
```

- [ ] **Step 7: Update matching service implementation**

Inject `TemplateDifficultyService`, `TemplateHistoryPreferenceService`, and `TemplateMatchLoggerService`.

At the start of `match(profile)`:

```ts
const templateTraceId = createMakeupTemplateId('matchTrace');
this.logger.log({
  templateTraceId,
  event: 'request_received',
  data: { rawUserInput: profile.rawUserInput },
});
```

After `embedText`:

```ts
if (embedding.status !== 'configured' || embedding.vector.length === 0) {
  this.logger.warn({
    templateTraceId,
    event: 'embedding_failed',
    data: { status: embedding.status, error: embedding.errorMessage },
  });
  throw new TemplateModelUnavailableException(
    'TEMPLATE_EMBEDDING_UNAVAILABLE',
    embedding.errorMessage ?? 'Template embedding service is unavailable',
    templateTraceId,
  );
}
```

After `rerank`, throw `TEMPLATE_RERANKER_UNAVAILABLE` if status is not configured or score count is invalid.

For each candidate, compute:

```ts
const historyPreference = await this.historyPreference.score({
  userId: profile.userId,
  styleFamily: template.styleFamily,
  productSubCategories: profile.preferredProductCategories,
});
const difficulty = this.difficulty.calculate({
  stepScores: template.stepBlocks.map((step) => step.difficultyScore),
  productSlotCount: template.productSlots.length,
  specialTechniqueCount: template.styleTags.filter((tag) =>
    ['CUT_CREASE', 'STAGE', 'CREATIVE'].includes(tag),
  ).length,
});
```

Add `referenceImageFit`, `faceShapeFit`, `historyPreference`, and improved `difficultyPenalty` to score breakdown. Keep scores clamped.

Set result:

```ts
return {
  templateTraceId,
  profile,
  selected,
  candidates,
  modelStatus: {
    embedding: embedding.status,
    reranker: rerank.status,
    vlm: profile.referenceImageFeatures ? 'configured' : 'skipped',
  },
  degraded: false,
  referenceImageFeatures: profile.referenceImageFeatures,
  faceShapeAdjustments,
  difficultyBreakdown,
  productCoverageBreakdown,
  historyPreferenceScore: selected.breakdown.historyPreference,
};
```

- [ ] **Step 8: Register services**

In `makeup-templates.module.ts`, add:

```ts
TemplateDifficultyService,
TemplateHistoryPreferenceService,
```

- [ ] **Step 9: Run focused tests**

Run:

```bash
cd backend
npm test -- template-difficulty.service.spec.ts template-history-preference.service.spec.ts template-matching.service.spec.ts --runInBand
```

Expected: PASS.

- [ ] **Step 10: Commit matching scoring**

```bash
cd backend
git add src/makeup-templates/template-library/template-difficulty.service.ts src/makeup-templates/template-library/template-difficulty.service.spec.ts src/makeup-templates/template-library/template-history-preference.service.ts src/makeup-templates/template-library/template-history-preference.service.spec.ts src/makeup-templates/template-library/template-matching.service.ts src/makeup-templates/template-library/template-matching.service.spec.ts src/makeup-templates/makeup-templates.module.ts
git commit -m "feat: add mmu template scoring evidence"
```

---

## Task 4: Persist Evidence Through Template Generation And Recommendation Mapping

**Files:**
- Modify: `backend/src/makeup-templates/dto/generate-makeup-template.dto.ts`
- Modify: `backend/src/makeup-templates/makeup-template-generation.service.ts`
- Modify: `backend/src/makeup-templates/makeup-template.mapper.ts`
- Modify: `backend/src/makeup-templates/template-library/template-match-profile.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-blueprint-adapter.service.ts`
- Modify: `backend/src/recommendations/recommendations.service.ts`
- Modify: `backend/src/recommendations/recommendation.mapper.ts`
- Test: `backend/src/makeup-templates/makeup-template-generation.service.spec.ts`
- Test: `backend/src/recommendations/recommendations.service.spec.ts`

- [ ] **Step 1: Extend generate DTO**

In `generate-makeup-template.dto.ts`, add:

```ts
  @ApiPropertyOptional({
    example: 'data:image/png;base64,iVBORw0KGgo=',
    description: 'Optional local reference makeup image as a data URL.',
  })
  @IsOptional()
  @IsString()
  @MaxLength(8_000_000)
  referenceImageDataUrl?: string;
```

Restrict `referenceType` to current supported values but keep API compatibility:

```ts
@IsIn(['none', 'image', 'template'])
```

If that would break existing clients, keep validator as-is but in service reject `video` and `creator` with `BadRequestException('Only image reference is supported in this phase')`.

- [ ] **Step 2: Pass face shape and reference features into profile**

In `template-match-profile.service.ts`, extend `TemplateMatchBuildInput` to include:

```ts
referenceImageFeatures?: ReferenceImageFeatures;
```

Return:

```ts
userId: input.user.id,
faceShape: resolveFaceShape(input.rawUserInput, input.user.makeupPreference),
referenceImageFeatures: input.referenceImageFeatures,
```

Implement `resolveFaceShape`:

```ts
function resolveFaceShape(rawUserInput: string, makeupPreference: string) {
  const source = `${rawUserInput} ${makeupPreference}`;
  if (source.includes('圆脸')) return 'round';
  if (source.includes('长脸')) return 'long';
  if (source.includes('短脸')) return 'short';
  if (source.includes('方圆')) return 'square_round';
  if (source.includes('窄脸')) return 'narrow';
  if (source.includes('鹅蛋')) return 'oval';
  return undefined;
}
```

- [ ] **Step 3: Persist standard step codes and difficulty score on generated steps**

In `makeup-template-generation.service.ts`, when creating steps, add:

```ts
standardStepCodes: step.standardStepCodes ?? [],
difficultyScore: step.difficultyScore,
```

When building `templateInclude()`, include these new fields.

In `template-blueprint-adapter.service.ts`, keep existing `standardStepCodes` and `difficultyScore` in blueprint output.

- [ ] **Step 4: Parse reference image before matching**

Inject `TemplateModelClientService` and `TemplateMatchLoggerService` into `MakeupTemplateGenerationService`.

Before building match profile:

```ts
const templateTraceId = createMakeupTemplateId('matchTrace');
let referenceImageFeatures: ReferenceImageFeatures | undefined;
const referenceImage = input.referenceImageDataUrl?.trim();
if (referenceImage) {
  const vlm = await this.modelClient.parseReferenceImage(referenceImage);
  if (vlm.status !== 'configured' || !vlm.features) {
    throw new TemplateModelUnavailableException(
      'REFERENCE_IMAGE_PARSE_FAILED',
      vlm.errorMessage ?? 'Reference image parsing failed',
      templateTraceId,
    );
  }
  referenceImageFeatures = vlm.features;
}
```

Pass `templateTraceId` and `referenceImageFeatures` to matching. If matching currently generates its own trace ID, update it to accept optional `templateTraceId` so one ID spans VLM and matching.

- [ ] **Step 5: Persist trace evidence**

When creating `TemplateMatchTrace`, add the new columns:

```ts
templateTraceId: matchResult.templateTraceId,
embeddingModel: matchResult.modelEvidence.embedding.model,
embeddingStatus: matchResult.modelStatus.embedding,
embeddingLatencyMs: matchResult.modelEvidence.embedding.latencyMs,
embeddingVectorDim: matchResult.modelEvidence.embedding.vectorDim,
rerankerModel: matchResult.modelEvidence.reranker.model,
rerankerStatus: matchResult.modelStatus.reranker,
rerankerLatencyMs: matchResult.modelEvidence.reranker.latencyMs,
vlmModel: matchResult.modelEvidence.vlm?.model,
vlmStatus: matchResult.modelStatus.vlm,
vlmLatencyMs: matchResult.modelEvidence.vlm?.latencyMs,
referenceImageFeatures: matchResult.referenceImageFeatures as Prisma.InputJsonValue,
faceShapeAdjustments: matchResult.faceShapeAdjustments as Prisma.InputJsonValue,
difficultyBreakdown: matchResult.difficultyBreakdown as Prisma.InputJsonValue,
productCoverageBreakdown: matchResult.productCoverageBreakdown as Prisma.InputJsonValue,
historyPreferenceScore: matchResult.historyPreferenceScore,
```

Keep existing `profile`, `scoreBreakdown`, `modelStatus`, `candidates`.

- [ ] **Step 6: Map evidence to template response**

In `makeup-template.mapper.ts`, add trace fields to `TemplateWithIncludes`:

```ts
matchTrace?: {
  templateTraceId?: string | null;
  modelStatus: unknown;
  scoreBreakdown: unknown;
  referenceImageFeatures?: unknown;
  faceShapeAdjustments?: unknown;
  difficultyBreakdown?: unknown;
  historyPreferenceScore?: number | null;
} | null;
```

Return:

```ts
templateTraceId: template.matchTrace?.templateTraceId ?? template.matchTraceId ?? undefined,
modelStatus: normalizeModelStatus(template.matchTrace?.modelStatus),
scoreBreakdown: normalizeScoreBreakdown(template.matchTrace?.scoreBreakdown),
referenceImageFeatures: asRecord(template.matchTrace?.referenceImageFeatures),
faceShapeAdjustments: asArrayRecords(template.matchTrace?.faceShapeAdjustments),
difficultyBreakdown: asRecord(template.matchTrace?.difficultyBreakdown),
historyPreferenceScore: template.matchTrace?.historyPreferenceScore ?? undefined,
```

For each step return:

```ts
standardStepCodes: step.standardStepCodes,
difficultyScore: step.difficultyScore ?? undefined,
```

- [ ] **Step 7: Include evidence in recommendations**

In `recommendations.service.ts`, extend `GENERATED_TEMPLATE_INCLUDE` to select:

```ts
matchTraceId: true,
matchTrace: {
  select: {
    templateTraceId: true,
    modelStatus: true,
    scoreBreakdown: true,
    referenceImageFeatures: true,
    faceShapeAdjustments: true,
    difficultyBreakdown: true,
    historyPreferenceScore: true,
  },
},
```

In step select include:

```ts
standardStepCodes: true,
difficultyScore: true,
```

In `recommendation.mapper.ts`, add fields to result and each step.

- [ ] **Step 8: Run generation and recommendation tests**

Run:

```bash
cd backend
npm test -- makeup-template-generation.service.spec.ts recommendations.service.spec.ts --runInBand
```

Expected: PASS.

- [ ] **Step 9: Commit evidence persistence**

```bash
cd backend
git add src/makeup-templates/dto/generate-makeup-template.dto.ts src/makeup-templates/makeup-template-generation.service.ts src/makeup-templates/makeup-template.mapper.ts src/makeup-templates/template-library/template-match-profile.service.ts src/makeup-templates/template-library/template-blueprint-adapter.service.ts src/recommendations/recommendations.service.ts src/recommendations/recommendation.mapper.ts src/makeup-templates/makeup-template-generation.service.spec.ts src/recommendations/recommendations.service.spec.ts
git commit -m "feat: persist template matching evidence"
```

---

## Task 5: Expand MMU Seed Data And Management Fields

**Files:**
- Modify: `backend/src/makeup-templates/template-library/template-library.seed-data.ts`
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.data.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-seed.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-admin.service.spec.ts`
- Modify: `frontend/app/template-library/detail.tsx`

- [ ] **Step 1: Add seed tests for MMU taxonomy minimums**

In `template-library-seed.service.spec.ts`, add:

```ts
expect(prisma.templateProductCategory.upsert).toHaveBeenCalledWith(
  expect.objectContaining({
    where: { categoryCode: 'foundation' },
    create: expect.objectContaining({
      parentCode: 'base',
      textureTags: expect.arrayContaining(['dewy', 'matte', 'long_lasting']),
      shadeTags: expect.arrayContaining(['cool_fair', 'warm_fair', 'natural']),
    }),
  }),
);
expect(prisma.templateProductCategory.upsert).toHaveBeenCalledWith(
  expect.objectContaining({
    where: { categoryCode: 'eyeliner' },
    create: expect.objectContaining({
      parentCode: 'eye',
      functionTags: expect.arrayContaining(['inner_line', 'winged_line']),
    }),
  }),
);
expect(prisma.templateDifficultyRule.upsert).toHaveBeenCalledWith(
  expect.objectContaining({
    where: { actionCode: 'false_lashes_lower_lashes_precise_concealer' },
    create: expect.objectContaining({ baseScore: 2.5 }),
  }),
);
```

- [ ] **Step 2: Run seed tests and verify they fail**

Run:

```bash
cd backend
npm test -- template-library-seed.service.spec.ts --runInBand
```

Expected: FAIL because detailed subcategories are not all seeded.

- [ ] **Step 3: Expand product category seed**

In `template-library.seed-data.ts`, keep the 9 parent categories and add child records. Use explicit IDs and sort orders:

```ts
{
  id: 'cat_foundation',
  categoryCode: 'foundation',
  displayName: '粉底液',
  parentCode: 'base',
  aliases: ['粉底', '粉底液', 'foundation'],
  textureTags: ['dewy', 'matte', 'long_lasting', 'skincare_base'],
  functionTags: ['tone_even', 'coverage', 'base'],
  shadeTags: ['cool_fair', 'warm_fair', 'natural', 'wheat'],
  sortOrder: 210,
}
```

Add child records for at least:

```text
toner, lotion_cream, sunscreen, primer, foundation, cushion, concealer,
loose_powder, powder_compact, setting_spray, brow_pencil, brow_powder,
brow_gel, brow_mascara, eyeshadow, eyeliner, eyelash_curler, mascara,
lash_primer, false_lashes, lash_glue, double_eyelid_tape, contour,
highlight, blush, lip_balm, lipstick, lip_glaze, lip_mud, lip_liner,
makeup_remover_water, makeup_remover_oil, makeup_remover_balm,
makeup_wipes, brush_set, puff
```

- [ ] **Step 4: Expand difficulty rules**

Replace generalized difficulty rules with MMU-aligned action codes while keeping old codes if tests rely on them:

```ts
{
  id: 'difficulty_cleanse_toner_lotion_sunscreen',
  actionCode: 'cleanse_toner_lotion_sunscreen',
  displayName: '洁面爽肤乳液防晒',
  baseScore: 1.0,
  productPenalty: 0,
  specialBonus: 0,
  tags: ['prep', 'beginner'],
},
{
  id: 'difficulty_eyeliner_mascara_contour_lip_liner',
  actionCode: 'eyeliner_mascara_contour_lip_liner',
  displayName: '眼线睫毛膏修容唇线',
  baseScore: 2.2,
  productPenalty: 0.2,
  specialBonus: 0,
  tags: ['precision'],
},
{
  id: 'difficulty_false_lashes_lower_lashes_precise_concealer',
  actionCode: 'false_lashes_lower_lashes_precise_concealer',
  displayName: '假睫毛下睫毛精准遮瑕',
  baseScore: 2.5,
  productPenalty: 0.3,
  specialBonus: 0,
  tags: ['advanced'],
}
```

- [ ] **Step 5: Verify five-step templates still map to MMU 14-step codes**

In `standard-template-library.data.ts`, ensure the five blocks have:

```ts
BASE: ['SKIN_PREP', 'SUNSCREEN_PRIMER', 'CONCEALER', 'FOUNDATION', 'SETTING']
BROW: ['BROW']
EYE: ['EYESHADOW', 'LASH', 'EYELINER']
CHEEK: ['CONTOUR', 'HIGHLIGHT', 'BLUSH']
LIP: ['LIP', 'SECOND_SETTING']
```

Keep user-facing `STANDARD_MAKEUP_TEMPLATES` at 5 step blocks.

- [ ] **Step 6: Improve frontend template detail editing visibility**

In `frontend/app/template-library/detail.tsx`, add visible fields:

For each step card, show:

```tsx
<Text className="mt-2 text-[12px] text-[#8D817B]">
  标准步骤：{step.standardStepCodes.join(' / ')}
</Text>
<Text className="mt-1 text-[12px] text-[#8D817B]">
  操作区域：{step.operationAreas.join(' / ')}
</Text>
<Text className="mt-1 text-[12px] text-[#8D817B]">
  难度分：{step.difficultyScore.toFixed(1)}
</Text>
```

For each slot card, show:

```tsx
<Text className="text-[12px] text-[#8D817B]">
  可接受子类：{slot.acceptableSubCategories.join(' / ') || '无'}
</Text>
<Text className="text-[12px] text-[#8D817B]">
  目标质地：{slot.desiredFinish.join(' / ') || '无'}
</Text>
```

If existing UI already has editable JSON/draft controls, do not add a large new form; keep this as visible/editable through existing draft state.

- [ ] **Step 7: Run backend seed tests and frontend checks**

Run:

```bash
cd backend
npm test -- template-library-seed.service.spec.ts template-library-admin.service.spec.ts --runInBand
cd ../frontend
npx tsc --noEmit
npm run lint
```

Expected: PASS.

- [ ] **Step 8: Commit MMU taxonomy expansion**

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
git -C backend add src/makeup-templates/template-library/template-library.seed-data.ts src/makeup-templates/template-library/standard-template-library.data.ts src/makeup-templates/template-library/template-library-seed.service.spec.ts src/makeup-templates/template-library/template-library-admin.service.spec.ts
git -C backend commit -m "feat: expand mmu template taxonomy"
git -C frontend add app/template-library/detail.tsx
git -C frontend commit -m "feat: show mmu template management fields"
```

---

## Task 6: Add Match Debug API Reference Image Support And Recommendation API Evidence

**Files:**
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Modify: `backend/src/recommendations/dto/generate-recommendation.dto.ts`
- Modify: `backend/src/recommendations/recommendations.service.ts`
- Test: `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`
- Test: `backend/test/app.e2e-spec.ts`

- [ ] **Step 1: Write failing controller/e2e tests**

In `template-library.controller.spec.ts`, add a match-debug test:

```ts
it('returns trace evidence for match-debug with reference image', async () => {
  matchingService.match.mockResolvedValue({
    templateTraceId: 'mtrace_20260511_debug',
    selected: {
      template: {
        id: 'std_daily_clear_commute',
        sourceTemplateVersionId: 'std_daily_clear_commute_v1',
        styleFamily: 'DAILY_COMMUTE',
        displayName: '清透通勤标准模板',
      },
      score: 0.88,
      reasons: ['参考图妆效匹配。'],
      breakdown: {
        embeddingSimilarity: 0.8,
        rerankerRelevance: 0.9,
        styleMatch: 0.8,
        sceneMatch: 1,
        referenceImageFit: 0.7,
        productCoverage: 0.6,
        userProfileFit: 0.5,
        historyPreference: 0,
        difficultyPenalty: 0,
        missingRequiredSlotPenalty: 0.2,
      },
    },
    candidates: [],
    modelStatus: { embedding: 'configured', reranker: 'configured', vlm: 'configured' },
    degraded: false,
    referenceImageFeatures: { styleSignals: ['clean'] },
    faceShapeAdjustments: [],
    difficultyBreakdown: {
      stepScore: 1.8,
      productCountWeight: 0.5,
      specialTechniqueBonus: 0,
      totalDifficultyScore: 2.3,
      level: 'L2',
    },
    productCoverageBreakdown: {
      requiredSlots: 3,
      matchedRequiredSlots: 2,
      coverageRate: 0.67,
      missingRequiredSlotCodes: ['BROW_PENCIL'],
    },
    historyPreferenceScore: 0,
  });

  const result = await controller.matchDebug(user, {
    rawUserInput: '参考图同款清透妆',
    referenceImageDataUrl: 'data:image/png;base64,AAAA',
  });

  expect(result.templateTraceId).toBe('mtrace_20260511_debug');
  expect(result.modelStatus.vlm).toBe('configured');
  expect(result.referenceImageFeatures).toEqual({ styleSignals: ['clean'] });
});
```

In `backend/test/app.e2e-spec.ts`, add this e2e case near the existing recommendation generation tests:

```ts
it('/recommendations/generate returns model evidence and MMU step codes', async () => {
  const response = await request(app.getHttpServer())
    .post('/recommendations/generate')
    .set('Authorization', `Bearer ${DEMO_TOKEN}`)
    .send({
      userId: 'user-001',
      scenario: '通勤',
      scenarioDetails: '明天上班想要清透通勤妆，优先用已有产品',
    })
    .expect(201);

  expect(response.body.generatedTemplateId).toMatch(/^tmpl_/);
  expect(response.body.templateTraceId).toMatch(/^mtrace_/);
  expect(response.body.modelStatus).toEqual({
    embedding: 'configured',
    reranker: 'configured',
    vlm: 'skipped',
  });
  expect(response.body.scoreBreakdown).toEqual(
    expect.objectContaining({
      embeddingSimilarity: expect.any(Number),
      rerankerRelevance: expect.any(Number),
    }),
  );
  expect(response.body.steps).toHaveLength(5);
  expect(response.body.steps[0].standardStepCodes).toEqual(
    expect.arrayContaining(['SKIN_PREP', 'FOUNDATION']),
  );
});
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd backend
npm test -- template-library.controller.spec.ts --runInBand
npm run test:e2e -- --runInBand
```

Expected: FAIL until controller and recommendation DTO support evidence.

- [ ] **Step 3: Extend match-debug DTO**

In `template-library.controller.ts`, update `TemplateMatchDebugRequestDto`:

```ts
@ApiPropertyOptional({ example: 'data:image/png;base64,AAAA' })
@IsOptional()
@IsString()
referenceImageDataUrl?: string;
```

Use `modelClient.parseReferenceImage` or reuse a helper from generation service so reference parsing logic is not duplicated. Prefer creating a private controller helper only if it stays below 40 lines; otherwise extract a service.

- [ ] **Step 4: Return evidence from match-debug**

Return:

```ts
templateTraceId: result.templateTraceId,
selectedTemplateId: result.selected.template.id,
selectedTemplateVersionId: result.selected.template.sourceTemplateVersionId,
selectedFamily: result.selected.template.styleFamily,
selectedScore: result.selected.score,
modelStatus: result.modelStatus,
referenceImageFeatures: result.referenceImageFeatures,
scoreBreakdown: result.selected.breakdown,
difficultyBreakdown: result.difficultyBreakdown,
faceShapeAdjustments: result.faceShapeAdjustments,
historyPreferenceScore: result.historyPreferenceScore,
productCoverageBreakdown: result.productCoverageBreakdown,
```

- [ ] **Step 5: Add recommendation reference image payload**

In `backend/src/recommendations/dto/generate-recommendation.dto.ts`, add:

```ts
@ApiPropertyOptional({ example: 'data:image/png;base64,AAAA' })
@IsOptional()
@IsString()
@MaxLength(8_000_000)
referenceImageDataUrl?: string;
```

In `recommendations.service.ts`, pass:

```ts
referenceType: payload.referenceImageDataUrl ? 'image' : 'none',
referenceImageDataUrl: payload.referenceImageDataUrl,
```

to `makeupTemplateGenerationService.generate`.

- [ ] **Step 6: Run controller and e2e tests**

Run:

```bash
cd backend
npm test -- template-library.controller.spec.ts --runInBand
npm run test:e2e -- --runInBand
```

Expected: PASS.

- [ ] **Step 7: Commit API evidence support**

```bash
cd backend
git add src/makeup-templates/template-library/template-library.controller.ts src/makeup-templates/template-library/template-library.controller.spec.ts src/recommendations/dto/generate-recommendation.dto.ts src/recommendations/recommendations.service.ts test/app.e2e-spec.ts
git commit -m "feat: expose model-backed template evidence api"
```

---

## Task 7: Update Frontend Generated Recommendation Flow And Evidence UI

**Files:**
- Modify: `frontend/types/recommendation.ts`
- Modify: `frontend/store/demo-store.ts`
- Modify: `frontend/services/recommendationService.ts`
- Modify: `frontend/hooks/use-demo-queries.ts`
- Modify: `frontend/app/recommendation/scenario.tsx`
- Modify: `frontend/app/recommendation/result.tsx`
- Modify: `frontend/app/recommendation/products.tsx`

- [ ] **Step 1: Extend frontend recommendation types**

In `frontend/types/recommendation.ts`, add:

```ts
export interface TemplateModelStatus {
  embedding: 'configured' | 'unavailable' | 'failed' | 'skipped';
  reranker: 'configured' | 'unavailable' | 'failed' | 'skipped';
  vlm: 'configured' | 'unavailable' | 'failed' | 'skipped';
}

export interface TemplateScoreBreakdown {
  embeddingSimilarity: number;
  rerankerRelevance: number;
  styleMatch: number;
  sceneMatch: number;
  referenceImageFit?: number;
  productCoverage: number;
  userProfileFit: number;
  historyPreference: number;
  difficultyPenalty: number;
  missingRequiredSlotPenalty: number;
}

export interface TemplateDifficultyBreakdown {
  stepScore: number;
  productCountWeight: number;
  specialTechniqueBonus: number;
  totalDifficultyScore: number;
  level: string;
}

export interface ReferenceImageFeatures {
  baseFinish?: string;
  eyeIntensity?: number;
  blushPlacement?: string;
  lipColorFamily?: string;
  styleSignals?: string[];
}
```

Add to `RecommendationResultStep`:

```ts
standardStepCodes?: string[];
difficultyScore?: number;
```

Add to `RecommendationResult`:

```ts
sourceStandardTemplateVersionId?: string;
templateTraceId?: string;
modelStatus?: TemplateModelStatus;
scoreBreakdown?: TemplateScoreBreakdown;
difficultyBreakdown?: TemplateDifficultyBreakdown;
referenceImageFeatures?: ReferenceImageFeatures;
faceShapeAdjustments?: Array<{ target: string; scoreDelta: number; reason: string }>;
historyPreferenceScore?: number;
```

- [ ] **Step 2: Store reference image**

In `frontend/store/demo-store.ts`, add state:

```ts
recommendationReferenceImageDataUrl: string | null;
setRecommendationReferenceImageDataUrl: (dataUrl: string | null) => void;
```

Initialize to `null`, clear on logout and `selectRecommendationTemplate`, and implement setter.

- [ ] **Step 3: Remove local fallback for authenticated generated path**

In `frontend/services/recommendationService.ts`, update `GenerateRecommendationParams`:

```ts
referenceImageDataUrl?: string | null;
```

When `currentUser?.id` exists, do not catch backend errors and return local fallback. Instead:

```ts
result = await apiRequest<RecommendationResult>('/recommendations/generate', {
  method: 'POST',
  body: {
    scenario: normalizedInput.scenario,
    userId: params.currentUser.id,
    ...(normalizedInput.scenarioDetails ? { scenarioDetails: normalizedInput.scenarioDetails } : {}),
    ...(normalizedInput.requirements.length ? { requirements: normalizedInput.requirements } : {}),
    ...(params.referenceImageDataUrl ? { referenceImageDataUrl: params.referenceImageDataUrl } : {}),
  },
});
```

Keep fallback only for unauthenticated or explicit static template mode.

- [ ] **Step 4: Include reference image in query**

In `frontend/hooks/use-demo-queries.ts`, update:

```ts
export function useGeneratedRecommendationQuery(
  scenario: string,
  userId?: string,
  enabled = true,
  referenceImageDataUrl?: string | null,
) {
  return useQuery({
    queryKey: ['generated-recommendation', userId, scenario, referenceImageDataUrl ? 'with-reference' : 'no-reference'],
    queryFn: async () => ...
  });
}
```

Pass `referenceImageDataUrl` to service.

Update all call sites to pass the store value where generated mode is used.

- [ ] **Step 5: Add reference image picker to scenario screen**

In `frontend/app/recommendation/scenario.tsx`, import:

```ts
import * as ImagePicker from 'expo-image-picker';
```

Add store setter:

```ts
const setReferenceImage = useDemoStore((state) => state.setRecommendationReferenceImageDataUrl);
const referenceImageDataUrl = useDemoStore((state) => state.recommendationReferenceImageDataUrl);
```

Add function:

```ts
async function pickReferenceImage() {
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ImagePicker.MediaTypeOptions.Images,
    allowsEditing: true,
    quality: 0.65,
    base64: true,
  });

  if (result.canceled || !result.assets[0]?.base64) {
    return;
  }

  const asset = result.assets[0];
  setReferenceImage(`data:${asset.mimeType ?? 'image/jpeg'};base64,${asset.base64}`);
}
```

Add a visible control after `AssetMatchPreview`:

```tsx
<Pressable
  onPress={pickReferenceImage}
  className="mt-6 flex-row items-center justify-between rounded-[18px] border border-[#E8DDD8] bg-white px-5 py-4">
  <View className="flex-1 pr-4">
    <Text className="text-[16px] font-semibold text-[#171312]">参考妆容图片</Text>
    <Text className="mt-1 text-[13px] text-[#7A6E68]">
      {referenceImageDataUrl ? '已选择，将用于 VLM 妆效解析。' : '可选，上传后会影响模板匹配。'}
    </Text>
  </View>
  <Ionicons name={referenceImageDataUrl ? 'checkmark-circle' : 'image-outline'} size={24} color={BRAND} />
</Pressable>
```

- [ ] **Step 6: Add evidence card to result screen**

In `frontend/app/recommendation/result.tsx`, create:

```tsx
function ModelEvidencePanel({ result }: { result: RecommendationResult }) {
  const model = result.modelStatus;
  return (
    <View className="mt-5 rounded-[18px] border border-[#EFE3DD] bg-[#FFFCFB] px-5 py-5">
      <Text className="text-[13px] font-semibold uppercase tracking-[1px] text-[#9B4E5D]">Model Evidence</Text>
      <Text className="mt-2 text-[18px] font-semibold text-[#171312]">Trace {result.templateTraceId ?? '-'}</Text>
      <View className="mt-4 flex-row gap-3">
        <EvidencePill label="Embedding" value={model?.embedding ?? '-'} />
        <EvidencePill label="Rerank" value={model?.reranker ?? '-'} />
        <EvidencePill label="VLM" value={model?.vlm ?? 'skipped'} />
      </View>
      {result.scoreBreakdown ? (
        <Text className="mt-4 text-[13px] leading-5 text-[#6D625C]">
          语义 {Math.round(result.scoreBreakdown.embeddingSimilarity * 100)}% / 重排 {Math.round(result.scoreBreakdown.rerankerRelevance * 100)}% / 产品覆盖 {Math.round(result.scoreBreakdown.productCoverage * 100)}%
        </Text>
      ) : null}
      {result.referenceImageFeatures?.styleSignals?.length ? (
        <Text className="mt-2 text-[13px] leading-5 text-[#6D625C]">
          参考图：{result.referenceImageFeatures.styleSignals.join('、')}
        </Text>
      ) : null}
      {result.difficultyBreakdown ? (
        <Text className="mt-2 text-[13px] leading-5 text-[#6D625C]">
          难度 {result.difficultyBreakdown.level}，总分 {result.difficultyBreakdown.totalDifficultyScore.toFixed(1)}
        </Text>
      ) : null}
    </View>
  );
}

function EvidencePill({ label, value }: { label: string; value: string }) {
  return (
    <View className="flex-1 rounded-[12px] bg-[#F8F4F2] px-3 py-3">
      <Text className="text-[11px] text-[#8D817B]">{label}</Text>
      <Text className="mt-1 text-[13px] font-semibold text-[#171312]">{value}</Text>
    </View>
  );
}
```

Render `<ModelEvidencePanel result={result} />` after `TemplateEvidenceCard`.

Update empty error copy to:

```tsx
{isError ? t('模板匹配模型服务未就绪，请检查 embedding/rerank 服务后重试。') : ...}
```

- [ ] **Step 7: Show standard step codes in result and products pages**

In result step overview:

```tsx
{step.standardStepCodes?.length ? (
  <Text className="mt-1 text-[12px] text-[#8D817B]">
    MMU：{step.standardStepCodes.join(' / ')}
  </Text>
) : null}
```

In `frontend/app/recommendation/products.tsx`, add this line below each step title/instruction block:

```tsx
{step.standardStepCodes?.length ? (
  <Text className="mt-1 text-[12px] text-[#8D817B]">
    MMU：{step.standardStepCodes.join(' / ')}
  </Text>
) : null}
```

- [ ] **Step 8: Run frontend checks**

Run:

```bash
cd frontend
npx tsc --noEmit
npm run lint
```

Expected: PASS.

- [ ] **Step 9: Commit frontend generated flow**

```bash
cd frontend
git add types/recommendation.ts store/demo-store.ts services/recommendationService.ts hooks/use-demo-queries.ts app/recommendation/scenario.tsx app/recommendation/result.tsx app/recommendation/products.tsx
git commit -m "feat: show model-backed template evidence"
```

---

## Task 8: Add Runbook, Mock Model Services, And End-To-End Verification

**Files:**
- Create: `scripts/start-template-model-mock-services.mjs`
- Modify: `docs/team-runbook.md`
- Modify: `docs/template-matching-test-guide.md`
- Modify: `backend/test/app.e2e-spec.ts`

- [ ] **Step 1: Create mock service script**

Create `scripts/start-template-model-mock-services.mjs`:

```js
#!/usr/bin/env node
import http from 'node:http';

function readJson(req) {
  return new Promise((resolve, reject) => {
    let body = '';
    req.on('data', (chunk) => {
      body += chunk;
    });
    req.on('end', () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (error) {
        reject(error);
      }
    });
  });
}

function start(port, handler) {
  const server = http.createServer(async (req, res) => {
    try {
      if (req.url === '/health') {
        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ ok: true }));
        return;
      }
      const payload = await readJson(req);
      const result = await handler(req.url, payload);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(result));
    } catch (error) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: String(error) }));
    }
  });
  server.listen(port, '0.0.0.0', () => {
    console.log(`template mock service listening on ${port}`);
  });
}

start(8030, (_url, payload) => ({
  object: 'list',
  data: [
    {
      object: 'embedding',
      index: 0,
      embedding: Array.from({ length: 16 }, (_, index) =>
        String(payload.input ?? '').includes('通勤') && index === 0 ? 1 : 0.1,
      ),
    },
  ],
}));

start(8031, (_url, payload) => ({
  results: (payload.documents ?? []).map((document, index) => ({
    index,
    relevance_score: String(document).includes('通勤') ? 0.95 : 0.2,
  })),
}));

start(8032, () => ({
  choices: [
    {
      message: {
        content: JSON.stringify({
          baseFinish: 'dewy',
          eyeIntensity: 2,
          blushPlacement: 'upper_cheek',
          lipColorFamily: 'bean_paste',
          styleSignals: ['clean', 'soft_eye', 'low_saturation'],
        }),
      },
    },
  ],
}));
```

- [ ] **Step 2: Update runbook**

In `docs/team-runbook.md`, add:

```md
### Template matching model services

For local smoke tests, start mock OpenAI-compatible services:

```bash
node scripts/start-template-model-mock-services.mjs
```

Then set backend env:

```bash
TEMPLATE_EMBEDDING_BASE_URL=http://127.0.0.1:8030
TEMPLATE_RERANKER_BASE_URL=http://127.0.0.1:8031
TEMPLATE_VLM_BASE_URL=http://127.0.0.1:8032
```

Production-like deployment must point these variables to real Qwen embedding, reranker, and VLM services. Template matching does not silently fall back if embedding or reranker is unavailable.

Search logs by `templateTraceId` when debugging.
```
```

- [ ] **Step 3: Update test guide**

In `docs/template-matching-test-guide.md`, add a section:

```md
## Model-backed MMU matching verification

Expected evidence fields:

- `templateTraceId`
- `modelStatus.embedding = configured`
- `modelStatus.reranker = configured`
- `scoreBreakdown.embeddingSimilarity`
- `scoreBreakdown.rerankerRelevance`
- `difficultyBreakdown.level`
- `steps[].standardStepCodes`

If embedding or reranker is down, generation should fail with a clear model unavailable error. This is expected and means the product is not using low-quality rule fallback.
```

- [ ] **Step 4: Add e2e mock env setup**

In `backend/test/app.e2e-spec.ts`, where Prisma and app setup occurs, mock `TemplateModelClientService` with configured responses if e2e is not running external mock services. Use:

```ts
.overrideProvider(TemplateModelClientService)
.useValue({
  embedText: jest.fn().mockResolvedValue({
    status: 'configured',
    model: 'mock-embedding',
    latencyMs: 1,
    vector: [1, 0, 0],
  }),
  rerank: jest.fn().mockResolvedValue({
    status: 'configured',
    model: 'mock-reranker',
    latencyMs: 1,
    scores: [0.95, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2, 0.2],
  }),
  parseReferenceImage: jest.fn().mockResolvedValue({
    status: 'configured',
    model: 'mock-vlm',
    latencyMs: 1,
    features: { styleSignals: ['clean'] },
  }),
})
```

Assert e2e response includes evidence.

- [ ] **Step 5: Run full backend and frontend validation**

Run:

```bash
cd backend
npm run build
npm test -- --runInBand
npm run test:e2e -- --runInBand
cd ../frontend
npx tsc --noEmit
npm run lint
cd ..
bash -n scripts/start-qwen-vl-32b.sh
node --check scripts/start-template-model-mock-services.mjs
```

Expected:

- Backend build passes.
- Backend unit tests pass.
- Backend e2e tests pass.
- Frontend TypeScript passes.
- Frontend lint passes.
- Script syntax checks pass.

- [ ] **Step 6: Commit docs and verification tooling**

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
git add scripts/start-template-model-mock-services.mjs docs/team-runbook.md docs/template-matching-test-guide.md
git commit -m "docs: add template model matching runbook"
```

If `backend/test/app.e2e-spec.ts` changed in this task, commit it in backend:

```bash
git -C backend add test/app.e2e-spec.ts
git -C backend commit -m "test: verify model-backed template journey"
```

---

## Final Verification

- [ ] **Backend full verification**

```bash
cd backend
npm run build
npm test -- --runInBand
npm run test:e2e -- --runInBand
```

Expected: build exits 0; all unit and e2e tests pass.

- [ ] **Frontend full verification**

```bash
cd frontend
npx tsc --noEmit
npm run lint
```

Expected: both commands exit 0.

- [ ] **Top-level verification**

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
bash -n scripts/start-qwen-vl-32b.sh
node --check scripts/start-template-model-mock-services.mjs
git status --short --branch
git -C backend status --short --branch
git -C frontend status --short --branch
```

Expected: syntax checks exit 0. Git status shows only intended committed changes and the existing untracked source docx files remain untracked unless the user explicitly asks to commit them.

## Spec Coverage Checklist

- MMU standard taxonomy seeded and queryable: Task 5.
- Five-step user flow preserved: Tasks 3, 4, 5, 7.
- Five-step blocks map to MMU 14-step codes: Tasks 1, 4, 5, 7.
- Embedding and reranker mandatory: Tasks 2, 3, 6, 8.
- Reference image through VLM: Tasks 2, 4, 6, 7.
- Face shape, difficulty, product coverage, history preference visible in trace/response: Tasks 1, 3, 4, 7.
- Structured logs with `templateTraceId`: Tasks 2, 4, 8.
- Frontend evidence UI: Task 7.
- Runbook and test guide: Task 8.
