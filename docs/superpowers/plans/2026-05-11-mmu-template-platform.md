# MMU Makeup Template Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the platform-level MMU makeup template system across model health, database-backed template management, generated-result persistence, evaluation, preview, AI step evaluation, frontend testing flows, and observability.

**Architecture:** Keep the existing NestJS `makeup-templates`, `makeup`, and `recommendations` modules as the backend boundaries, and extend them with a small `platform` health module plus focused services for result history, preview linkage, and step evaluation. Keep the Expo Router frontend routes already present, and complete the missing UI surfaces rather than creating parallel pages. Existing completed work in `2026-05-10-formal-template-library-platform.md` and `2026-05-11-mmu-template-model-matching.md` is treated as the base layer; this plan fills the remaining platform gaps from `2026-05-11-mmu-template-platform-design.md`.

**Tech Stack:** NestJS 11, Prisma 7, PostgreSQL, Jest, Supertest, Expo Router, React Native, TanStack Query, Zustand, TypeScript, Python stdlib eval scripts.

---

## Existing Foundation

These capabilities already exist and should be extended, not duplicated:

- `backend/src/makeup-templates/template-library/*`: DB-backed standard template library, seed/admin services, model-backed matching, trace evidence, MMU taxonomy.
- `frontend/app/template-library/*`: template library management routes.
- `frontend/app/recommendation/*`: scenario, result, product checklist, preview, execution, coach, live coach routes.
- `eval/template_matching/*`: initial template matching eval script and family cases.
- `scripts/start-template-model-mock-services.mjs`: local mock embedding/rerank/VLM services.

Before implementation, merge/rebase current feature work with remote `origin/main` or `origin/master` per repository, because frontend and backend remote heads have moved.

---

## File Structure

### Top-Level Repo

- Modify `docs/team-runbook.md`
  - Add platform health, eval, trace search, and smoke commands.
- Modify `docs/template-matching-test-guide.md`
  - Update user journey for generated history, preview, and step-evaluate testing.
- Modify `eval/template_matching/cases.json`
  - Upgrade cases to structured profile/product/reference schema.
- Modify `eval/template_matching/run_template_matching_eval.py`
  - Add report output, per-family summary, model-status capture, and generated recommendation path.
- Create `scripts/start-mimu-platform-services.sh`
  - Start model mocks or real configured services with logs.
- Create `scripts/smoke-mimu-platform.sh`
  - Verify health, seed, generation, preview job creation, step-evaluate, and eval.

### Backend Repo

- Create `backend/src/platform/platform.module.ts`
  - Register platform health service/controller.
- Create `backend/src/platform/platform-health.controller.ts`
  - Expose `GET /platform/health`.
- Create `backend/src/platform/platform-health.service.ts`
  - Check database, template model client, coach config, ASR, and ComfyUI.
- Create `backend/src/platform/platform-health.service.spec.ts`
  - Unit test model/database health aggregation.
- Modify `backend/src/app.module.ts`
  - Import `PlatformModule`.
- Modify `backend/src/makeup-templates/makeup-templates.controller.ts`
  - Add generated list, detail alias, event, feedback endpoints under `/makeup-templates/generated`.
- Modify `backend/src/makeup-templates/makeup-template-generation.service.ts`
  - Add list/get generated history helpers with ownership filtering.
- Create `backend/src/makeup-templates/dto/query-generated-templates.dto.ts`
  - Pagination and source filters.
- Create `backend/src/makeup-templates/dto/template-feedback.dto.ts`
  - Satisfaction and free-text feedback DTO.
- Modify `backend/src/makeup-templates/makeup-template-event.service.ts`
  - Add typed feedback and step lifecycle helpers.
- Modify `backend/src/makeup-templates/makeup-template-event.service.spec.ts`
  - Test feedback, step complete, and ownership checks.
- Modify `backend/src/makeup/dto/makeup-job-response.dto.ts`
  - Add preview trace ID, template IDs, comparison metadata.
- Modify `backend/src/makeup/makeup-job.service.ts`
  - Store optional metadata on queued preview jobs.
- Modify `backend/src/makeup/makeup.service.ts`
  - Accept generated template metadata for preview jobs.
- Modify `backend/src/makeup/makeup.controller.ts`
  - Parse multipart metadata and add `POST /makeup/coach/step-evaluate`.
- Modify `backend/src/makeup/dto/makeup-coach.dto.ts`
  - Add step-evaluate request/response fields and trace IDs.
- Modify `backend/src/makeup/makeup-coach.service.ts`
  - Add reusable step evaluation method and trace ID output.
- Modify `backend/src/makeup/makeup-realtime-session.service.ts`
  - Return same completion schema as step-evaluate.
- Modify `backend/test/app.e2e-spec.ts`
  - Add platform e2e smoke for health, seed, generate, event, and step-evaluate.

### Frontend Repo

- Modify `frontend/types/makeup-coach.ts`
  - Add step-evaluate request/response and trace fields.
- Modify `frontend/types/recommendation.ts`
  - Add `generatedTemplateId`, `sourceStandardTemplateVersionId`, `templateTraceId`, and preview metadata fields to the recommendation result types used by preview and history.
- Modify `frontend/types/template-library.ts`
  - Ensure editable step/slot/difficulty fields are typed.
- Modify `frontend/services/makeupCoachService.ts`
  - Add `evaluateStepImage`.
- Modify `frontend/services/virtualTryOnService.ts`
  - Send generated template ID, standard version ID, product slot metadata, and comparison mode.
- Create `frontend/services/generatedTemplateService.ts`
  - List generated templates, record feedback/events.
- Modify `frontend/hooks/use-demo-queries.ts`
  - Add generated template history and platform health queries.
- Modify `frontend/store/demo-store.ts`
  - Persist last generated template ID and last preview job ID.
- Modify `frontend/app/recommendation/preview.tsx`
  - Bind preview request to generated template evidence and show trace ID.
- Modify `frontend/components/recommendation/makeup-try-on-panel.tsx`
  - Add real trace/job metadata and slider/side-by-side states tied to API response.
- Modify `frontend/app/recommendation/execution.tsx`
  - Record step lifecycle events and consume auto-next completion signals.
- Modify `frontend/app/recommendation/coach.tsx`
  - Add still-image upload test entry.
- Modify `frontend/app/recommendation/live-coach.native.tsx`
  - Consume standardized coach completion schema.
- Modify `frontend/app/recommendation/history.tsx`
  - Show generated template history from backend, not only local state.
- Modify `frontend/app/template-library/detail.tsx`
  - Complete editable common fields for steps, slots, operation areas, difficulty, and MMU codes.

---

## Task 1: Merge Remote Heads And Confirm Baseline

**Files:**
- Inspect: top-level git repo
- Inspect: `backend`
- Inspect: `frontend`

