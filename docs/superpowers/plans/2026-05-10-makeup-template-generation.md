# Makeup Template Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the personalized makeup template generation architecture from the approved PRD, including persisted generation requests, snapshots, generated templates, product slot matching, event tracking, and compatibility with the existing recommendation flow.

**Architecture:** Add a new NestJS `makeup-templates` domain with focused services for intent parsing, snapshots, slot matching, template generation, persistence, mapping, and event recording. Keep existing `/recommendations/generate` working by calling the new generation service and mapping the generated template back into the current `Recommendation` and `RecommendationStep` records. Frontend changes are limited to optional response fields so the current pages keep working.

**Tech Stack:** NestJS 11, TypeScript, Prisma 7, PostgreSQL, Jest, Expo/React Native TypeScript.

---

## File Structure

Create or modify these files:

- Create: `backend/prisma/migrations/20260510090000_add_makeup_template_generation/migration.sql`
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/src/makeup-templates/makeup-template-id.util.ts`
- Create: `backend/src/makeup-templates/makeup-template.types.ts`
- Create: `backend/src/makeup-templates/dto/generate-makeup-template.dto.ts`
- Create: `backend/src/makeup-templates/dto/record-template-event.dto.ts`
- Create: `backend/src/makeup-templates/dto/makeup-template-response.dto.ts`
- Create: `backend/src/makeup-templates/makeup-template-intent.service.ts`
- Create: `backend/src/makeup-templates/makeup-template-intent.service.spec.ts`
- Create: `backend/src/makeup-templates/makeup-template-slot-matching.service.ts`
- Create: `backend/src/makeup-templates/makeup-template-slot-matching.service.spec.ts`
- Create: `backend/src/makeup-templates/makeup-template-snapshot.service.ts`
- Create: `backend/src/makeup-templates/makeup-template.mapper.ts`
- Create: `backend/src/makeup-templates/makeup-template-generation.service.ts`
- Create: `backend/src/makeup-templates/makeup-template-generation.service.spec.ts`
- Create: `backend/src/makeup-templates/makeup-template-event.service.ts`
- Create: `backend/src/makeup-templates/makeup-template-event.service.spec.ts`
- Create: `backend/src/makeup-templates/makeup-templates.controller.ts`
- Create: `backend/src/makeup-templates/makeup-templates.module.ts`
- Modify: `backend/src/app.module.ts`
- Modify: `backend/src/recommendations/recommendations.module.ts`
- Modify: `backend/src/recommendations/recommendations.service.ts`
- Modify: `backend/src/recommendations/dto/recommendation-response.dto.ts`
- Modify: `backend/src/recommendations/dto/recommendation-step-response.dto.ts`
- Modify: `backend/src/recommendations/recommendation.mapper.ts`
- Create: `backend/src/recommendations/recommendations.service.spec.ts`
- Modify: `backend/src/executions/executions.service.ts`
- Modify: `backend/src/executions/executions.module.ts`
- Create: `backend/src/executions/executions-template-events.spec.ts`
- Modify: `frontend/types/recommendation.ts`
- Modify: `frontend/services/recommendationService.ts`

Implementation boundaries:

- `makeup-template-intent.service.ts` only parses user intent and builds deterministic tags.
- `makeup-template-snapshot.service.ts` only reads user/product state and creates snapshot payloads.
- `makeup-template-slot-matching.service.ts` only scores product candidates for generated product slots.
- `makeup-template-generation.service.ts` coordinates persistence and generation; it does not know about frontend fallback logic.
- `recommendations.service.ts` remains the compatibility layer for existing frontend routes.
- `executions.service.ts` records template events only when a recommendation is linked to a generated template.

---

### Task 1: Add Prisma Models and Migration

**Files:**
- Modify: `backend/prisma/schema.prisma`
- Create: `backend/prisma/migrations/20260510090000_add_makeup_template_generation/migration.sql`

- [ ] **Step 1: Add Prisma relations and models**

In `backend/prisma/schema.prisma`, add these relation fields to `model User`:

```prisma
  makeupGenerationRequests MakeupGenerationRequest[]
  userConditionSnapshots   UserConditionSnapshot[]
  userProductSnapshots     UserProductSnapshot[]
  generatedMakeupTemplates GeneratedMakeupTemplate[]
  templateEvents           TemplateEvent[]
```

Add this relation field to `model Product`:

```prisma
  matchedTemplateSlots TemplateProductSlot[]
```

Add this relation field to `model UserProduct`:

```prisma
  matchedTemplateSlots TemplateProductSlot[]
```

In `model Recommendation`, add:

```prisma
  generatedTemplateId String? @map("generated_template_id") @db.VarChar(50)
  generatedTemplate   GeneratedMakeupTemplate? @relation(fields: [generatedTemplateId], references: [id], onDelete: SetNull)
```

Then add this index inside `model Recommendation`:

```prisma
  @@index([generatedTemplateId])
```

Append these models to the schema:

```prisma
model MakeupGenerationRequest {
  id                String   @id @db.VarChar(50)
  userId            String   @map("user_id") @db.VarChar(50)
  rawUserInput      String   @map("raw_user_input") @db.Text
  parsedScene       String   @map("parsed_scene") @db.VarChar(100)
  parsedStyleTags   String[] @map("parsed_style_tags") @default([])
  parsedEffectTags  String[] @map("parsed_effect_tags") @default([])
  parsedConstraints String[] @map("parsed_constraints") @default([])
  referenceType     String?  @map("reference_type") @db.VarChar(40)
  referenceId       String?  @map("reference_id") @db.VarChar(100)
  generationSource  String   @map("generation_source") @db.VarChar(80)
  createdAt         DateTime @map("created_at") @default(now())
  user              User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  generatedTemplate GeneratedMakeupTemplate?
  events            TemplateEvent[]

  @@index([userId, createdAt])
  @@map("makeup_generation_requests")
}

model UserConditionSnapshot {
  id                  String   @id @db.VarChar(50)
  userId              String   @map("user_id") @db.VarChar(50)
  skinTone            String?  @map("skin_tone") @db.VarChar(50)
  skinType            String?  @map("skin_type") @db.VarChar(50)
  faceShape           String?  @map("face_shape") @db.VarChar(50)
  eyeShape            String?  @map("eye_shape") @db.VarChar(50)
  makeupSkillLevel    String   @map("makeup_skill_level") @db.VarChar(30)
  preferredStyles     String[] @map("preferred_styles") @default([])
  avoidStyles         String[] @map("avoid_styles") @default([])
  preferredFinish     String[] @map("preferred_finish") @default([])
  allergyOrAvoidNotes String[] @map("allergy_or_avoid_notes") @default([])
  createdAt           DateTime @map("created_at") @default(now())
  user                User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  generatedTemplates  GeneratedMakeupTemplate[]
  events              TemplateEvent[]

  @@index([userId, createdAt])
  @@map("user_condition_snapshots")
}

model UserProductSnapshot {
  id                           String   @id @db.VarChar(50)
  userId                       String   @map("user_id") @db.VarChar(50)
  availableProductCount        Int      @map("available_product_count")
  availableCategories          String[] @map("available_categories") @default([])
  missingCategories            String[] @map("missing_categories") @default([])
  ownedProducts                Json     @map("owned_products")
  expiredOrUnavailableProducts Json     @map("expired_or_unavailable_products")
  createdAt                    DateTime @map("created_at") @default(now())
  user                         User     @relation(fields: [userId], references: [id], onDelete: Cascade)
  generatedTemplates           GeneratedMakeupTemplate[]
  events                       TemplateEvent[]

  @@index([userId, createdAt])
  @@map("user_product_snapshots")
}

model GeneratedMakeupTemplate {
  id                       String                    @id @db.VarChar(50)
  userId                   String                    @map("user_id") @db.VarChar(50)
  requestId                String                    @unique @map("request_id") @db.VarChar(50)
  conditionSnapshotId      String                    @map("condition_snapshot_id") @db.VarChar(50)
  productSnapshotId        String                    @map("product_snapshot_id") @db.VarChar(50)
  displayName              String                    @map("display_name") @db.VarChar(150)
  templateType             String                    @map("template_type") @db.VarChar(40)
  primaryScene             String                    @map("primary_scene") @db.VarChar(100)
  stylePrimary             String                    @map("style_primary") @db.VarChar(80)
  styleTags                String[]                  @map("style_tags") @default([])
  effectTags               String[]                  @map("effect_tags") @default([])
  overallEffect            String                    @map("overall_effect") @db.VarChar(500)
  difficultyLevel          String                    @map("difficulty_level") @db.VarChar(10)
  estimatedTimeMinutes     Int                       @map("estimated_time_minutes")
  productCoverageRate      Float                     @map("product_coverage_rate")
  ownedProductUsageCount   Int                       @map("owned_product_usage_count")
  missingProductTypes      String[]                  @map("missing_product_types") @default([])
  substitutionCount        Int                       @map("substitution_count")
  personalizationReasons   String[]                  @map("personalization_reasons") @default([])
  generationConfidence     String                    @map("generation_confidence") @db.VarChar(20)
  templateReuseKey         String                    @map("template_reuse_key") @db.VarChar(160)
  createdAt                DateTime                  @map("created_at") @default(now())
  updatedAt                DateTime                  @map("updated_at") @updatedAt
  user                     User                      @relation(fields: [userId], references: [id], onDelete: Cascade)
  request                  MakeupGenerationRequest   @relation(fields: [requestId], references: [id], onDelete: Cascade)
  conditionSnapshot        UserConditionSnapshot     @relation(fields: [conditionSnapshotId], references: [id], onDelete: Restrict)
  productSnapshot          UserProductSnapshot       @relation(fields: [productSnapshotId], references: [id], onDelete: Restrict)
  steps                    GeneratedTemplateStep[]
  productSlots             TemplateProductSlot[]
  events                   TemplateEvent[]
  recommendations          Recommendation[]

  @@index([userId, createdAt])
  @@index([templateReuseKey])
  @@map("generated_makeup_templates")
}

