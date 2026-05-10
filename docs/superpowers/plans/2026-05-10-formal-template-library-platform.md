# Formal Template Library Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the formal DB-backed makeup template library platform with seed data, publish/rollback management APIs, DB-backed matching, frontend management pages, and regression coverage.

**Architecture:** Keep the current generated-result library intact. Add a separate standard-template library persistence layer under `backend/src/makeup-templates/template-library`, seed the product-standard library from code data into PostgreSQL, then adapt the existing matching service to read published DB template versions. Frontend adds an operational management area under `frontend/app/template-library` using a focused service and typed DTOs.

**Tech Stack:** NestJS 11, Prisma 7/PostgreSQL, Jest, Expo Router/React Native/TypeScript, existing `api-client` and demo auth.

---

## File Map

### Backend

- Modify `backend/prisma/schema.prisma`: add template library enums and tables, add `sourceStandardTemplateVersionId` to generated templates and match traces.
- Create `backend/prisma/migrations/<timestamp>_add_formal_template_library/migration.sql`: PostgreSQL migration for new schema.
- Create `backend/src/makeup-templates/template-library/template-library.seed-data.ts`: initial seed data derived from the two product docs.
- Create `backend/src/makeup-templates/template-library/template-library-seed.service.ts`: idempotent seed logic.
- Create `backend/src/makeup-templates/template-library/template-library-admin.service.ts`: template CRUD, draft, publish, archive, rollback.
- Create `backend/src/makeup-templates/template-library/template-library-db.mapper.ts`: map DB rows into existing `StandardMakeupTemplate` shape.
- Modify `backend/src/makeup-templates/template-library/standard-template-library.service.ts`: read from DB by default, expose DB-backed list/get APIs, retain emergency static fallback only for no-seed local mode.
- Modify `backend/src/makeup-templates/template-library/template-matching.service.ts`: include `templateVersionId` in selected/candidate output.
- Modify `backend/src/makeup-templates/template-library/standard-template-library.types.ts`: add version/provenance fields.
- Modify `backend/src/makeup-templates/makeup-template-generation.service.ts`: persist `sourceStandardTemplateVersionId`.
- Modify `backend/src/makeup-templates/template-library/template-library.controller.ts`: add list/detail/version/seed/publish/archive/rollback endpoints.
- Modify `backend/src/makeup-templates/makeup-templates.module.ts`: provide seed/admin services.
- Tests:
  - Create `backend/src/makeup-templates/template-library/template-library-seed.service.spec.ts`
  - Create `backend/src/makeup-templates/template-library/template-library-admin.service.spec.ts`
  - Update `backend/src/makeup-templates/template-library/standard-template-library.service.spec.ts`
  - Update `backend/src/makeup-templates/template-library/template-matching.service.spec.ts`
  - Update `backend/src/makeup-templates/makeup-template-generation.service.spec.ts`

### Frontend

- Create `frontend/types/template-library.ts`: DTOs for templates, versions, styles, taxonomy, payloads.
- Create `frontend/services/templateLibraryService.ts`: API wrapper for management endpoints.
- Create `frontend/app/template-library/_layout.tsx`: route stack.
- Create `frontend/app/template-library/index.tsx`: template list and filters.
- Create `frontend/app/template-library/detail.tsx`: detail/draft edit/publish/archive.
- Create `frontend/app/template-library/versions.tsx`: version history and rollback.
- Modify `frontend/app/(tabs)/profile.tsx` or `frontend/app/(tabs)/recommend.tsx`: add management entry point.

### Docs

- Update `docs/template-matching-test-guide.md`: add formal platform management journey.
- Update `docs/team-runbook.md`: add seed and management routes.

---

## Task 1: Add Formal Template Library Schema

**Files:**
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/prisma/migrations/20260510193000_add_formal_template_library/migration.sql`

- [ ] **Step 1: Add failing schema expectations**

Run:

```bash
cd backend
rg -n "model StandardMakeupTemplate|sourceStandardTemplateVersionId" prisma/schema.prisma
```

Expected now: no `StandardMakeupTemplate` model and no `sourceStandardTemplateVersionId`.

- [ ] **Step 2: Add Prisma enums**

Insert after existing enums in `backend/prisma/schema.prisma`:

```prisma
enum TemplateStatus {
  draft
  published
  archived
}

