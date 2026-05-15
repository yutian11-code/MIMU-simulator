# Public Video Template Library Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an automated public-video ingestion pipeline that retains source evidence locally, generates MMU-aligned 5-step drafts, and auto-publishes at least 30 usable formal templates into the existing template library.

**Architecture:** Extend the existing formal template library instead of replacing it. Add separate ingestion persistence for source videos, extraction artifacts, drafts, and publish runs; write machine-generated output into the current `StandardMakeupTemplate*` tables with source/evidence metadata stored in `templatePayload` and surfaced through the current admin/template APIs.

**Tech Stack:** NestJS, Prisma/PostgreSQL, existing template-library services, Node child process integration for `yt-dlp`/`ffprobe`, ffmpeg-static, React Native Expo web admin pages, Jest.

---

### Task 1: Add ingestion persistence and formal-library metadata support

**Files:**
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/prisma/migrations/20260513120000_add_public_video_template_ingestion/migration.sql`
- Modify: `backend/src/makeup-templates/template-library/template-library-admin.service.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-db.mapper.ts`
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.types.ts`
- Test: `backend/src/makeup-templates/template-library/template-library-admin.service.spec.ts`

- [ ] **Step 1: Write the failing metadata mapping test**

```ts
it('exposes machine-generated template metadata from templatePayload', async () => {
  const template = await service.getById('std_public_demo');
  expect(template.machineGenerated).toBe(true);
  expect(template.priorityClass).toBe('P2');
  expect(template.sourcePlatform).toBe('youtube');
  expect(template.evidenceAvailable).toBe(true);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && npm test -- --runInBand src/makeup-templates/template-library/template-library-admin.service.spec.ts`
Expected: FAIL because `machineGenerated`, `priorityClass`, `sourcePlatform`, `sourceUrl`, `autoQualityScore`, or `evidenceAvailable` are missing from template mapping.

- [ ] **Step 3: Add Prisma persistence for ingestion entities and metadata-compatible types**

```prisma
enum TemplateSource {
  seed
  user_created
  user_edited
  rollback
  machine_generated
}

model PublicVideoSource {
  id                String   @id @db.VarChar(80)
  platform          String   @db.VarChar(40)
  sourceUrl         String   @unique @map("source_url") @db.VarChar(2048)
  authorName        String?  @map("author_name") @db.VarChar(180)
  title             String   @db.VarChar(300)
  publishTime       DateTime? @map("publish_time")
  crawlTime         DateTime @map("crawl_time")
  visibilityStatus  String   @map("visibility_status") @db.VarChar(40)
  accessibility     String   @db.VarChar(40)
  notes             String?  @db.VarChar(500)
  rawAsset          PublicVideoAsset?
  extractions       PublicVideoExtraction[]
  drafts            PublicVideoTemplateDraft[]
  createdAt         DateTime @default(now()) @map("created_at")
  updatedAt         DateTime @updatedAt @map("updated_at")

  @@index([platform, crawlTime])
  @@map("public_video_sources")
}
```

- [ ] **Step 4: Extend template mapping to surface machine metadata from `templatePayload`**

```ts
const machineMetadata = readMachineTemplateMetadata(row.currentVersion?.templatePayload);

return {
  id: row.id,
  templateCode: row.templateCode,
  // ...
  source: row.source,
  machineGenerated: row.source === 'machine_generated' || machineMetadata.machineGenerated,
  priorityClass: machineMetadata.priorityClass ?? null,
  sourcePlatform: machineMetadata.sourcePlatform ?? null,
  sourceUrl: machineMetadata.sourceUrl ?? null,
  autoQualityScore: machineMetadata.autoQualityScore ?? null,
  evidenceAvailable: machineMetadata.evidenceAvailable ?? false,
};
```

- [ ] **Step 5: Run targeted tests and generate Prisma client**

Run: `cd backend && npm run prisma:generate && npm test -- --runInBand src/makeup-templates/template-library/template-library-admin.service.spec.ts`
Expected: PASS for admin mapping tests and Prisma client generation succeeds.

