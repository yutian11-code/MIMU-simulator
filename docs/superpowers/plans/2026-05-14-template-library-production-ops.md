# Template Library Production Ops Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the current template library safe for production matching and usable by operators at scale by adding a real production-eligibility gate, backlog cleanup tooling, batch operations, generated-result disposition states, and end-to-end operator verification.

**Architecture:** Extend the existing `makeup-template-library`, `makeup-templates`, and `ops-workbench` modules instead of introducing a new workflow engine. Keep matching model-backed, but constrain the library read path to production-eligible templates only; normalize existing data with a one-shot backfill script; then add focused backoffice APIs and queue-first frontend UX for batch quality review and generated-result disposition.

**Tech Stack:** NestJS 11, Prisma 7, PostgreSQL, Jest, Expo Router 6, React Native, Zustand, TanStack Query.

---

## File Map

### Backend schema, migration, and backfill
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/prisma/migrations/20260514190000_add_generated_template_ops_review_state/migration.sql`
- Modify: `backend/package.json`
- Create: `backend/src/scripts/backfill-template-library-production.ts`
- Create: `backend/src/scripts/backfill-template-library-production.spec.ts`

### Backend production eligibility and template batch ops
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.service.ts`
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-matching.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-matching.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-quality.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-quality.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`
- Create: `backend/src/makeup-templates/template-library/dto/batch-update-template-quality.dto.ts`
- Create: `backend/src/makeup-templates/template-library/dto/batch-archive-templates.dto.ts`

### Backend generated-result disposition and ops summary
- Modify: `backend/src/makeup-templates/dto/query-generated-templates.dto.ts`
- Modify: `backend/src/makeup-templates/dto/makeup-template-response.dto.ts`
- Modify: `backend/src/makeup-templates/makeup-template.mapper.ts`
- Modify: `backend/src/makeup-templates/makeup-template-generation.service.ts`
- Modify: `backend/src/makeup-templates/makeup-templates.controller.ts`
- Create: `backend/src/makeup-templates/dto/update-generated-template-review.dto.ts`
- Create: `backend/src/makeup-templates/generated-template-review.service.ts`
- Create: `backend/src/makeup-templates/generated-template-review.service.spec.ts`
- Modify: `backend/src/makeup-templates/makeup-templates.module.ts`
- Modify: `backend/src/ops-workbench/ops-workbench.service.ts`
- Modify: `backend/src/ops-workbench/ops-workbench.controller.ts`
- Modify: `backend/src/ops-workbench/dto/query-ops-workbench-tasks.dto.ts`

### Frontend queue UX and batch actions
- Modify: `frontend/types/template-library.ts`
- Modify: `frontend/types/recommendation.ts`
- Modify: `frontend/services/templateLibraryService.ts`
- Modify: `frontend/services/generatedTemplateService.ts`
- Modify: `frontend/services/opsWorkbenchService.ts`
- Modify: `frontend/app/template-library/quality-queue.tsx`
- Modify: `frontend/app/template-library/index.tsx`
- Modify: `frontend/app/template-library/generated.tsx`
- Modify: `frontend/app/ops-workbench/index.tsx`
- Modify: `frontend/app/ops-workbench/tasks.tsx`

### Docs and verification
- Modify: `docs/template-matching-test-guide.md`
- Create: `docs/template-library-production-ops-runbook.md`

## Task 1: Add generated-result review state to the schema and map it end to end

**Files:**
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/prisma/migrations/20260514190000_add_generated_template_ops_review_state/migration.sql`
- Modify: `backend/src/makeup-templates/dto/query-generated-templates.dto.ts`
- Modify: `backend/src/makeup-templates/dto/makeup-template-response.dto.ts`
- Modify: `backend/src/makeup-templates/makeup-template.mapper.ts`
- Test: `backend/src/makeup-templates/generated-template-review.service.spec.ts`

- [ ] **Step 1: Write the failing generated-result review-state test**

```ts
it('maps generated template review state and filters pending queue only', async () => {
  prisma.generatedMakeupTemplate.findMany.mockResolvedValue([
    {
      id: 'tmpl_001',
      displayName: '清透通勤妆',
      reviewState: 'pending',
      operatorNote: null,
      reviewedAt: null,
      reviewedById: null,
      linkedStandardTemplateId: null,
      linkedStandardVersionId: null,
      linkedStandardTemplate: null,
    },
  ] as never);

  const result = await service.listGenerated({
    scope: 'all',
    reviewState: 'pending',
  });

  expect(result.items[0]).toMatchObject({
    id: 'tmpl_001',
    reviewState: 'pending',
    linkedTemplateStatus: undefined,
  });
});
```