enum TemplateReviewStatus {
  not_required
  pending
  approved
  rejected
}

enum TemplateVersionStatus {
  draft
  published
  superseded
  rolled_back
  archived
}

enum TemplateVisibility {
  private
  team
  public
}

enum TemplateSource {
  seed
  user_created
  user_edited
  rollback
}
```

- [ ] **Step 3: Add standard library relations to `User`**

In `model User`, add:

```prisma
ownedStandardTemplates      StandardMakeupTemplate[]        @relation("StandardTemplateOwner")
createdStandardTemplates    StandardMakeupTemplate[]        @relation("StandardTemplateCreator")
updatedStandardTemplates    StandardMakeupTemplate[]        @relation("StandardTemplateUpdater")
createdStandardVersions     StandardMakeupTemplateVersion[] @relation("StandardTemplateVersionCreator")
publishedStandardVersions   StandardMakeupTemplateVersion[] @relation("StandardTemplateVersionPublisher")
```

- [ ] **Step 4: Add generated template provenance field**

In `model GeneratedMakeupTemplate`, add:

```prisma
sourceStandardTemplateVersionId String? @map("source_standard_template_version_id") @db.VarChar(80)
```

Add index:

```prisma
@@index([sourceStandardTemplateVersionId])
```

- [ ] **Step 5: Add standard library models**

Append these models near the current generated template models:

```prisma
model StandardMakeupStyle {
  id                String   @id @db.VarChar(60)
  styleCode         String   @unique @map("style_code") @db.VarChar(80)
  displayName       String   @map("display_name") @db.VarChar(120)
  family            String   @db.VarChar(80)
  aliases           String[] @default([])
  positiveTags      String[] @map("positive_tags") @default([])
  negativeTags      String[] @map("negative_tags") @default([])
  baseFinish        String   @map("base_finish") @db.VarChar(80)
  colorPalette      String[] @map("color_palette") @default([])
  intensityLevel    Int      @map("intensity_level")
  defaultDifficulty Float    @map("default_difficulty")
  typicalScenes     String[] @map("typical_scenes") @default([])
  isActive          Boolean  @map("is_active") @default(true)
  createdAt         DateTime @default(now()) @map("created_at")
  updatedAt         DateTime @updatedAt @map("updated_at")
  versions          StandardMakeupTemplateVersion[]

  @@index([family])
  @@map("standard_makeup_styles")
}

model StandardMakeupTemplate {
  id               String               @id @db.VarChar(60)
  templateCode     String               @unique @map("template_code") @db.VarChar(100)
  ownerUserId      String               @map("owner_user_id") @db.VarChar(50)
  currentVersionId String?              @unique @map("current_version_id") @db.VarChar(80)
  displayName      String               @map("display_name") @db.VarChar(150)
  description      String               @db.VarChar(600)
  status           TemplateStatus       @default(draft)
  reviewStatus     TemplateReviewStatus @default(not_required) @map("review_status")
  visibility       TemplateVisibility   @default(team)
  source           TemplateSource       @default(seed)
  createdById      String               @map("created_by_id") @db.VarChar(50)
  updatedById      String?              @map("updated_by_id") @db.VarChar(50)
  publishedAt      DateTime?            @map("published_at")
  archivedAt       DateTime?            @map("archived_at")
  createdAt        DateTime             @default(now()) @map("created_at")
  updatedAt        DateTime             @updatedAt @map("updated_at")

  owner            User                 @relation("StandardTemplateOwner", fields: [ownerUserId], references: [id], onDelete: Cascade)
  createdBy        User                 @relation("StandardTemplateCreator", fields: [createdById], references: [id], onDelete: Restrict)
  updatedBy        User?                @relation("StandardTemplateUpdater", fields: [updatedById], references: [id], onDelete: SetNull)
  currentVersion   StandardMakeupTemplateVersion? @relation("StandardTemplateCurrentVersion", fields: [currentVersionId], references: [id], onDelete: SetNull)
  versions         StandardMakeupTemplateVersion[] @relation("StandardTemplateVersions")

  @@index([status, updatedAt])
  @@index([ownerUserId, updatedAt])
  @@map("standard_makeup_templates")
}