- [ ] **Step 6: Commit**

```bash
git add backend/prisma/schema.prisma \
  backend/prisma/migrations/20260513120000_add_public_video_template_ingestion/migration.sql \
  backend/src/makeup-templates/template-library/template-library-admin.service.ts \
  backend/src/makeup-templates/template-library/template-library-db.mapper.ts \
  backend/src/makeup-templates/template-library/standard-template-library.types.ts \
  backend/src/makeup-templates/template-library/template-library-admin.service.spec.ts
git commit -m "feat: add public video template ingestion schema"
```

### Task 2: Implement source ingestion, extraction, draft generation, and publish services

**Files:**
- Create: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-ingestion.types.ts`
- Create: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-manifest.service.ts`
- Create: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-downloader.service.ts`
- Create: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-extraction.service.ts`
- Create: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-draft-generator.service.ts`
- Create: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-publish.service.ts`
- Create: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-ingestion.service.ts`
- Modify: `backend/src/makeup-templates/makeup-templates.module.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library-seed.service.ts`
- Test: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-ingestion.service.spec.ts`

- [ ] **Step 1: Write the failing orchestration test**

```ts
it('publishes visible P1/P2 templates and hides P3 templates from a manifest run', async () => {
  const result = await service.ingestFromManifest({
    manifestPath: 'test/fixtures/public-video-manifest.json',
    maxPublishCount: 3,
  });

  expect(result.autoReadyCount).toBe(3);
  expect(result.publishedVisibleCount).toBe(2);
  expect(result.publishedHiddenCount).toBe(1);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && npm test -- --runInBand src/makeup-templates/template-library/public-video-ingestion/public-video-ingestion.service.spec.ts`
Expected: FAIL because the ingestion module and services do not exist.

- [ ] **Step 3: Implement deterministic manifest-driven ingestion and extraction services**

```ts
async ingestFromManifest(input: IngestionRunInput): Promise<IngestionRunResult> {
  const sources = await this.manifest.load(input.manifestPath, input.limit);
  const run = await this.publishRuns.createStartedRun(sources.length, input.manifestPath);

  for (const source of sources) {
    const storedSource = await this.sourceStore.upsertSource(source);
    const asset = await this.downloader.ensureRawVideo(storedSource);
    const extraction = await this.extractor.extract(asset, storedSource, run.id);
    const draft = await this.draftGenerator.generate({ source: storedSource, asset, extraction });
    await this.publisher.publishDraft(draft, run.id);
  }

  return this.publishRuns.complete(run.id);
}
```

- [ ] **Step 4: Reuse the existing 5-step standard template skeletons and attach evidence-backed payload metadata**

```ts
const baseTemplate = this.templateLibrary.pickSkeleton(style.styleId);

return {
  displayName: `${source.title}·${style.displayName}`,
  description: `来源于公开视频：${source.title}`,
  styleId: style.styleId,
  styleFamily: style.family,
  primaryScene: scene,
  styleTags,
  effectTags,
  difficultyBaseScore: difficulty.score,
  minSkillLevel: difficulty.level,
  estimatedTimeMinutes: estimatedMinutes,
  templateDescription,
  visualDescription,
  stepBlocks: withEvidenceFrames(baseTemplate.stepBlocks, extraction.keyFrames),
  productSlots: baseTemplate.productSlots,
  templatePayload: {
    machineGenerated: true,
    sourcePlatform: source.platform,
    sourceUrl: source.sourceUrl,
    priorityClass,
    autoQualityScore,
    evidenceAvailable: true,
    publicVideoSourceId: source.id,
    publicVideoDraftId: draftId,
    publishRunId: runId,
  },
};
```

- [ ] **Step 5: Publish into formal template tables through a dedicated machine-publish path**