model GeneratedTemplateStep {
  id                 String                  @id @db.VarChar(50)
  templateId         String                  @map("template_id") @db.VarChar(50)
  stepOrder          Int                     @map("step_order")
  sectionCode        String                  @map("section_code") @db.VarChar(40)
  stepName           String                  @map("step_name") @db.VarChar(100)
  stepGoal           String                  @map("step_goal") @db.VarChar(255)
  userInstruction    String                  @map("user_instruction") @db.VarChar(700)
  visualChange       String                  @map("visual_change") @db.VarChar(255)
  aiDetectionArea    String                  @map("ai_detection_area") @db.VarChar(120)
  completionCriteria String                  @map("completion_criteria") @db.VarChar(255)
  failureFeedback    String                  @map("failure_feedback") @db.VarChar(255)
  editableByUser     Boolean                 @map("editable_by_user") @default(true)
  nextStepCondition  String                  @map("next_step_condition") @db.VarChar(255)
  createdAt          DateTime                @map("created_at") @default(now())
  template           GeneratedMakeupTemplate @relation(fields: [templateId], references: [id], onDelete: Cascade)
  productSlots       TemplateProductSlot[]
  events             TemplateEvent[]

  @@index([templateId, stepOrder])
  @@map("generated_template_steps")
}

model TemplateProductSlot {
  id                    String                  @id @db.VarChar(50)
  templateId            String                  @map("template_id") @db.VarChar(50)
  stepId                String                  @map("step_id") @db.VarChar(50)
  slotCode              String                  @map("slot_code") @db.VarChar(60)
  category              String                  @db.VarChar(40)
  subCategory           String?                 @map("sub_category") @db.VarChar(80)
  requiredLevel         String                  @map("required_level") @db.VarChar(20)
  desiredEffect         String[]                @map("desired_effect") @default([])
  desiredColorFamily    String?                 @map("desired_color_family") @db.VarChar(80)
  desiredFinish         String[]                @map("desired_finish") @default([])
  matchedUserProductId  String?                 @map("matched_user_product_id") @db.VarChar(50)
  matchedProductId      String?                 @map("matched_product_id") @db.VarChar(50)
  matchStatus           String                  @map("match_status") @db.VarChar(20)
  matchReason           String                  @map("match_reason") @db.VarChar(255)
  alternativeProductIds String[]                @map("alternative_product_ids") @default([])
  fallbackInstruction   String                  @map("fallback_instruction") @db.VarChar(255)
  createdAt             DateTime                @map("created_at") @default(now())
  template              GeneratedMakeupTemplate @relation(fields: [templateId], references: [id], onDelete: Cascade)
  step                  GeneratedTemplateStep   @relation(fields: [stepId], references: [id], onDelete: Cascade)
  matchedUserProduct    UserProduct?            @relation(fields: [matchedUserProductId], references: [id], onDelete: SetNull)
  matchedProduct        Product?                @relation(fields: [matchedProductId], references: [id], onDelete: SetNull)
  events                TemplateEvent[]

  @@index([templateId])
  @@index([stepId])
  @@index([matchedUserProductId])
  @@index([matchedProductId])
  @@map("template_product_slots")
}

model TemplateEvent {
  id                  String                   @id @db.VarChar(50)
  userId              String                   @map("user_id") @db.VarChar(50)
  sessionId           String?                  @map("session_id") @db.VarChar(80)
  requestId           String?                  @map("request_id") @db.VarChar(50)
  templateId          String?                  @map("template_id") @db.VarChar(50)
  stepId              String?                  @map("step_id") @db.VarChar(50)
  slotId              String?                  @map("slot_id") @db.VarChar(50)
  productSnapshotId   String?                  @map("product_snapshot_id") @db.VarChar(50)
  conditionSnapshotId String?                  @map("condition_snapshot_id") @db.VarChar(50)
  eventName           String                   @map("event_name") @db.VarChar(80)
  payload             Json
  appVersion          String?                  @map("app_version") @db.VarChar(40)
  createdAt           DateTime                 @map("created_at") @default(now())
  user                User                     @relation(fields: [userId], references: [id], onDelete: Cascade)
  request             MakeupGenerationRequest? @relation(fields: [requestId], references: [id], onDelete: SetNull)
  template            GeneratedMakeupTemplate? @relation(fields: [templateId], references: [id], onDelete: SetNull)
  step                GeneratedTemplateStep?   @relation(fields: [stepId], references: [id], onDelete: SetNull)
  slot                TemplateProductSlot?     @relation(fields: [slotId], references: [id], onDelete: SetNull)
  productSnapshot     UserProductSnapshot?     @relation(fields: [productSnapshotId], references: [id], onDelete: SetNull)
  conditionSnapshot   UserConditionSnapshot?   @relation(fields: [conditionSnapshotId], references: [id], onDelete: SetNull)

  @@index([userId, createdAt])
  @@index([templateId, eventName])
  @@index([requestId])
  @@map("template_events")
}
```

- [ ] **Step 2: Write the migration SQL**

Create `backend/prisma/migrations/20260510090000_add_makeup_template_generation/migration.sql` with:

```sql
ALTER TABLE "recommendations"
ADD COLUMN "generated_template_id" VARCHAR(50);

CREATE TABLE "makeup_generation_requests" (
  "id" VARCHAR(50) NOT NULL,
  "user_id" VARCHAR(50) NOT NULL,
  "raw_user_input" TEXT NOT NULL,
  "parsed_scene" VARCHAR(100) NOT NULL,
  "parsed_style_tags" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "parsed_effect_tags" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "parsed_constraints" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "reference_type" VARCHAR(40),
  "reference_id" VARCHAR(100),
  "generation_source" VARCHAR(80) NOT NULL,
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "makeup_generation_requests_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "user_condition_snapshots" (
  "id" VARCHAR(50) NOT NULL,
  "user_id" VARCHAR(50) NOT NULL,
  "skin_tone" VARCHAR(50),
  "skin_type" VARCHAR(50),
  "face_shape" VARCHAR(50),
  "eye_shape" VARCHAR(50),
  "makeup_skill_level" VARCHAR(30) NOT NULL,
  "preferred_styles" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "avoid_styles" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "preferred_finish" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "allergy_or_avoid_notes" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "user_condition_snapshots_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "user_product_snapshots" (
  "id" VARCHAR(50) NOT NULL,
  "user_id" VARCHAR(50) NOT NULL,
  "available_product_count" INTEGER NOT NULL,
  "available_categories" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "missing_categories" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "owned_products" JSONB NOT NULL,
  "expired_or_unavailable_products" JSONB NOT NULL,
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "user_product_snapshots_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "generated_makeup_templates" (
  "id" VARCHAR(50) NOT NULL,
  "user_id" VARCHAR(50) NOT NULL,
  "request_id" VARCHAR(50) NOT NULL,
  "condition_snapshot_id" VARCHAR(50) NOT NULL,
  "product_snapshot_id" VARCHAR(50) NOT NULL,
  "display_name" VARCHAR(150) NOT NULL,
  "template_type" VARCHAR(40) NOT NULL,
  "primary_scene" VARCHAR(100) NOT NULL,
  "style_primary" VARCHAR(80) NOT NULL,
  "style_tags" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "effect_tags" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "overall_effect" VARCHAR(500) NOT NULL,
  "difficulty_level" VARCHAR(10) NOT NULL,
  "estimated_time_minutes" INTEGER NOT NULL,
  "product_coverage_rate" DOUBLE PRECISION NOT NULL,
  "owned_product_usage_count" INTEGER NOT NULL,
  "missing_product_types" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "substitution_count" INTEGER NOT NULL,
  "personalization_reasons" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "generation_confidence" VARCHAR(20) NOT NULL,
  "template_reuse_key" VARCHAR(160) NOT NULL,
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  "updated_at" TIMESTAMP(3) NOT NULL,
  CONSTRAINT "generated_makeup_templates_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "generated_template_steps" (
  "id" VARCHAR(50) NOT NULL,
  "template_id" VARCHAR(50) NOT NULL,
  "step_order" INTEGER NOT NULL,
  "section_code" VARCHAR(40) NOT NULL,
  "step_name" VARCHAR(100) NOT NULL,
  "step_goal" VARCHAR(255) NOT NULL,
  "user_instruction" VARCHAR(700) NOT NULL,
  "visual_change" VARCHAR(255) NOT NULL,
  "ai_detection_area" VARCHAR(120) NOT NULL,
  "completion_criteria" VARCHAR(255) NOT NULL,
  "failure_feedback" VARCHAR(255) NOT NULL,
  "editable_by_user" BOOLEAN NOT NULL DEFAULT true,
  "next_step_condition" VARCHAR(255) NOT NULL,
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "generated_template_steps_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "template_product_slots" (
  "id" VARCHAR(50) NOT NULL,
  "template_id" VARCHAR(50) NOT NULL,
  "step_id" VARCHAR(50) NOT NULL,
  "slot_code" VARCHAR(60) NOT NULL,
  "category" VARCHAR(40) NOT NULL,
  "sub_category" VARCHAR(80),
  "required_level" VARCHAR(20) NOT NULL,
  "desired_effect" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "desired_color_family" VARCHAR(80),
  "desired_finish" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "matched_user_product_id" VARCHAR(50),
  "matched_product_id" VARCHAR(50),
  "match_status" VARCHAR(20) NOT NULL,
  "match_reason" VARCHAR(255) NOT NULL,
  "alternative_product_ids" TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
  "fallback_instruction" VARCHAR(255) NOT NULL,
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "template_product_slots_pkey" PRIMARY KEY ("id")
);

CREATE TABLE "template_events" (
  "id" VARCHAR(50) NOT NULL,
  "user_id" VARCHAR(50) NOT NULL,
  "session_id" VARCHAR(80),
  "request_id" VARCHAR(50),
  "template_id" VARCHAR(50),
  "step_id" VARCHAR(50),
  "slot_id" VARCHAR(50),
  "product_snapshot_id" VARCHAR(50),
  "condition_snapshot_id" VARCHAR(50),
  "event_name" VARCHAR(80) NOT NULL,
  "payload" JSONB NOT NULL,
  "app_version" VARCHAR(40),
  "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT "template_events_pkey" PRIMARY KEY ("id")
);

CREATE UNIQUE INDEX "generated_makeup_templates_request_id_key" ON "generated_makeup_templates"("request_id");
CREATE INDEX "makeup_generation_requests_user_id_created_at_idx" ON "makeup_generation_requests"("user_id", "created_at");
CREATE INDEX "user_condition_snapshots_user_id_created_at_idx" ON "user_condition_snapshots"("user_id", "created_at");
CREATE INDEX "user_product_snapshots_user_id_created_at_idx" ON "user_product_snapshots"("user_id", "created_at");
CREATE INDEX "generated_makeup_templates_user_id_created_at_idx" ON "generated_makeup_templates"("user_id", "created_at");
CREATE INDEX "generated_makeup_templates_template_reuse_key_idx" ON "generated_makeup_templates"("template_reuse_key");
CREATE INDEX "generated_template_steps_template_id_step_order_idx" ON "generated_template_steps"("template_id", "step_order");
CREATE INDEX "template_product_slots_template_id_idx" ON "template_product_slots"("template_id");
CREATE INDEX "template_product_slots_step_id_idx" ON "template_product_slots"("step_id");
CREATE INDEX "template_product_slots_matched_user_product_id_idx" ON "template_product_slots"("matched_user_product_id");
CREATE INDEX "template_product_slots_matched_product_id_idx" ON "template_product_slots"("matched_product_id");
CREATE INDEX "template_events_user_id_created_at_idx" ON "template_events"("user_id", "created_at");
CREATE INDEX "template_events_template_id_event_name_idx" ON "template_events"("template_id", "event_name");
CREATE INDEX "template_events_request_id_idx" ON "template_events"("request_id");
CREATE INDEX "recommendations_generated_template_id_idx" ON "recommendations"("generated_template_id");