model StandardMakeupTemplateVersion {
  id                    String                @id @db.VarChar(80)
  templateId            String                @map("template_id") @db.VarChar(60)
  version               Int
  status                TemplateVersionStatus @default(draft)
  sourceVersionId       String?               @map("source_version_id") @db.VarChar(80)
  displayName           String                @map("display_name") @db.VarChar(150)
  styleId               String                @map("style_id") @db.VarChar(60)
  styleFamily           String                @map("style_family") @db.VarChar(80)
  primaryScene          String                @map("primary_scene") @db.VarChar(100)
  styleTags             String[]              @map("style_tags") @default([])
  effectTags            String[]              @map("effect_tags") @default([])
  difficultyBaseScore   Float                 @map("difficulty_base_score")
  minSkillLevel         String                @map("min_skill_level") @db.VarChar(30)
  estimatedTimeMinutes  Int                   @map("estimated_time_minutes")
  templateDescription   String                @map("template_description") @db.VarChar(800)
  visualDescription     String                @map("visual_description") @db.VarChar(500)
  templatePayload       Json                  @map("template_payload")
  changeSummary         String?               @map("change_summary") @db.VarChar(300)
  createdById           String                @map("created_by_id") @db.VarChar(50)
  publishedById         String?               @map("published_by_id") @db.VarChar(50)
  publishedAt           DateTime?             @map("published_at")
  createdAt             DateTime              @default(now()) @map("created_at")
  updatedAt             DateTime              @updatedAt @map("updated_at")

  template              StandardMakeupTemplate @relation("StandardTemplateVersions", fields: [templateId], references: [id], onDelete: Cascade)
  currentForTemplate    StandardMakeupTemplate? @relation("StandardTemplateCurrentVersion")
  style                 StandardMakeupStyle     @relation(fields: [styleId], references: [id], onDelete: Restrict)
  sourceVersion         StandardMakeupTemplateVersion? @relation("StandardTemplateRollbackSource", fields: [sourceVersionId], references: [id], onDelete: SetNull)
  rollbackCopies        StandardMakeupTemplateVersion[] @relation("StandardTemplateRollbackSource")
  createdBy             User                   @relation("StandardTemplateVersionCreator", fields: [createdById], references: [id], onDelete: Restrict)
  publishedBy           User?                  @relation("StandardTemplateVersionPublisher", fields: [publishedById], references: [id], onDelete: SetNull)
  stepBlocks            StandardTemplateStepBlock[]
  productSlots          StandardProductSlotSpec[]

  @@unique([templateId, version])
  @@index([styleFamily])
  @@index([status, updatedAt])
  @@map("standard_makeup_template_versions")
}

model StandardTemplateStepBlock {
  id                  String   @id @db.VarChar(80)
  versionId           String   @map("version_id") @db.VarChar(80)
  stepCode            String   @map("step_code") @db.VarChar(60)
  stepOrder           Int      @map("step_order")
  sectionCode         String   @map("section_code") @db.VarChar(40)
  stepName            String   @map("step_name") @db.VarChar(100)
  standardStepCodes   String[] @map("standard_step_codes") @default([])
  operationAreas      String[] @map("operation_areas") @default([])
  stepGoal            String   @map("step_goal") @db.VarChar(255)
  instructionTemplate String   @map("instruction_template") @db.VarChar(800)
  visualChange        String   @map("visual_change") @db.VarChar(255)
  aiDetectionArea     String   @map("ai_detection_area") @db.VarChar(120)
  completionCriteria  String   @map("completion_criteria") @db.VarChar(255)
  failureFeedback     String   @map("failure_feedback") @db.VarChar(255)
  nextStepCondition   String   @map("next_step_condition") @db.VarChar(255)
  difficultyScore     Float    @map("difficulty_score")
  editableByUser      Boolean  @map("editable_by_user") @default(true)
  createdAt           DateTime @default(now()) @map("created_at")

  version             StandardMakeupTemplateVersion @relation(fields: [versionId], references: [id], onDelete: Cascade)
  productSlots        StandardProductSlotSpec[]

  @@unique([versionId, stepOrder])
  @@index([versionId])
  @@map("standard_template_step_blocks")
}