- [ ] **Step 1: Fetch all repositories**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
git fetch origin
cd backend
git fetch origin
cd ../frontend
git fetch origin
```

Expected: fetch completes without changing worktree files.

- [ ] **Step 2: Inspect ahead/behind and local changes**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
git status --short --branch
cd backend
git status --short --branch
git log --oneline --decorate --left-right HEAD...origin/master -12
cd ../frontend
git status --short --branch
git log --oneline --decorate --left-right HEAD...origin/main -12
```

Expected: only known untracked product `.docx` files in the top-level repo; backend and frontend worktrees clean.

- [ ] **Step 3: Merge remote main/master into feature branches**

Run backend merge:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
git merge --no-edit origin/master
```

Run frontend merge:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/frontend
git merge --no-edit origin/main
```

Expected: merge succeeds, or conflicts are limited to files touched by this feature. If conflict occurs, keep the current feature implementation for template/model matching behavior and integrate non-overlapping cleanup from remote.

- [ ] **Step 4: Run baseline verification**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
npm run build
npm test -- --runInBand
npm run test:e2e -- --runInBand
cd ../frontend
npx tsc --noEmit
npm run lint
```

Expected: all commands exit 0 before new implementation starts.

- [ ] **Step 5: Commit merge-only changes if any**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
git status --short
git commit -m "chore: merge remote template platform baseline"
cd ../frontend
git status --short
git commit -m "chore: merge remote template platform baseline"
```

Expected: commit only if the merge produced changes. If there is nothing to commit, leave the repo clean.

---

## Task 2: Platform Health And Model Observability

**Files:**
- Create: `backend/src/platform/platform.module.ts`
- Create: `backend/src/platform/platform-health.controller.ts`
- Create: `backend/src/platform/platform-health.service.ts`
- Create: `backend/src/platform/platform-health.service.spec.ts`
- Modify: `backend/src/app.module.ts`
- Modify: `backend/src/makeup-templates/template-library/template-model-client.service.ts`
- Modify: `backend/src/makeup/makeup.service.ts`

- [ ] **Step 1: Write failing health service tests**

Create `backend/src/platform/platform-health.service.spec.ts`:

```ts
import { Test } from '@nestjs/testing';
import { PlatformHealthService } from './platform-health.service';
import { PrismaService } from '../prisma/prisma.service';
import { TemplateModelClientService } from '../makeup-templates/template-library/template-model-client.service';

describe('PlatformHealthService', () => {
  const prisma = {
    $queryRaw: jest.fn(),
  };
  const modelClient = {
    checkEmbeddingHealth: jest.fn(),
    checkRerankerHealth: jest.fn(),
    checkVlmHealth: jest.fn(),
  };

  beforeEach(() => {
    jest.clearAllMocks();
    prisma.$queryRaw.mockResolvedValue([{ ok: 1 }]);
    modelClient.checkEmbeddingHealth.mockResolvedValue({
      configured: true,
      healthy: true,
      model: 'Qwen3-Embedding-4B',
      baseUrl: 'http://127.0.0.1:8030/v1',
      latencyMs: 12,
    });
    modelClient.checkRerankerHealth.mockResolvedValue({
      configured: true,
      healthy: true,
      model: 'Qwen3-Reranker-8B',
      baseUrl: 'http://127.0.0.1:8031/v1',
      latencyMs: 18,
    });
    modelClient.checkVlmHealth.mockResolvedValue({
      configured: true,
      healthy: true,
      model: 'Qwen2.5-VL-32B-Instruct-AWQ',
      baseUrl: 'http://127.0.0.1:8010/v1',
      latencyMs: 25,
    });
  });

  async function createService() {
    const module = await Test.createTestingModule({
      providers: [
        PlatformHealthService,
        { provide: PrismaService, useValue: prisma },
        { provide: TemplateModelClientService, useValue: modelClient },
      ],
    }).compile();

    return module.get(PlatformHealthService);
  }

  it('returns database and model health with model names and latency', async () => {
    const service = await createService();
    const result = await service.getHealth();

    expect(result.backend).toBe('ok');
    expect(result.database).toBe('ok');
    expect(result.models.templateEmbedding).toMatchObject({
      configured: true,
      healthy: true,
      model: 'Qwen3-Embedding-4B',
      latencyMs: 12,
    });
    expect(result.models.templateReranker).toMatchObject({
      configured: true,
      healthy: true,
      model: 'Qwen3-Reranker-8B',
      latencyMs: 18,
    });
    expect(result.models.referenceVlm).toMatchObject({
      configured: true,
      healthy: true,
      model: 'Qwen2.5-VL-32B-Instruct-AWQ',
    });
  });

  it('marks database down without hiding model health', async () => {
    prisma.$queryRaw.mockRejectedValue(new Error('connection refused'));
    const service = await createService();
    const result = await service.getHealth();

    expect(result.backend).toBe('degraded');
    expect(result.database).toBe('down');
    expect(result.models.templateEmbedding.healthy).toBe(true);
  });
});
```

- [ ] **Step 2: Run health tests and verify they fail**

Run:

```bash
cd backend
npm test -- platform-health.service.spec.ts --runInBand
```

Expected: FAIL because `PlatformHealthService` does not exist.

- [ ] **Step 3: Implement platform health module and service**

Create `backend/src/platform/platform-health.service.ts`:

```ts
import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';
import { TemplateModelClientService } from '../makeup-templates/template-library/template-model-client.service';

type ServiceHealth = {
  configured: boolean;
  healthy: boolean;
  baseUrl?: string;
  model?: string;
  latencyMs?: number;
  error?: string;
};

export type PlatformHealthResponse = {
  backend: 'ok' | 'degraded';
  database: 'ok' | 'down';
  models: {
    templateEmbedding: ServiceHealth;
    templateReranker: ServiceHealth;
    referenceVlm: ServiceHealth;
    asr: ServiceHealth;
    coach: ServiceHealth;
    comfyui: ServiceHealth;
  };
};

@Injectable()
export class PlatformHealthService {
  constructor(
    private readonly prisma: PrismaService,
    private readonly modelClient: TemplateModelClientService,
  ) {}

  async getHealth(): Promise<PlatformHealthResponse> {
    const [database, embedding, reranker, vlm, asr, coach, comfyui] =
      await Promise.all([
        this.checkDatabase(),
        this.modelClient.checkEmbeddingHealth(),
        this.modelClient.checkRerankerHealth(),
        this.modelClient.checkVlmHealth(),
        this.checkHttpService('COACH_ASR_BASE_URL', 'ASR'),
        this.checkConfiguredModel('COACH_LLM_BASE_URL', 'COACH_LLM_MODEL'),
        this.checkHttpService('COMFY_UI_BASE_URL', 'ComfyUI'),
      ]);

    const backend = database === 'ok' ? 'ok' : 'degraded';

    return {
      backend,
      database,
      models: {
        templateEmbedding: embedding,
        templateReranker: reranker,
        referenceVlm: vlm,
        asr,
        coach,
        comfyui,
      },
    };
  }

  private async checkDatabase(): Promise<'ok' | 'down'> {
    try {
      await this.prisma.$queryRaw`SELECT 1`;
      return 'ok';
    } catch {
      return 'down';
    }
  }

  private async checkHttpService(
    baseUrlEnv: string,
    label: string,
  ): Promise<ServiceHealth> {
    const baseUrl = process.env[baseUrlEnv]?.trim();

    if (!baseUrl) {
      return {
        configured: false,
        healthy: false,
        error: `${label} base URL is not configured`,
      };
    }

    const startedAt = Date.now();
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 2000);

    try {
      const response = await fetch(`${baseUrl.replace(/\/$/, '')}/health`, {
        signal: controller.signal,
      });

      return {
        configured: true,
        healthy: response.ok,
        baseUrl,
        latencyMs: Date.now() - startedAt,
        error: response.ok ? undefined : `HTTP ${response.status}`,
      };
    } catch (error) {
      return {
        configured: true,
        healthy: false,
        baseUrl,
        latencyMs: Date.now() - startedAt,
        error: error instanceof Error ? error.message : String(error),
      };
    } finally {
      clearTimeout(timeout);
    }
  }

  private async checkConfiguredModel(
    baseUrlEnv: string,
    modelEnv: string,
  ): Promise<ServiceHealth> {
    const baseUrl = process.env[baseUrlEnv]?.trim();
    const model = process.env[modelEnv]?.trim();

    return {
      configured: Boolean(baseUrl),
      healthy: Boolean(baseUrl),
      baseUrl: baseUrl || undefined,
      model: model || undefined,
      error: baseUrl ? undefined : `${baseUrlEnv} is not configured`,
    };
  }
}
```