```ts
await tx.standardMakeupTemplate.upsert({
  where: { id: templateId },
  create: {
    id: templateId,
    templateCode: templateId,
    ownerUserId: ownerUserId,
    displayName: payload.displayName,
    description: payload.templateDescription,
    status: 'published',
    reviewStatus: 'not_required',
    visibility: priorityClass === 'P3' ? 'private' : 'team',
    source: 'machine_generated',
    createdById: ownerUserId,
    updatedById: ownerUserId,
    publishedAt: now,
  },
  update: {
    displayName: payload.displayName,
    description: payload.templateDescription,
    visibility: priorityClass === 'P3' ? 'private' : 'team',
    source: 'machine_generated',
    updatedById: ownerUserId,
    publishedAt: now,
  },
});
```

- [ ] **Step 6: Run the new service tests**

Run: `cd backend && npm test -- --runInBand src/makeup-templates/template-library/public-video-ingestion/public-video-ingestion.service.spec.ts`
Expected: PASS with coverage for source persistence, evidence assignment, priority visibility, and publish summary.

- [ ] **Step 7: Commit**

```bash
git add backend/src/makeup-templates/makeup-templates.module.ts \
  backend/src/makeup-templates/template-library/template-library-seed.service.ts \
  backend/src/makeup-templates/template-library/public-video-ingestion \
  backend/src/makeup-templates/template-library/public-video-ingestion/public-video-ingestion.service.spec.ts
git commit -m "feat: implement public video template ingestion pipeline"
```

### Task 3: Expose operator APIs and update the template-library UI

**Files:**
- Create: `backend/src/makeup-templates/template-library/dto/run-public-video-ingestion.dto.ts`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Test: `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`
- Modify: `frontend/types/template-library.ts`
- Modify: `frontend/services/templateLibraryService.ts`
- Modify: `frontend/app/template-library/index.tsx`
- Modify: `frontend/app/template-library/detail.tsx`

- [ ] **Step 1: Write the failing API/controller and frontend shape tests**

```ts
it('returns ingestion run summaries from the template-library controller', async () => {
  await expect(controller.runPublicVideoIngestion(user, dto)).resolves.toMatchObject({
    runId: expect.any(String),
    autoReadyCount: expect.any(Number),
  });
});
```

```ts
type TemplateLibraryItem = {
  machineGenerated: boolean;
  priorityClass?: 'P1' | 'P2' | 'P3' | null;
  sourcePlatform?: string | null;
};
```

- [ ] **Step 2: Run controller tests to verify they fail**

Run: `cd backend && npm test -- --runInBand src/makeup-templates/template-library/template-library.controller.spec.ts`
Expected: FAIL because the ingestion endpoints are not defined.

- [ ] **Step 3: Add internal ingestion endpoints to the current controller**

```ts
@Post('ingestion/runs')
async runPublicVideoIngestion(
  @CurrentUser() user: AuthenticatedUser,
  @Body() body: RunPublicVideoIngestionDto,
) {
  return this.ingestionService.ingestFromManifest({
    manifestPath: body.manifestPath,
    limit: body.limit,
    maxPublishCount: body.maxPublishCount,
    ownerUserId: user.id,
  });
}

@Get('ingestion/runs')
async listIngestionRuns() {
  return this.ingestionService.listRuns();
}
```

- [ ] **Step 4: Extend the template-library UI to show machine metadata and launch status**

```tsx
<Meta icon="hardware-chip-outline" label={item.machineGenerated ? '机器生成' : '人工模板'} />
{item.priorityClass ? <Meta icon="flag-outline" label={item.priorityClass} /> : null}
{item.sourcePlatform ? <Meta icon="globe-outline" label={item.sourcePlatform} /> : null}
{item.evidenceAvailable ? <Meta icon="images-outline" label="含证据帧" /> : null}
```

- [ ] **Step 5: Run backend and frontend validation**

Run: `cd backend && npm test -- --runInBand src/makeup-templates/template-library/template-library.controller.spec.ts`
Expected: PASS with ingestion endpoints covered.

Run: `cd frontend && npx tsc --noEmit`
Expected: PASS with updated template-library types and screens.

- [ ] **Step 6: Commit**