ALTER TABLE "makeup_generation_requests" ADD CONSTRAINT "makeup_generation_requests_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "user_condition_snapshots" ADD CONSTRAINT "user_condition_snapshots_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "user_product_snapshots" ADD CONSTRAINT "user_product_snapshots_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "generated_makeup_templates" ADD CONSTRAINT "generated_makeup_templates_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "generated_makeup_templates" ADD CONSTRAINT "generated_makeup_templates_request_id_fkey" FOREIGN KEY ("request_id") REFERENCES "makeup_generation_requests"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "generated_makeup_templates" ADD CONSTRAINT "generated_makeup_templates_condition_snapshot_id_fkey" FOREIGN KEY ("condition_snapshot_id") REFERENCES "user_condition_snapshots"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "generated_makeup_templates" ADD CONSTRAINT "generated_makeup_templates_product_snapshot_id_fkey" FOREIGN KEY ("product_snapshot_id") REFERENCES "user_product_snapshots"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
ALTER TABLE "generated_template_steps" ADD CONSTRAINT "generated_template_steps_template_id_fkey" FOREIGN KEY ("template_id") REFERENCES "generated_makeup_templates"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "template_product_slots" ADD CONSTRAINT "template_product_slots_template_id_fkey" FOREIGN KEY ("template_id") REFERENCES "generated_makeup_templates"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "template_product_slots" ADD CONSTRAINT "template_product_slots_step_id_fkey" FOREIGN KEY ("step_id") REFERENCES "generated_template_steps"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "template_product_slots" ADD CONSTRAINT "template_product_slots_matched_user_product_id_fkey" FOREIGN KEY ("matched_user_product_id") REFERENCES "user_products"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "template_product_slots" ADD CONSTRAINT "template_product_slots_matched_product_id_fkey" FOREIGN KEY ("matched_product_id") REFERENCES "products"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "template_events" ADD CONSTRAINT "template_events_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;
ALTER TABLE "template_events" ADD CONSTRAINT "template_events_request_id_fkey" FOREIGN KEY ("request_id") REFERENCES "makeup_generation_requests"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "template_events" ADD CONSTRAINT "template_events_template_id_fkey" FOREIGN KEY ("template_id") REFERENCES "generated_makeup_templates"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "template_events" ADD CONSTRAINT "template_events_step_id_fkey" FOREIGN KEY ("step_id") REFERENCES "generated_template_steps"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "template_events" ADD CONSTRAINT "template_events_slot_id_fkey" FOREIGN KEY ("slot_id") REFERENCES "template_product_slots"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "template_events" ADD CONSTRAINT "template_events_product_snapshot_id_fkey" FOREIGN KEY ("product_snapshot_id") REFERENCES "user_product_snapshots"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "template_events" ADD CONSTRAINT "template_events_condition_snapshot_id_fkey" FOREIGN KEY ("condition_snapshot_id") REFERENCES "user_condition_snapshots"("id") ON DELETE SET NULL ON UPDATE CASCADE;
ALTER TABLE "recommendations" ADD CONSTRAINT "recommendations_generated_template_id_fkey" FOREIGN KEY ("generated_template_id") REFERENCES "generated_makeup_templates"("id") ON DELETE SET NULL ON UPDATE CASCADE;
```

- [ ] **Step 3: Run Prisma generation**

Run:

```bash
cd backend
npm run prisma:generate
```

Expected: Prisma Client generation completes without schema validation errors.

- [ ] **Step 4: Commit schema and migration**

```bash
git add backend/prisma/schema.prisma backend/prisma/migrations/20260510090000_add_makeup_template_generation/migration.sql
git commit -m "feat: add makeup template generation schema"
```

---

### Task 2: Add Intent Parsing and Shared Types

**Files:**
- Create: `backend/src/makeup-templates/makeup-template-id.util.ts`
- Create: `backend/src/makeup-templates/makeup-template.types.ts`
- Create: `backend/src/makeup-templates/makeup-template-intent.service.ts`
- Create: `backend/src/makeup-templates/makeup-template-intent.service.spec.ts`

- [ ] **Step 1: Write failing intent tests**

Create `backend/src/makeup-templates/makeup-template-intent.service.spec.ts`:

```ts
import { MakeupTemplateIntentService } from './makeup-template-intent.service';

describe('MakeupTemplateIntentService', () => {
  let service: MakeupTemplateIntentService;

  beforeEach(() => {
    service = new MakeupTemplateIntentService();
  });

  it('parses commute clear makeup requirements', () => {
    expect(
      service.parse({
        rawUserInput: '明天上班想画一个清透又显气色的妆，最好用我已有的产品，十分钟内完成',
        requirements: ['不要太浓'],
      }),
    ).toEqual({
      parsedScene: 'COMMUTE',
      parsedStyleTags: ['CLEAR', 'NATURAL'],
      parsedEffectTags: ['GOOD_COMPLEXION'],
      parsedConstraints: ['OWNED_PRODUCTS_FIRST', 'FAST', 'LOW_INTENSITY'],
    });
  });

  it('falls back to daily natural makeup for unknown input', () => {
    expect(
      service.parse({
        rawUserInput: '随便给我一个今天能用的妆',
      }),
    ).toEqual({
      parsedScene: 'DAILY',
      parsedStyleTags: ['NATURAL'],
      parsedEffectTags: ['GOOD_COMPLEXION'],
      parsedConstraints: ['OWNED_PRODUCTS_FIRST'],
    });
  });
});
```

- [ ] **Step 2: Run intent tests and verify failure**

Run:

```bash
cd backend
npm test -- makeup-template-intent.service.spec.ts --runInBand
```

Expected: FAIL because `makeup-template-intent.service.ts` does not exist.

- [ ] **Step 3: Add ID utility**

Create `backend/src/makeup-templates/makeup-template-id.util.ts`:

```ts
import { randomUUID } from 'crypto';

const PREFIXES = {
  request: 'greq',
  conditionSnapshot: 'ucsnap',
  productSnapshot: 'upsnap',
  template: 'tmpl',
  step: 'tstep',
  slot: 'slot',
  event: 'tevt',
} as const;

export type MakeupTemplateIdKind = keyof typeof PREFIXES;

export function createMakeupTemplateId(kind: MakeupTemplateIdKind, now = new Date()) {
  const datePart = now.toISOString().slice(0, 10).replace(/-/g, '');
  const randomPart = randomUUID().replace(/-/g, '').slice(0, 8);

  return `${PREFIXES[kind]}_${datePart}_${randomPart}`;
}
```

- [ ] **Step 4: Add shared types**

Create `backend/src/makeup-templates/makeup-template.types.ts`:

```ts
import type { Product, ProductCategory, User, UserProduct } from '@prisma/client';

export type ParsedMakeupIntent = {
  parsedScene: string;
  parsedStyleTags: string[];
  parsedEffectTags: string[];
  parsedConstraints: string[];
};

export type IntentParseInput = {
  rawUserInput: string;
  requirements?: string[];
};

export type UserProductWithProductAndUsage = UserProduct & {
  product: Product;
  usageProfile?: {
    remainingPercent: number;
    interventionPriority: string;
    interventionReason: string;
  } | null;
};

export type SnapshotProduct = {
  userProductId: string;
  productId: string;
  productCategory: ProductCategory;
  subCategory: string;
  brandName: string;
  productName: string;
  colorFamily: string | null;
  finishType: string | null;
  suitabilityTags: string[];
  status: string;
  usagePreference: string;
};

export type MakeupStepBlueprint = {
  sectionCode: string;
  stepName: string;
  stepGoal: string;
  userInstruction: string;
  visualChange: string;
  aiDetectionArea: string;
  completionCriteria: string;
  failureFeedback: string;
  editableByUser: boolean;
  nextStepCondition: string;
  slots: ProductSlotBlueprint[];
};

export type ProductSlotBlueprint = {
  slotCode: string;
  category: ProductCategory;
  subCategory?: string;
  requiredLevel: 'required' | 'recommended' | 'optional';
  desiredEffect: string[];
  desiredColorFamily?: string;
  desiredFinish: string[];
  fallbackInstruction: string;
};

export type ProductSlotMatch = ProductSlotBlueprint & {
  matchedUserProductId?: string;
  matchedProductId?: string;
  matchStatus: 'matched' | 'substitutable' | 'missing';
  matchReason: string;
  alternativeProductIds: string[];
};

export type TemplateGenerationContext = {
  user: User;
  intent: ParsedMakeupIntent;
  rawUserInput: string;
  requirements: string[];
  availableProducts: UserProductWithProductAndUsage[];
};
```

- [ ] **Step 5: Implement intent parser**

Create `backend/src/makeup-templates/makeup-template-intent.service.ts`:

```ts
import { Injectable } from '@nestjs/common';
import type { IntentParseInput, ParsedMakeupIntent } from './makeup-template.types';

@Injectable()
export class MakeupTemplateIntentService {
  parse(input: IntentParseInput): ParsedMakeupIntent {
    const text = `${input.rawUserInput} ${(input.requirements ?? []).join(' ')}`;
    const parsedScene = this.parseScene(text);
    const parsedStyleTags = this.unique([
      ...this.findTags(text, [
        ['CLEAR', ['清透', '清爽', '干净']],
        ['NATURAL', ['自然', '日常', '淡妆']],
        ['SWEET', ['甜美', '嫩妹', '甜妹']],
        ['GENTLE', ['温柔', '低饱和', '豆沙']],
        ['GLAM', ['欧美', '浓颜', '上镜']],
      ]),
      'NATURAL',
    ]).slice(0, text.includes('清透') ? 2 : 1);
    const parsedEffectTags = this.unique([
      ...this.findTags(text, [
        ['DEWY', ['水光', '奶油肌', '光泽']],
        ['MATTE', ['哑光', '雾面']],
        ['LONG_LASTING', ['持妆', '不脱妆']],
        ['COVERAGE', ['遮瑕', '遮盖']],
        ['GOOD_COMPLEXION', ['显气色', '精神', '提气色']],
      ]),
      'GOOD_COMPLEXION',
    ]);
    const parsedConstraints = this.unique([
      ...(text.includes('已有') || text.includes('自己的') || text.includes('产品') ? ['OWNED_PRODUCTS_FIRST'] : []),
      ...(text.includes('快') || text.includes('十分钟') || text.includes('10分钟') ? ['FAST'] : []),
      ...(text.includes('敏感') || text.includes('避雷') ? ['SENSITIVE_SAFE'] : []),
      ...(text.includes('不要太浓') || text.includes('不浓') || text.includes('淡') ? ['LOW_INTENSITY'] : []),
      'OWNED_PRODUCTS_FIRST',
    ]);

    return {
      parsedScene,
      parsedStyleTags,
      parsedEffectTags,
      parsedConstraints,
    };
  }