Create `backend/src/platform/platform-health.controller.ts`:

```ts
import { Controller, Get } from '@nestjs/common';
import { ApiOkResponse, ApiTags } from '@nestjs/swagger';
import { PlatformHealthService } from './platform-health.service';

@ApiTags('platform')
@Controller('platform')
export class PlatformHealthController {
  constructor(private readonly healthService: PlatformHealthService) {}

  @Get('health')
  @ApiOkResponse({ description: 'Platform and model service health summary' })
  getHealth() {
    return this.healthService.getHealth();
  }
}
```

Create `backend/src/platform/platform.module.ts`:

```ts
import { Module } from '@nestjs/common';
import { PrismaModule } from '../prisma/prisma.module';
import { MakeupTemplatesModule } from '../makeup-templates/makeup-templates.module';
import { PlatformHealthController } from './platform-health.controller';
import { PlatformHealthService } from './platform-health.service';

@Module({
  imports: [PrismaModule, MakeupTemplatesModule],
  controllers: [PlatformHealthController],
  providers: [PlatformHealthService],
})
export class PlatformModule {}
```

Modify `backend/src/app.module.ts` to import `PlatformModule` and include it in `imports`.

- [ ] **Step 4: Add health methods to `TemplateModelClientService`**

Add methods with this public signature to `backend/src/makeup-templates/template-library/template-model-client.service.ts`:

```ts
async checkEmbeddingHealth(): Promise<TemplateServiceHealth> {
  return this.checkOpenAiCompatibleHealth(
    this.embeddingBaseUrl,
    this.embeddingModel,
    'embedding',
  );
}

async checkRerankerHealth(): Promise<TemplateServiceHealth> {
  return this.checkOpenAiCompatibleHealth(
    this.rerankerBaseUrl,
    this.rerankerModel,
    'reranker',
  );
}

async checkVlmHealth(): Promise<TemplateServiceHealth> {
  return this.checkOpenAiCompatibleHealth(this.vlmBaseUrl, this.vlmModel, 'vlm');
}
```

Use a simple `/models` request for OpenAI-compatible services and return `{ configured, healthy, baseUrl, model, latencyMs, error }`.

- [ ] **Step 5: Run tests and commit**

Run:

```bash
cd backend
npm test -- platform-health.service.spec.ts template-model-client.service.spec.ts --runInBand
npm run build
git add src/platform src/app.module.ts src/makeup-templates/template-library/template-model-client.service.ts src/makeup-templates/template-library/template-model-client.service.spec.ts
git commit -m "feat: add platform model health endpoint"
```

Expected: tests and build pass; commit contains only platform health changes.

---

## Task 3: Generated Result History, Feedback, And Event Closure

**Files:**
- Create: `backend/src/makeup-templates/dto/query-generated-templates.dto.ts`
- Create: `backend/src/makeup-templates/dto/template-feedback.dto.ts`
- Modify: `backend/src/makeup-templates/makeup-templates.controller.ts`
- Modify: `backend/src/makeup-templates/makeup-template-generation.service.ts`
- Modify: `backend/src/makeup-templates/makeup-template-event.service.ts`
- Modify: `backend/src/makeup-templates/makeup-template-generation.service.spec.ts`
- Modify: `backend/src/makeup-templates/makeup-template-event.service.spec.ts`
- Modify: `frontend/services/generatedTemplateService.ts`
- Modify: `frontend/app/recommendation/history.tsx`

- [ ] **Step 1: Write failing backend tests for generated history**

Add to `backend/src/makeup-templates/makeup-template-generation.service.spec.ts`:

```ts
it('lists generated templates for the current user only with trace evidence', async () => {
  prisma.generatedMakeupTemplate.findMany.mockResolvedValue([
    buildGeneratedTemplateFixture({
      id: 'tmpl_20260511_user001',
      userId: 'user-001',
      matchTrace: {
        templateTraceId: 'mtrace_20260511_abcd1234',
        modelStatus: { embedding: 'configured', reranker: 'configured', vlm: 'skipped' },
        scoreBreakdown: { rerankerRelevance: 0.91 },
      },
    }),
  ]);

  const result = await service.listGeneratedForUser('user-001', { limit: 10 });

  expect(prisma.generatedMakeupTemplate.findMany).toHaveBeenCalledWith(
    expect.objectContaining({
      where: { userId: 'user-001' },
      take: 10,
    }),
  );
  expect(result.items[0].templateTraceId).toBe('mtrace_20260511_abcd1234');
  expect(result.items[0].modelStatus?.reranker).toBe('configured');
});
```

Add to `backend/src/makeup-templates/makeup-template-event.service.spec.ts`:

```ts
it('records satisfaction feedback as a typed template event', async () => {
  prisma.generatedMakeupTemplate.findUnique.mockResolvedValue({
    id: 'tmpl_001',
    userId: 'user-001',
  });
  prisma.templateEvent.create.mockResolvedValue({});

  await service.recordFeedback('tmpl_001', {
    userId: 'user-001',
    satisfactionScore: 4,
    difficultStepIds: ['tstep_001'],
    changedStepIds: ['tstep_002'],
    replacedSlotIds: ['slot_001'],
    comment: '眼妆稍微难',
  });

  expect(prisma.templateEvent.create).toHaveBeenCalledWith(
    expect.objectContaining({
      data: expect.objectContaining({
        eventName: 'template_feedback_submitted',
        payload: expect.objectContaining({
          satisfactionScore: 4,
          difficultStepIds: ['tstep_001'],
        }),
      }),
    }),
  );
});
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd backend
npm test -- makeup-template-generation.service.spec.ts makeup-template-event.service.spec.ts --runInBand
```

