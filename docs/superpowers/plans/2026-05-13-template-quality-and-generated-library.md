# Template Quality Layering And Generated Result Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add template quality layering, generated-result-library persistence, editable user template instances, repair workflow, and P1-first consumption so the current 100-template library becomes a real product platform rather than a static catalog.

**Architecture:** Reuse the existing `GeneratedMakeupTemplate` result library instead of introducing a duplicate generated-instance table. Extend the current backend template-library module with quality-review metadata, generated-result management APIs, and materialize/publish linkage into the versioned `StandardMakeupTemplate` library, then wire the frontend template-library screens to manage quality queue, generated-result publishing, and P1-first consumption.

**Tech Stack:** NestJS 11, Prisma 7, PostgreSQL, Jest, Expo Router 6, React Native, Zustand, TanStack Query.

---

## Progress Snapshot

- Task 1 completed: standard template quality persistence is in Prisma schema and migration.
- Task 2 completed: quality update API and quality queue API are implemented and covered by service/controller tests.
- Revised execution decision: the remaining generated-result-library work will build on existing `GeneratedMakeupTemplate`, `GeneratedTemplateStep`, `TemplateProductSlot`, `TemplateEvent`, and `TemplateMatchTrace` instead of creating a second generated-instance model.
- Remaining delivery scope:
  - add generated-result management/materialization/publish linkage into the formal template library
  - expose generated-result management APIs and frontend management pages
  - make template matching consume P1 first and degrade to P2/P3 only when needed
  - finish P3 repair workflow and user-facing template-library operations

## Revised Execution Notes

- The original Task 3/4 wording below assumed a new `GeneratedTemplateInstance` model. That is no longer the implementation path.
- For the rest of execution, treat `GeneratedMakeupTemplate` as the generated result library row and `StandardMakeupTemplate` as the formal published library row.
- "Edit generated result" is implemented by materializing a linked formal-template draft from the generated result, then reusing the existing versioned draft/publish/rollback flows.

## File Map

### Backend schema and domain
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/prisma/migrations/<timestamp>_add_template_quality_and_generated_instances/`
- Create: `backend/src/makeup-templates/template-library/dto/update-template-quality.dto.ts`
- Create: `backend/src/makeup-templates/template-library/dto/create-generated-template-instance.dto.ts`
- Create: `backend/src/makeup-templates/template-library/dto/update-generated-template-instance.dto.ts`
- Create: `backend/src/makeup-templates/template-library/dto/list-generated-template-instances.dto.ts`
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.types.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-machine-metadata.ts`

### Backend services and controllers
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-admin.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Create: `backend/src/makeup-templates/template-library/template-quality.service.ts`
- Create: `backend/src/makeup-templates/template-library/generated-template-instance.service.ts`
- Create: `backend/src/makeup-templates/template-library/template-quality.service.spec.ts`
- Create: `backend/src/makeup-templates/template-library/generated-template-instance.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-admin.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.service.spec.ts`

### Recommendation and matching integration
- Modify: `backend/src/recommendations/recommendations.service.ts`
- Modify: `backend/src/recommendations/recommendations.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-db.mapper.ts`

### Frontend service and screens
- Modify: `frontend/services/templateLibraryService.ts`
- Modify: `frontend/types/template-library.ts`
- Modify: `frontend/app/template-library/index.tsx`
- Modify: `frontend/app/template-library/detail.tsx`
- Create: `frontend/app/template-library/generated.tsx`
- Create: `frontend/app/template-library/quality-queue.tsx`

### Frontend tests/docs
- Modify: `docs/template-matching-test-guide.md`
- Create: `docs/superpowers/plans/2026-05-13-template-quality-and-generated-library.md`

## Task 1: Add template quality persistence to the database