- [ ] **Step 2: Run the targeted test to verify it fails**

Run: `cd backend && npm test -- generated-template-review.service.spec.ts --runInBand`
Expected: FAIL because `GeneratedMakeupTemplate` has no `reviewState`, `reviewedAt`, `reviewedById`, or `operatorNote` fields yet.

- [ ] **Step 3: Add the new enum and fields to Prisma**

```prisma
enum GeneratedTemplateReviewState {
  pending
  deferred
  materialized
  published
  rejected
  archived
}

model GeneratedMakeupTemplate {
  id           String                       @id @db.VarChar(50)
  reviewState  GeneratedTemplateReviewState @default(pending) @map("review_state")
  operatorNote String?                      @map("operator_note") @db.VarChar(500)
  reviewedById String?                      @map("reviewed_by_id") @db.VarChar(50)
  reviewedAt   DateTime?                    @map("reviewed_at")
}
```

- [ ] **Step 4: Write the migration SQL**

```sql
CREATE TYPE "GeneratedTemplateReviewState" AS ENUM (
  'pending',
  'deferred',
  'materialized',
  'published',
  'rejected',
  'archived'
);

ALTER TABLE "generated_makeup_templates"
  ADD COLUMN "review_state" "GeneratedTemplateReviewState" NOT NULL DEFAULT 'pending',
  ADD COLUMN "operator_note" VARCHAR(500),
  ADD COLUMN "reviewed_by_id" VARCHAR(50),
  ADD COLUMN "reviewed_at" TIMESTAMP(3);

CREATE INDEX "generated_makeup_templates_review_state_created_at_idx"
  ON "generated_makeup_templates" ("review_state", "created_at");
```

- [ ] **Step 5: Map the new fields through backend DTOs**

```ts
@ApiPropertyOptional({ enum: ['pending', 'deferred', 'materialized', 'published', 'rejected', 'archived'] })
reviewState?: 'pending' | 'deferred' | 'materialized' | 'published' | 'rejected' | 'archived';
```

```ts
reviewState: template.reviewState,
operatorNote: template.operatorNote ?? undefined,
reviewedAt: template.reviewedAt?.toISOString() ?? undefined,
reviewedById: template.reviewedById ?? undefined,
```

- [ ] **Step 6: Re-run Prisma generate and the targeted test**

Run: `cd backend && npm run prisma:generate && npm test -- generated-template-review.service.spec.ts --runInBand`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd backend
git add prisma/schema.prisma prisma/migrations src/makeup-templates
git commit -m "feat: add generated template review state"
```

## Task 2: Enforce production eligibility in the template library read path

**Files:**
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.service.ts`
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-matching.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-matching.service.spec.ts`
- Test: `backend/src/recommendations/recommendations.service.spec.ts`

- [ ] **Step 1: Write the failing production-eligibility tests**

```ts
it('returns only reviewed P1/P2 published non-private templates for matching', async () => {
  prisma.standardMakeupTemplate.findMany.mockResolvedValue([
    buildTemplateRow({
      id: 'std_p1_live',
      status: 'published',
      visibility: 'team',
      qualityTier: 'P1',
      qualityReviewStatus: 'reviewed',
    }),
    buildTemplateRow({
      id: 'std_p3_pending',
      status: 'published',
      visibility: 'team',
      qualityTier: 'P3',
      qualityReviewStatus: 'pending',
    }),
  ] as never);

  const items = await service.listActiveTemplatesForProduction();

  expect(items.map((item) => item.id)).toEqual(['std_p1_live']);
});

it('does not allow unreviewed machine templates into production candidate pools', async () => {
  const items = await service.match({
    rawUserInput: '通勤淡妆',
    scene: 'COMMUTE',
    styleTags: ['CLEAR'],
    effectTags: ['GOOD_COMPLEXION'],
    constraints: [],
    skillLevel: 'beginner',
    preferredProductCategories: [],
  });

  expect(
    items.candidates.every((candidate) => candidate.template.qualityTier !== 'P3'),
  ).toBe(true);
});
```

- [ ] **Step 2: Run the matching and library tests to verify they fail**

Run: `cd backend && npm test -- standard-template-library.service.spec.ts template-matching.service.spec.ts recommendations.service.spec.ts --runInBand`
Expected: FAIL because the library does not yet expose a production-only query path.

- [ ] **Step 3: Add a dedicated production eligibility query to the library service**

```ts
async listActiveTemplatesForProduction() {
  return this.listActiveTemplates({
    qualityTiers: ['P1', 'P2'],
    qualityReviewStatus: 'reviewed',
    visibility: ['team', 'public'],
    status: 'published',
  });
}
```

```ts
const productionTemplates =
  await this.library.listActiveTemplatesForProduction();