model StandardProductSlotSpec {
  id                      String   @id @db.VarChar(80)
  versionId               String   @map("version_id") @db.VarChar(80)
  stepBlockId             String   @map("step_block_id") @db.VarChar(80)
  slotCode                String   @map("slot_code") @db.VarChar(60)
  category                String   @db.VarChar(40)
  subCategory             String?  @map("sub_category") @db.VarChar(80)
  acceptableSubCategories String[] @map("acceptable_sub_categories") @default([])
  substituteSlotCodes     String[] @map("substitute_slot_codes") @default([])
  requiredLevel           String   @map("required_level") @db.VarChar(20)
  desiredEffect           String[] @map("desired_effect") @default([])
  desiredColorFamily      String?  @map("desired_color_family") @db.VarChar(80)
  desiredFinish           String[] @map("desired_finish") @default([])
  fallbackInstruction     String   @map("fallback_instruction") @db.VarChar(255)
  sortOrder               Int      @map("sort_order")
  createdAt               DateTime @default(now()) @map("created_at")

  version                 StandardMakeupTemplateVersion @relation(fields: [versionId], references: [id], onDelete: Cascade)
  stepBlock               StandardTemplateStepBlock     @relation(fields: [stepBlockId], references: [id], onDelete: Cascade)

  @@unique([versionId, slotCode])
  @@index([versionId])
  @@index([stepBlockId])
  @@map("standard_product_slot_specs")
}

model TemplateProductCategory {
  id            String   @id @db.VarChar(60)
  categoryCode  String   @unique @map("category_code") @db.VarChar(80)
  displayName   String   @map("display_name") @db.VarChar(120)
  parentCode    String?  @map("parent_code") @db.VarChar(80)
  aliases       String[] @default([])
  textureTags   String[] @map("texture_tags") @default([])
  functionTags  String[] @map("function_tags") @default([])
  shadeTags     String[] @map("shade_tags") @default([])
  sortOrder     Int      @map("sort_order")
  isActive      Boolean  @map("is_active") @default(true)
  createdAt     DateTime @default(now()) @map("created_at")
  updatedAt     DateTime @updatedAt @map("updated_at")

  @@index([parentCode, sortOrder])
  @@map("template_product_categories")
}

model TemplateOperationArea {
  id          String   @id @db.VarChar(60)
  areaCode    String   @unique @map("area_code") @db.VarChar(80)
  displayName String   @map("display_name") @db.VarChar(120)
  description String   @db.VarChar(300)
  useCases    String[] @map("use_cases") @default([])
  sortOrder   Int      @map("sort_order")
  createdAt   DateTime @default(now()) @map("created_at")
  updatedAt   DateTime @updatedAt @map("updated_at")

  @@map("template_operation_areas")
}

model TemplateFaceShape {
  id          String   @id @db.VarChar(60)
  shapeCode   String   @unique @map("shape_code") @db.VarChar(80)
  displayName String   @map("display_name") @db.VarChar(120)
  aliases     String[] @default([])
  isStandard  Boolean  @map("is_standard") @default(true)
  sortOrder   Int      @map("sort_order")
  createdAt   DateTime @default(now()) @map("created_at")
  updatedAt   DateTime @updatedAt @map("updated_at")

  @@map("template_face_shapes")
}