  private parseScene(text: string) {
    if (text.includes('上班') || text.includes('通勤') || text.includes('办公室')) {
      return 'COMMUTE';
    }

    if (text.includes('约会')) {
      return 'DATE';
    }

    if (text.includes('面试') || text.includes('见客户')) {
      return 'INTERVIEW';
    }

    if (text.includes('上镜') || text.includes('拍照') || text.includes('聚会')) {
      return 'CAMERA';
    }

    return 'DAILY';
  }

  private findTags(text: string, rules: Array<[string, string[]]>) {
    return rules
      .filter(([, keywords]) => keywords.some((keyword) => text.includes(keyword)))
      .map(([tag]) => tag);
  }

  private unique(values: string[]) {
    return [...new Set(values)];
  }
}
```

- [ ] **Step 6: Run intent tests and commit**

Run:

```bash
cd backend
npm test -- makeup-template-intent.service.spec.ts --runInBand
```

Expected: PASS.

Commit:

```bash
git add backend/src/makeup-templates/makeup-template-id.util.ts backend/src/makeup-templates/makeup-template.types.ts backend/src/makeup-templates/makeup-template-intent.service.ts backend/src/makeup-templates/makeup-template-intent.service.spec.ts
git commit -m "feat: add makeup template intent parsing"
```

---

### Task 3: Add Product Slot Matching

**Files:**
- Create: `backend/src/makeup-templates/makeup-template-slot-matching.service.ts`
- Create: `backend/src/makeup-templates/makeup-template-slot-matching.service.spec.ts`

- [ ] **Step 1: Write failing slot matching tests**

Create `backend/src/makeup-templates/makeup-template-slot-matching.service.spec.ts`:

```ts
import { MakeupTemplateSlotMatchingService } from './makeup-template-slot-matching.service';
import type { ProductSlotBlueprint, UserProductWithProductAndUsage } from './makeup-template.types';

function userProduct(overrides: Partial<UserProductWithProductAndUsage>): UserProductWithProductAndUsage {
  const now = new Date('2026-05-10T00:00:00.000Z');

  return {
    id: 'user-prod-1',
    userId: 'user-001',
    productId: 'prod-1',
    status: 'active',
    openedAt: now,
    expiresAt: new Date('2026-07-01T00:00:00.000Z'),
    usageCount: 3,
    lastUsedAt: new Date('2026-05-01T00:00:00.000Z'),
    notes: null,
    isOpened: true,
    customExpiresAt: null,
    purchaseChannel: null,
    purchaseDate: null,
    userTags: [],
    sortOrder: 0,
    createdAt: now,
    updatedAt: now,
    product: {
      id: 'prod-1',
      name: '轻透底妆',
      brand: 'Demo',
      category: 'makeup',
      subCategory: 'foundation',
      tags: ['base', 'natural', 'dewy'],
      halalStatus: 'unknown',
      halalCertifier: null,
      halalNote: null,
      shelfLifeMonths: 12,
      image: 'mock://prod-1',
      shadeName: 'N1',
      colorCode: '#D8A37B',
      barcode: null,
      officialShelfLifeMonths: null,
      periodAfterOpeningMonths: null,
      imageUrls: [],
      purchaseChannels: [],
      createdAt: now,
      updatedAt: now,
    },
    usageProfile: null,
    ...overrides,
  };
}

describe('MakeupTemplateSlotMatchingService', () => {
  let service: MakeupTemplateSlotMatchingService;
  const baseSlot: ProductSlotBlueprint = {
    slotCode: 'BASE_FOUNDATION',
    category: 'makeup',
    subCategory: 'foundation',
    requiredLevel: 'required',
    desiredEffect: ['base', 'natural'],
    desiredFinish: ['dewy'],
    fallbackInstruction: '没有粉底时先保持妆前保湿和遮瑕。',
  };

  beforeEach(() => {
    service = new MakeupTemplateSlotMatchingService();
  });

  it('matches the highest scoring active user product', () => {
    const result = service.matchSlot(baseSlot, [
      userProduct({ id: 'user-prod-1', productId: 'prod-1' }),
      userProduct({
        id: 'user-prod-2',
        productId: 'prod-2',
        product: {
          ...userProduct({}).product,
          id: 'prod-2',
          name: '雾面粉底',
          tags: ['base'],
        },
      }),
    ]);

    expect(result).toMatchObject({
      matchedUserProductId: 'user-prod-1',
      matchedProductId: 'prod-1',
      matchStatus: 'matched',
      alternativeProductIds: ['prod-2'],
    });
    expect(result.matchReason).toContain('子类命中');
  });

  it('does not match expired products', () => {
    const result = service.matchSlot(baseSlot, [
      userProduct({ status: 'expired' }),
    ]);

    expect(result).toMatchObject({
      matchStatus: 'missing',
      matchReason: '没有可用产品匹配 BASE_FOUNDATION 槽位。',
    });
  });

  it('marks same-category products as substitutable when subcategory differs', () => {
    const result = service.matchSlot(baseSlot, [
      userProduct({
        product: {
          ...userProduct({}).product,
          subCategory: 'concealer',
          tags: ['base', 'natural'],
        },
      }),
    ]);

    expect(result).toMatchObject({
      matchedProductId: 'prod-1',
      matchStatus: 'substitutable',
    });
  });
});
```

- [ ] **Step 2: Run slot matching tests and verify failure**

Run:

```bash
cd backend
npm test -- makeup-template-slot-matching.service.spec.ts --runInBand
```

Expected: FAIL because `makeup-template-slot-matching.service.ts` does not exist.

- [ ] **Step 3: Implement slot matching service**

Create `backend/src/makeup-templates/makeup-template-slot-matching.service.ts`:

```ts
import { Injectable } from '@nestjs/common';
import type {
  ProductSlotBlueprint,
  ProductSlotMatch,
  UserProductWithProductAndUsage,
} from './makeup-template.types';

type CandidateScore = {
  item: UserProductWithProductAndUsage;
  score: number;
  subCategoryMatched: boolean;
  tagMatches: string[];
};

@Injectable()
export class MakeupTemplateSlotMatchingService {
  matchSlot(
    slot: ProductSlotBlueprint,
    products: UserProductWithProductAndUsage[],
  ): ProductSlotMatch {
    const candidates = products
      .filter((item) => ['active', 'idle'].includes(item.status))
      .filter((item) => item.product.category === slot.category)
      .map((item) => this.scoreCandidate(slot, item))
      .filter((candidate): candidate is CandidateScore => candidate !== null)
      .sort((left, right) => this.compareCandidates(left, right));

    if (candidates.length === 0) {
      return {
        ...slot,
        matchStatus: 'missing',
        matchReason: `没有可用产品匹配 ${slot.slotCode} 槽位。`,
        alternativeProductIds: [],
      };
    }

    const best = candidates[0];
    const matchStatus = best.subCategoryMatched ? 'matched' : 'substitutable';

    return {
      ...slot,
      matchedUserProductId: best.item.id,
      matchedProductId: best.item.productId,
      matchStatus,
      matchReason: this.buildReason(best, matchStatus),
      alternativeProductIds: [
        ...new Set(candidates.slice(1).map((candidate) => candidate.item.productId)),
      ].slice(0, 3),
    };
  }

  private scoreCandidate(
    slot: ProductSlotBlueprint,
    item: UserProductWithProductAndUsage,
  ): CandidateScore | null {
    const subCategoryMatched = slot.subCategory
      ? item.product.subCategory === slot.subCategory
      : false;
    const desiredTags = [...slot.desiredEffect, ...slot.desiredFinish];
    const userTags = item.userTags ?? [];
    const searchableTags = [...item.product.tags, ...userTags];
    const tagMatches = desiredTags.filter((tag) => searchableTags.includes(tag));

    if (slot.subCategory && !subCategoryMatched && tagMatches.length === 0) {
      return null;
    }

    const usageProfileBoost = item.usageProfile?.interventionPriority === 'high' ? 3 : 0;
    const statusBoost = item.status === 'active' ? 5 : 1;
    const usageBoost = Math.min(item.usageCount, 10);
    const recencyBoost = Math.max(0, 30 - this.daysSince(item.lastUsedAt));
    const score =
      (subCategoryMatched ? 100 : 20) +
      tagMatches.length * 15 +
      statusBoost +
      usageBoost +
      usageProfileBoost +
      recencyBoost / 10;

    return {
      item,
      score,
      subCategoryMatched,
      tagMatches,
    };
  }

  private compareCandidates(left: CandidateScore, right: CandidateScore) {
    if (right.score !== left.score) {
      return right.score - left.score;
    }

    return left.item.id.localeCompare(right.item.id);
  }

  private daysSince(date: Date) {
    const reference = new Date('2026-05-10T00:00:00.000Z').getTime();
    return Math.round((reference - date.getTime()) / (24 * 60 * 60 * 1000));
  }