Expected: FAIL because list and feedback helpers do not exist.

- [ ] **Step 3: Add DTOs**

Create `backend/src/makeup-templates/dto/query-generated-templates.dto.ts`:

```ts
import { ApiPropertyOptional } from '@nestjs/swagger';
import { IsInt, IsOptional, IsString, Max, Min } from 'class-validator';
import { Type } from 'class-transformer';

export class QueryGeneratedTemplatesDto {
  @ApiPropertyOptional({ example: 20 })
  @IsOptional()
  @Type(() => Number)
  @IsInt()
  @Min(1)
  @Max(100)
  limit?: number;

  @ApiPropertyOptional({ example: 'std_elegant_luxury' })
  @IsOptional()
  @IsString()
  sourceStandardTemplateId?: string;
}
```

Create `backend/src/makeup-templates/dto/template-feedback.dto.ts`:

```ts
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsArray, IsInt, IsOptional, IsString, Max, Min } from 'class-validator';

export class TemplateFeedbackDto {
  @ApiProperty({ example: 4, minimum: 1, maximum: 5 })
  @IsInt()
  @Min(1)
  @Max(5)
  satisfactionScore!: number;

  @ApiPropertyOptional({ type: [String], example: ['tstep_001'] })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  difficultStepIds?: string[];

  @ApiPropertyOptional({ type: [String], example: ['tstep_002'] })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  changedStepIds?: string[];

  @ApiPropertyOptional({ type: [String], example: ['slot_001'] })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  replacedSlotIds?: string[];

  @ApiPropertyOptional({ example: '眼妆步骤稍微难。' })
  @IsOptional()
  @IsString()
  comment?: string;
}
```

- [ ] **Step 4: Implement backend history and feedback methods**

In `MakeupTemplateGenerationService`, add:

```ts
async listGeneratedForUser(
  userId: string,
  query: { limit?: number; sourceStandardTemplateId?: string },
) {
  const limit = Math.max(1, Math.min(query.limit ?? 20, 100));
  const templates = await this.prisma.generatedMakeupTemplate.findMany({
    where: {
      userId,
      ...(query.sourceStandardTemplateId
        ? { sourceStandardTemplateId: query.sourceStandardTemplateId }
        : {}),
    },
    include: this.buildTemplateInclude(),
    orderBy: { createdAt: 'desc' },
    take: limit,
  });

  return {
    items: templates.map(mapMakeupTemplate),
  };
}
```

Extract the repeated include object currently used by `getById` into a private `buildTemplateInclude()` helper and reuse it for `getById` and history.

In `MakeupTemplateEventService`, add:

```ts
async recordFeedback(
  templateId: string,
  input: {
    userId: string;
    satisfactionScore: number;
    difficultStepIds?: string[];
    changedStepIds?: string[];
    replacedSlotIds?: string[];
    comment?: string;
  },
): Promise<void> {
  await this.recordForTemplate(templateId, {
    userId: input.userId,
    eventName: 'template_feedback_submitted',
    payload: {
      satisfactionScore: input.satisfactionScore,
      difficultStepIds: input.difficultStepIds ?? [],
      changedStepIds: input.changedStepIds ?? [],
      replacedSlotIds: input.replacedSlotIds ?? [],
      comment: input.comment ?? '',
    },
  });
}
```

- [ ] **Step 5: Add controller routes**

In `MakeupTemplatesController`, add routes before `@Get(':templateId')`:

```ts
@Get('generated')
@ApiOkResponse({ description: 'Generated makeup template history' })
listGenerated(
  @CurrentUser() user: AuthenticatedUser,
  @Query() query: QueryGeneratedTemplatesDto,
) {
  return this.generationService.listGeneratedForUser(user.id, query);
}

@Get('generated/:templateId')
@ApiOkResponse({ type: MakeupTemplateResponseDto })
getGeneratedById(
  @CurrentUser() user: AuthenticatedUser,
  @Param('templateId') templateId: string,
) {
  return this.generationService.getById(templateId, user.id);
}

@Post('generated/:templateId/feedback')
@HttpCode(HttpStatus.OK)
@ApiOkResponse({ schema: { example: { ok: true } } })
async recordFeedback(
  @CurrentUser() user: AuthenticatedUser,
  @Param('templateId') templateId: string,
  @Body() body: TemplateFeedbackDto,
) {
  await this.eventService.recordFeedback(templateId, {
    ...body,
    userId: user.id,
  });

  return { ok: true };
}
```

Import `Query` plus the new DTOs.

- [ ] **Step 6: Add frontend service and history query**

Create `frontend/services/generatedTemplateService.ts`:

```ts
import { apiRequest } from '@/services/api-client';
import type { MakeupTemplateResponse } from '@/types/recommendation';

export type GeneratedTemplateHistoryResponse = {
  items: MakeupTemplateResponse[];
};

export type TemplateFeedbackInput = {
  satisfactionScore: number;
  difficultStepIds?: string[];
  changedStepIds?: string[];
  replacedSlotIds?: string[];
  comment?: string;
};

export const generatedTemplateService = {
  list(limit = 20) {
    return apiRequest<GeneratedTemplateHistoryResponse>('/makeup-templates/generated', {
      query: { limit },
    });
  },
  get(templateId: string) {
    return apiRequest<MakeupTemplateResponse>(`/makeup-templates/generated/${encodeURIComponent(templateId)}`);
  },
  submitFeedback(templateId: string, body: TemplateFeedbackInput) {
    return apiRequest<{ ok: true }>(`/makeup-templates/generated/${encodeURIComponent(templateId)}/feedback`, {
      method: 'POST',
      body,
    });
  },
};
```

Add a generated history query to `frontend/hooks/use-demo-queries.ts` with key `['generated-templates', currentUserId]`.

- [ ] **Step 7: Run tests and commit**

Run:

```bash
cd backend
npm test -- makeup-template-generation.service.spec.ts makeup-template-event.service.spec.ts --runInBand
npm run build
cd ../frontend
npx tsc --noEmit
npm run lint
cd ../backend
git add src/makeup-templates
git commit -m "feat: expose generated makeup template history"
cd ../frontend
git add services/generatedTemplateService.ts hooks/use-demo-queries.ts app/recommendation/history.tsx types
git commit -m "feat: show generated makeup template history"
```

Expected: backend tests/build and frontend type/lint pass.

---

## Task 4: Upgrade Template Matching Evaluation Suite

**Files:**
- Modify: `eval/template_matching/cases.json`
- Modify: `eval/template_matching/run_template_matching_eval.py`
- Create: `eval/template_matching/README.md`
- Modify: `docs/team-runbook.md`