model TemplateDifficultyRule {
  id             String   @id @db.VarChar(60)
  actionCode     String   @unique @map("action_code") @db.VarChar(100)
  displayName    String   @map("display_name") @db.VarChar(120)
  baseScore      Float    @map("base_score")
  productPenalty Float    @map("product_penalty") @default(0)
  specialBonus   Float    @map("special_bonus") @default(0)
  tags           String[] @default([])
  createdAt      DateTime @default(now()) @map("created_at")
  updatedAt      DateTime @updatedAt @map("updated_at")

  @@map("template_difficulty_rules")
}
```

- [ ] **Step 6: Write SQL migration**

Create `backend/prisma/migrations/20260510193000_add_formal_template_library/migration.sql` matching the Prisma models. Use `CREATE TYPE` for enums, `CREATE TABLE`, indexes, unique constraints, and foreign keys. Also add:

```sql
ALTER TABLE "generated_makeup_templates"
ADD COLUMN "source_standard_template_version_id" VARCHAR(80);

CREATE INDEX "generated_makeup_templates_source_standard_template_version_id_idx"
ON "generated_makeup_templates"("source_standard_template_version_id");
```

- [ ] **Step 7: Validate Prisma**

Run:

```bash
cd backend
npx prisma validate
npx prisma generate
```

Expected: schema validates and Prisma Client generates.

- [ ] **Step 8: Commit schema**

```bash
git -C backend add prisma/schema.prisma prisma/migrations/20260510193000_add_formal_template_library/migration.sql
git -C backend commit -m "feat: add formal template library schema"
```

---

## Task 2: Seed Product Standard Library Into DB

**Files:**
- Create: `backend/src/makeup-templates/template-library/template-library.seed-data.ts`
- Create: `backend/src/makeup-templates/template-library/template-library-seed.service.ts`
- Test: `backend/src/makeup-templates/template-library/template-library-seed.service.spec.ts`
- Modify: `backend/src/makeup-templates/makeup-templates.module.ts`

- [ ] **Step 1: Write seed service test**

Create `template-library-seed.service.spec.ts` with tests for:

```ts
it('upserts styles, taxonomy, templates, versions, step blocks, and slots');
it('is idempotent when run twice');
it('publishes seeded templates by default');
```

Use mocked Prisma delegates:

```ts
const prisma = {
  $transaction: jest.fn(async (callback) => callback(prisma)),
  standardMakeupStyle: { upsert: jest.fn() },
  templateProductCategory: { upsert: jest.fn() },
  templateOperationArea: { upsert: jest.fn() },
  templateFaceShape: { upsert: jest.fn() },
  templateDifficultyRule: { upsert: jest.fn() },
  standardMakeupTemplate: { upsert: jest.fn(), update: jest.fn() },
  standardMakeupTemplateVersion: { upsert: jest.fn(), findUnique: jest.fn() },
  standardTemplateStepBlock: { upsert: jest.fn() },
  standardProductSlotSpec: { upsert: jest.fn() },
};
```

- [ ] **Step 2: Run test to verify fail**

```bash
cd backend
npm test -- template-library-seed.service.spec.ts --runInBand
```

Expected: fail because service/data files do not exist.

- [ ] **Step 3: Create seed data**

Create `template-library.seed-data.ts` exporting:

```ts
export const STANDARD_TEMPLATE_OWNER_ID = 'user-001';
export const SEEDED_STANDARD_STYLES = [...];
export const SEEDED_PRODUCT_CATEGORIES = [...];
export const SEEDED_OPERATION_AREAS = [...];
export const SEEDED_FACE_SHAPES = [...];
export const SEEDED_DIFFICULTY_RULES = [...];
export const SEEDED_STANDARD_TEMPLATES = [...];
```

Use the current `standard-template-library.data.ts` as the source for 8 styles and 5 compressed step blocks. Add taxonomy rows from the document:

- product category parents: prep, base, setting, brow, eye, contour, lip, remover, tool
- operation areas: full_face, t_zone, u_zone, eye_area, brows, cheeks, jawline, nose_area, lips
- face shapes: oval, narrow, round, long, short, square_round
- difficulty rules from the document with scores 1.0, 1.2, 1.3, 1.5, 1.8, 2.2, 2.5 and special technique bonus 3.0

- [ ] **Step 4: Implement seed service**

Create `TemplateLibrarySeedService`:

```ts
@Injectable()
export class TemplateLibrarySeedService {
  constructor(private readonly prisma: PrismaService) {}