  private buildReason(candidate: CandidateScore, matchStatus: 'matched' | 'substitutable') {
    const parts = [matchStatus === 'matched' ? '子类命中' : '同类可替代'];

    if (candidate.tagMatches.length > 0) {
      parts.push(`标签命中 ${candidate.tagMatches.join('/')}`);
    }

    parts.push('综合状态、使用频率和最近使用时间排序靠前');

    return parts.join('，');
  }
}
```

- [ ] **Step 4: Run slot matching tests and commit**

Run:

```bash
cd backend
npm test -- makeup-template-slot-matching.service.spec.ts --runInBand
```

Expected: PASS.

Commit:

```bash
git add backend/src/makeup-templates/makeup-template-slot-matching.service.ts backend/src/makeup-templates/makeup-template-slot-matching.service.spec.ts
git commit -m "feat: match makeup template product slots"
```

---

### Task 4: Add Template Generation Service and API

**Files:**
- Create: `backend/src/makeup-templates/dto/generate-makeup-template.dto.ts`
- Create: `backend/src/makeup-templates/dto/record-template-event.dto.ts`
- Create: `backend/src/makeup-templates/dto/makeup-template-response.dto.ts`
- Create: `backend/src/makeup-templates/makeup-template-snapshot.service.ts`
- Create: `backend/src/makeup-templates/makeup-template.mapper.ts`
- Create: `backend/src/makeup-templates/makeup-template-generation.service.ts`
- Create: `backend/src/makeup-templates/makeup-template-generation.service.spec.ts`
- Create: `backend/src/makeup-templates/makeup-template-event.service.ts`
- Create: `backend/src/makeup-templates/makeup-template-event.service.spec.ts`
- Create: `backend/src/makeup-templates/makeup-templates.controller.ts`
- Create: `backend/src/makeup-templates/makeup-templates.module.ts`
- Modify: `backend/src/app.module.ts`

- [ ] **Step 1: Write failing generation service test**

Create `backend/src/makeup-templates/makeup-template-generation.service.spec.ts` with a mocked Prisma service:

```ts
import { NotFoundException } from '@nestjs/common';
import { MakeupTemplateGenerationService } from './makeup-template-generation.service';
import { MakeupTemplateIntentService } from './makeup-template-intent.service';
import { MakeupTemplateSlotMatchingService } from './makeup-template-slot-matching.service';
import { MakeupTemplateSnapshotService } from './makeup-template-snapshot.service';
import { MakeupTemplateEventService } from './makeup-template-event.service';

describe('MakeupTemplateGenerationService', () => {
  const now = new Date('2026-05-10T00:00:00.000Z');
  const user = {
    id: 'user-001',
    nickname: 'Demo',
    skinType: 'oily',
    makeupPreference: 'natural',
    commonScenarios: ['通勤'],
    createdAt: now,
    updatedAt: now,
  };
  const product = {
    id: 'prod-007',
    name: '柔雾持妆粉底液',
    brand: 'Lustre',
    category: 'makeup',
    subCategory: 'foundation',
    tags: ['base', 'natural', '通勤'],
    halalStatus: 'unknown',
    halalCertifier: null,
    halalNote: null,
    shelfLifeMonths: 12,
    image: 'mock://prod-007',
    shadeName: 'N1',
    colorCode: '#D7A37B',
    barcode: null,
    officialShelfLifeMonths: null,
    periodAfterOpeningMonths: null,
    imageUrls: [],
    purchaseChannels: [],
    createdAt: now,
    updatedAt: now,
  };

  function makePrisma() {
    const prisma = {
      user: {
        findUnique: jest.fn().mockResolvedValue(user),
      },
      userProduct: {
        findMany: jest.fn().mockResolvedValue([
          {
            id: 'user-prod-003',
            userId: 'user-001',
            productId: 'prod-007',
            status: 'active',
            openedAt: now,
            expiresAt: new Date('2026-07-01T00:00:00.000Z'),
            usageCount: 5,
            lastUsedAt: now,
            notes: null,
            isOpened: true,
            customExpiresAt: null,
            purchaseChannel: null,
            purchaseDate: null,
            userTags: ['natural'],
            sortOrder: 0,
            createdAt: now,
            updatedAt: now,
            product,
            usageProfile: null,
          },
        ]),
      },
      makeupGenerationRequest: {
        create: jest.fn(async ({ data }) => ({ ...data, createdAt: now })),
      },
      userConditionSnapshot: {
        create: jest.fn(async ({ data }) => ({ ...data, createdAt: now })),
      },
      userProductSnapshot: {
        create: jest.fn(async ({ data }) => ({ ...data, createdAt: now })),
      },
      generatedMakeupTemplate: {
        create: jest.fn(async ({ data }) => ({
          ...data,
          createdAt: now,
          updatedAt: now,
          steps: data.steps.create.map((step) => ({
            ...step,
            createdAt: now,
            productSlots: data.productSlots.create
              .filter((slot) => slot.stepId === step.id)
              .map((slot) => ({ ...slot, createdAt: now })),
          })),
          productSlots: data.productSlots.create.map((slot) => ({ ...slot, createdAt: now })),
        })),
        findUnique: jest.fn(),
      },
      templateEvent: {
        create: jest.fn(async ({ data }) => ({ ...data, createdAt: now })),
      },
    };

    return prisma;
  }

  it('generates a persisted template with snapshots, steps and slots', async () => {
    const prisma = makePrisma();
    const service = new MakeupTemplateGenerationService(
      prisma as never,
      new MakeupTemplateIntentService(),
      new MakeupTemplateSnapshotService(prisma as never),
      new MakeupTemplateSlotMatchingService(),
      new MakeupTemplateEventService(prisma as never),
    );

    const result = await service.generate({
      userId: 'user-001',
      rawUserInput: '明天上班想画清透通勤妆，优先使用已有产品',
      generationSource: 'recommendation_scenario',
      requirements: ['快速'],
    });

    expect(result.id).toMatch(/^tmpl_/);
    expect(result.request.rawUserInput).toContain('清透通勤妆');
    expect(result.steps).toHaveLength(5);
    expect(result.steps[0].productSlots[0]).toMatchObject({
      slotCode: 'BASE_FOUNDATION',
      matchStatus: 'matched',
      matchedProductId: 'prod-007',
    });
    expect(result.productCoverageRate).toBeGreaterThan(0);
    expect(prisma.templateEvent.create).toHaveBeenCalledWith(
      expect.objectContaining({
        data: expect.objectContaining({
          eventName: 'template_generation_completed',
        }),
      }),
    );
  });

  it('throws when user does not exist', async () => {
    const prisma = makePrisma();
    prisma.user.findUnique.mockResolvedValue(null);
    const service = new MakeupTemplateGenerationService(
      prisma as never,
      new MakeupTemplateIntentService(),
      new MakeupTemplateSnapshotService(prisma as never),
      new MakeupTemplateSlotMatchingService(),
      new MakeupTemplateEventService(prisma as never),
    );

    await expect(
      service.generate({
        userId: 'missing-user',
        rawUserInput: '通勤妆',
        generationSource: 'recommendation_scenario',
      }),
    ).rejects.toBeInstanceOf(NotFoundException);
  });
});
```

- [ ] **Step 2: Run generation test and verify failure**

Run:

```bash
cd backend
npm test -- makeup-template-generation.service.spec.ts --runInBand
```

Expected: FAIL because generation service files do not exist.

- [ ] **Step 3: Add DTOs**

Create `backend/src/makeup-templates/dto/generate-makeup-template.dto.ts`:

```ts
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsArray, IsIn, IsOptional, IsString, MinLength } from 'class-validator';

export class GenerateMakeupTemplateDto {
  @ApiProperty({ example: 'user-001' })
  @IsString()
  userId!: string;

  @ApiProperty({ example: '明天上班想画清透又显气色的妆，最好用我已有的产品' })
  @IsString()
  @MinLength(1)
  rawUserInput!: string;

  @ApiProperty({ example: 'recommendation_scenario' })
  @IsString()
  generationSource!: string;

  @ApiPropertyOptional({ example: 'none', enum: ['none', 'image', 'video', 'creator', 'template'] })
  @IsOptional()
  @IsIn(['none', 'image', 'video', 'creator', 'template'])
  referenceType?: string;

  @ApiPropertyOptional({ example: 'tpl-sweet-5' })
  @IsOptional()
  @IsString()
  referenceId?: string;

  @ApiPropertyOptional({ example: ['已有产品优先', '快速'], type: [String] })
  @IsOptional()
  @IsArray()
  @IsString({ each: true })
  requirements?: string[];
}
```

Create `backend/src/makeup-templates/dto/record-template-event.dto.ts`:

```ts
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';
import { IsObject, IsOptional, IsString } from 'class-validator';

export class RecordTemplateEventDto {
  @ApiProperty({ example: 'user-001' })
  @IsString()
  userId!: string;

  @ApiProperty({ example: 'step_completed' })
  @IsString()
  eventName!: string;

  @ApiPropertyOptional({ example: 'session-001' })
  @IsOptional()
  @IsString()
  sessionId?: string;

  @ApiPropertyOptional({ example: 'tstep_20260510_1234abcd' })
  @IsOptional()
  @IsString()
  stepId?: string;

  @ApiPropertyOptional({ example: 'slot_20260510_1234abcd' })
  @IsOptional()
  @IsString()
  slotId?: string;

  @ApiPropertyOptional({ type: 'object', additionalProperties: true })
  @IsOptional()
  @IsObject()
  payload?: Record<string, unknown>;

  @ApiPropertyOptional({ example: '1.0.0' })
  @IsOptional()
  @IsString()
  appVersion?: string;
}
```

Create `backend/src/makeup-templates/dto/makeup-template-response.dto.ts` with Swagger-compatible classes for response shape:

```ts
import { ApiProperty, ApiPropertyOptional } from '@nestjs/swagger';

export class TemplateProductSlotResponseDto {
  @ApiProperty()
  id!: string;

  @ApiProperty()
  slotCode!: string;

  @ApiProperty()
  category!: string;

  @ApiPropertyOptional()
  subCategory?: string;

  @ApiProperty()
  requiredLevel!: string;

  @ApiProperty({ type: [String] })
  desiredEffect!: string[];

  @ApiProperty({ type: [String] })
  desiredFinish!: string[];

  @ApiPropertyOptional()
  matchedUserProductId?: string;

  @ApiPropertyOptional()
  matchedProductId?: string;

  @ApiProperty()
  matchStatus!: 'matched' | 'substitutable' | 'missing';

  @ApiProperty()
  matchReason!: string;

  @ApiProperty({ type: [String] })
  alternativeProductIds!: string[];

  @ApiProperty()
  fallbackInstruction!: string;
}

export class GeneratedTemplateStepResponseDto {
  @ApiProperty()
  id!: string;

  @ApiProperty()
  stepOrder!: number;

  @ApiProperty()
  sectionCode!: string;

  @ApiProperty()
  stepName!: string;

  @ApiProperty()
  stepGoal!: string;

  @ApiProperty()
  userInstruction!: string;

  @ApiProperty()
  visualChange!: string;

  @ApiProperty()
  aiDetectionArea!: string;

  @ApiProperty()
  completionCriteria!: string;

  @ApiProperty()
  failureFeedback!: string;

  @ApiProperty()
  editableByUser!: boolean;

  @ApiProperty()
  nextStepCondition!: string;

  @ApiProperty({ type: [TemplateProductSlotResponseDto] })
  productSlots!: TemplateProductSlotResponseDto[];
}