- [ ] **Step 1: Write failing local eval expectations**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
python eval/template_matching/run_template_matching_eval.py \
  --backend-url http://127.0.0.1:13001 \
  --token demo-token \
  --output eval/template_matching/report.latest.json
```

Expected now: command either does not support `--output` or does not emit model status/per-family summary.

- [ ] **Step 2: Upgrade case schema**

Replace each case in `eval/template_matching/cases.json` with this shape:

```json
{
  "id": "elegant_interview",
  "rawUserInput": "面试需要轻熟知性优雅妆，不要太浓",
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
    },
    {
      "category": "lip",
      "subCategory": "lipstick",
      "finish": "satin"
    }
  ],
  "referenceImage": null,
  "expectedTemplateId": "std_elegant_luxury",
  "expectedFamily": "ELEGANT_LUXURY",
  "requiredStepCodes": ["SKIN_PREP", "FOUNDATION", "BROW", "LIP"]
}
```

Keep at least one case per MMU family:

- `DAILY_COMMUTE`
- `KOREAN_JAPANESE_GIRL`
- `ELEGANT_LUXURY`
- `ASIAN_MIXED`
- `CHINESE_STYLE`
- `WESTERN`
- `STAGE_CREATIVE`
- `SPECIFIC_VISUAL`

- [ ] **Step 3: Implement report output**

Update `eval/template_matching/run_template_matching_eval.py` so `main()` accepts:

```python
parser.add_argument("--output", default="")
parser.add_argument("--mode", choices=["match-debug", "recommendation"], default="match-debug")
```

Change `evaluate_case()` to return:

```python
{
    "id": case["id"],
    "passed": template_ok and family_ok,
    "selectedTemplateId": selected_template_id,
    "selectedFamily": selected_family,
    "expectedTemplateId": expected_template_id,
    "expectedFamily": expected_family,
    "templateTraceId": result.get("templateTraceId"),
    "modelStatus": result.get("modelStatus", {}),
    "scoreBreakdown": result.get("scoreBreakdown", {}),
    "failureReason": "" if template_ok and family_ok else "selected template/family mismatch",
}
```

Add summary:

```python
def build_summary(results: list[dict]) -> dict:
    by_family: dict[str, dict[str, int]] = {}
    for item in results:
        family = item.get("expectedFamily") or "UNKNOWN"
        bucket = by_family.setdefault(family, {"passed": 0, "total": 0})
        bucket["total"] += 1
        if item["passed"]:
            bucket["passed"] += 1
    return {
        "passed": sum(1 for item in results if item["passed"]),
        "total": len(results),
        "byFamily": by_family,
        "results": results,
    }
```

Write `--output` JSON when provided and print the same summary to stdout.

- [ ] **Step 4: Add README**

Create `eval/template_matching/README.md`:

````md
# Template Matching Eval

Runs MMU template matching regression cases against the backend.

```bash
python eval/template_matching/run_template_matching_eval.py \
  --backend-url http://127.0.0.1:13001 \
  --token demo-token \
  --output eval/template_matching/report.latest.json
```

Use `scripts/start-template-model-mock-services.mjs` for local smoke. Use real
embedding/rerank services for acceptance.
````

- [ ] **Step 5: Run eval script syntax and commit**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
python -m py_compile eval/template_matching/run_template_matching_eval.py
git add eval/template_matching docs/team-runbook.md
git commit -m "test: upgrade template matching evaluation suite"
```

Expected: Python compile passes. Do not commit `report.latest.json`.

---

## Task 5: Makeup Preview Binding And Comparison Metadata

**Files:**
- Modify: `backend/src/makeup/dto/makeup-job-response.dto.ts`
- Modify: `backend/src/makeup/makeup-job.service.ts`
- Modify: `backend/src/makeup/makeup.service.ts`
- Modify: `backend/src/makeup/makeup.controller.ts`
- Modify: `backend/src/makeup/makeup-job.service.spec.ts`
- Modify: `backend/src/makeup/makeup.service.spec.ts`
- Modify: `frontend/services/virtualTryOnService.ts`
- Modify: `frontend/components/recommendation/makeup-try-on-panel.tsx`
- Modify: `frontend/app/recommendation/preview.tsx`

- [ ] **Step 1: Write failing preview job metadata tests**

Add to `backend/src/makeup/makeup-job.service.spec.ts`:

```ts
it('returns template metadata and preview trace id with queued jobs', () => {
  const job = service.enqueue(
    async () => ({ imageUrl: 'http://127.0.0.1:13001/makeup/result?filename=a.png&type=output&subfolder=' }),
    {
      traceId: 'preview_20260511_abcd1234',
      generatedTemplateId: 'tmpl_001',
      sourceStandardTemplateVersionId: 'std_daily_v1',
      comparisonMode: 'slider',
    },
  );

  expect(job.traceId).toBe('preview_20260511_abcd1234');
  expect(job.generatedTemplateId).toBe('tmpl_001');
  expect(job.comparisonMode).toBe('slider');
});
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd backend
npm test -- makeup-job.service.spec.ts makeup.service.spec.ts --runInBand
```

Expected: FAIL because `enqueue` does not accept metadata yet.

- [ ] **Step 3: Extend job DTO and service**

In `MakeupJobResponseDto`, add optional fields:

```ts
traceId?: string;
generatedTemplateId?: string;
sourceStandardTemplateVersionId?: string;
comparisonMode?: 'template' | 'side-by-side' | 'slider';
productSlotSummary?: Record<string, unknown>;
```

In `MakeupJobService`, change `enqueue` signature:

```ts
type MakeupJobMetadata = {
  traceId?: string;
  generatedTemplateId?: string;
  sourceStandardTemplateVersionId?: string;
  comparisonMode?: 'template' | 'side-by-side' | 'slider';
  productSlotSummary?: Record<string, unknown>;
};

enqueue(processor: MakeupJobProcessor, metadata: MakeupJobMetadata = {}): MakeupJobResponseDto
```

Store `metadata` on `MakeupJobRecord` and spread it in `toDto()`.

- [ ] **Step 4: Parse metadata in controller**

In `MakeupController.createMakeupJob`, read form fields from `@Body()`:

```ts
type MakeupJobBody = {
  scenario?: string;
  templateId?: string;
  generatedTemplateId?: string;
  sourceStandardTemplateVersionId?: string;
  comparisonMode?: 'template' | 'side-by-side' | 'slider';
  productSlotSummary?: string;
};
```

Pass metadata to `makeupService.enqueueMakeup(...)`:

```ts
{
  generatedTemplateId: body.generatedTemplateId,
  sourceStandardTemplateVersionId: body.sourceStandardTemplateVersionId,
  comparisonMode: body.comparisonMode,
  productSlotSummary: parseJsonObject(body.productSlotSummary),
}
```