**Files:**
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/prisma/migrations/<timestamp>_add_template_quality_and_generated_instances/`
- Test: `backend/src/makeup-templates/template-library/template-quality.service.spec.ts`

- [ ] **Step 1: Write the failing schema/service test for template quality fields**

```ts
it('persists quality tier, score, reasons, and review state for a standard template', async () => {
  const result = await service.updateQuality('tpl-001', {
    qualityTier: 'P1',
    qualityScore: 92,
    qualityReasons: ['clear tutorial flow', 'five-step evidence complete'],
    reviewStatus: 'reviewed',
    operatorNote: 'ready for storefront',
  });

  expect(result.qualityTier).toBe('P1');
  expect(result.qualityScore).toBe(92);
  expect(result.qualityReasons).toEqual([
    'clear tutorial flow',
    'five-step evidence complete',
  ]);
  expect(result.reviewStatus).toBe('reviewed');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && npm test -- template-quality.service.spec.ts`
Expected: FAIL because `TemplateQualityService` and DB fields do not exist.

- [ ] **Step 3: Add Prisma fields and enums for quality metadata**

```prisma
enum TemplateQualityReviewStatus {
  pending
  reviewed
  repaired
  archived
}

model StandardMakeupTemplate {
  id             String   @id
  qualityTier    String?  @db.VarChar(8)
  qualityScore   Int?
  qualityReasons Json?
  reviewStatus   TemplateQualityReviewStatus @default(pending)
  operatorNote   String?
  repairedAt     DateTime?
}
```

- [ ] **Step 4: Create and apply migration locally**

Run: `cd backend && npx prisma migrate dev --name add_template_quality_and_generated_instances`
Expected: migration directory created and local DB updated.

- [ ] **Step 5: Run Prisma generate and schema-targeted tests**

Run: `cd backend && npm run prisma:generate && npm test -- template-quality.service.spec.ts`
Expected: still FAIL until service is implemented, but Prisma compile errors are gone.

- [ ] **Step 6: Commit**

```bash
cd backend
git add prisma/schema.prisma prisma/migrations
git commit -m "feat: add template quality persistence schema"
```

## Task 2: Implement backend template quality service and API

**Files:**
- Create: `backend/src/makeup-templates/template-library/template-quality.service.ts`
- Create: `backend/src/makeup-templates/template-library/dto/update-template-quality.dto.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`
- Test: `backend/src/makeup-templates/template-library/template-quality.service.spec.ts`

- [ ] **Step 1: Write failing controller test for quality update and queue listing**

```ts
it('updates template quality and lists the quality queue', async () => {
  await request(app.getHttpServer())
    .patch('/makeup-template-library/templates/tpl-001/quality')
    .send({
      qualityTier: 'P2',
      qualityScore: 74,
      qualityReasons: ['good structure', 'weak source title'],
      reviewStatus: 'reviewed',
    })
    .expect(200);

  const response = await request(app.getHttpServer())
    .get('/makeup-template-library/quality-queue?tier=P2')
    .expect(200);

  expect(response.body.items[0].qualityTier).toBe('P2');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && npm test -- template-library.controller.spec.ts template-quality.service.spec.ts`
Expected: FAIL because endpoint and service are missing.

- [ ] **Step 3: Implement DTO and service methods**

```ts
export class UpdateTemplateQualityDto {
  qualityTier!: 'P1' | 'P2' | 'P3';
  qualityScore!: number;
  qualityReasons!: string[];
  reviewStatus!: 'pending' | 'reviewed' | 'repaired' | 'archived';
  operatorNote?: string;
}
```

```ts
async updateQuality(templateId: string, dto: UpdateTemplateQualityDto) {
  return this.prisma.standardMakeupTemplate.update({
    where: { id: templateId },
    data: {
      qualityTier: dto.qualityTier,
      qualityScore: dto.qualityScore,
      qualityReasons: dto.qualityReasons,
      reviewStatus: dto.reviewStatus,
      operatorNote: dto.operatorNote ?? null,
      repairedAt: dto.reviewStatus === 'repaired' ? new Date() : undefined,
    },
  });
}
```

- [ ] **Step 4: Add controller routes**

```ts
@Patch('templates/:templateId/quality')
updateTemplateQuality(...) {}

@Get('quality-queue')
listQualityQueue(...) {}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd backend && npm test -- template-library.controller.spec.ts template-quality.service.spec.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add src/makeup-templates/template-library
git commit -m "feat: add template quality admin api"
```

## Task 3: Add generated template instance data model

**Files:**
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/src/makeup-templates/template-library/generated-template-instance.service.ts`
- Create: `backend/src/makeup-templates/template-library/dto/create-generated-template-instance.dto.ts`
- Create: `backend/src/makeup-templates/template-library/dto/update-generated-template-instance.dto.ts`
- Create: `backend/src/makeup-templates/template-library/generated-template-instance.service.spec.ts`

- [ ] **Step 1: Write failing service test for generated template instances**

```ts
it('creates a generated template instance with source template, user context, and product usage', async () => {
  const instance = await service.create({
    userId: 'user-001',
    sourceTemplateId: 'std_machine_pv_vimeo_xxx',
    scenario: 'office commute',
    generationReason: 'user requested fast polished daily look',
    userProfileSnapshot: { skinTone: 'neutral', skillLevel: 'beginner' },
    usedProducts: [{ slotCode: 'slot_foundation', userProductId: 'up-1' }],
    missingProducts: ['slot_setting_spray'],
  });

  expect(instance.userId).toBe('user-001');
  expect(instance.sourceTemplateId).toBe('std_machine_pv_vimeo_xxx');
  expect(instance.missingProducts).toEqual(['slot_setting_spray']);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && npm test -- generated-template-instance.service.spec.ts`
Expected: FAIL because model/service do not exist.

- [ ] **Step 3: Add Prisma model for generated instances**

```prisma
model GeneratedTemplateInstance {
  id                  String   @id @default(cuid())
  userId              String
  sourceTemplateId    String
  sourceVersionId     String?
  scenario            String
  generationReason    String
  qualityTierAtCreate String?
  userProfileSnapshot Json
  usedProducts        Json
  missingProducts     Json
  replacedProducts    Json?
  editedSteps         Json?
  executionSummary    Json?
  satisfactionScore   Int?
  status              String   @default("draft")
  createdAt           DateTime @default(now())
  updatedAt           DateTime @updatedAt
}
```

- [ ] **Step 4: Implement create/list/update service methods**

```ts
async create(dto: CreateGeneratedTemplateInstanceDto) {
  return this.prisma.generatedTemplateInstance.create({ data: { ...dto } });
}
```

- [ ] **Step 5: Run migration/generate/tests**

Run: `cd backend && npm run prisma:generate && npm test -- generated-template-instance.service.spec.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add prisma src/makeup-templates/template-library/generated-template-instance.service*
git commit -m "feat: add generated template instance model"
```

## Task 4: Expose generated instance CRUD and user edit/publish/rollback lifecycle

**Files:**
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-admin.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-admin.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`

- [ ] **Step 1: Write failing controller test for generated-instance lifecycle**

```ts
it('creates, edits, publishes, and rolls back a generated template instance', async () => {
  const created = await request(app.getHttpServer())
    .post('/makeup-template-library/generated-instances')
    .send({
      userId: 'user-001',
      sourceTemplateId: 'tpl-001',
      scenario: 'daily commute',
      generationReason: 'need a 5-minute office look',
      userProfileSnapshot: { skinTone: 'neutral' },
      usedProducts: [],
      missingProducts: [],
    })
    .expect(201);

  await request(app.getHttpServer())
    .patch(`/makeup-template-library/generated-instances/${created.body.id}`)
    .send({ status: 'edited', editedSteps: [{ stepCode: 'block_eye', action: 'replace' }] })
    .expect(200);

  await request(app.getHttpServer())
    .post(`/makeup-template-library/generated-instances/${created.body.id}/publish`)
    .send({ changeSummary: 'publish first personal version' })
    .expect(201);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && npm test -- template-library.controller.spec.ts template-library-admin.service.spec.ts`
Expected: FAIL.

- [ ] **Step 3: Implement controller routes for generated instances**

```ts
@Post('generated-instances')
createGeneratedInstance(...) {}

@Patch('generated-instances/:instanceId')
updateGeneratedInstance(...) {}

@Post('generated-instances/:instanceId/publish')
publishGeneratedInstance(...) {}
```

- [ ] **Step 4: Reuse existing versioned publish/rollback machinery for generated templates**

```ts
async publishGeneratedInstance(instanceId: string, dto: PublishStandardTemplateDto) {
  const instance = await this.generatedTemplateInstances.getById(instanceId);
  return this.publishDraftAsStandardTemplate({
    ownerUserId: instance.userId,
    payload: buildDraftPayloadFromGeneratedInstance(instance),
    changeSummary: dto.changeSummary,
  });
}
```

- [ ] **Step 5: Run tests to verify it passes**

Run: `cd backend && npm test -- template-library.controller.spec.ts template-library-admin.service.spec.ts generated-template-instance.service.spec.ts`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd backend
git add src/makeup-templates/template-library
git commit -m "feat: add generated template instance lifecycle api"
```

## Task 5: Default recommendation consumption to P1, fallback to P2

**Files:**
- Modify: `backend/src/recommendations/recommendations.service.ts`
- Modify: `backend/src/recommendations/recommendations.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.service.ts`

- [ ] **Step 1: Write failing recommendation test for P1-first behavior**

```ts
it('prefers P1 templates and only falls back to P2 when P1 candidates are insufficient', async () => {
  const result = await service.generateRecommendation({ scenario: 'daily commute' });
  expect(result.templates.every((item) => item.qualityTier === 'P1')).toBe(true);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && npm test -- recommendations.service.spec.ts`
Expected: FAIL because recommendation query does not filter by quality tier.

- [ ] **Step 3: Add quality-aware query path**

```ts
const p1Templates = await this.templateLibrary.listPublishedTemplates({
  visibility: 'team',
  qualityTier: 'P1',
});

const templates = p1Templates.length >= requestedCount
  ? p1Templates
  : [
      ...p1Templates,
      ...(await this.templateLibrary.listPublishedTemplates({
        visibility: 'team',
        qualityTier: 'P2',
      })),
    ];
```

- [ ] **Step 4: Run tests to verify it passes**

Run: `cd backend && npm test -- recommendations.service.spec.ts standard-template-library.service.spec.ts`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd backend
git add src/recommendations src/makeup-templates/template-library
git commit -m "feat: make recommendation consume P1 templates first"
```

## Task 6: Add frontend quality queue and generated-instance management pages

**Files:**
- Modify: `frontend/services/templateLibraryService.ts`
- Modify: `frontend/types/template-library.ts`
- Modify: `frontend/app/template-library/index.tsx`
- Modify: `frontend/app/template-library/detail.tsx`
- Create: `frontend/app/template-library/generated.tsx`
- Create: `frontend/app/template-library/quality-queue.tsx`

- [ ] **Step 1: Write the missing TypeScript contract first**

```ts
export type TemplateQualityTier = 'P1' | 'P2' | 'P3';

export type GeneratedTemplateInstance = {
  id: string;
  userId: string;
  sourceTemplateId: string;
  scenario: string;
  generationReason: string;
  status: string;
  missingProducts: string[];
  editedSteps?: Array<Record<string, unknown>>;
};
```

- [ ] **Step 2: Run typecheck to verify frontend is missing the new contracts**

Run: `cd frontend && npx tsc --noEmit`
Expected: FAIL after service/page references are added.

- [ ] **Step 3: Add service methods**

```ts
listQualityQueue(params?: { tier?: TemplateQualityTier })
updateTemplateQuality(templateId: string, payload: UpdateTemplateQualityPayload)
listGeneratedInstances()
createGeneratedInstance(payload: CreateGeneratedTemplateInstancePayload)
publishGeneratedInstance(instanceId: string, payload: { changeSummary: string })
```

- [ ] **Step 4: Add management screens**

```tsx
// quality-queue.tsx
// Show tier filter tabs, score, reasons, review status, and promote/demote actions

// generated.tsx
// Show generated instances, missing products, edit state, publish action, rollback entry
```

- [ ] **Step 5: Update template-library home/detail pages**

```tsx
// add entry cards:
// - 模板质量队列
// - 个人生成模板
// show qualityTier badge on template cards
```

- [ ] **Step 6: Run typecheck and lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
cd frontend
git add app/template-library services/templateLibraryService.ts types/template-library.ts
git commit -m "feat: add quality queue and generated template screens"
```

## Task 7: Add P3 repair workflow

**Files:**
- Modify: `backend/src/makeup-templates/template-library/template-quality.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-quality.service.spec.ts`
- Modify: `frontend/app/template-library/quality-queue.tsx`

- [ ] **Step 1: Write failing test for repair workflow**

```ts
it('moves a P3 template into repair state and records the repair note', async () => {
  const result = await service.markForRepair('tpl-p3', {
    operatorNote: 'weak step evidence, rerun extraction',
  });

  expect(result.reviewStatus).toBe('repaired');
  expect(result.operatorNote).toContain('rerun extraction');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && npm test -- template-quality.service.spec.ts`
Expected: FAIL.

- [ ] **Step 3: Implement repair action and queue filtering**

```ts
async markForRepair(templateId: string, dto: { operatorNote: string }) {
  return this.prisma.standardMakeupTemplate.update({
    where: { id: templateId },
    data: {
      reviewStatus: 'repaired',
      operatorNote: dto.operatorNote,
      repairedAt: new Date(),
    },
  });
}
```

- [ ] **Step 4: Add frontend repair action button for P3 rows**

```tsx
<Button onPress={() => mutateRepair({ templateId, operatorNote })}>移入修复队列</Button>
```

- [ ] **Step 5: Run backend/frontend verification**

Run: `cd backend && npm test -- template-quality.service.spec.ts`
Run: `cd frontend && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd backend && git add src/makeup-templates/template-library && git commit -m "feat: add p3 repair workflow"
cd ../frontend && git add app/template-library/quality-queue.tsx && git commit -m "feat: expose p3 repair queue action"
```

## Task 8: Update docs and test guide

**Files:**
- Modify: `docs/template-matching-test-guide.md`
- Modify: `docs/team-runbook.md`
- Create: `docs/superpowers/plans/2026-05-13-template-quality-and-generated-library.md`

- [ ] **Step 1: Document the new quality queue and generated-instance user journey**

Add sections covering:
- quality tier review flow,
- P1-only default storefront behavior,
- generated template instance creation/edit/publish/rollback,
- P3 repair workflow.

- [ ] **Step 2: Add concrete API verification commands**

```bash
curl -fsS -H "Authorization: Bearer demo-token"   http://127.0.0.1:13000/makeup-template-library/quality-queue

curl -fsS -H "Authorization: Bearer demo-token"   http://127.0.0.1:13000/makeup-template-library/generated-instances
```

- [ ] **Step 3: Run a final backend/frontend verification pass**

Run:
- `cd backend && npm run build && npm test`
- `cd frontend && npx tsc --noEmit && npm run lint`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add docs
git commit -m "docs: add template quality and generated library runbook"
```

## Self-Review

- Spec coverage: this plan covers quality layering, generated result library, editable/publishable user-generated instances, P3 repair queue, and P1-first recommendation consumption.
- Placeholder scan: no TBD/TODO placeholders remain; all tasks name exact files and commands.
- Type consistency: `qualityTier`, `reviewStatus`, and `GeneratedTemplateInstance` naming is consistent across schema, services, APIs, and frontend contracts.