export class MakeupTemplateResponseDto {
  @ApiProperty()
  id!: string;

  @ApiProperty()
  userId!: string;

  @ApiProperty()
  displayName!: string;

  @ApiProperty()
  primaryScene!: string;

  @ApiProperty({ type: [String] })
  styleTags!: string[];

  @ApiProperty({ type: [String] })
  effectTags!: string[];

  @ApiProperty()
  overallEffect!: string;

  @ApiProperty()
  difficultyLevel!: string;

  @ApiProperty()
  estimatedTimeMinutes!: number;

  @ApiProperty()
  productCoverageRate!: number;

  @ApiProperty({ type: [String] })
  missingProductTypes!: string[];

  @ApiProperty({ type: [String] })
  personalizationReasons!: string[];

  @ApiProperty()
  generationConfidence!: string;

  @ApiProperty({ type: [GeneratedTemplateStepResponseDto] })
  steps!: GeneratedTemplateStepResponseDto[];

  @ApiProperty()
  request!: {
    id: string;
    rawUserInput: string;
    parsedScene: string;
    parsedStyleTags: string[];
    parsedEffectTags: string[];
    parsedConstraints: string[];
  };

  @ApiProperty()
  conditionSnapshotId!: string;

  @ApiProperty()
  productSnapshotId!: string;
}
```

- [ ] **Step 4: Add snapshot, event, mapper and generation services**

Create the services with these public methods:

```ts
// backend/src/makeup-templates/makeup-template-snapshot.service.ts
createConditionSnapshot(user: User): Promise<UserConditionSnapshot>
createProductSnapshot(userId: string, products: UserProductWithProductAndUsage[]): Promise<UserProductSnapshot>
```

```ts
// backend/src/makeup-templates/makeup-template-event.service.ts
record(input: {
  userId: string;
  eventName: string;
  sessionId?: string;
  requestId?: string;
  templateId?: string;
  stepId?: string;
  slotId?: string;
  productSnapshotId?: string;
  conditionSnapshotId?: string;
  payload?: Record<string, unknown>;
  appVersion?: string;
}): Promise<void>
```

```ts
// backend/src/makeup-templates/makeup-template-generation.service.ts
generate(input: GenerateMakeupTemplateDto): Promise<MakeupTemplateResponseDto>
getById(templateId: string): Promise<MakeupTemplateResponseDto>
```

Use this deterministic five-step blueprint inside `MakeupTemplateGenerationService`:

```ts
private buildStepBlueprints(intent: ParsedMakeupIntent): MakeupStepBlueprint[] {
  const clearTone = intent.parsedStyleTags.includes('CLEAR');

  return [
    {
      sectionCode: 'BASE',
      stepName: '底妆',
      stepGoal: clearTone ? '完成清透均匀的底妆' : '完成干净均匀的底妆',
      userInstruction: '从面中开始少量多次上底妆，鼻翼、嘴角和眼下用余量轻拍融合。',
      visualChange: '肤色更均匀，泛红和暗沉减轻，粉感保持自然。',
      aiDetectionArea: 'full_face',
      completionCriteria: '面中肤色均匀，底妆边缘没有明显色块。',
      failureFeedback: '底妆偏厚时减少叠加，用湿粉扑轻拍边缘。',
      editableByUser: true,
      nextStepCondition: '底妆均匀后进入眉毛步骤。',
      slots: [
        {
          slotCode: 'BASE_FOUNDATION',
          category: 'makeup',
          subCategory: 'foundation',
          requiredLevel: 'required',
          desiredEffect: ['base', 'natural'],
          desiredFinish: clearTone ? ['dewy'] : ['matte'],
          fallbackInstruction: '没有粉底时，用遮瑕局部修饰并保持妆前保湿。',
        },
      ],
    },
    {
      sectionCode: 'BROW',
      stepName: '眉毛',
      stepGoal: '补齐眉形并保持自然毛流',
      userInstruction: '顺毛流填补空缺，眉尾自然拉长，眉头用刷子晕淡。',
      visualChange: '眉形更完整，五官精神感提升。',
      aiDetectionArea: 'brows',
      completionCriteria: '两侧眉形高度接近，眉头不过重。',
      failureFeedback: '眉头过重时用螺旋刷向上梳开。',
      editableByUser: true,
      nextStepCondition: '眉形平衡后进入眼妆步骤。',
      slots: [
        {
          slotCode: 'BROW_PENCIL',
          category: 'makeup',
          subCategory: 'brow',
          requiredLevel: 'required',
          desiredEffect: ['brow', 'natural'],
          desiredFinish: ['soft'],
          fallbackInstruction: '没有眉笔时，用哑光棕色眼影少量填补眉尾。',
        },
      ],
    },
    {
      sectionCode: 'EYE',
      stepName: '眼妆',
      stepGoal: '增强眼部层次但保持干净',
      userInstruction: '浅色打底后在眼尾轻扫阴影，夹翘睫毛并加强睫毛根部。',
      visualChange: '眼睛更有神，眼妆边缘干净。',
      aiDetectionArea: 'eyes',
      completionCriteria: '眼影边界柔和，睫毛根部有存在感。',
      failureFeedback: '眼影过深时用干净刷子向外晕染。',
      editableByUser: true,
      nextStepCondition: '眼妆干净后进入腮红步骤。',
      slots: [
        {
          slotCode: 'EYE_SHADOW_OR_LINER',
          category: 'makeup',
          subCategory: 'eye',
          requiredLevel: 'recommended',
          desiredEffect: ['eye', 'natural'],
          desiredFinish: ['soft'],
          fallbackInstruction: '没有眼影时，跳过眼影并重点夹翘睫毛。',
        },
      ],
    },
    {
      sectionCode: 'BLUSH',
      stepName: '腮红',
      stepGoal: '提升面中气色',
      userInstruction: '腮红从苹果肌偏上位置少量多次晕染，范围不要低于鼻翼。',
      visualChange: '面中更饱满，气色更柔和。',
      aiDetectionArea: 'cheeks',
      completionCriteria: '腮红颜色柔和，左右位置接近。',
      failureFeedback: '腮红过重时用底妆余量轻压边缘。',
      editableByUser: true,
      nextStepCondition: '腮红位置自然后进入唇妆步骤。',
      slots: [
        {
          slotCode: 'CHEEK_BLUSH',
          category: 'makeup',
          subCategory: 'blush',
          requiredLevel: 'recommended',
          desiredEffect: ['blush', 'good_complexion'],
          desiredFinish: ['soft'],
          fallbackInstruction: '没有腮红时，用少量口红点拍在面中并迅速晕开。',
        },
      ],
    },
    {
      sectionCode: 'LIP',
      stepName: '唇妆',
      stepGoal: '完成协调自然的唇色',
      userInstruction: '口红从唇内侧向外晕染，边缘保持柔和，不画锋利唇线。',
      visualChange: '唇色更均匀，整体妆容完成。',
      aiDetectionArea: 'lips',
      completionCriteria: '唇色均匀，边缘自然，和腮红色系协调。',
      failureFeedback: '唇色过重时用纸巾轻抿，再用指腹晕开边缘。',
      editableByUser: true,
      nextStepCondition: '唇色完成后结束模板执行。',
      slots: [
        {
          slotCode: 'LIP_COLOR',
          category: 'makeup',
          subCategory: 'lip',
          requiredLevel: 'required',
          desiredEffect: ['lip', 'good_complexion'],
          desiredFinish: ['soft'],
          fallbackInstruction: '没有口红时，用润唇膏提升唇部状态并完成妆容。',
        },
      ],
    },
  ];
}
```

Use `mapMakeupTemplate` in `makeup-template.mapper.ts` to return `MakeupTemplateResponseDto` with steps sorted by `stepOrder` and slots grouped by `stepId`.

- [ ] **Step 5: Add controller and module**

Create `backend/src/makeup-templates/makeup-templates.controller.ts`:

```ts
import { Body, Controller, Get, HttpCode, HttpStatus, Param, Post } from '@nestjs/common';
import { ApiCreatedResponse, ApiOkResponse, ApiTags } from '@nestjs/swagger';
import { GenerateMakeupTemplateDto } from './dto/generate-makeup-template.dto';
import { MakeupTemplateResponseDto } from './dto/makeup-template-response.dto';
import { RecordTemplateEventDto } from './dto/record-template-event.dto';
import { MakeupTemplateEventService } from './makeup-template-event.service';
import { MakeupTemplateGenerationService } from './makeup-template-generation.service';

@ApiTags('makeup-templates')
@Controller('makeup-templates')
export class MakeupTemplatesController {
  constructor(
    private readonly generationService: MakeupTemplateGenerationService,
    private readonly eventService: MakeupTemplateEventService,
  ) {}

  @Post('generate')
  @ApiCreatedResponse({ type: MakeupTemplateResponseDto })
  generate(@Body() body: GenerateMakeupTemplateDto) {
    return this.generationService.generate(body);
  }

  @Get(':templateId')
  @ApiOkResponse({ type: MakeupTemplateResponseDto })
  getById(@Param('templateId') templateId: string) {
    return this.generationService.getById(templateId);
  }

  @Post(':templateId/events')
  @HttpCode(HttpStatus.OK)
  recordEvent(@Param('templateId') templateId: string, @Body() body: RecordTemplateEventDto) {
    return this.eventService.record({
      ...body,
      templateId,
      payload: body.payload ?? {},
    });
  }
}
```

Create `backend/src/makeup-templates/makeup-templates.module.ts`:

```ts
import { Module } from '@nestjs/common';
import { PrismaModule } from '../prisma/prisma.module';
import { MakeupTemplateEventService } from './makeup-template-event.service';
import { MakeupTemplateGenerationService } from './makeup-template-generation.service';
import { MakeupTemplateIntentService } from './makeup-template-intent.service';
import { MakeupTemplateSlotMatchingService } from './makeup-template-slot-matching.service';
import { MakeupTemplateSnapshotService } from './makeup-template-snapshot.service';
import { MakeupTemplatesController } from './makeup-templates.controller';