Generate preview trace IDs with `createMakeupTemplateId('preview')` or a makeup-local helper that returns `preview_<date>_<hex>`.

- [ ] **Step 5: Send metadata from frontend**

Extend `RequestMakeupPreviewParams` in frontend types to include:

```ts
generatedTemplateId?: string;
sourceStandardTemplateVersionId?: string;
comparisonMode?: 'template' | 'side-by-side' | 'slider';
productSlotSummary?: Record<string, unknown>;
```

In `frontend/services/virtualTryOnService.ts`, append:

```ts
if (params.generatedTemplateId) {
  formData.append('generatedTemplateId', params.generatedTemplateId);
}
if (params.sourceStandardTemplateVersionId) {
  formData.append('sourceStandardTemplateVersionId', params.sourceStandardTemplateVersionId);
}
if (params.comparisonMode) {
  formData.append('comparisonMode', params.comparisonMode);
}
if (params.productSlotSummary) {
  formData.append('productSlotSummary', JSON.stringify(params.productSlotSummary));
}
```

- [ ] **Step 6: Bind preview page to generated recommendation**

In `frontend/app/recommendation/preview.tsx`, pass:

```tsx
<MakeupTryOnPanel
  templateId={templateId}
  scenario={result?.scenario ?? scenarioInput}
  productIds={matchedProductIds}
  productSummary={productSummary}
  generatedTemplateId={result?.generatedTemplateId}
  sourceStandardTemplateVersionId={result?.sourceStandardTemplateVersionId}
  productSlotSummary={{
    templateTraceId: result?.templateTraceId,
    productCoverageRate: result?.productCoverageRate,
    steps: result?.steps.map((step) => ({
      id: step.id,
      standardStepCodes: step.standardStepCodes,
      productSlots: step.productSlots,
    })),
  }}
  defaultOpen
/>
```

Update `MakeupTryOnPanelProps` to accept those props and pass them into `virtualTryOnService.requestPreviewJob`.

- [ ] **Step 7: Run tests and commit**

Run:

```bash
cd backend
npm test -- makeup-job.service.spec.ts makeup.service.spec.ts --runInBand
npm run build
cd ../frontend
npx tsc --noEmit
npm run lint
cd ../backend
git add src/makeup
git commit -m "feat: bind makeup preview jobs to generated templates"
cd ../frontend
git add services/virtualTryOnService.ts components/recommendation/makeup-try-on-panel.tsx app/recommendation/preview.tsx types
git commit -m "feat: send generated template metadata to preview"
```

Expected: preview metadata appears in job responses and frontend compiles.

---

## Task 6: Coach Step-Evaluate And Auto-Next Completion Schema

**Files:**
- Modify: `backend/src/makeup/dto/makeup-coach.dto.ts`
- Modify: `backend/src/makeup/makeup-coach.service.ts`
- Modify: `backend/src/makeup/makeup.controller.ts`
- Modify: `backend/src/makeup/makeup-coach.service.spec.ts`
- Modify: `backend/src/makeup/makeup-realtime-session.service.ts`
- Modify: `backend/src/makeup/makeup-realtime-session.service.spec.ts`
- Modify: `frontend/types/makeup-coach.ts`
- Modify: `frontend/services/makeupCoachService.ts`
- Modify: `frontend/app/recommendation/coach.tsx`
- Modify: `frontend/app/recommendation/execution.tsx`
- Modify: `frontend/app/recommendation/live-coach.native.tsx`

- [ ] **Step 1: Write failing coach step-evaluate tests**

Add to `backend/src/makeup/makeup-coach.service.spec.ts`:

```ts
it('evaluates a still image with standardized step completion fields', async () => {
  const result = await service.evaluateStep({
    generatedTemplateId: 'tmpl_001',
    stepId: 'tstep_001',
    stepCode: 'LIP',
    scenario: '五步演示妆容',
    stepTitle: '唇妆',
    stepInstruction: '完成豆沙色唇妆。',
    completionCriteria: '唇色均匀，边缘清晰。',
    imageDataUrl: 'data:image/png;base64,AAAA',
  });

  expect(result.traceId).toMatch(/^coach_/);
  expect(result.generatedTemplateId).toBe('tmpl_001');
  expect(result.stepCode).toBe('LIP');
  expect(result.completionLevel).toEqual(expect.any(Number));
  expect(result.canAutoAdvance).toEqual(expect.any(Boolean));
  expect(result.voiceText).toEqual(expect.any(String));
});
```

- [ ] **Step 2: Run tests and verify they fail**

Run:

```bash
cd backend
npm test -- makeup-coach.service.spec.ts makeup-realtime-session.service.spec.ts --runInBand
```

Expected: FAIL because `evaluateStep` and the new DTOs do not exist.

- [ ] **Step 3: Add DTO classes**

In `backend/src/makeup/dto/makeup-coach.dto.ts`, add:

```ts
export class MakeupStepEvaluateRequestDto extends MakeupCoachRequestDto {
  @ApiProperty({ example: 'tmpl_20260511_abcd1234' })
  @IsString()
  generatedTemplateId!: string;

  @ApiPropertyOptional({ example: 'tstep_20260511_abcd1234' })
  @IsOptional()
  @IsString()
  stepId?: string;

  @ApiPropertyOptional({ example: 'LIP' })
  @IsOptional()
  @IsString()
  stepCode?: string;

  @ApiPropertyOptional({ example: '唇色均匀，边缘清晰。' })
  @IsOptional()
  @IsString()
  completionCriteria?: string;
}

export class MakeupStepEvaluateResponseDto extends MakeupCoachResponseDto {
  @ApiProperty({ example: 'coach_20260511_abcd1234' })
  traceId!: string;

  @ApiProperty({ example: 'tmpl_20260511_abcd1234' })
  generatedTemplateId!: string;

  @ApiPropertyOptional({ example: 'tstep_20260511_abcd1234' })
  stepId?: string;

  @ApiPropertyOptional({ example: 'LIP' })
  stepCode?: string;

  @ApiProperty({ example: 0.86 })
  completionLevel!: number;

  @ApiProperty({ example: true })
  canAutoAdvance!: boolean;

  @ApiProperty({ example: ['LIP_UNEVEN_EDGE'], type: [String] })
  mistakeTypes!: string[];

  @ApiProperty({ example: '唇妆完成度不错，可以进入定妆。' })
  voiceText!: string;
}
```

- [ ] **Step 4: Implement reusable step evaluation**

In `MakeupCoachService`, add:

```ts
async evaluateStep(
  request: MakeupStepEvaluateRequestDto,
): Promise<MakeupStepEvaluateResponseDto> {
  const base = await this.guide(request);
  const completionLevel = Math.max(0, Math.min(1, base.qualityScore / 100));
  const canAutoAdvance =
    base.shouldProceed && completionLevel >= 0.72 && base.detectedIssues.length === 0;

  return {
    ...base,
    traceId: createMakeupTemplateId('coach'),
    generatedTemplateId: request.generatedTemplateId,
    stepId: request.stepId,
    stepCode: request.stepCode,
    completionLevel,
    canAutoAdvance,
    mistakeTypes: base.detectedIssues.map((issue) => this.normalizeMistakeType(issue)),
    voiceText: canAutoAdvance ? base.nextAction : base.guidance,
  };
}
```