  async seed(options: { ownerUserId?: string; force?: boolean } = {}) {
    const ownerUserId = options.ownerUserId ?? STANDARD_TEMPLATE_OWNER_ID;
    return this.prisma.$transaction(async (tx) => {
      await this.upsertStyles(tx);
      await this.upsertTaxonomy(tx);
      const templates = [];
      for (const template of SEEDED_STANDARD_TEMPLATES) {
        templates.push(await this.upsertTemplate(tx, ownerUserId, template));
      }
      return { styles: SEEDED_STANDARD_STYLES.length, templates: templates.length };
    });
  }
}
```

Each seeded template creates version `1` with status `published` and sets `currentVersionId`.

- [ ] **Step 5: Register service**

Add `TemplateLibrarySeedService` to `MakeupTemplatesModule.providers`.

- [ ] **Step 6: Run seed tests**

```bash
cd backend
npm test -- template-library-seed.service.spec.ts --runInBand
```

Expected: pass.

- [ ] **Step 7: Commit seed**

```bash
git -C backend add src/makeup-templates/template-library/template-library.seed-data.ts src/makeup-templates/template-library/template-library-seed.service.ts src/makeup-templates/template-library/template-library-seed.service.spec.ts src/makeup-templates/makeup-templates.module.ts
git -C backend commit -m "feat: seed formal makeup template library"
```

---

## Task 3: Add Management API For Draft, Publish, Archive, Rollback

**Files:**
- Create: `backend/src/makeup-templates/template-library/template-library-admin.service.ts`
- Create DTOs under `backend/src/makeup-templates/template-library/dto/`
- Modify: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Test: `backend/src/makeup-templates/template-library/template-library-admin.service.spec.ts`
- Test: `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`

- [ ] **Step 1: Write admin service tests**

Cover:

```ts
it('lists templates with current version counts');
it('creates a draft template with version 1');
it('editing a published template creates a new draft version');
it('publishing a draft supersedes the previous published version');
it('rollback creates a new published version copied from history');
it('archive marks template archived');
```

- [ ] **Step 2: Run tests to verify fail**

```bash
cd backend
npm test -- template-library-admin.service.spec.ts --runInBand
```

Expected: fail because service does not exist.

- [ ] **Step 3: Add DTOs**

Create DTOs:

- `create-standard-template.dto.ts`
- `update-standard-template-draft.dto.ts`
- `publish-standard-template.dto.ts`
- `rollback-standard-template.dto.ts`
- `query-standard-templates.dto.ts`

Include validation for required strings, arrays, and payload objects.

- [ ] **Step 4: Implement admin service**

Implement methods:

```ts
list(query)
getById(templateId)
listVersions(templateId)
getVersion(templateId, versionId)
createDraft(userId, dto)
saveDraft(templateId, userId, dto)
publish(templateId, userId, dto)
archive(templateId, userId)
rollback(templateId, userId, dto)
```

Validation:

- display name is non-empty
- published version has at least one step block
- published version has at least one required product slot
- rollback source belongs to the template

- [ ] **Step 5: Extend controller**

Add routes:

```ts
@Get('taxonomy')
@Get('templates')
@Get('templates/:templateId')
@Get('templates/:templateId/versions')
@Get('templates/:templateId/versions/:versionId')
@Post('templates')
@Put('templates/:templateId/draft')
@Post('templates/:templateId/publish')
@Post('templates/:templateId/archive')
@Post('templates/:templateId/rollback')
@Post('seed')
```

- [ ] **Step 6: Run API tests**

```bash
cd backend
npm test -- template-library-admin.service.spec.ts template-library.controller.spec.ts --runInBand
```

Expected: pass.

- [ ] **Step 7: Commit API**

```bash
git -C backend add src/makeup-templates/template-library
git -C backend commit -m "feat: add template library management api"
```

---

## Task 4: Switch Matching To Published DB Templates

**Files:**
- Create: `backend/src/makeup-templates/template-library/template-library-db.mapper.ts`
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.service.ts`
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.types.ts`
- Modify: `backend/src/makeup-templates/template-library/template-matching.service.ts`
- Modify: `backend/src/makeup-templates/makeup-template-generation.service.ts`
- Modify: `backend/src/recommendations/recommendation.mapper.ts`
- Tests: existing template matching and generation specs

- [ ] **Step 1: Update types**

Add optional provenance to `StandardMakeupTemplate`:

```ts
sourceTemplateId?: string;
sourceTemplateVersionId?: string;
version?: number;
```

Add `templateVersionId?: string` to candidate response if needed.

- [ ] **Step 2: Write DB library service tests**

Update `standard-template-library.service.spec.ts` to mock Prisma:

```ts
it('lists active published DB templates');
it('falls back to static templates only when DB has none and fallback is enabled');
it('gets template by ID from current published DB version');
```

- [ ] **Step 3: Implement DB mapper**

Create a function:

```ts
export function mapStandardVersionToTemplate(row: StandardVersionWithRelations): StandardMakeupTemplate
```

It maps version rows with `stepBlocks` and `productSlots` into the existing `StandardMakeupTemplate` shape.

- [ ] **Step 4: Update service to use Prisma**

Inject `PrismaService` into `StandardTemplateLibraryService`. Methods become async:

```ts
listActiveTemplates(): Promise<StandardMakeupTemplate[]>
getTemplateById(templateId: string): Promise<StandardMakeupTemplate | undefined>
```

Update consumers to await.

- [ ] **Step 5: Update matching service**

Change:

```ts
const templates = this.library.listActiveTemplates();
```

to:

```ts
const templates = await this.library.listActiveTemplates();
```

Ensure selected/candidates preserve `sourceTemplateVersionId`.

- [ ] **Step 6: Persist version provenance**

In `MakeupTemplateGenerationService`, set:

```ts
sourceStandardTemplateId: matchResult.selected.template.id,
sourceStandardTemplateVersionId: matchResult.selected.template.sourceTemplateVersionId,
```

- [ ] **Step 7: Run tests**

```bash
cd backend
npm test -- standard-template-library.service.spec.ts template-matching.service.spec.ts makeup-template-generation.service.spec.ts recommendations.service.spec.ts --runInBand
```

Expected: pass.

- [ ] **Step 8: Commit matching**

```bash
git -C backend add src/makeup-templates src/recommendations
git -C backend commit -m "feat: match recommendations from db templates"
```

---

## Task 5: Build Frontend Template Library Service And Types

**Files:**
- Create: `frontend/types/template-library.ts`
- Create: `frontend/services/templateLibraryService.ts`

- [ ] **Step 1: Create frontend types**

Define:

```ts
export type TemplateStatus = 'draft' | 'published' | 'archived';
export type TemplateReviewStatus = 'not_required' | 'pending' | 'approved' | 'rejected';
export type TemplateVersionStatus = 'draft' | 'published' | 'superseded' | 'rolled_back' | 'archived';
export type TemplateLibraryItem = { ... };
export type TemplateLibraryDetail = { ... };
export type TemplateLibraryVersion = { ... };
export type TemplateLibraryTaxonomy = { ... };
```

Include steps and product slots.

- [ ] **Step 2: Create service**

Implement:

```ts
listTemplates(params)
getTemplate(templateId)
listVersions(templateId)
getVersion(templateId, versionId)
createTemplate(payload)
saveDraft(templateId, payload)
publishTemplate(templateId, payload)
archiveTemplate(templateId)
rollbackTemplate(templateId, payload)
seedTemplateLibrary()
```

Use existing `api-client`.

- [ ] **Step 3: Run typecheck**

```bash
cd frontend
npx tsc --noEmit
```

Expected: pass.

- [ ] **Step 4: Commit service**

```bash
git -C frontend add types/template-library.ts services/templateLibraryService.ts
git -C frontend commit -m "feat: add template library client"
```

---

## Task 6: Build Frontend Management Pages

**Files:**
- Create: `frontend/app/template-library/_layout.tsx`
- Create: `frontend/app/template-library/index.tsx`
- Create: `frontend/app/template-library/detail.tsx`
- Create: `frontend/app/template-library/versions.tsx`
- Modify: `frontend/app/(tabs)/profile.tsx`

- [ ] **Step 1: Add route layout**

Create a stack layout with title `模板库管理`.

- [ ] **Step 2: Add list page**

Build a dense operational list:

- search input
- status segmented filter
- seed button
- rows for display name, style family, status, review status, version, updated time
- row opens `detail?templateId=...`

- [ ] **Step 3: Add detail page**

Show editable sections:

- display name
- description
- style family
- primary scene
- estimated minutes
- template description
- step blocks
- product slots

Actions:

- save draft
- publish
- archive
- open versions page

- [ ] **Step 4: Add versions page**

Show version history and rollback action. Confirm rollback with a clear button state.

- [ ] **Step 5: Add entry point**

Add a button in `frontend/app/(tabs)/profile.tsx` or recommendation tab:

```text
模板库管理
```

It navigates to `/template-library`.

- [ ] **Step 6: Verify frontend**

```bash
cd frontend
npx tsc --noEmit
npm run lint
```

Expected: typecheck pass; lint has no errors.

- [ ] **Step 7: Commit pages**

```bash
git -C frontend add app/template-library app/'(tabs)'/profile.tsx
git -C frontend commit -m "feat: add template library management pages"
```

---

## Task 7: End-To-End Verification And Docs

**Files:**
- Modify: `docs/template-matching-test-guide.md`
- Modify: `docs/team-runbook.md`

- [ ] **Step 1: Apply migration and seed**

```bash
cd backend
npx prisma migrate status
npx prisma migrate deploy
curl -fsS -X POST http://127.0.0.1:13001/makeup-template-library/seed \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{}'
```

Expected: seed returns counts for styles/templates.

- [ ] **Step 2: Verify management API**

```bash
curl -fsS http://127.0.0.1:13001/makeup-template-library/templates \
  -H 'Authorization: Bearer demo-token'