@Module({
  imports: [PrismaModule],
  controllers: [MakeupTemplatesController],
  providers: [
    MakeupTemplateEventService,
    MakeupTemplateGenerationService,
    MakeupTemplateIntentService,
    MakeupTemplateSlotMatchingService,
    MakeupTemplateSnapshotService,
  ],
  exports: [MakeupTemplateEventService, MakeupTemplateGenerationService],
})
export class MakeupTemplatesModule {}
```

Modify `backend/src/app.module.ts`:

```ts
import { MakeupTemplatesModule } from './makeup-templates/makeup-templates.module';
```

Add `MakeupTemplatesModule` to the `imports` array.

- [ ] **Step 6: Run tests and commit**

Run:

```bash
cd backend
npm test -- makeup-template-generation.service.spec.ts makeup-template-intent.service.spec.ts makeup-template-slot-matching.service.spec.ts --runInBand
```

Expected: PASS.

Commit:

```bash
git add backend/src/makeup-templates backend/src/app.module.ts
git commit -m "feat: generate personalized makeup templates"
```

---

### Task 5: Integrate Generated Templates with Recommendations

**Files:**
- Modify: `backend/src/recommendations/recommendations.module.ts`
- Modify: `backend/src/recommendations/recommendations.service.ts`
- Modify: `backend/src/recommendations/dto/recommendation-response.dto.ts`
- Modify: `backend/src/recommendations/dto/recommendation-step-response.dto.ts`
- Modify: `backend/src/recommendations/recommendation.mapper.ts`
- Create: `backend/src/recommendations/recommendations.service.spec.ts`

- [ ] **Step 1: Write failing recommendation compatibility test**

Create `backend/src/recommendations/recommendations.service.spec.ts`:

```ts
import { RecommendationsService } from './recommendations.service';

describe('RecommendationsService generated template compatibility', () => {
  it('maps a generated template into recommendation response fields', async () => {
    const prisma = {
      recommendation: {
        create: jest.fn(async ({ data }) => ({
          id: data.id,
          userId: data.userId,
          templateId: null,
          generatedTemplateId: data.generatedTemplateId,
          scenario: data.scenario,
          title: data.title,
          summary: data.summary,
          halalStatus: data.halalStatus,
          certifiedCount: data.certifiedCount,
          notHalalCount: data.notHalalCount,
          unknownCount: data.unknownCount,
          missingCount: data.missingCount,
          halalNote: data.halalNote,
          reasons: data.reasons,
          createdAt: new Date('2026-05-10T00:00:00.000Z'),
          updatedAt: new Date('2026-05-10T00:00:00.000Z'),
          steps: data.steps.create.map((step) => ({
            ...step,
            recommendationId: data.id,
            createdAt: new Date('2026-05-10T00:00:00.000Z'),
          })),
        })),
      },
    };
    const generationService = {
      generate: jest.fn().mockResolvedValue({
        id: 'tmpl_20260510_abcd1234',
        userId: 'user-001',
        displayName: '清透通勤妆',
        primaryScene: 'COMMUTE',
        styleTags: ['CLEAR', 'NATURAL'],
        effectTags: ['GOOD_COMPLEXION'],
        overallEffect: '清透显气色',
        difficultyLevel: 'L2',
        estimatedTimeMinutes: 10,
        productCoverageRate: 0.6,
        missingProductTypes: ['blush', 'lip'],
        personalizationReasons: ['用户偏好自然妆，且已有底妆产品。'],
        generationConfidence: 'medium',
        request: {
          id: 'greq_20260510_abcd1234',
          rawUserInput: '清透通勤妆',
          parsedScene: 'COMMUTE',
          parsedStyleTags: ['CLEAR', 'NATURAL'],
          parsedEffectTags: ['GOOD_COMPLEXION'],
          parsedConstraints: ['OWNED_PRODUCTS_FIRST'],
        },
        conditionSnapshotId: 'ucsnap_20260510_abcd1234',
        productSnapshotId: 'upsnap_20260510_abcd1234',
        steps: [
          {
            id: 'tstep_20260510_step0001',
            stepOrder: 1,
            sectionCode: 'BASE',
            stepName: '底妆',
            stepGoal: '均匀肤色',
            userInstruction: '少量多次上底妆。',
            visualChange: '肤色均匀。',
            aiDetectionArea: 'full_face',
            completionCriteria: '肤色均匀。',
            failureFeedback: '减少粉量。',
            editableByUser: true,
            nextStepCondition: '底妆完成。',
            productSlots: [
              {
                id: 'slot_20260510_abcd1234',
                slotCode: 'BASE_FOUNDATION',
                category: 'makeup',
                subCategory: 'foundation',
                requiredLevel: 'required',
                desiredEffect: ['base'],
                desiredFinish: ['dewy'],
                matchedProductId: 'prod-007',
                matchStatus: 'matched',
                matchReason: '子类命中',
                alternativeProductIds: [],
                fallbackInstruction: '没有粉底时使用遮瑕。',
              },
            ],
          },
        ],
      }),
    };
    const service = new RecommendationsService(
      prisma as never,
      {} as never,
      { summarize: jest.fn().mockReturnValue({
        status: 'unknown',
        certifiedCount: 0,
        notHalalCount: 0,
        unknownCount: 1,
        missingCount: 0,
        note: 'Halal 状态待确认。',
      }) } as never,
      { isEnabled: () => false, maybeGenerate: jest.fn() } as never,
      generationService as never,
    );

    const result = await service.generate({
      userId: 'user-001',
      scenario: '清透通勤妆',
      requirements: ['快速'],
    });

    expect(generationService.generate).toHaveBeenCalledWith({
      userId: 'user-001',
      rawUserInput: '清透通勤妆',
      generationSource: 'recommendation_generate',
      requirements: ['快速'],
    });
    expect(result).toMatchObject({
      generatedTemplateId: 'tmpl_20260510_abcd1234',
      productCoverageRate: 0.6,
      steps: [
        {
          id: 'tstep_20260510_step0001',
          matchedProductId: 'prod-007',
          missing: false,
        },
      ],
    });
  });
});
```

- [ ] **Step 2: Run compatibility test and verify failure**

Run:

```bash
cd backend
npm test -- recommendations.service.spec.ts --runInBand
```

Expected: FAIL because `RecommendationsService` does not inject `MakeupTemplateGenerationService`.

- [ ] **Step 3: Import module and inject service**

Modify `backend/src/recommendations/recommendations.module.ts`:

```ts
import { MakeupTemplatesModule } from '../makeup-templates/makeup-templates.module';
```

Set:

```ts
imports: [PrismaModule, MakeupTemplatesModule],
```

Modify `backend/src/recommendations/recommendations.service.ts` constructor to inject `MakeupTemplateGenerationService`:

```ts
import { MakeupTemplateGenerationService } from '../makeup-templates/makeup-template-generation.service';
```

```ts
constructor(
  private readonly prisma: PrismaService,
  private readonly recommendationMatchingService: RecommendationMatchingService,
  private readonly recommendationHalalService: RecommendationHalalService,
  private readonly recommendationLlmService: RecommendationLlmService,
  private readonly makeupTemplateGenerationService: MakeupTemplateGenerationService,
) {}
```

At the start of `generate(payload)`, replace the old template lookup path with:

```ts
const generatedTemplate = await this.makeupTemplateGenerationService.generate({
  userId: payload.userId,
  rawUserInput: payload.scenarioDetails?.trim() || payload.scenario.trim(),
  generationSource: 'recommendation_generate',
  requirements: payload.requirements ?? [],
});

return this.createRecommendationFromGeneratedTemplate(payload.userId, generatedTemplate);
```

Add private method:

```ts
private async createRecommendationFromGeneratedTemplate(
  userId: string,
  template: MakeupTemplateResponseDto,
) {
  const matchedSteps = template.steps.map((step) => {
    const matchedSlot = step.productSlots.find((slot) => slot.matchedProductId);
    const missing = step.productSlots.some(
      (slot) => slot.requiredLevel === 'required' && slot.matchStatus === 'missing',
    );

    return {
      id: step.id,
      sortOrder: step.stepOrder,
      title: step.stepName,
      instruction: step.userInstruction,
      matchedProductId: matchedSlot?.matchedProductId,
      alternativeProductIds: [
        ...new Set(step.productSlots.flatMap((slot) => slot.alternativeProductIds)),
      ],
      halalStatus: 'unknown' as const,
      reason: step.productSlots.map((slot) => slot.matchReason).join('；'),
      missing,
    };
  });
  const halalSummary = this.recommendationHalalService.summarize(matchedSteps);
  const missingStepCount = matchedSteps.filter((step) => step.missing).length;

  const recommendation = await this.prisma.recommendation.create({
    data: {
      id: `rec-${randomUUID().slice(0, 8)}`,
      userId,
      generatedTemplateId: template.id,
      scenario: template.primaryScene,
      title: template.displayName,
      summary: `${template.overallEffect}，已有产品覆盖率 ${Math.round(template.productCoverageRate * 100)}%，缺失 ${missingStepCount} 个步骤。`,
      halalStatus: halalSummary.status,
      certifiedCount: halalSummary.certifiedCount,
      notHalalCount: halalSummary.notHalalCount,
      unknownCount: halalSummary.unknownCount,
      missingCount: halalSummary.missingCount,
      halalNote: halalSummary.note,
      reasons: template.personalizationReasons,
      steps: {
        create: matchedSteps.map((step) => ({
          id: `rec-step-${randomUUID().slice(0, 8)}`,
          stepId: step.id,
          sortOrder: step.sortOrder,
          title: step.title,
          instruction: step.instruction,
          matchedProductId: step.matchedProductId,
          alternativeProductIds: step.alternativeProductIds,
          halalStatus: step.halalStatus,
          reason: step.reason,
          missing: step.missing,
        })),
      },
    },
    include: {
      steps: {
        orderBy: {
          sortOrder: 'asc',
        },
      },
    },
  });

  return {
    ...mapRecommendation(recommendation),
    generatedTemplateId: template.id,
    productCoverageRate: template.productCoverageRate,
    missingProductTypes: template.missingProductTypes,
  };
}
```

- [ ] **Step 4: Extend DTOs and mapper**

Modify `backend/src/recommendations/dto/recommendation-response.dto.ts`:

```ts
  @ApiPropertyOptional({ example: 'tmpl_20260510_abcd1234' })
  generatedTemplateId?: string;

  @ApiPropertyOptional({ example: 0.6 })
  productCoverageRate?: number;

  @ApiPropertyOptional({ example: ['blush', 'lip'], type: [String] })
  missingProductTypes?: string[];
```

Modify `backend/src/recommendations/dto/recommendation-step-response.dto.ts` to add optional fields:

```ts
  @ApiPropertyOptional({ example: 'BASE' })
  sectionCode?: string;

  @ApiPropertyOptional({ example: '完成清透均匀的底妆' })
  stepGoal?: string;