Add `normalizeMistakeType(issue: string)` that maps Chinese issue text into stable uppercase labels such as `BASE_TOO_THICK`, `BROW_ASYMMETRY`, `BLUSH_POSITION`, `LIP_UNEVEN_EDGE`, or `STEP_NEEDS_RECHECK`.

- [ ] **Step 5: Add backend route**

In `MakeupController`, add:

```ts
@Post('makeup/coach/step-evaluate')
@HttpCode(HttpStatus.OK)
@ApiOkResponse({ type: MakeupStepEvaluateResponseDto })
evaluateMakeupStep(
  @Body() body: MakeupStepEvaluateRequestDto,
): Promise<MakeupStepEvaluateResponseDto> {
  return this.makeupCoachService.evaluateStep(body);
}
```

- [ ] **Step 6: Standardize realtime result**

In `MakeupRealtimeSessionService`, when emitting `coach_result`, ensure the payload contains:

```ts
traceId
completionLevel
canAutoAdvance
mistakeTypes
voiceText
```

Use `MakeupCoachService.evaluateStep()` when the realtime session has a `generatedTemplateId`; otherwise wrap the existing `guideWithVoice()` result with equivalent derived fields.

- [ ] **Step 7: Add frontend service and upload test UI**

In `frontend/types/makeup-coach.ts`, add matching `MakeupStepEvaluateRequest` and `MakeupStepEvaluateResponse`.

In `frontend/services/makeupCoachService.ts`, add:

```ts
async evaluateStepImage(params: MakeupStepEvaluateRequest): Promise<ServiceResponse<MakeupStepEvaluateResponse>> {
  return {
    data: await apiRequest<MakeupStepEvaluateResponse>('/makeup/coach/step-evaluate', {
      method: 'POST',
      body: params,
    }),
    error: null,
  };
}
```

In `frontend/app/recommendation/coach.tsx`, add a visible “上传图片测试” button that picks an image and calls `evaluateStepImage` for the current step. Show `completionLevel`, `canAutoAdvance`, `mistakeTypes`, `voiceText`, and `traceId`.

In `frontend/app/recommendation/execution.tsx`, auto-advance only when `canAutoAdvance` is true for the current step; also keep the manual next button.

- [ ] **Step 8: Run tests and commit**

Run:

```bash
cd backend
npm test -- makeup-coach.service.spec.ts makeup-realtime-session.service.spec.ts --runInBand
npm run build
cd ../frontend
npx tsc --noEmit
npm run lint
cd ../backend
git add src/makeup
git commit -m "feat: add makeup step evaluation schema"
cd ../frontend
git add types/makeup-coach.ts services/makeupCoachService.ts app/recommendation/coach.tsx app/recommendation/execution.tsx app/recommendation/live-coach.native.tsx
git commit -m "feat: add image-based coach step testing"
```

Expected: still-image route and realtime path share completion fields.

---

## Task 7: Complete Frontend Template Management Editing

**Files:**
- Modify: `frontend/types/template-library.ts`
- Modify: `frontend/services/templateLibraryService.ts`
- Modify: `frontend/app/template-library/detail.tsx`
- Modify: `frontend/app/template-library/index.tsx`
- Modify: `frontend/app/template-library/versions.tsx`
- Modify: `docs/template-matching-test-guide.md`

- [ ] **Step 1: Inspect editable field coverage**

Run:

```bash
cd frontend
rg -n "standardStepCodes|operationAreas|difficulty|productSlots|slotCode|save draft|发布|回滚" app/template-library types/template-library.ts services/templateLibraryService.ts
```

Expected: output shows whether `detail.tsx` already references MMU codes, operation areas, difficulty, and product slots. Continue with Steps 2-4 regardless of current coverage, adding any missing controls and preserving existing working controls.

- [ ] **Step 2: Add type coverage**

Ensure `frontend/types/template-library.ts` has:

```ts
export type TemplateStepBlockDraft = {
  id?: string;
  stepCode: string;
  stepOrder: number;
  sectionCode: string;
  stepName: string;
  standardStepCodes: string[];
  operationAreas: string[];
  stepGoal: string;
  instructionTemplate: string;
  visualChange: string;
  aiDetectionArea: string;
  completionCriteria: string;
  failureFeedback: string;
  nextStepCondition: string;
  difficultyScore?: number;
  editableByUser: boolean;
};

export type TemplateProductSlotDraft = {
  id?: string;
  stepCode?: string;
  slotCode: string;
  category: string;
  subCategory?: string;
  acceptableSubCategories: string[];
  substituteSlotCodes: string[];
  requiredLevel: string;
  desiredEffect: string[];
  desiredColorFamily?: string;
  desiredFinish: string[];
  fallbackInstruction: string;
  sortOrder: number;
};
```

- [ ] **Step 3: Add form sections to detail page**

In `frontend/app/template-library/detail.tsx`, add these visible sections:

- “基础信息”: name, scene, style tags, effect tags, estimated minutes.
- “五步结构”: step name, MMU codes, operation areas, completion criteria, failure feedback.
- “产品槽位”: slot code, category, subcategory, required level, desired finish, fallback instruction.
- “难度”: difficulty base score, step score, and a boolean special technique marker stored in the draft payload as `hasSpecialTechnique`.

Use existing `TextInput`, `Pressable`, and local style patterns. Avoid JSON textareas for common fields.

- [ ] **Step 4: Validate draft payload before save**

Add local validation in `detail.tsx`:

```ts
function validateDraftPayload(draft: StandardTemplateDraftPayload) {
  if (!draft.stepBlocks.length) {
    return '至少需要一个步骤';
  }
  if (draft.stepBlocks.some((step) => step.standardStepCodes.length === 0)) {
    return '每个步骤都需要绑定 MMU 标准步骤码';
  }
  if (draft.productSlots.some((slot) => !slot.slotCode || !slot.category)) {
    return '每个产品槽位都需要槽位编码和类目';
  }
  return null;
}
```

Show the validation message before calling the backend.

- [ ] **Step 5: Run frontend verification and commit**

Run:

```bash
cd frontend
npx tsc --noEmit
npm run lint
git add types/template-library.ts services/templateLibraryService.ts app/template-library docs/../..
git commit -m "feat: complete template library management editing"
```

Expected: TypeScript and lint pass. Use correct repo paths: frontend files are committed in the frontend repo; docs are committed in the top-level repo separately.

---

## Task 8: Platform Smoke Scripts And Runbook