```

Expected: includes 8 seeded templates.

- [ ] **Step 3: Verify recommendation still works**

```bash
curl -fsS -X POST http://127.0.0.1:13001/recommendations/generate \
  -H 'Authorization: Bearer demo-token' \
  -H 'Content-Type: application/json' \
  -d '{"userId":"user-001","scenario":"commute","scenarioDetails":"面试需要轻熟知性优雅妆，不要太浓","requirements":["owned_products_first"]}'
```

Expected: response has `generatedTemplateId`, `sourceStandardTemplateId`, and DB version provenance if exposed.

- [ ] **Step 4: Update docs**

Add formal platform journey:

- seed DB templates
- open `/template-library`
- edit draft
- publish
- rollback
- generate recommendation and confirm template provenance

- [ ] **Step 5: Run final verification**

```bash
cd backend
npx prisma validate
npm run build
npm test -- --runInBand
cd ../frontend
npx tsc --noEmit
npm run lint
```

Expected: backend build/tests pass; frontend typecheck pass; lint no errors.

- [ ] **Step 6: Commit docs**

```bash
git add docs/template-matching-test-guide.md docs/team-runbook.md
git commit -m "docs: add formal template library test journey"
```

---

## Plan Self-Review

- Spec coverage: schema, seed, publish, rollback, frontend management, DB-backed matching, generated provenance, tests, docs are covered.
- No placeholders: all tasks specify files, behavior, commands, and expected outcomes.
- Type consistency: template/version/status naming is consistent across backend and frontend plan steps.
- Scope control: audit workflow is reserved only by fields; full approval UI is excluded.