```bash
git add backend/src/makeup-templates/template-library/dto/run-public-video-ingestion.dto.ts \
  backend/src/makeup-templates/template-library/template-library.controller.ts \
  backend/src/makeup-templates/template-library/template-library.controller.spec.ts \
  frontend/types/template-library.ts \
  frontend/services/templateLibraryService.ts \
  frontend/app/template-library/index.tsx \
  frontend/app/template-library/detail.tsx
git commit -m "feat: expose public video template ingestion operations"
```

### Task 4: Add source manifests, runtime script, and launch verification

**Files:**
- Create: `backend/data/public-video-template-library/public-video-seeds.json`
- Create: `scripts/run-public-video-template-library.sh`
- Create: `docs/public-video-template-library-runbook.md`
- Modify: `README.md`
- Test: `backend/src/makeup-templates/template-library/public-video-ingestion/public-video-manifest.service.spec.ts`

- [ ] **Step 1: Write the failing manifest validation test**

```ts
it('loads at least 30 public source items from the default manifest', async () => {
  const items = await service.loadDefaultManifest();
  expect(items.length).toBeGreaterThanOrEqual(30);
  expect(items.every((item) => item.url.startsWith('http'))).toBe(true);
});
```

- [ ] **Step 2: Run the manifest test to verify it fails**

Run: `cd backend && npm test -- --runInBand src/makeup-templates/template-library/public-video-ingestion/public-video-manifest.service.spec.ts`
Expected: FAIL because no default manifest exists yet.

- [ ] **Step 3: Add the default manifest and runtime shell entrypoint**

```json
[
  {
    "platform": "youtube",
    "url": "https://www.youtube.com/watch?v=...",
    "title": "Clear daily makeup tutorial",
    "author": "Creator Name",
    "styleHints": ["CLEAR", "NATURAL"],
    "priorityHint": "P1"
  }
]
```

```bash
#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../backend"
npx prisma migrate deploy
npm run prisma:generate
node dist/scripts/run-public-video-template-library.js
```

- [ ] **Step 4: Run a real ingestion smoke to hit the AutoReady30 contract**

Run: `cd backend && npm run build`
Expected: PASS.

Run: `cd backend && npm run db:migrate && npm run prisma:generate`
Expected: PASS.

Run: `bash scripts/run-public-video-template-library.sh`
Expected: a completed publish run with `autoReadyCount >= 30`, `publishedVisibleCount >= 30` or visible+hidden totals meeting the threshold with P3 hidden.

- [ ] **Step 5: Verify product compatibility**

Run: `curl -fsS http://127.0.0.1:13000/health`
Expected: `{"status":"ok"}` or equivalent healthy response.

Run: `curl -fsS -H "Authorization: Bearer $DEMO_TOKEN" http://127.0.0.1:13000/makeup-template-library/templates | jq '.items | length'`
Expected: template count includes the machine-published sources.

Run: `curl -fsS -H "Authorization: Bearer $DEMO_TOKEN" http://127.0.0.1:13000/makeup-template-library/templates | jq '[.items[] | select(.machineGenerated == true)] | length'`
Expected: `30` or more.

- [ ] **Step 6: Commit**

```bash
git add backend/data/public-video-template-library/public-video-seeds.json \
  scripts/run-public-video-template-library.sh \
  docs/public-video-template-library-runbook.md \
  README.md \
  backend/src/makeup-templates/template-library/public-video-ingestion/public-video-manifest.service.spec.ts
git commit -m "feat: bootstrap public video template library launch dataset"
```

## Self-Review

- Spec coverage:
  - Source retention, extraction artifacts, draft pool, formal publish, and AutoReady30 are covered by Tasks 1, 2, and 4.
  - API/UI operator visibility is covered by Task 3.
  - P1/P2 visible and P3 hidden behavior is covered by Task 2 and Task 3.
- Placeholder scan:
  - No TODO/TBD placeholders remain; each task names exact files and verification commands.
- Type consistency:
  - `machineGenerated`, `priorityClass`, `sourcePlatform`, `sourceUrl`, `autoQualityScore`, and `evidenceAvailable` are the metadata names used consistently across Prisma payload, controller mapping, frontend types, and UI.