if (productionTemplates.length > 0) {
  return productionTemplates;
}
```

- [ ] **Step 4: Update the Prisma query mapper to include eligibility filters**

```ts
where: {
  status: 'published',
  qualityTier: { in: ['P1', 'P2'] },
  qualityReviewStatus: 'reviewed',
  visibility: { in: ['team', 'public'] },
}
```

- [ ] **Step 5: Keep debug behavior explicit**

```ts
async listActiveTemplates(input: {
  qualityTiers?: Array<'P1' | 'P2' | 'P3'>;
  qualityReviewStatus?: 'pending' | 'reviewed' | 'repaired' | 'archived';
  visibility?: Array<'team' | 'public' | 'private'>;
  status?: 'draft' | 'published' | 'archived';
} = {}) {
  return this.prisma.standardMakeupTemplate.findMany({
    where: buildTemplateWhere(input),
    include: this.templateInclude(),
    orderBy: [{ updatedAt: 'desc' }, { id: 'asc' }],
  });
}
```

- [ ] **Step 6: Re-run the targeted backend tests**

Run: `cd backend && npm test -- standard-template-library.service.spec.ts template-matching.service.spec.ts recommendations.service.spec.ts --runInBand`
Expected: PASS, with commute matching still selecting the reviewed daily commute baseline.

- [ ] **Step 7: Commit**

```bash
cd backend
git add src/makeup-templates/template-library src/recommendations
git commit -m "feat: gate production matching on reviewed templates"
```

## Task 3: Add the one-shot backfill script for current template normalization

**Files:**
- Modify: `backend/package.json`
- Create: `backend/src/scripts/backfill-template-library-production.ts`
- Create: `backend/src/scripts/backfill-template-library-production.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-machine-metadata.ts`

- [ ] **Step 1: Write the failing backfill script test**

```ts
it('marks curated templates as reviewed and machine templates as pending P3/private by default', async () => {
  prisma.standardMakeupTemplate.findMany.mockResolvedValue([
    buildTemplate({ id: 'std_daily_clear_commute', source: 'seed', displayName: '清透通勤标准模板' }),
    buildTemplate({ id: 'std_machine_001', source: 'machine_generated', displayName: 'GRWM' }),
  ] as never);

  await runBackfill(prisma, { dryRun: false });

  expect(prisma.standardMakeupTemplate.updateMany).toHaveBeenCalledWith(
    expect.objectContaining({
      data: expect.objectContaining({
        qualityReviewStatus: 'reviewed',
      }),
    }),
  );
  expect(prisma.standardMakeupTemplate.update).toHaveBeenCalledWith(
    expect.objectContaining({
      where: { id: 'std_machine_001' },
      data: expect.objectContaining({
        qualityTier: 'P3',
        qualityReviewStatus: 'pending',
        visibility: 'private',
      }),
    }),
  );
});
```

- [ ] **Step 2: Run the script test to verify it fails**

Run: `cd backend && npm test -- backfill-template-library-production.spec.ts --runInBand`
Expected: FAIL because the backfill script does not exist.

- [ ] **Step 3: Create the backfill script with explicit normalization rules**

```ts
export async function runBackfill(
  prisma: PrismaServiceLike,
  input: { dryRun: boolean },
) {
  const templates = await prisma.standardMakeupTemplate.findMany({
    include: { currentVersion: true },
  });

  for (const template of templates) {
    if (template.source === 'seed') {
      await prisma.standardMakeupTemplate.update({
        where: { id: template.id },
        data: {
          qualityTier: inferCuratedTier(template),
          qualityReviewStatus: 'reviewed',
        },
      });
      continue;
    }

    const hide = shouldHideMachineTemplate(template);
    await prisma.standardMakeupTemplate.update({
      where: { id: template.id },
      data: {
        qualityTier: 'P3',
        qualityReviewStatus: 'pending',
        visibility: hide ? 'private' : template.visibility,
        operatorNote: hide
          ? 'auto-hidden by production backfill'
          : template.operatorNote,
      },
    });
  }
}
```

- [ ] **Step 4: Expose the script through package.json**

```json
{
  "scripts": {
    "ops:backfill-template-library": "ts-node src/scripts/backfill-template-library-production.ts"
  }
}
```

- [ ] **Step 5: Re-run the targeted test**

Run: `cd backend && npm test -- backfill-template-library-production.spec.ts --runInBand`
Expected: PASS.

- [ ] **Step 6: Dry-run the backfill locally**

Run: `cd backend && npm run ops:backfill-template-library -- --dry-run`
Expected: A summary showing how many curated templates would be marked reviewed and how many machine templates would be downgraded or hidden, with no writes applied.

- [ ] **Step 7: Commit**

```bash
cd backend
git add package.json src/scripts src/makeup-templates/template-library/template-library-machine-metadata.ts
git commit -m "feat: add template library production backfill script"
```

## Task 4: Add batch quality and archive APIs for operators

**Files:**
- Create: `backend/src/makeup-templates/template-library/dto/batch-update-template-quality.dto.ts`
- Create: `backend/src/makeup-templates/template-library/dto/batch-archive-templates.dto.ts`
- Modify: `backend/src/makeup-templates/template-library/template-quality.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-quality.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`

- [ ] **Step 1: Write the failing batch-quality and batch-archive tests**

```ts
it('batch updates quality tier and review status for multiple templates', async () => {
  await service.batchUpdateTemplateQuality('user-001', {
    templateIds: ['std_001', 'std_002'],
    qualityTier: 'P1',
    reviewStatus: 'reviewed',
    qualityScore: 92,
    qualityReasons: ['operator approved'],
    operatorNote: 'launch-ready',
  });

  expect(prisma.standardMakeupTemplate.updateMany).toHaveBeenCalledWith(
    expect.objectContaining({
      where: { id: { in: ['std_001', 'std_002'] } },
      data: expect.objectContaining({
        qualityTier: 'P1',
        qualityReviewStatus: 'reviewed',
      }),
    }),
  );
});