**Files:**
- Create: `scripts/start-mimu-platform-services.sh`
- Create: `scripts/smoke-mimu-platform.sh`
- Modify: `docs/team-runbook.md`
- Modify: `docs/template-matching-test-guide.md`

- [ ] **Step 1: Create service startup script**

Create `scripts/start-mimu-platform-services.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$ROOT_DIR/var/logs"
mkdir -p "$LOG_DIR"

MODE="${MIMU_MODEL_MODE:-mock}"

if [[ "$MODE" == "mock" ]]; then
  tmux new-session -d -s mimu_template_model_mocks \
    "cd '$ROOT_DIR' && node scripts/start-template-model-mock-services.mjs 2>&1 | tee '$LOG_DIR/template-model-mocks.log'" || true
  echo "Started mock template model services on 8030/8031/8032"
else
  echo "Real model mode selected. Start embedding/rerank/VLM with the configured conda environments and ports from docs/team-runbook.md"
fi
```

- [ ] **Step 2: Create smoke script**

Create `scripts/smoke-mimu-platform.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

BACKEND_URL="${MIMU_BACKEND_URL:-http://127.0.0.1:13001}"
TOKEN="${MIMU_DEMO_TOKEN:-demo-token}"

curl -fsS "$BACKEND_URL/health" >/dev/null
curl -fsS "$BACKEND_URL/platform/health" | python -m json.tool >/tmp/mimu-platform-health.json

curl -fsS -X POST "$BACKEND_URL/makeup-template-library/seed" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}' | python -m json.tool >/tmp/mimu-template-seed.json

curl -fsS -X POST "$BACKEND_URL/recommendations/generate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"scenario":"面试","scenarioDetails":"面试需要轻熟知性优雅妆，不要太浓","requirements":["不要太浓"]}' \
  | python -m json.tool >/tmp/mimu-generation.json

python eval/template_matching/run_template_matching_eval.py \
  --backend-url "$BACKEND_URL" \
  --token "$TOKEN" \
  --output /tmp/mimu-template-matching-report.json

echo "MIMU platform smoke passed"
```

Run:

```bash
chmod +x scripts/start-mimu-platform-services.sh scripts/smoke-mimu-platform.sh
```

- [ ] **Step 3: Update runbook**

Add to `docs/team-runbook.md`:

````md
## Platform Smoke

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
MIMU_MODEL_MODE=mock bash scripts/start-mimu-platform-services.sh
MIMU_BACKEND_URL=http://127.0.0.1:13001 bash scripts/smoke-mimu-platform.sh
```

Use `GET /platform/health` to confirm embedding, rerank, VLM, ASR, coach, and
ComfyUI status. Search backend logs by `templateTraceId`, `preview_`, `coach_`,
or `voice_`.
````

- [ ] **Step 4: Run shell checks and commit**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
bash -n scripts/start-mimu-platform-services.sh
bash -n scripts/smoke-mimu-platform.sh
git add scripts/start-mimu-platform-services.sh scripts/smoke-mimu-platform.sh docs/team-runbook.md docs/template-matching-test-guide.md
git commit -m "docs: add platform smoke runbook"
```

Expected: shell syntax checks pass.

---

## Task 9: End-To-End Platform Verification

**Files:**
- Modify: `backend/test/app.e2e-spec.ts`
- Modify: `docs/template-matching-test-guide.md`

- [ ] **Step 1: Add e2e coverage for platform routes**

In `backend/test/app.e2e-spec.ts`, add tests:

```ts
it('/platform/health returns model health summary', async () => {
  const response = await request(app.getHttpServer())
    .get('/platform/health')
    .expect(200);

  expect(response.body).toHaveProperty('backend');
  expect(response.body.models).toHaveProperty('templateEmbedding');
  expect(response.body.models).toHaveProperty('templateReranker');
});

it('/makeup/coach/step-evaluate returns auto-next schema', async () => {
  const response = await request(app.getHttpServer())
    .post('/makeup/coach/step-evaluate')
    .send({
      generatedTemplateId: 'tmpl_e2e_001',
      stepId: 'tstep_e2e_lip',
      stepCode: 'LIP',
      scenario: '五步演示妆容',
      stepTitle: '唇妆',
      stepInstruction: '完成豆沙色唇妆。',
      completionCriteria: '唇色均匀，边缘清晰。',
      imageDataUrl: 'data:image/png;base64,AAAA',
    })
    .expect(200);

  expect(response.body.traceId).toMatch(/^coach_/);
  expect(response.body).toHaveProperty('completionLevel');
  expect(response.body).toHaveProperty('canAutoAdvance');
  expect(response.body).toHaveProperty('voiceText');
});
```

- [ ] **Step 2: Run full verification**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
npm run build
npm test -- --runInBand
npm run test:e2e -- --runInBand
cd ../frontend
npx tsc --noEmit
npm run lint
cd ..
python -m py_compile eval/template_matching/run_template_matching_eval.py
bash -n scripts/start-mimu-platform-services.sh
bash -n scripts/smoke-mimu-platform.sh
```

Expected: every command exits 0.

- [ ] **Step 3: Update user journey doc**

Update `docs/template-matching-test-guide.md` with:

- `GET /platform/health` check.
- generated template history path.
- preview trace/job test.
- still-image step-evaluate test.
- model error diagnosis.
- full smoke command.

- [ ] **Step 4: Commit final verification docs**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
git add test/app.e2e-spec.ts
git commit -m "test: cover platform health and coach evaluation"
cd ..
git add docs/template-matching-test-guide.md
git commit -m "docs: update platform user journey"
```

Expected: backend and top-level repos have final verification commits.

---

## Final Verification Checklist

Run these commands before claiming completion:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/backend
npm run build
npm test -- --runInBand
npm run test:e2e -- --runInBand

cd /storage/nvme3/shushanfu/MIMU-colleague/frontend
npx tsc --noEmit
npm run lint

cd /storage/nvme3/shushanfu/MIMU-colleague
python -m py_compile eval/template_matching/run_template_matching_eval.py
bash -n scripts/start-mimu-platform-services.sh
bash -n scripts/smoke-mimu-platform.sh
```

Manual acceptance:

- Open frontend and login demo user.
- Seed standard templates from template library management.
- Edit, publish, and rollback one template.
- Generate “面试需要轻熟知性优雅妆，不要太浓”.
- Confirm result page shows model evidence and trace ID.
- Open product checklist and confirm MMU codes and slot status.
- Open preview, upload selfie, create preview job, and see trace ID.
- Open coach page, upload a still image for current step, and see completion fields.
- Open generated history and confirm the generated template is listed.

---

## Self-Review Notes

- Spec coverage: all eight requested improvement areas map to Tasks 2-9.
- Existing formal template library and model matching plans are referenced as foundation and not duplicated.
- The plan keeps five user-facing steps while preserving MMU step-code mapping.
- The plan requires model-backed matching and explicit errors; no silent rule fallback is introduced.
- The plan includes backend, frontend, eval, runbook, and smoke verification.