```

Modify `backend/src/recommendations/recommendation.mapper.ts` so regular DB reads include `generatedTemplateId` if present:

```ts
generatedTemplateId: recommendation.generatedTemplateId ?? undefined,
```

- [ ] **Step 5: Run recommendation tests and commit**

Run:

```bash
cd backend
npm test -- recommendations.service.spec.ts makeup-template-generation.service.spec.ts --runInBand
```

Expected: PASS.

Commit:

```bash
git add backend/src/recommendations backend/src/makeup-templates
git commit -m "feat: route recommendations through generated templates"
```

---

### Task 6: Record Template Events from Execution Progress

**Files:**
- Modify: `backend/src/executions/executions.module.ts`
- Modify: `backend/src/executions/executions.service.ts`
- Create: `backend/src/executions/executions-template-events.spec.ts`

- [ ] **Step 1: Write failing execution event test**

Create `backend/src/executions/executions-template-events.spec.ts`:

```ts
import { ExecutionsService } from './executions.service';

describe('ExecutionsService template events', () => {
  it('records completion and skip events for generated template recommendations', async () => {
    const eventService = {
      record: jest.fn().mockResolvedValue(undefined),
    };
    const prisma = {
      execution: {
        findUnique: jest.fn().mockResolvedValue({
          id: 'exec-001',
          userId: 'user-001',
          recommendationId: 'rec-001',
          selectedProducts: {},
          substitutedProducts: {},
          currentStepId: 'tstep-1',
          completedStepIds: [],
          skippedStepIds: [],
          status: 'draft',
          satisfaction: null,
          notes: null,
          createdAt: new Date('2026-05-10T00:00:00.000Z'),
          updatedAt: new Date('2026-05-10T00:00:00.000Z'),
          recommendation: {
            id: 'rec-001',
            userId: 'user-001',
            generatedTemplateId: 'tmpl_20260510_abcd1234',
            scenario: 'COMMUTE',
            title: '清透通勤妆',
            steps: [{ stepId: 'tstep-1' }, { stepId: 'tstep-2' }],
          },
        }),
        update: jest.fn().mockResolvedValue({
          id: 'exec-001',
          userId: 'user-001',
          recommendationId: 'rec-001',
          selectedProducts: {},
          substitutedProducts: {},
          currentStepId: 'tstep-2',
          completedStepIds: ['tstep-1'],
          skippedStepIds: ['tstep-2'],
          status: 'draft',
          satisfaction: null,
          notes: null,
          createdAt: new Date('2026-05-10T00:00:00.000Z'),
          updatedAt: new Date('2026-05-10T00:00:00.000Z'),
          recommendation: {
            id: 'rec-001',
            scenario: 'COMMUTE',
            title: '清透通勤妆',
          },
        }),
      },
      product: {
        findMany: jest.fn().mockResolvedValue([]),
      },
    };
    const service = new ExecutionsService(prisma as never, eventService as never);

    await service.updateProgress('exec-001', {
      currentStepId: 'tstep-2',
      completedStepIds: ['tstep-1'],
      skippedStepIds: ['tstep-2'],
    });

    expect(eventService.record).toHaveBeenCalledWith(expect.objectContaining({
      userId: 'user-001',
      templateId: 'tmpl_20260510_abcd1234',
      stepId: 'tstep-1',
      eventName: 'step_completed',
    }));
    expect(eventService.record).toHaveBeenCalledWith(expect.objectContaining({
      userId: 'user-001',
      templateId: 'tmpl_20260510_abcd1234',
      stepId: 'tstep-2',
      eventName: 'step_skipped',
    }));
  });
});
```

- [ ] **Step 2: Run event test and verify failure**

Run:

```bash
cd backend
npm test -- executions-template-events.spec.ts --runInBand
```

Expected: FAIL because `ExecutionsService` only accepts `PrismaService`.

- [ ] **Step 3: Import template module in executions module**

Modify `backend/src/executions/executions.module.ts`:

```ts
import { MakeupTemplatesModule } from '../makeup-templates/makeup-templates.module';
```

Set:

```ts
imports: [PrismaModule, MakeupTemplatesModule],
```

- [ ] **Step 4: Inject event service and record deltas**

Modify `backend/src/executions/executions.service.ts` constructor:

```ts
constructor(
  private readonly prisma: PrismaService,
  private readonly templateEventService: MakeupTemplateEventService,
) {}
```

Import:

```ts
import { MakeupTemplateEventService } from '../makeup-templates/makeup-template-event.service';
```

After the `execution.update` call in `updateProgress`, call:

```ts
await this.recordTemplateProgressEvents(execution, payload);
```

Add:

```ts
private async recordTemplateProgressEvents(
  execution: {
    userId: string;
    recommendation: {
      generatedTemplateId?: string | null;
    };
    completedStepIds: string[];
    skippedStepIds: string[];
  },
  payload: UpdateExecutionProgressDto,
) {
  const templateId = execution.recommendation.generatedTemplateId;
  if (!templateId) {
    return;
  }

  const previousCompleted = new Set(execution.completedStepIds);
  const previousSkipped = new Set(execution.skippedStepIds);
  const nextCompleted = payload.completedStepIds ?? execution.completedStepIds;
  const nextSkipped = payload.skippedStepIds ?? execution.skippedStepIds;

  for (const stepId of nextCompleted) {
    if (!previousCompleted.has(stepId)) {
      await this.templateEventService.record({
        userId: execution.userId,
        templateId,
        stepId,
        eventName: 'step_completed',
        payload: { completionMethod: 'manual_or_ai' },
      });
    }
  }

  for (const stepId of nextSkipped) {
    if (!previousSkipped.has(stepId)) {
      await this.templateEventService.record({
        userId: execution.userId,
        templateId,
        stepId,
        eventName: 'step_skipped',
        payload: { skipReason: 'user_action' },
      });
    }
  }
}
```

In `submitFeedback`, after updating an execution with a generated template, record:

```ts
await this.templateEventService.record({
  userId: existing.userId,
  templateId: existing.recommendation.generatedTemplateId,
  eventName: 'template_feedback_submitted',
  payload: {
    satisfactionScore: payload.satisfaction,
    notesProvided: Boolean(payload.notes),
    status: payload.status,
  },
});
```

Guard the call with `if (existing.recommendation.generatedTemplateId)`.

- [ ] **Step 5: Run execution event tests and commit**

Run:

```bash
cd backend
npm test -- executions-template-events.spec.ts --runInBand
```

Expected: PASS.

Commit:

```bash
git add backend/src/executions backend/src/makeup-templates
git commit -m "feat: record generated template execution events"
```

---

### Task 7: Add Frontend Type Compatibility

**Files:**
- Modify: `frontend/types/recommendation.ts`
- Modify: `frontend/services/recommendationService.ts`

- [ ] **Step 1: Extend frontend recommendation types**

Modify `frontend/types/recommendation.ts`:

```ts
export interface RecommendationResultProductSlot {
  id: string;
  slotCode: string;
  category: ProductCategory;
  subCategory?: string;
  requiredLevel: 'required' | 'recommended' | 'optional';
  desiredEffect: string[];
  desiredFinish: string[];
  matchedUserProductId?: string;
  matchedProductId?: string;
  matchStatus: 'matched' | 'substitutable' | 'missing';
  matchReason: string;
  alternativeProductIds: string[];
  fallbackInstruction: string;
}
```

Add optional fields to `RecommendationResultStep`:

```ts
  sectionCode?: string;
  stepGoal?: string;
  visualChange?: string;
  aiDetectionArea?: string;
  completionCriteria?: string;
  failureFeedback?: string;
  productSlots?: RecommendationResultProductSlot[];
```

Add optional fields to `RecommendationResult`:

```ts
  generatedTemplateId?: string;
  productCoverageRate?: number;
  missingProductTypes?: string[];
```

- [ ] **Step 2: Preserve optional fields in service fallback payload**

Modify `frontend/services/recommendationService.ts` only if TypeScript complains about result shape. Keep the current fallback behavior. No page should require the new fields.

- [ ] **Step 3: Run frontend lint**

Run:

```bash
cd frontend
npm run lint
```

Expected: lint completes without TypeScript or ESLint errors caused by the new fields.

- [ ] **Step 4: Commit frontend compatibility**

```bash
git add frontend/types/recommendation.ts frontend/services/recommendationService.ts
git commit -m "feat: accept generated template recommendation fields"
```

---

### Task 8: Verification

**Files:**
- No new source files.

- [ ] **Step 1: Run backend unit tests for new modules**

Run:

```bash
cd backend
npm test -- makeup-template-intent.service.spec.ts makeup-template-slot-matching.service.spec.ts makeup-template-generation.service.spec.ts makeup-template-event.service.spec.ts recommendations.service.spec.ts executions-template-events.spec.ts --runInBand
```

Expected: PASS.

- [ ] **Step 2: Run full backend tests**

Run:

```bash
cd backend
npm test -- --runInBand
```

Expected: PASS.

- [ ] **Step 3: Run backend build**

Run:

```bash
cd backend
npm run build
```

Expected: Nest build exits 0.

- [ ] **Step 4: Run Prisma migration and seed in the configured dev database**

Run:

```bash
cd backend
npm run db:migrate
npm run db:seed
```

Expected: migrations apply and seed completes. Existing users, products, recommendation templates, generated template tables, and old recommendation tables are usable.

- [ ] **Step 5: Smoke test template generation API**

Start backend on a free port if not already running:

```bash
cd backend
HOST=0.0.0.0 PORT=13001 npm run start:dev
```

In another shell:

```bash
curl -fsS http://127.0.0.1:13001/makeup-templates/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "userId":"user-001",
    "rawUserInput":"明天上班想画清透又显气色的妆，最好用我已有的产品",
    "generationSource":"manual_smoke",
    "requirements":["快速","已有产品优先"]
  }'
```

Expected: JSON contains `id` beginning with `tmpl_`, `steps` length 5, and each step contains `productSlots`.

- [ ] **Step 6: Smoke test recommendation compatibility API**

Run:

```bash
curl -fsS http://127.0.0.1:13001/recommendations/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "userId":"user-001",
    "scenario":"明天上班想画清透又显气色的妆，最好用我已有的产品",
    "requirements":["快速"]
  }'
```

Expected: JSON contains `steps`, `reasons`, `generatedTemplateId`, and `productCoverageRate`. Existing frontend fields `steps[*].matchedProductId`, `steps[*].alternativeProductIds`, and `steps[*].missing` are present.

- [ ] **Step 7: Run frontend lint**

Run:

```bash
cd frontend
npm run lint
```

Expected: lint exits 0.

- [ ] **Step 8: Check Git status**

Run:

```bash
git status --short
cd backend && git status --short
cd ../frontend && git status --short
```

Expected: only intended source changes are present or all implementation commits have been made. The product document `docs/妆容生成搭建模板.docx` remains untracked unless the user explicitly asks to commit it.