it('archives multiple templates and records ops audit data', async () => {
  await service.batchArchiveTemplates('user-001', {
    templateIds: ['std_003', 'std_004'],
    operatorNote: 'duplicate low-signal source',
  });

  expect(prisma.standardMakeupTemplate.updateMany).toHaveBeenCalled();
  expect(prisma.templateOpsAuditLog.createMany).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `cd backend && npm test -- template-quality.service.spec.ts template-library.controller.spec.ts --runInBand`
Expected: FAIL because batch DTOs and methods do not exist.

- [ ] **Step 3: Add the batch DTOs**

```ts
export class BatchUpdateTemplateQualityDto {
  @IsArray()
  @ArrayMinSize(1)
  templateIds!: string[];

  @IsIn(['P1', 'P2', 'P3'])
  qualityTier!: 'P1' | 'P2' | 'P3';

  @IsIn(['pending', 'reviewed', 'repaired', 'archived'])
  reviewStatus!: 'pending' | 'reviewed' | 'repaired' | 'archived';

  @IsInt()
  qualityScore!: number;
}
```

```ts
export class BatchArchiveTemplatesDto {
  @IsArray()
  @ArrayMinSize(1)
  templateIds!: string[];

  @IsOptional()
  @IsString()
  operatorNote?: string;
}
```

- [ ] **Step 4: Implement the batch service methods**

```ts
async batchUpdateTemplateQuality(userId: string, dto: BatchUpdateTemplateQualityDto) {
  return this.prisma.$transaction(async (tx) => {
    await tx.standardMakeupTemplate.updateMany({
      where: { id: { in: dto.templateIds } },
      data: {
        qualityTier: dto.qualityTier,
        qualityScore: dto.qualityScore,
        qualityReasons: dto.qualityReasons,
        qualityReviewStatus: dto.reviewStatus,
        operatorNote: dto.operatorNote ?? null,
        updatedById: userId,
      },
    });
    await tx.templateOpsAuditLog.createMany({
      data: dto.templateIds.map((templateId) => ({
        id: createMakeupTemplateId('tops'),
        actorUserId: userId,
        actorRole: 'operator',
        eventType: 'quality_updated',
        entityType: 'standard_template',
        entityId: templateId,
        status: dto.reviewStatus,
        summary: `Batch updated template quality to ${dto.qualityTier}/${dto.reviewStatus}`,
        payload: {
          qualityTier: dto.qualityTier,
          qualityScore: dto.qualityScore,
          qualityReasons: dto.qualityReasons,
          operatorNote: dto.operatorNote ?? null,
        },
      })),
    });
  });
}
```

```ts
async batchArchiveTemplates(userId: string, dto: BatchArchiveTemplatesDto) {
  return this.prisma.$transaction(async (tx) => {
    await tx.standardMakeupTemplate.updateMany({
      where: { id: { in: dto.templateIds } },
      data: {
        status: 'archived',
        archivedAt: new Date(),
        visibility: 'private',
        updatedById: userId,
        operatorNote: dto.operatorNote ?? null,
      },
    });
  });
}
```

- [ ] **Step 5: Add backoffice routes**

```ts
@Post('templates/batch-quality')
@BackofficeRoles('admin', 'operator')
batchUpdateTemplateQuality(
  @CurrentUser() user: AuthenticatedUser,
  @Body() body: BatchUpdateTemplateQualityDto,
) {
  return this.qualityService.batchUpdateTemplateQuality(user.id, body);
}
```

```ts
@Post('templates/batch-archive')
@BackofficeRoles('admin', 'operator')
batchArchiveTemplates(
  @CurrentUser() user: AuthenticatedUser,
  @Body() body: BatchArchiveTemplatesDto,
) {
  return this.qualityService.batchArchiveTemplates(user.id, body);
}
```

- [ ] **Step 6: Re-run the targeted backend tests**

Run: `cd backend && npm test -- template-quality.service.spec.ts template-library.controller.spec.ts --runInBand`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd backend
git add src/makeup-templates/template-library
git commit -m "feat: add batch template quality operations"
```

## Task 5: Add generated-result disposition APIs and queue semantics

**Files:**
- Create: `backend/src/makeup-templates/dto/update-generated-template-review.dto.ts`
- Create: `backend/src/makeup-templates/generated-template-review.service.ts`
- Create: `backend/src/makeup-templates/generated-template-review.service.spec.ts`
- Modify: `backend/src/makeup-templates/makeup-templates.controller.ts`
- Modify: `backend/src/makeup-templates/makeup-templates.module.ts`
- Modify: `backend/src/makeup-templates/makeup-template-generation.service.ts`
- Modify: `backend/src/makeup-templates/template-library/generated-template-publication.service.ts`
- Modify: `backend/src/ops-workbench/ops-workbench.service.ts`

- [ ] **Step 1: Write the failing review-service tests**

```ts
it('marks generated result as materialized after formal draft linkage', async () => {
  prisma.generatedMakeupTemplate.update.mockResolvedValue({
    id: 'tmpl_001',
    reviewState: 'materialized',
    linkedStandardTemplateId: 'std_generated_001',
  } as never);

  const result = await service.markMaterialized('tmpl_001', 'user-001', {
    linkedStandardTemplateId: 'std_generated_001',
    linkedStandardVersionId: 'std_generated_001_v1',
  });

  expect(result.reviewState).toBe('materialized');
});

it('rejects generated results with operator note', async () => {
  await service.updateReviewState('tmpl_002', 'user-001', {
    reviewState: 'rejected',
    operatorNote: 'historical bad bridal commute match',
  });

  expect(prisma.generatedMakeupTemplate.update).toHaveBeenCalledWith(
    expect.objectContaining({
      data: expect.objectContaining({
        reviewState: 'rejected',
        operatorNote: 'historical bad bridal commute match',
      }),
    }),
  );
});
```

- [ ] **Step 2: Run the targeted tests to verify they fail**

Run: `cd backend && npm test -- generated-template-review.service.spec.ts --runInBand`
Expected: FAIL because the review service does not exist.

- [ ] **Step 3: Add the DTO and service**

```ts
export class UpdateGeneratedTemplateReviewDto {
  @IsIn(['pending', 'deferred', 'materialized', 'published', 'rejected', 'archived'])
  reviewState!: 'pending' | 'deferred' | 'materialized' | 'published' | 'rejected' | 'archived';

  @IsOptional()
  @IsString()
  @MaxLength(500)
  operatorNote?: string;
}
```

```ts
async updateReviewState(templateId: string, userId: string, dto: UpdateGeneratedTemplateReviewDto) {
  return this.prisma.generatedMakeupTemplate.update({
    where: { id: templateId },
    data: {
      reviewState: dto.reviewState,
      operatorNote: dto.operatorNote?.trim() || null,
      reviewedById: userId,
      reviewedAt: new Date(),
    },
  });
}
```

- [ ] **Step 4: Update publication flows to synchronize review state**

```ts
await tx.generatedMakeupTemplate.update({
  where: { id: templateId },
  data: {
    linkedStandardTemplateId: published.id,
    linkedStandardVersionId: published.currentVersionId,
    reviewState: 'published',
    reviewedById: userId,
    reviewedAt: new Date(),
  },
});
```

```ts
await tx.generatedMakeupTemplate.update({
  where: { id: templateId },
  data: {
    linkedStandardTemplateId: linkedTemplate.id,
    linkedStandardVersionId: linkedTemplate.currentVersionId,
    reviewState: 'materialized',
  },
});
```

- [ ] **Step 5: Add controller routes and query filtering**

```ts
@Patch('generated/:templateId/review')
@UseGuards(DemoAuthGuard, BackofficeRoleGuard)
@BackofficeRoles('admin', 'operator')
updateGeneratedReviewState(
  @CurrentUser() user: AuthenticatedUser,
  @Param('templateId') templateId: string,
  @Body() body: UpdateGeneratedTemplateReviewDto,
) {
  return this.reviewService.updateReviewState(templateId, user.id, body);
}
```

```ts
if (query.reviewState) {
  where.reviewState = query.reviewState;
}
```

- [ ] **Step 6: Update ops workbench summary and pending queues**

```ts
pendingGeneratedCount: await this.prisma.generatedMakeupTemplate.count({
  where: { reviewState: 'pending' },
})
```

```ts
pendingGeneratedResults: await this.prisma.generatedMakeupTemplate.findMany({
  where: { reviewState: 'pending' },
  orderBy: { createdAt: 'desc' },
  take: 10,
})
```

- [ ] **Step 7: Re-run the generated-result and ops tests**

Run: `cd backend && npm test -- generated-template-review.service.spec.ts recommendations.service.spec.ts template-library.controller.spec.ts --runInBand`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
cd backend
git add src/makeup-templates src/ops-workbench
git commit -m "feat: add generated result disposition flow"
```

## Task 6: Make the frontend queues operator-first and add batch actions

**Files:**
- Modify: `frontend/types/template-library.ts`
- Modify: `frontend/types/recommendation.ts`
- Modify: `frontend/services/templateLibraryService.ts`
- Modify: `frontend/services/generatedTemplateService.ts`
- Modify: `frontend/app/template-library/quality-queue.tsx`
- Modify: `frontend/app/template-library/index.tsx`
- Modify: `frontend/app/template-library/generated.tsx`
- Modify: `frontend/app/ops-workbench/index.tsx`
- Modify: `frontend/app/ops-workbench/tasks.tsx`

- [ ] **Step 1: Write the failing frontend type and service expectations**

```ts
type GeneratedMakeupTemplate = {
  id: string;
  reviewState: 'pending' | 'deferred' | 'materialized' | 'published' | 'rejected' | 'archived';
  operatorNote?: string | null;
};

const batchQualityPayload = {
  templateIds: ['std_001', 'std_002'],
  qualityTier: 'P1',
  reviewStatus: 'reviewed',
  qualityScore: 95,
  qualityReasons: ['launch-ready'],
};
```

- [ ] **Step 2: Run typecheck to verify it fails on missing fields and methods**

Run: `cd frontend && npx tsc --noEmit`
Expected: FAIL because the new generated-result fields and batch service methods are missing.

- [ ] **Step 3: Extend frontend types and services**

```ts
export type GeneratedTemplateReviewState =
  | 'pending'
  | 'deferred'
  | 'materialized'
  | 'published'
  | 'rejected'
  | 'archived';
```

```ts
batchUpdateTemplateQuality(payload: {
  templateIds: string[];
  qualityTier: TemplateQualityTier;
  reviewStatus: TemplateQualityReviewStatus;
  qualityScore: number;
  qualityReasons: string[];
  operatorNote?: string | null;
}) {
  return apiRequest('/makeup-template-library/templates/batch-quality', {
    method: 'POST',
    body: payload,
  });
}
```

```ts
updateReviewState(templateId: string, payload: {
  reviewState: GeneratedTemplateReviewState;
  operatorNote?: string | null;
}) {
  return apiRequest(`/makeup-templates/generated/${encodeURIComponent(templateId)}/review`, {
    method: 'PATCH',
    body: payload,
  });
}
```

- [ ] **Step 4: Change quality queue defaults and add selection mode**

```tsx
const [tier, setTier] = useState<TemplateQualityTier | undefined>();
const [reviewStatus, setReviewStatus] =
  useState<TemplateQualityReviewStatus | undefined>('pending');
const [selectedIds, setSelectedIds] = useState<string[]>([]);
```

```tsx
<Pressable
  onPress={() => toggleSelected(item.id)}
  className="mr-3 h-5 w-5 rounded border"
  style={{ backgroundColor: selected ? BRAND : '#FFFFFF' }}
/>
```

```tsx
<ActionButton
  label="批量标为 P1 reviewed"
  onPress={() =>
    batchQualityMutation.mutate({
      templateIds: selectedIds,
      qualityTier: 'P1',
      reviewStatus: 'reviewed',
      qualityScore: 90,
      qualityReasons: ['operator batch approved'],
    })
  }
/>
```

- [ ] **Step 5: Add batch archive from the formal template list**

```tsx
const [selectedTemplateIds, setSelectedTemplateIds] = useState<string[]>([]);
```

```tsx
<ActionButton
  label="批量归档"
  disabled={!selectedTemplateIds.length}
  onPress={() =>
    batchArchiveMutation.mutate({
      templateIds: selectedTemplateIds,
      operatorNote: 'batch archived from template list',
    })
  }
/>
```

- [ ] **Step 6: Add generated-result disposition actions**

```tsx
<Pressable
  onPress={() =>
    reviewMutation.mutate({
      templateId: item.id,
      reviewState: 'rejected',
      operatorNote: 'historical mismatch; not suitable for formal library',
    })
  }
>
  <Text>驳回</Text>
</Pressable>
```

```tsx
<Pressable
  onPress={() =>
    reviewMutation.mutate({
      templateId: item.id,
      reviewState: 'deferred',
      operatorNote: 'hold for later manual review',
    })
  }
>
  <Text>暂缓</Text>
</Pressable>
```

- [ ] **Step 7: Surface real queue counts in the ops workbench**

```tsx
<MetricCard label="待复核" value={summary.pendingReviewCount} accent="#9B4152" />
<MetricCard label="待转正式" value={summary.pendingGeneratedCount} accent="#B78928" />
```

```tsx
<PendingStrip
  title="待转正式生成结果"
  count={pending.pendingGeneratedResults.length}
  description={pending.pendingGeneratedResults[0]?.displayName ?? '当前没有待转正式生成结果'}
/>
```

- [ ] **Step 8: Run frontend verification**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: PASS.

- [ ] **Step 9: Commit**

```bash
cd frontend
git add app services types
git commit -m "feat: add operator-first template queue UX"
```

## Task 7: Apply the backfill, verify the operator path, and update runbooks

**Files:**
- Modify: `docs/template-matching-test-guide.md`
- Create: `docs/template-library-production-ops-runbook.md`
- Test: live backend/frontend/runtime verification commands only

- [ ] **Step 1: Add the launch runbook**

```md
## Production Ops Launch Checklist

1. Run Prisma migration.
2. Run template-library production backfill in dry-run mode.
3. Run template-library production backfill in apply mode.
4. Verify reviewed P1/P2 pool exists.
5. Verify pending machine backlog is visible in the quality queue.
6. Verify generated-result queue can reject, defer, and publish.
7. Verify recommendation, preview, and five-step voice checks.
```

- [ ] **Step 2: Update the template matching test guide**

```md
- Production matching only consumes `published + reviewed + P1/P2 + non-private` templates.
- Public-video machine templates start in the backlog, not in the live pool.
- Generated results must be `published` or linked through formal publication to leave the pending queue.
```

- [ ] **Step 3: Run the database migration**

Run: `cd backend && npm run db:migrate`
Expected: migration applies successfully.

- [ ] **Step 4: Run the backfill dry-run and apply pass**

Run: `cd backend && npm run ops:backfill-template-library -- --dry-run`
Expected: summary only, no writes.

Run: `cd backend && npm run ops:backfill-template-library -- --apply`
Expected: curated templates become reviewed; machine templates are normalized to backlog-safe states.

- [ ] **Step 5: Verify the production template pool**

Run:

```bash
curl -s -H 'Authorization: Bearer demo-token' \
  http://127.0.0.1:13000/ops-workbench/summary | jq
```

Expected:
- `qualityTierCounts.P1 + qualityTierCounts.P2 > 0`
- `pendingReviewCount` drops below the full raw template count

- [ ] **Step 6: Verify the production matching gate**

Run:

```bash
curl -s -X POST http://127.0.0.1:13000/makeup-template-library/match-debug \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{"rawUserInput":"通勤淡妆，清透自然，不要太浓。"}' | jq
```

Expected:
- selected template is reviewed and `P1/P2`
- no unreviewed `P3` machine template is selected

- [ ] **Step 7: Verify preview smoke still works**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague && \
python eval/makeup/scripts/run_eval_pipeline.py \
  --project-root . \
  --backend-url http://127.0.0.1:13000 \
  --limit 1 \
  --case-count 1 \
  --vlm-mode mock \
  --run-id smoke_prod_ops_preview
```

Expected: `case_0001: success`

- [ ] **Step 8: Verify five-step voice evaluation still works**

Run:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague && \
python eval/coach/scripts/run_five_step_voice_eval.py \
  --backend-url http://127.0.0.1:13001 \
  --group-id group_001 \
  --timeout 180 \
  --sleep-sec 0
```

Expected: `passed: 5/5`

- [ ] **Step 9: Manual operator UAT**

Run this exact UI path:

1. Open `Profile -> 运营工作台`
2. Open `模板质量队列`
3. Select multiple pending templates
4. Batch-mark one set reviewed
5. Batch-archive one clearly unsuitable set
6. Open `生成结果队列`
7. Reject one historical bad result
8. Publish one safe result
9. Generate one frontend recommendation and confirm the result still matches a reviewed production template

Expected: counts update across queue screens and workbench cards without database access.

- [ ] **Step 10: Commit**

```bash
git add docs/template-matching-test-guide.md docs/template-library-production-ops-runbook.md
git commit -m "docs: add template library production ops runbook"
```

## Task 8: P1 follow-up implementation wave after P0 is stable

**Files:**
- Modify: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-draft-generator.service.ts`
- Modify: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-publish.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-matching.service.ts`
- Modify: `backend/src/ops-workbench/ops-workbench.service.ts`
- Modify: `frontend/app/template-library/quality-queue.tsx`
- Modify: `frontend/app/template-library/detail.tsx`
- Modify: `frontend/app/ops-workbench/tasks.tsx`

- [ ] **Step 1: Write failing tests for duplicate suppression and source priors**

```ts
it('suppresses near-duplicate machine templates from the same family during shortlist ranking', async () => {
  const shortlisted = shortlistTemplatesForRerank({
    profile,
    templates: duplicateFamilyTemplates,
    queryTokens,
    limit: 8,
  });

  expect(shortlisted.filter((item) => item.styleFamily === 'DAILY_COMMUTE').length).toBeLessThan(8);
});
```

- [ ] **Step 2: Run the duplicate-suppression test to verify it fails**

Run: `cd backend && npm test -- template-matching.service.spec.ts --runInBand`
Expected: FAIL because diversity priors are not present.

- [ ] **Step 3: Add ranking priors after the mandatory model path**

```ts
const reviewedPrior = template.qualityReviewStatus === 'reviewed' ? 0.08 : 0;
const sourcePrior = template.source === 'seed' ? 0.06 : 0;
const diversityPenalty = seenStyleFamilies.has(template.styleFamily) ? 0.05 : 0;
```

- [ ] **Step 4: Add evidence drill-through fields to queue and detail views**

```tsx
<Meta label={item.sourcePlatform ?? '未记录来源'} />
<Meta label={item.evidenceAvailable ? '有证据帧' : '无证据帧'} />
<Text>{item.sourceUrl}</Text>
```

- [ ] **Step 5: Add queue ergonomics improvements**

```tsx
const sortOptions = ['updatedAt', 'autoQualityScore', 'styleFamily', 'sourcePlatform'] as const;
```

- [ ] **Step 6: Re-run targeted backend and frontend verification**

Run: `cd backend && npm test -- template-matching.service.spec.ts public-video-publish.service.spec.ts --runInBand`
Expected: PASS.

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/src/makeup-templates/template-library frontend/app/template-library frontend/app/ops-workbench
git commit -m "feat: improve template library operator quality flow"
```
