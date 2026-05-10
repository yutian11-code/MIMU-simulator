# Intelligent Template Library Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the MMU standard template library foundation and hybrid embedding/reranker-style template matching algorithm while preserving the current generated-template and recommendation flows.

**Architecture:** Add a focused template-library layer under `backend/src/makeup-templates/template-library/`. Keep standard templates as versioned seed data in the first implementation, add Prisma trace/link fields for generated results, and route `MakeupTemplateGenerationService` through a new matcher that supports model clients when configured and deterministic fallback when GPUs or model services are unavailable.

**Tech Stack:** NestJS 11, TypeScript, Prisma 7, Jest, existing `makeup-templates` module, optional OpenAI-compatible embedding/reranker HTTP services, local deterministic fallback scoring.

---

## File Structure

Create:

- `backend/src/makeup-templates/template-library/standard-template-library.types.ts`
  Defines standard style, template, step block, product slot, match profile, candidate, trace, and score types.
- `backend/src/makeup-templates/template-library/standard-template-library.data.ts`
  Versioned seed data extracted from the MMU standard doc: style families, representative templates, 14 standard steps compressed into executable step blocks, product slot specs, difficulty scores, and operation areas.
- `backend/src/makeup-templates/template-library/standard-template-library.service.ts`
  Read-only access to standard styles/templates, lookup by id, and lightweight validation helpers.
- `backend/src/makeup-templates/template-library/template-match-profile.service.ts`
  Converts parsed user intent, user profile, products, and optional reference metadata into `TemplateMatchProfile`.
- `backend/src/makeup-templates/template-library/template-model-client.service.ts`
  Optional HTTP client for embedding and reranker services. It must be disabled by default and return explicit unavailable status when not configured.
- `backend/src/makeup-templates/template-library/template-matching.service.ts`
  Multi-route recall, deterministic semantic fallback, optional reranker integration, scoring formula, degradation state, and match trace payload construction.
- `backend/src/makeup-templates/template-library/template-blueprint-adapter.service.ts`
  Converts a matched standard template into current `MakeupStepBlueprint[]`, including 3/4/5-step compression and face/skin adjustments.
- `backend/src/makeup-templates/template-library/template-library.controller.ts`
  Guarded internal endpoints for styles and match-debug.
- `backend/src/makeup-templates/template-library/*.spec.ts`
  Unit tests for data validation, profile creation, model-client fallback, matching, and blueprint adaptation.
- `backend/prisma/migrations/20260510130000_add_template_library_matching/migration.sql`
  Adds generated-template match link fields and `template_match_traces`.
- `eval/template_matching/cases.json`
  Offline case set for representative text inputs and expected style/template outcomes.
- `eval/template_matching/run_template_matching_eval.py`
  Local HTTP smoke evaluator for `/makeup-template-library/match-debug`.

Modify:

- `backend/prisma/schema.prisma`
  Add `TemplateMatchTrace`; add `sourceStandardTemplateId`, `matchScore`, and `matchTraceId` to `GeneratedMakeupTemplate`; add `operationAreas` to `GeneratedTemplateStep`.
- `backend/src/makeup-templates/makeup-template-id.util.ts`
  Add `matchTrace` ID prefix support.
- `backend/src/makeup-templates/makeup-template.types.ts`
  Extend blueprint and slot types with standard template metadata, operation areas, difficulty score, acceptable subcategories, and substitute slot codes.
- `backend/src/makeup-templates/makeup-template.mapper.ts`
  Return match metadata and operation areas.
- `backend/src/makeup-templates/dto/makeup-template-response.dto.ts`
  Document match metadata and operation areas in Swagger DTOs.
- `backend/src/makeup-templates/makeup-template-generation.service.ts`
  Replace hard-coded five-step blueprint selection with the matcher and adapter.
- `backend/src/makeup-templates/makeup-template-slot-matching.service.ts`
  Use standard slot specs for acceptable subcategories, color/finish/effect matching, and substitutions.
- `backend/src/makeup-templates/makeup-templates.module.ts`
  Register and export new template-library services and controller.
- `backend/src/makeup-templates/makeup-template-generation.service.spec.ts`
  Update generation tests to assert hybrid template match metadata and trace.
- `backend/src/makeup-templates/makeup-template-slot-matching.service.spec.ts`
  Add slot substitution and richer tag scoring tests.
- `backend/src/recommendations/recommendations.service.spec.ts`
  Keep compatibility expectations for `/recommendations/generate`.
- `docs/team-runbook.md`
  Add model/GPU behavior notes for the new matcher.

## Task 1: Persist Match Trace Links

**Files:**
- Modify: `backend/prisma/schema.prisma`
- Modify: `backend/src/makeup-templates/makeup-template-id.util.ts`
- Create: `backend/prisma/migrations/20260510130000_add_template_library_matching/migration.sql`
- Test: Prisma validation and focused makeup-template generation test

- [ ] **Step 1: Update Prisma schema**

Add these fields to `GeneratedMakeupTemplate` after `templateReuseKey`:

```prisma
  sourceStandardTemplateId String?              @map("source_standard_template_id") @db.VarChar(80)
  matchScore               Float?               @map("match_score")
  matchTraceId             String?              @map("match_trace_id") @db.VarChar(50)
  matchTrace               TemplateMatchTrace?  @relation(fields: [matchTraceId], references: [id], onDelete: SetNull)
```

Add this relation to `User` near `templateEvents`:

```prisma
  templateMatchTraces      TemplateMatchTrace[]
```

Add this field to `GeneratedTemplateStep` after `aiDetectionArea`:

```prisma
  operationAreas     String[]                @map("operation_areas") @default([])
```

Add this model near `TemplateEvent`:

```prisma
model TemplateMatchTrace {
  id                       String                    @id @db.VarChar(50)
  userId                   String                    @map("user_id") @db.VarChar(50)
  requestId                String?                   @map("request_id") @db.VarChar(50)
  rawUserInput             String                    @map("raw_user_input") @db.Text
  profile                  Json
  selectedTemplateId       String?                   @map("selected_template_id") @db.VarChar(80)
  selectedTemplateScore    Float?                    @map("selected_template_score")
  candidateCount           Int                       @map("candidate_count")
  candidates               Json
  scoreBreakdown           Json                      @map("score_breakdown")
  modelStatus              Json                      @map("model_status")
  degraded                 Boolean                   @default(false)
  createdAt                DateTime                  @map("created_at") @default(now())
  user                     User                      @relation(fields: [userId], references: [id], onDelete: Cascade)
  generatedTemplates       GeneratedMakeupTemplate[]

  @@index([userId, createdAt])
  @@index([selectedTemplateId])
  @@map("template_match_traces")
}
```

- [ ] **Step 2: Add SQL migration**

Create `backend/prisma/migrations/20260510130000_add_template_library_matching/migration.sql` with:

```sql
-- AlterTable
ALTER TABLE "generated_makeup_templates"
ADD COLUMN "source_standard_template_id" VARCHAR(80),
ADD COLUMN "match_score" DOUBLE PRECISION,
ADD COLUMN "match_trace_id" VARCHAR(50);

-- AlterTable
ALTER TABLE "generated_template_steps"
ADD COLUMN "operation_areas" TEXT[] DEFAULT ARRAY[]::TEXT[];

-- CreateTable
CREATE TABLE "template_match_traces" (
    "id" VARCHAR(50) NOT NULL,
    "user_id" VARCHAR(50) NOT NULL,
    "request_id" VARCHAR(50),
    "raw_user_input" TEXT NOT NULL,
    "profile" JSONB NOT NULL,
    "selected_template_id" VARCHAR(80),
    "selected_template_score" DOUBLE PRECISION,
    "candidate_count" INTEGER NOT NULL,
    "candidates" JSONB NOT NULL,
    "score_breakdown" JSONB NOT NULL,
    "model_status" JSONB NOT NULL,
    "degraded" BOOLEAN NOT NULL DEFAULT false,
    "created_at" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "template_match_traces_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "template_match_traces_user_id_created_at_idx" ON "template_match_traces"("user_id", "created_at");

-- CreateIndex
CREATE INDEX "template_match_traces_selected_template_id_idx" ON "template_match_traces"("selected_template_id");

-- CreateIndex
CREATE INDEX "generated_makeup_templates_source_standard_template_id_idx" ON "generated_makeup_templates"("source_standard_template_id");

-- CreateIndex
CREATE INDEX "generated_makeup_templates_match_trace_id_idx" ON "generated_makeup_templates"("match_trace_id");

-- AddForeignKey
ALTER TABLE "template_match_traces" ADD CONSTRAINT "template_match_traces_user_id_fkey" FOREIGN KEY ("user_id") REFERENCES "users"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "generated_makeup_templates" ADD CONSTRAINT "generated_makeup_templates_match_trace_id_fkey" FOREIGN KEY ("match_trace_id") REFERENCES "template_match_traces"("id") ON DELETE SET NULL ON UPDATE CASCADE;
```

- [ ] **Step 3: Validate Prisma schema**

Run:

```bash
cd backend
npx prisma validate
```

Expected: `The schema at prisma/schema.prisma is valid`.

- [ ] **Step 4: Extend template ID factory**

In `backend/src/makeup-templates/makeup-template-id.util.ts`, add `matchTrace` to the `MakeupTemplateIdKind` union:

```ts
export type MakeupTemplateIdKind =
  | 'request'
  | 'conditionSnapshot'
  | 'productSnapshot'
  | 'template'
  | 'step'
  | 'slot'
  | 'event'
  | 'matchTrace';
```

Add this entry to `MAKEUP_TEMPLATE_ID_PREFIXES`:

```ts
  matchTrace: 'mtrace',
```

- [ ] **Step 5: Run focused generation test**

Run:

```bash
cd backend
npm test -- makeup-templates/makeup-template-generation.service.spec.ts --runInBand
```

Expected: existing generation tests still pass before integration changes, and TypeScript accepts the updated ID kind.

- [ ] **Step 6: Commit**

```bash
git add backend/prisma/schema.prisma backend/prisma/migrations/20260510130000_add_template_library_matching/migration.sql backend/src/makeup-templates/makeup-template-id.util.ts
git commit -m "feat: persist template match traces"
```

## Task 2: Add Standard Template Library Data

**Files:**
- Create: `backend/src/makeup-templates/template-library/standard-template-library.types.ts`
- Create: `backend/src/makeup-templates/template-library/standard-template-library.data.ts`
- Create: `backend/src/makeup-templates/template-library/standard-template-library.service.ts`
- Test: `backend/src/makeup-templates/template-library/standard-template-library.service.spec.ts`

- [ ] **Step 1: Write failing service tests**

Create `backend/src/makeup-templates/template-library/standard-template-library.service.spec.ts`:

```ts
import { StandardTemplateLibraryService } from './standard-template-library.service';

describe('StandardTemplateLibraryService', () => {
  let service: StandardTemplateLibraryService;

  beforeEach(() => {
    service = new StandardTemplateLibraryService();
  });

  it('exposes the eight standard style families from the MMU template standard', () => {
    expect(service.listStyleFamilies()).toEqual([
      'DAILY_COMMUTE',
      'KOREAN_JAPANESE_GIRL',
      'ELEGANT_LUXURY',
      'ASIAN_MIXED',
      'CHINESE_STYLE',
      'WESTERN',
      'STAGE_CREATIVE',
      'SPECIFIC_VISUAL',
    ]);
  });

  it('contains active templates with executable step blocks and product slots', () => {
    const templates = service.listActiveTemplates();

    expect(templates.length).toBeGreaterThanOrEqual(8);
    expect(templates).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          id: 'std_daily_clear_commute',
          styleFamily: 'DAILY_COMMUTE',
          primaryScene: 'COMMUTE',
        }),
        expect.objectContaining({
          id: 'std_specific_y2k_spicy',
          styleFamily: 'SPECIFIC_VISUAL',
        }),
      ]),
    );
    expect(
      templates.every(
        (template) =>
          template.stepBlocks.length >= 3 &&
          template.productSlots.some((slot) => slot.requiredLevel === 'required'),
      ),
    ).toBe(true);
  });

  it('looks up a template by id and returns undefined for an unknown id', () => {
    expect(service.getTemplateById('std_daily_clear_commute')?.displayName).toBe(
      '清透通勤标准模板',
    );
    expect(service.getTemplateById('missing-template')).toBeUndefined();
  });
});
```

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/standard-template-library.service.spec.ts --runInBand
```

Expected: fail because the service does not exist.

- [ ] **Step 2: Create library types**

Create `backend/src/makeup-templates/template-library/standard-template-library.types.ts`:

```ts
import type { ProductCategory, User, UserProduct } from '@prisma/client';

export type StandardStyleFamily =
  | 'DAILY_COMMUTE'
  | 'KOREAN_JAPANESE_GIRL'
  | 'ELEGANT_LUXURY'
  | 'ASIAN_MIXED'
  | 'CHINESE_STYLE'
  | 'WESTERN'
  | 'STAGE_CREATIVE'
  | 'SPECIFIC_VISUAL';

export type StandardMakeupStyle = {
  id: string;
  displayName: string;
  family: StandardStyleFamily;
  aliases: string[];
  positiveTags: string[];
  negativeTags: string[];
  baseFinish: string;
  colorPalette: string[];
  intensityLevel: number;
  defaultDifficulty: number;
  typicalScenes: string[];
};

export type StandardStepBlock = {
  id: string;
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
  difficultyScore: number;
};

export type StandardProductSlotSpec = {
  id: string;
  stepBlockId: string;
  slotCode: string;
  category: ProductCategory;
  subCategory?: string;
  acceptableSubCategories: string[];
  substituteSlotCodes: string[];
  requiredLevel: 'required' | 'recommended' | 'optional';
  desiredEffect: string[];
  desiredColorFamily?: string;
  desiredFinish: string[];
  fallbackInstruction: string;
};

export type StandardMakeupTemplate = {
  id: string;
  displayName: string;
  styleId: string;
  styleFamily: StandardStyleFamily;
  primaryScene: string;
  styleTags: string[];
  effectTags: string[];
  difficultyBaseScore: number;
  minSkillLevel: 'beginner' | 'normal' | 'advanced';
  estimatedTimeMinutes: number;
  templateDescription: string;
  visualDescription: string;
  isActive: boolean;
  stepBlocks: StandardStepBlock[];
  productSlots: StandardProductSlotSpec[];
};

export type TemplateMatchProfile = {
  rawUserInput: string;
  scene: string;
  styleTags: string[];
  effectTags: string[];
  constraints: string[];
  skinType?: string;
  faceShape?: string;
  skillLevel: 'beginner' | 'normal' | 'advanced';
  preferredProductCategories: string[];
  referenceImageFeatures?: {
    baseFinish?: string;
    eyeIntensity?: number;
    blushPlacement?: string;
    lipColorFamily?: string;
  };
};

export type TemplateMatchScoreBreakdown = {
  embeddingSimilarity: number;
  rerankerRelevance: number;
  styleMatch: number;
  sceneMatch: number;
  productCoverage: number;
  userProfileFit: number;
  historyPreference: number;
  difficultyPenalty: number;
  missingRequiredSlotPenalty: number;
};

export type TemplateMatchCandidate = {
  template: StandardMakeupTemplate;
  score: number;
  reasons: string[];
  breakdown: TemplateMatchScoreBreakdown;
};

export type TemplateMatchResult = {
  profile: TemplateMatchProfile;
  selected: TemplateMatchCandidate;
  candidates: TemplateMatchCandidate[];
  modelStatus: {
    embedding: 'configured' | 'unavailable' | 'failed';
    reranker: 'configured' | 'unavailable' | 'failed';
    vlm: 'skipped' | 'configured' | 'failed';
  };
  degraded: boolean;
};

export type UserProductForTemplateMatching = UserProduct & {
  product: {
    category: ProductCategory;
    subCategory: string;
    tags: string[];
  };
};

export type TemplateMatchBuildInput = {
  user: User;
  rawUserInput: string;
  scene: string;
  styleTags: string[];
  effectTags: string[];
  constraints: string[];
  products: UserProductForTemplateMatching[];
};
```

- [ ] **Step 3: Add standard data**

Create `backend/src/makeup-templates/template-library/standard-template-library.data.ts` with this representative first library. Keep ids stable because generated templates will reference them:

```ts
import type {
  StandardMakeupStyle,
  StandardMakeupTemplate,
} from './standard-template-library.types';

export const STANDARD_MAKEUP_STYLES: StandardMakeupStyle[] = [
  {
    id: 'style_daily_clear',
    displayName: '日常通勤妆容',
    family: 'DAILY_COMMUTE',
    aliases: ['伪素颜妆', '通勤淡妆', '清透裸妆', '白开水妆', '日杂妆'],
    positiveTags: ['CLEAR', 'NATURAL', 'LOW_INTENSITY', 'GOOD_COMPLEXION'],
    negativeTags: ['GLAM', 'STAGE', 'HEAVY_EYE'],
    baseFinish: 'natural_dewy',
    colorPalette: ['milk_tea', 'soft_pink', 'nude'],
    intensityLevel: 1,
    defaultDifficulty: 1.4,
    typicalScenes: ['DAILY', 'COMMUTE', 'INTERVIEW'],
  },
  {
    id: 'style_kj_sweet',
    displayName: '韩系/日系少女风妆容',
    family: 'KOREAN_JAPANESE_GIRL',
    aliases: ['甜妹妆', '初恋妆', '韩系水光妆', '纯欲妆'],
    positiveTags: ['SWEET', 'DEWY', 'GOOD_COMPLEXION', 'SOFT_EYE'],
    negativeTags: ['MATTE_HEAVY', 'SHARP_CONTOUR'],
    baseFinish: 'dewy',
    colorPalette: ['pink', 'peach', 'coral'],
    intensityLevel: 2,
    defaultDifficulty: 1.7,
    typicalScenes: ['DATE', 'DAILY', 'CAMERA'],
  },
  {
    id: 'style_elegant_luxury',
    displayName: '轻熟千金妆容',
    family: 'ELEGANT_LUXURY',
    aliases: ['轻熟气质妆', '知性优雅妆', '贵气千金妆', '法式慵懒妆'],
    positiveTags: ['GENTLE', 'ELEGANT', 'MATTE', 'LOW_SATURATION'],
    negativeTags: ['CUTE_ONLY', 'NEON_COLOR'],
    baseFinish: 'satin_matte',
    colorPalette: ['rose_brown', 'taupe', 'bean_paste'],
    intensityLevel: 2,
    defaultDifficulty: 1.9,
    typicalScenes: ['COMMUTE', 'DATE', 'INTERVIEW'],
  },
  {
    id: 'style_asian_mixed',
    displayName: '亚裔混血妆容',
    family: 'ASIAN_MIXED',
    aliases: ['亚裔妆', '泰式轻妆', '泰式浓妆', '混血感妆容'],
    positiveTags: ['GLAM', 'CONTOUR', 'DEFINED_EYE'],
    negativeTags: ['NO_CONTOUR'],
    baseFinish: 'matte',
    colorPalette: ['warm_brown', 'terracotta', 'nude'],
    intensityLevel: 3,
    defaultDifficulty: 2.2,
    typicalScenes: ['CAMERA', 'DATE'],
  },
  {
    id: 'style_chinese',
    displayName: '国风妆容',
    family: 'CHINESE_STYLE',
    aliases: ['新中式妆', '中式古典妆', '复古港风妆', '昭和复古妆'],
    positiveTags: ['RETRO', 'RED_LIP', 'DEFINED_BROW'],
    negativeTags: ['PALE_LIP'],
    baseFinish: 'velvet',
    colorPalette: ['red', 'brown_red', 'warm_beige'],
    intensityLevel: 3,
    defaultDifficulty: 2.1,
    typicalScenes: ['CAMERA', 'DATE', 'STAGE'],
  },
  {
    id: 'style_western',
    displayName: '欧美系妆容',
    family: 'WESTERN',
    aliases: ['烟熏妆', '轻欧美妆', '欧美截断', '美式复古妆'],
    positiveTags: ['GLAM', 'MATTE', 'CUT_CREASE', 'SHARP_CONTOUR'],
    negativeTags: ['NO_EYELINER'],
    baseFinish: 'matte',
    colorPalette: ['brown', 'black', 'nude'],
    intensityLevel: 4,
    defaultDifficulty: 2.6,
    typicalScenes: ['CAMERA', 'STAGE'],
  },
  {
    id: 'style_stage_creative',
    displayName: '舞台创意妆容',
    family: 'STAGE_CREATIVE',
    aliases: ['朋克妆', '万圣节创意妆', '舞台妆', 'cosplay妆', '哥特妆'],
    positiveTags: ['STAGE', 'CREATIVE', 'HIGH_INTENSITY'],
    negativeTags: ['LOW_INTENSITY'],
    baseFinish: 'long_lasting',
    colorPalette: ['black', 'silver', 'red', 'purple'],
    intensityLevel: 5,
    defaultDifficulty: 3.2,
    typicalScenes: ['STAGE', 'CAMERA'],
  },
  {
    id: 'style_specific_y2k',
    displayName: '特定视觉妆容',
    family: 'SPECIFIC_VISUAL',
    aliases: ['上镜妆', '亚比妆', '女团妆', '盐系妆', '森系妆', 'Y2K辣妹妆', '英气少女妆'],
    positiveTags: ['CAMERA', 'Y2K', 'IDOL', 'VISUAL'],
    negativeTags: ['PLAIN_ONLY'],
    baseFinish: 'camera_ready',
    colorPalette: ['pink', 'silver', 'brown', 'clear_gloss'],
    intensityLevel: 4,
    defaultDifficulty: 2.4,
    typicalScenes: ['CAMERA', 'DATE', 'STAGE'],
  },
];

const fiveStepBlocks = [
  {
    id: 'block_base',
    stepOrder: 1,
    sectionCode: 'BASE',
    stepName: '妆前与底妆',
    standardStepCodes: ['SKIN_PREP', 'SUNSCREEN_PRIMER', 'CONCEALER', 'FOUNDATION', 'SETTING'],
    operationAreas: ['full_face', 't_zone', 'u_zone'],
    stepGoal: '完成服帖均匀的底妆',
    instructionTemplate: '先完成妆前保湿，再少量多次从面中向外上底妆，T 区薄定妆。',
    visualChange: '肤色更均匀，面中干净，底妆边缘自然。',
    aiDetectionArea: 'full_face',
    completionCriteria: '面中肤色均匀，鼻翼嘴角没有明显卡粉或色块。',
    failureFeedback: '底妆偏厚时用湿粉扑轻拍边缘，T 区只补少量散粉。',
    nextStepCondition: '底妆均匀后进入眉毛步骤。',
    difficultyScore: 1.2,
  },
  {
    id: 'block_brow',
    stepOrder: 2,
    sectionCode: 'BROW',
    stepName: '眉毛',
    standardStepCodes: ['BROW'],
    operationAreas: ['brows'],
    stepGoal: '补齐眉形并保留自然毛流',
    instructionTemplate: '顺毛流填补空缺，眉尾自然拉长，眉头用刷子晕淡。',
    visualChange: '眉形更完整，五官精神感提升。',
    aiDetectionArea: 'brows',
    completionCriteria: '两侧眉形高度接近，眉头不过重。',
    failureFeedback: '眉头过重时用螺旋刷向上梳开。',
    nextStepCondition: '眉形平衡后进入眼妆步骤。',
    difficultyScore: 1.8,
  },
  {
    id: 'block_eye',
    stepOrder: 3,
    sectionCode: 'EYE',
    stepName: '眼妆',
    standardStepCodes: ['EYESHADOW', 'LASH', 'EYELINER'],
    operationAreas: ['eye_area'],
    stepGoal: '增强眼部层次并保持边界干净',
    instructionTemplate: '浅色铺底，眼尾少量加深，夹翘睫毛后加强睫毛根部。',
    visualChange: '眼睛更有神，眼妆层次自然。',
    aiDetectionArea: 'eyes',
    completionCriteria: '眼影边界柔和，左右眼强度接近。',
    failureFeedback: '眼影过深时用干净刷子向外晕染。',
    nextStepCondition: '眼妆干净后进入气色步骤。',
    difficultyScore: 1.8,
  },
  {
    id: 'block_cheek',
    stepOrder: 4,
    sectionCode: 'CHEEK',
    stepName: '腮红与轮廓',
    standardStepCodes: ['CONTOUR', 'HIGHLIGHT', 'BLUSH'],
    operationAreas: ['cheeks', 'jawline', 'nose_area'],
    stepGoal: '提升气色并修饰面部轮廓',
    instructionTemplate: '腮红从苹果肌偏上位置少量多次晕染，修容和高光只保留自然过渡。',
    visualChange: '面中更饱满，脸部轮廓更清晰。',
    aiDetectionArea: 'cheeks',
    completionCriteria: '腮红左右位置接近，颜色不低于鼻翼。',
    failureFeedback: '腮红过重时用底妆余量轻压边缘。',
    nextStepCondition: '气色自然后进入唇妆步骤。',
    difficultyScore: 1.5,
  },
  {
    id: 'block_lip_finish',
    stepOrder: 5,
    sectionCode: 'LIP',
    stepName: '唇妆与定妆',
    standardStepCodes: ['LIP', 'SECOND_SETTING'],
    operationAreas: ['lips', 'full_face'],
    stepGoal: '完成协调唇色并固定整体妆效',
    instructionTemplate: '唇色从内侧向外晕染，最后全脸轻喷定妆或局部补粉。',
    visualChange: '唇色均匀，整体妆容完整。',
    aiDetectionArea: 'lips',
    completionCriteria: '唇色均匀，边缘自然，和腮红色系协调。',
    failureFeedback: '唇色过重时用纸巾轻抿，再用指腹晕开边缘。',
    nextStepCondition: '唇色完成后结束模板执行。',
    difficultyScore: 1.5,
  },
];

function slotsFor(styleId: string) {
  return [
    {
      id: `${styleId}_slot_foundation`,
      stepBlockId: 'block_base',
      slotCode: 'BASE_FOUNDATION',
      category: 'makeup' as const,
      subCategory: 'foundation',
      acceptableSubCategories: ['foundation', 'cushion', 'bb', 'concealer'],
      substituteSlotCodes: ['BASE_CONCEALER'],
      requiredLevel: 'required' as const,
      desiredEffect: ['base', 'natural'],
      desiredFinish: ['dewy', 'matte', 'satin'],
      fallbackInstruction: '没有粉底时，用遮瑕局部修饰并保持妆前保湿。',
    },
    {
      id: `${styleId}_slot_brow`,
      stepBlockId: 'block_brow',
      slotCode: 'BROW_PENCIL',
      category: 'makeup' as const,
      subCategory: 'brow',
      acceptableSubCategories: ['brow', 'eyeshadow'],
      substituteSlotCodes: ['EYE_SHADOW'],
      requiredLevel: 'required' as const,
      desiredEffect: ['brow', 'natural'],
      desiredFinish: ['soft'],
      fallbackInstruction: '没有眉笔时，用哑光棕色眼影少量填补眉尾。',
    },
    {
      id: `${styleId}_slot_eye`,
      stepBlockId: 'block_eye',
      slotCode: 'EYE_SHADOW_OR_LINER',
      category: 'makeup' as const,
      subCategory: 'eye',
      acceptableSubCategories: ['eye', 'eyeshadow', 'eyeliner', 'mascara'],
      substituteSlotCodes: [],
      requiredLevel: 'recommended' as const,
      desiredEffect: ['eye', 'natural'],
      desiredFinish: ['soft'],
      fallbackInstruction: '没有眼影时，跳过眼影并重点夹翘睫毛。',
    },
    {
      id: `${styleId}_slot_blush`,
      stepBlockId: 'block_cheek',
      slotCode: 'CHEEK_BLUSH',
      category: 'makeup' as const,
      subCategory: 'blush',
      acceptableSubCategories: ['blush', 'lip'],
      substituteSlotCodes: ['LIP_COLOR'],
      requiredLevel: 'recommended' as const,
      desiredEffect: ['blush', 'good_complexion'],
      desiredFinish: ['soft'],
      fallbackInstruction: '没有腮红时，用少量口红点拍在面中并迅速晕开。',
    },
    {
      id: `${styleId}_slot_lip`,
      stepBlockId: 'block_lip_finish',
      slotCode: 'LIP_COLOR',
      category: 'makeup' as const,
      subCategory: 'lip',
      acceptableSubCategories: ['lip', 'lipstick', 'lip_gloss'],
      substituteSlotCodes: [],
      requiredLevel: 'required' as const,
      desiredEffect: ['lip', 'good_complexion'],
      desiredFinish: ['soft'],
      fallbackInstruction: '没有口红时，用润唇膏提升唇部状态并完成妆容。',
    },
  ];
}

export const STANDARD_MAKEUP_TEMPLATES: StandardMakeupTemplate[] =
  STANDARD_MAKEUP_STYLES.map((style) => ({
    id:
      style.family === 'DAILY_COMMUTE'
        ? 'std_daily_clear_commute'
        : style.family === 'SPECIFIC_VISUAL'
          ? 'std_specific_y2k_spicy'
          : `std_${style.family.toLowerCase()}`,
    displayName:
      style.family === 'DAILY_COMMUTE'
        ? '清透通勤标准模板'
        : `${style.displayName}标准模板`,
    styleId: style.id,
    styleFamily: style.family,
    primaryScene: style.family === 'DAILY_COMMUTE' ? 'COMMUTE' : (style.typicalScenes[0] ?? 'DAILY'),
    styleTags: style.positiveTags,
    effectTags: [style.baseFinish, ...style.colorPalette],
    difficultyBaseScore: style.defaultDifficulty,
    minSkillLevel: style.defaultDifficulty > 2.5 ? 'advanced' : 'beginner',
    estimatedTimeMinutes: style.defaultDifficulty > 2.5 ? 25 : 15,
    templateDescription: `${style.displayName}，常见别名包括 ${style.aliases.join('、')}，核心标签 ${style.positiveTags.join('、')}。`,
    visualDescription: `${style.baseFinish} 底妆，${style.colorPalette.join('、')} 色系，强度 ${style.intensityLevel}/5。`,
    isActive: true,
    stepBlocks: fiveStepBlocks,
    productSlots: slotsFor(style.id),
  }));
```

- [ ] **Step 4: Implement service**

Create `backend/src/makeup-templates/template-library/standard-template-library.service.ts`:

```ts
import { Injectable } from '@nestjs/common';

import {
  STANDARD_MAKEUP_STYLES,
  STANDARD_MAKEUP_TEMPLATES,
} from './standard-template-library.data';
import type {
  StandardMakeupTemplate,
  StandardStyleFamily,
} from './standard-template-library.types';

@Injectable()
export class StandardTemplateLibraryService {
  listStyleFamilies(): StandardStyleFamily[] {
    return [
      ...new Set(STANDARD_MAKEUP_STYLES.map((style) => style.family)),
    ] as StandardStyleFamily[];
  }

  listStyles() {
    return STANDARD_MAKEUP_STYLES;
  }

  listActiveTemplates(): StandardMakeupTemplate[] {
    return STANDARD_MAKEUP_TEMPLATES.filter((template) => template.isActive);
  }

  getTemplateById(templateId: string): StandardMakeupTemplate | undefined {
    return this.listActiveTemplates().find(
      (template) => template.id === templateId,
    );
  }
}
```

- [ ] **Step 5: Run test**

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/standard-template-library.service.spec.ts --runInBand
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/makeup-templates/template-library
git commit -m "feat: add standard makeup template library"
```

## Task 3: Build Match Profiles

**Files:**
- Create: `backend/src/makeup-templates/template-library/template-match-profile.service.ts`
- Test: `backend/src/makeup-templates/template-library/template-match-profile.service.spec.ts`

- [ ] **Step 1: Write failing profile tests**

Create `backend/src/makeup-templates/template-library/template-match-profile.service.spec.ts`:

```ts
import { TemplateMatchProfileService } from './template-match-profile.service';

describe('TemplateMatchProfileService', () => {
  const service = new TemplateMatchProfileService();

  it('builds a fast clear commute profile from parsed intent and user products', () => {
    const profile = service.build({
      user: {
        id: 'user-001',
        nickname: 'Demo',
        skinType: 'oily',
        makeupPreference: 'natural',
        commonScenarios: ['通勤'],
        createdAt: new Date(),
        updatedAt: new Date(),
      },
      rawUserInput: '明天通勤想要清透妆，十分钟内完成',
      scene: 'COMMUTE',
      styleTags: ['CLEAR', 'NATURAL'],
      effectTags: ['GOOD_COMPLEXION'],
      constraints: ['OWNED_PRODUCTS_FIRST', 'FAST'],
      products: [
        {
          id: 'up-1',
          userId: 'user-001',
          productId: 'prod-1',
          status: 'active',
          openedAt: new Date(),
          expiresAt: new Date('2027-01-01T00:00:00.000Z'),
          usageCount: 3,
          lastUsedAt: new Date(),
          notes: null,
          isOpened: true,
          customExpiresAt: null,
          purchaseChannel: null,
          purchaseDate: null,
          userTags: [],
          sortOrder: 0,
          createdAt: new Date(),
          updatedAt: new Date(),
          product: { category: 'makeup', subCategory: 'foundation', tags: ['base'] },
        },
      ],
    });

    expect(profile).toMatchObject({
      rawUserInput: '明天通勤想要清透妆，十分钟内完成',
      scene: 'COMMUTE',
      styleTags: ['CLEAR', 'NATURAL', '通勤'],
      effectTags: ['GOOD_COMPLEXION'],
      constraints: ['OWNED_PRODUCTS_FIRST', 'FAST'],
      skinType: 'oily',
      skillLevel: 'beginner',
      preferredProductCategories: ['foundation'],
    });
  });

  it('marks advanced skill for high intensity style requests', () => {
    const profile = service.build({
      user: {
        id: 'user-001',
        nickname: 'Demo',
        skinType: 'dry',
        makeupPreference: 'glam',
        commonScenarios: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      },
      rawUserInput: '今晚想要欧美截断烟熏舞台妆',
      scene: 'CAMERA',
      styleTags: ['GLAM'],
      effectTags: ['MATTE'],
      constraints: ['OWNED_PRODUCTS_FIRST'],
      products: [],
    });

    expect(profile.skillLevel).toBe('advanced');
    expect(profile.styleTags).toEqual(expect.arrayContaining(['GLAM', 'glam']));
  });
});
```

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/template-match-profile.service.spec.ts --runInBand
```

Expected: fail because service does not exist.

- [ ] **Step 2: Implement profile service**

Create `backend/src/makeup-templates/template-library/template-match-profile.service.ts`:

```ts
import { Injectable } from '@nestjs/common';

import type {
  TemplateMatchBuildInput,
  TemplateMatchProfile,
} from './standard-template-library.types';

@Injectable()
export class TemplateMatchProfileService {
  build(input: TemplateMatchBuildInput): TemplateMatchProfile {
    const styleTags = unique([
      ...input.styleTags,
      input.user.makeupPreference,
      ...input.user.commonScenarios,
    ]);

    return {
      rawUserInput: input.rawUserInput,
      scene: input.scene,
      styleTags,
      effectTags: unique(input.effectTags),
      constraints: unique(input.constraints),
      skinType: input.user.skinType || undefined,
      skillLevel: this.resolveSkillLevel(input.rawUserInput, styleTags),
      preferredProductCategories: unique(
        input.products
          .filter((item) => ['active', 'idle'].includes(item.status))
          .map((item) => item.product.subCategory)
          .filter(Boolean),
      ),
    };
  }

  private resolveSkillLevel(
    rawUserInput: string,
    styleTags: string[],
  ): TemplateMatchProfile['skillLevel'] {
    const text = [rawUserInput, ...styleTags].join(' ').toLowerCase();

    if (
      ['欧美', '烟熏', '截断', '舞台', 'glam', 'stage', 'punk'].some((keyword) =>
        text.includes(keyword),
      )
    ) {
      return 'advanced';
    }

    if (['新手', '快速', '十分钟', '10分钟', '通勤'].some((keyword) => text.includes(keyword))) {
      return 'beginner';
    }

    return 'normal';
  }
}

function unique(values: string[]): string[] {
  return [...new Set(values.map((value) => value.trim()).filter(Boolean))];
}
```

- [ ] **Step 3: Run test**

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/template-match-profile.service.spec.ts --runInBand
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add backend/src/makeup-templates/template-library/template-match-profile.service.ts backend/src/makeup-templates/template-library/template-match-profile.service.spec.ts
git commit -m "feat: build template match profiles"
```

## Task 4: Add Optional Model Client With Safe Fallback

**Files:**
- Create: `backend/src/makeup-templates/template-library/template-model-client.service.ts`
- Test: `backend/src/makeup-templates/template-library/template-model-client.service.spec.ts`

- [ ] **Step 1: Write failing model client tests**

Create `backend/src/makeup-templates/template-library/template-model-client.service.spec.ts`:

```ts
import { TemplateModelClientService } from './template-model-client.service';

describe('TemplateModelClientService', () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
    jest.restoreAllMocks();
  });

  afterAll(() => {
    process.env = originalEnv;
  });

  it('reports unavailable when embedding and reranker endpoints are not configured', async () => {
    delete process.env.TEMPLATE_EMBEDDING_BASE_URL;
    delete process.env.TEMPLATE_RERANKER_BASE_URL;

    const service = new TemplateModelClientService();

    await expect(service.embedText('清透通勤妆')).resolves.toEqual({
      status: 'unavailable',
      vector: [],
    });
    await expect(
      service.rerank('清透通勤妆', ['清透通勤标准模板']),
    ).resolves.toEqual({
      status: 'unavailable',
      scores: [],
    });
  });

  it('calls an OpenAI-compatible embedding endpoint when configured', async () => {
    process.env.TEMPLATE_EMBEDDING_BASE_URL = 'http://127.0.0.1:18080/v1';
    process.env.TEMPLATE_EMBEDDING_MODEL = 'Qwen3-Embedding-4B';
    jest.spyOn(global, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ data: [{ embedding: [0.1, 0.2, 0.3] }] }),
    } as Response);

    const result = await new TemplateModelClientService().embedText('清透通勤妆');

    expect(result).toEqual({ status: 'configured', vector: [0.1, 0.2, 0.3] });
    expect(global.fetch).toHaveBeenCalledWith(
      'http://127.0.0.1:18080/v1/embeddings',
      expect.objectContaining({ method: 'POST' }),
    );
  });
});
```

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/template-model-client.service.spec.ts --runInBand
```

Expected: fail because service does not exist.

- [ ] **Step 2: Implement model client**

Create `backend/src/makeup-templates/template-library/template-model-client.service.ts`:

```ts
import { Injectable, Logger } from '@nestjs/common';

type EmbeddingResult = {
  status: 'configured' | 'unavailable' | 'failed';
  vector: number[];
};

type RerankResult = {
  status: 'configured' | 'unavailable' | 'failed';
  scores: number[];
};

@Injectable()
export class TemplateModelClientService {
  private readonly logger = new Logger(TemplateModelClientService.name);
  private readonly embeddingBaseUrl =
    process.env.TEMPLATE_EMBEDDING_BASE_URL?.trim().replace(/\/$/, '') ?? '';
  private readonly embeddingModel =
    process.env.TEMPLATE_EMBEDDING_MODEL?.trim() ?? 'Qwen3-Embedding-4B';
  private readonly rerankerBaseUrl =
    process.env.TEMPLATE_RERANKER_BASE_URL?.trim().replace(/\/$/, '') ?? '';
  private readonly rerankerModel =
    process.env.TEMPLATE_RERANKER_MODEL?.trim() ?? 'Qwen3-Reranker-8B';
  private readonly timeoutMs = Number(
    process.env.TEMPLATE_MODEL_TIMEOUT_MS?.trim() || 2500,
  );

  async embedText(text: string): Promise<EmbeddingResult> {
    if (!this.embeddingBaseUrl) {
      return { status: 'unavailable', vector: [] };
    }

    try {
      const response = await this.fetchWithTimeout(
        `${this.embeddingBaseUrl}/embeddings`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ model: this.embeddingModel, input: text }),
        },
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const payload = (await response.json()) as {
        data?: Array<{ embedding?: number[] }>;
      };

      return {
        status: 'configured',
        vector: payload.data?.[0]?.embedding ?? [],
      };
    } catch (error) {
      this.logger.warn(`Template embedding request failed: ${String(error)}`);
      return { status: 'failed', vector: [] };
    }
  }

  async rerank(query: string, documents: string[]): Promise<RerankResult> {
    if (!this.rerankerBaseUrl || documents.length === 0) {
      return { status: 'unavailable', scores: [] };
    }

    try {
      const response = await this.fetchWithTimeout(`${this.rerankerBaseUrl}/rerank`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model: this.rerankerModel,
          query,
          documents,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${await response.text()}`);
      }

      const payload = (await response.json()) as {
        results?: Array<{ index: number; relevance_score: number }>;
      };
      const scores = new Array(documents.length).fill(0);

      for (const item of payload.results ?? []) {
        scores[item.index] = item.relevance_score;
      }

      return { status: 'configured', scores };
    } catch (error) {
      this.logger.warn(`Template reranker request failed: ${String(error)}`);
      return { status: 'failed', scores: [] };
    }
  }

  private async fetchWithTimeout(url: string, init: RequestInit) {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), this.timeoutMs);

    try {
      return await fetch(url, { ...init, signal: controller.signal });
    } finally {
      clearTimeout(timeout);
    }
  }
}
```

- [ ] **Step 3: Run test**

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/template-model-client.service.spec.ts --runInBand
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add backend/src/makeup-templates/template-library/template-model-client.service.ts backend/src/makeup-templates/template-library/template-model-client.service.spec.ts
git commit -m "feat: add optional template model client"
```

## Task 5: Implement Hybrid Template Matching

**Files:**
- Create: `backend/src/makeup-templates/template-library/template-matching.service.ts`
- Test: `backend/src/makeup-templates/template-library/template-matching.service.spec.ts`

- [ ] **Step 1: Write failing matcher tests**

Create `backend/src/makeup-templates/template-library/template-matching.service.spec.ts`:

```ts
import { StandardTemplateLibraryService } from './standard-template-library.service';
import { TemplateMatchingService } from './template-matching.service';
import { TemplateModelClientService } from './template-model-client.service';

describe('TemplateMatchingService', () => {
  const unavailableModelClient = {
    embedText: jest.fn().mockResolvedValue({ status: 'unavailable', vector: [] }),
    rerank: jest.fn().mockResolvedValue({ status: 'unavailable', scores: [] }),
  } as unknown as TemplateModelClientService;

  function buildService() {
    return new TemplateMatchingService(
      new StandardTemplateLibraryService(),
      unavailableModelClient,
    );
  }

  it('selects the clear commute template for a clear commute request without model services', async () => {
    const result = await buildService().match({
      rawUserInput: '明天上班想要清透白开水通勤妆，十分钟内完成',
      scene: 'COMMUTE',
      styleTags: ['CLEAR', 'NATURAL'],
      effectTags: ['GOOD_COMPLEXION'],
      constraints: ['OWNED_PRODUCTS_FIRST', 'FAST'],
      skinType: 'oily',
      skillLevel: 'beginner',
      preferredProductCategories: ['foundation', 'brow', 'lip'],
    });

    expect(result.selected.template.id).toBe('std_daily_clear_commute');
    expect(result.degraded).toBe(true);
    expect(result.modelStatus).toMatchObject({
      embedding: 'unavailable',
      reranker: 'unavailable',
      vlm: 'skipped',
    });
    expect(result.selected.breakdown.sceneMatch).toBeGreaterThan(0);
    expect(result.selected.breakdown.productCoverage).toBeGreaterThan(0);
  });

  it('uses reranker scores when they are configured', async () => {
    const modelClient = {
      embedText: jest.fn().mockResolvedValue({ status: 'unavailable', vector: [] }),
      rerank: jest.fn().mockResolvedValue({
        status: 'configured',
        scores: [0.01, 0.99, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01],
      }),
    } as unknown as TemplateModelClientService;
    const service = new TemplateMatchingService(
      new StandardTemplateLibraryService(),
      modelClient,
    );

    const result = await service.match({
      rawUserInput: '我想要一个甜妹约会妆',
      scene: 'DATE',
      styleTags: ['SWEET'],
      effectTags: ['DEWY'],
      constraints: ['OWNED_PRODUCTS_FIRST'],
      skillLevel: 'normal',
      preferredProductCategories: [],
    });

    expect(result.modelStatus.reranker).toBe('configured');
    expect(result.candidates[0].breakdown.rerankerRelevance).toBeGreaterThan(0);
  });
});
```

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/template-matching.service.spec.ts --runInBand
```

Expected: fail because matcher does not exist.

- [ ] **Step 2: Implement matcher**

Create `backend/src/makeup-templates/template-library/template-matching.service.ts`:

```ts
import { Injectable } from '@nestjs/common';

import type {
  StandardMakeupTemplate,
  TemplateMatchCandidate,
  TemplateMatchProfile,
  TemplateMatchScoreBreakdown,
} from './standard-template-library.types';
import { StandardTemplateLibraryService } from './standard-template-library.service';
import { TemplateModelClientService } from './template-model-client.service';

const WEIGHTS = {
  embeddingSimilarity: 0.25,
  rerankerRelevance: 0.2,
  styleMatch: 0.15,
  sceneMatch: 0.1,
  productCoverage: 0.15,
  userProfileFit: 0.05,
  historyPreference: 0.05,
  difficultyPenalty: -0.03,
  missingRequiredSlotPenalty: -0.02,
};

@Injectable()
export class TemplateMatchingService {
  constructor(
    private readonly library: StandardTemplateLibraryService,
    private readonly modelClient: TemplateModelClientService,
  ) {}

  async match(profile: TemplateMatchProfile) {
    const templates = this.library.listActiveTemplates();
    const embedding = await this.modelClient.embedText(profile.rawUserInput);
    const rerank = await this.modelClient.rerank(
      profile.rawUserInput,
      templates.map((template) => this.describeTemplate(template)),
    );
    const candidates = templates
      .map((template, index) =>
        this.scoreCandidate(
          template,
          profile,
          this.resolveEmbeddingSimilarity(profile, template, embedding.vector),
          rerank.scores[index] ?? 0,
        ),
      )
      .sort((left, right) => right.score - left.score)
      .slice(0, 30);

    const selected = candidates[0];

    return {
      profile,
      selected,
      candidates,
      modelStatus: {
        embedding: embedding.status,
        reranker: rerank.status,
        vlm: 'skipped' as const,
      },
      degraded: embedding.status !== 'configured' || rerank.status !== 'configured',
    };
  }

  private describeTemplate(template: StandardMakeupTemplate): string {
    return [
      template.displayName,
      template.templateDescription,
      template.visualDescription,
      template.primaryScene,
      template.styleTags.join(' '),
      template.effectTags.join(' '),
    ].join('\n');
  }

  private scoreCandidate(
    template: StandardMakeupTemplate,
    profile: TemplateMatchProfile,
    embeddingSimilarity: number,
    rerankerRelevance: number,
  ): TemplateMatchCandidate {
    const breakdown: TemplateMatchScoreBreakdown = {
      embeddingSimilarity,
      rerankerRelevance,
      styleMatch: overlapRatio(profile.styleTags, [
        ...template.styleTags,
        template.styleFamily,
        template.displayName,
        template.templateDescription,
      ]),
      sceneMatch: template.primaryScene === profile.scene ? 1 : 0,
      productCoverage: this.estimateProductCoverage(template, profile),
      userProfileFit: this.scoreUserProfile(template, profile),
      historyPreference: 0,
      difficultyPenalty: this.scoreDifficultyPenalty(template, profile),
      missingRequiredSlotPenalty: this.scoreMissingRequiredSlots(template, profile),
    };

    const score = Object.entries(WEIGHTS).reduce(
      (sum, [key, weight]) =>
        sum + breakdown[key as keyof TemplateMatchScoreBreakdown] * weight,
      0,
    );

    return {
      template,
      score,
      reasons: this.buildReasons(template, profile, breakdown),
      breakdown,
    };
  }

  private resolveEmbeddingSimilarity(
    profile: TemplateMatchProfile,
    template: StandardMakeupTemplate,
    vector: number[],
  ): number {
    if (vector.length > 0) {
      return Math.min(1, Math.max(0, vector.reduce((sum, item) => sum + Math.abs(item), 0) / vector.length));
    }

    return overlapRatio(
      tokenize(profile.rawUserInput),
      tokenize(`${template.displayName} ${template.templateDescription} ${template.visualDescription}`),
    );
  }

  private estimateProductCoverage(
    template: StandardMakeupTemplate,
    profile: TemplateMatchProfile,
  ): number {
    const requiredSlots = template.productSlots.filter(
      (slot) => slot.requiredLevel === 'required',
    );

    if (requiredSlots.length === 0) {
      return 1;
    }

    const covered = requiredSlots.filter((slot) =>
      [slot.subCategory, ...slot.acceptableSubCategories]
        .filter(Boolean)
        .some((category) => profile.preferredProductCategories.includes(category)),
    ).length;

    return covered / requiredSlots.length;
  }

  private scoreUserProfile(
    template: StandardMakeupTemplate,
    profile: TemplateMatchProfile,
  ): number {
    if (profile.skillLevel === 'beginner' && template.difficultyBaseScore <= 1.8) {
      return 1;
    }

    if (profile.skillLevel === 'advanced' && template.difficultyBaseScore >= 2.2) {
      return 1;
    }

    return 0.5;
  }

  private scoreDifficultyPenalty(
    template: StandardMakeupTemplate,
    profile: TemplateMatchProfile,
  ): number {
    if (profile.constraints.includes('FAST') && template.estimatedTimeMinutes > 15) {
      return 1;
    }

    if (profile.skillLevel === 'beginner' && template.difficultyBaseScore > 2) {
      return 1;
    }

    return 0;
  }

  private scoreMissingRequiredSlots(
    template: StandardMakeupTemplate,
    profile: TemplateMatchProfile,
  ): number {
    return 1 - this.estimateProductCoverage(template, profile);
  }

  private buildReasons(
    template: StandardMakeupTemplate,
    profile: TemplateMatchProfile,
    breakdown: TemplateMatchScoreBreakdown,
  ): string[] {
    const reasons = [
      `候选模板 ${template.displayName} 与用户需求语义分 ${breakdown.embeddingSimilarity.toFixed(2)}。`,
      `风格匹配分 ${breakdown.styleMatch.toFixed(2)}，场景匹配分 ${breakdown.sceneMatch.toFixed(2)}。`,
      `已有产品覆盖预估 ${Math.round(breakdown.productCoverage * 100)}%。`,
    ];

    if (breakdown.difficultyPenalty > 0) {
      reasons.push(`用户熟练度 ${profile.skillLevel} 或快速诉求触发难度惩罚。`);
    }

    return reasons;
  }
}

function tokenize(text: string): string[] {
  return text
    .toLowerCase()
    .replace(/[，。、“”]/g, ' ')
    .split(/\s+/)
    .flatMap((token) => [token, ...Array.from(token)])
    .filter(Boolean);
}

function overlapRatio(left: string[], right: string[]): number {
  const rightSet = new Set(right.map((item) => item.toLowerCase()));
  const leftItems = left.map((item) => item.toLowerCase()).filter(Boolean);

  if (leftItems.length === 0) {
    return 0;
  }

  return leftItems.filter((item) => rightSet.has(item)).length / leftItems.length;
}
```

- [ ] **Step 3: Run matcher test**

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/template-matching.service.spec.ts --runInBand
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add backend/src/makeup-templates/template-library/template-matching.service.ts backend/src/makeup-templates/template-library/template-matching.service.spec.ts
git commit -m "feat: match standard makeup templates"
```

## Task 6: Adapt Matched Templates Into Executable Blueprints

**Files:**
- Modify: `backend/src/makeup-templates/makeup-template.types.ts`
- Create: `backend/src/makeup-templates/template-library/template-blueprint-adapter.service.ts`
- Test: `backend/src/makeup-templates/template-library/template-blueprint-adapter.service.spec.ts`

- [ ] **Step 1: Write failing adapter test**

Create `backend/src/makeup-templates/template-library/template-blueprint-adapter.service.spec.ts`:

```ts
import { StandardTemplateLibraryService } from './standard-template-library.service';
import { TemplateBlueprintAdapterService } from './template-blueprint-adapter.service';

describe('TemplateBlueprintAdapterService', () => {
  it('adapts a matched standard template into five executable step blueprints', () => {
    const library = new StandardTemplateLibraryService();
    const template = library.getTemplateById('std_daily_clear_commute');
    expect(template).toBeDefined();

    const result = new TemplateBlueprintAdapterService().adapt({
      template: template!,
      profile: {
        rawUserInput: '清透通勤五步演示',
        scene: 'COMMUTE',
        styleTags: ['CLEAR'],
        effectTags: ['GOOD_COMPLEXION'],
        constraints: ['FAST'],
        skinType: 'oily',
        faceShape: 'round',
        skillLevel: 'beginner',
        preferredProductCategories: ['foundation', 'brow', 'lip'],
      },
    });

    expect(result).toHaveLength(5);
    expect(result[0]).toMatchObject({
      sectionCode: 'BASE',
      operationAreas: ['full_face', 't_zone', 'u_zone'],
    });
    expect(result[0].userInstruction).toContain('T 区');
    expect(result[3].userInstruction).toContain('圆脸');
    expect(result.flatMap((step) => step.slots).map((slot) => slot.slotCode)).toEqual(
      expect.arrayContaining(['BASE_FOUNDATION', 'LIP_COLOR']),
    );
  });
});
```

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/template-blueprint-adapter.service.spec.ts --runInBand
```

Expected: fail because adapter and type fields do not exist.

- [ ] **Step 2: Extend blueprint types**

In `backend/src/makeup-templates/makeup-template.types.ts`, update `MakeupStepBlueprint`:

```ts
export type MakeupStepBlueprint = {
  sourceStepBlockId?: string;
  sectionCode: string;
  stepName: string;
  stepGoal: string;
  userInstruction: string;
  visualChange: string;
  aiDetectionArea: string;
  operationAreas: string[];
  difficultyScore?: number;
  completionCriteria: string;
  failureFeedback: string;
  editableByUser: boolean;
  nextStepCondition: string;
  slots: ProductSlotBlueprint[];
};
```

Update `ProductSlotBlueprint`:

```ts
export type ProductSlotBlueprint = {
  sourceSlotSpecId?: string;
  slotCode: string;
  category: ProductCategory;
  subCategory?: string;
  acceptableSubCategories?: string[];
  substituteSlotCodes?: string[];
  requiredLevel: 'required' | 'recommended' | 'optional';
  desiredEffect: string[];
  desiredColorFamily?: string;
  desiredFinish: string[];
  fallbackInstruction: string;
};
```

- [ ] **Step 3: Implement adapter**

Create `backend/src/makeup-templates/template-library/template-blueprint-adapter.service.ts`:

```ts
import { Injectable } from '@nestjs/common';

import type { MakeupStepBlueprint } from '../makeup-template.types';
import type {
  StandardMakeupTemplate,
  TemplateMatchProfile,
} from './standard-template-library.types';

type AdaptInput = {
  template: StandardMakeupTemplate;
  profile: TemplateMatchProfile;
};

@Injectable()
export class TemplateBlueprintAdapterService {
  adapt(input: AdaptInput): MakeupStepBlueprint[] {
    return input.template.stepBlocks.slice(0, this.resolveStepCount(input.profile)).map((block) => ({
      sourceStepBlockId: block.id,
      sectionCode: block.sectionCode,
      stepName: block.stepName,
      stepGoal: block.stepGoal,
      userInstruction: this.personalizeInstruction(block.instructionTemplate, input.profile, block.sectionCode),
      visualChange: block.visualChange,
      aiDetectionArea: block.aiDetectionArea,
      operationAreas: block.operationAreas,
      difficultyScore: block.difficultyScore,
      completionCriteria: block.completionCriteria,
      failureFeedback: block.failureFeedback,
      editableByUser: true,
      nextStepCondition: block.nextStepCondition,
      slots: input.template.productSlots
        .filter((slot) => slot.stepBlockId === block.id)
        .map((slot) => ({
          sourceSlotSpecId: slot.id,
          slotCode: slot.slotCode,
          category: slot.category,
          subCategory: slot.subCategory,
          acceptableSubCategories: slot.acceptableSubCategories,
          substituteSlotCodes: slot.substituteSlotCodes,
          requiredLevel: slot.requiredLevel,
          desiredEffect: slot.desiredEffect,
          desiredColorFamily: slot.desiredColorFamily,
          desiredFinish: slot.desiredFinish,
          fallbackInstruction: slot.fallbackInstruction,
        })),
    }));
  }

  private resolveStepCount(profile: TemplateMatchProfile): number {
    if (profile.rawUserInput.includes('三步') || profile.rawUserInput.includes('3步')) {
      return 3;
    }

    if (profile.rawUserInput.includes('四步') || profile.rawUserInput.includes('4步')) {
      return 4;
    }

    return 5;
  }

  private personalizeInstruction(
    instruction: string,
    profile: TemplateMatchProfile,
    sectionCode: string,
  ): string {
    const notes: string[] = [];

    if (profile.skinType === 'oily' && sectionCode === 'BASE') {
      notes.push('油皮需要把控油定妆重点放在 T 区。');
    }

    if (profile.faceShape === 'round' && sectionCode === 'CHEEK') {
      notes.push('圆脸腮红位置略微上提，避免横向铺太宽。');
    }

    if (profile.constraints.includes('FAST')) {
      notes.push('快速妆只保留最影响效果的动作。');
    }

    return [instruction, ...notes].join(' ');
  }
}
```

- [ ] **Step 4: Run adapter test**

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/template-blueprint-adapter.service.spec.ts --runInBand
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/makeup-templates/makeup-template.types.ts backend/src/makeup-templates/template-library/template-blueprint-adapter.service.ts backend/src/makeup-templates/template-library/template-blueprint-adapter.service.spec.ts
git commit -m "feat: adapt matched templates into execution blueprints"
```

## Task 7: Enhance Product Slot Matching

**Files:**
- Modify: `backend/src/makeup-templates/makeup-template-slot-matching.service.ts`
- Modify: `backend/src/makeup-templates/makeup-template-slot-matching.service.spec.ts`

- [ ] **Step 1: Add failing substitution tests**

Append to `backend/src/makeup-templates/makeup-template-slot-matching.service.spec.ts`:

```ts
  it('matches acceptable subcategories as substitutable alternatives', () => {
    const result = service.matchSlot(
      {
        ...baseSlot,
        subCategory: 'blush',
        acceptableSubCategories: ['blush', 'lip'],
        substituteSlotCodes: ['LIP_COLOR'],
        slotCode: 'CHEEK_BLUSH',
        desiredEffect: ['good_complexion'],
      },
      [
        userProduct({
          product: {
            ...userProduct({}).product,
            subCategory: 'lip',
            tags: ['lip', 'good_complexion', 'soft'],
          },
        }),
      ],
    );

    expect(result).toMatchObject({
      matchedProductId: 'prod-1',
      matchStatus: 'substitutable',
    });
    expect(result.matchReason).toContain('可替代类目命中');
  });

  it('prefers exact subcategory over acceptable substitute when both exist', () => {
    const result = service.matchSlot(
      {
        ...baseSlot,
        subCategory: 'blush',
        acceptableSubCategories: ['blush', 'lip'],
        slotCode: 'CHEEK_BLUSH',
        desiredEffect: ['good_complexion'],
      },
      [
        userProduct({
          id: 'user-prod-lip',
          productId: 'prod-lip',
          product: {
            ...userProduct({}).product,
            id: 'prod-lip',
            subCategory: 'lip',
            tags: ['good_complexion'],
          },
        }),
        userProduct({
          id: 'user-prod-blush',
          productId: 'prod-blush',
          product: {
            ...userProduct({}).product,
            id: 'prod-blush',
            subCategory: 'blush',
            tags: ['good_complexion'],
          },
        }),
      ],
    );

    expect(result.matchedProductId).toBe('prod-blush');
    expect(result.matchStatus).toBe('matched');
  });
```

Run:

```bash
cd backend
npm test -- makeup-templates/makeup-template-slot-matching.service.spec.ts --runInBand
```

Expected: fail because acceptable subcategories are ignored.

- [ ] **Step 2: Update scoring logic**

In `backend/src/makeup-templates/makeup-template-slot-matching.service.ts`, update `ScoredProduct`:

```ts
  acceptableSubCategoryMatched: boolean;
```

Replace subcategory matching in `scoreProduct` with:

```ts
    const subCategoryMatched =
      Boolean(slot.subCategory) &&
      userProduct.product.subCategory === slot.subCategory;
    const acceptableSubCategoryMatched =
      !subCategoryMatched &&
      Boolean(slot.acceptableSubCategories?.includes(userProduct.product.subCategory));

    if (
      slot.subCategory &&
      !subCategoryMatched &&
      !acceptableSubCategoryMatched &&
      matchedTags.length === 0
    ) {
      return null;
    }
```

Update the score object:

```ts
      score:
        (subCategoryMatched ? 100 : 0) +
        (acceptableSubCategoryMatched ? 65 : 0) +
        matchedTags.length * 12 +
        this.scoreStatus(userProduct.status) +
        this.scoreUsageProfile(userProduct) +
        this.scoreUsageCount(userProduct) +
        this.scoreRecency(userProduct),
      matchStatus: subCategoryMatched ? 'matched' : 'substitutable',
      matchedTags,
      subCategoryMatched,
      acceptableSubCategoryMatched,
```

Update `buildMatchReason`:

```ts
    if (candidate.acceptableSubCategoryMatched) {
      reasons.push('可替代类目命中');
    }
```

- [ ] **Step 3: Run slot matching tests**

Run:

```bash
cd backend
npm test -- makeup-templates/makeup-template-slot-matching.service.spec.ts --runInBand
```

Expected: pass.

- [ ] **Step 4: Commit**

```bash
git add backend/src/makeup-templates/makeup-template-slot-matching.service.ts backend/src/makeup-templates/makeup-template-slot-matching.service.spec.ts
git commit -m "feat: support standard slot substitutions"
```

## Task 8: Integrate Matcher Into Template Generation

**Files:**
- Modify: `backend/src/makeup-templates/makeup-template-generation.service.ts`
- Modify: `backend/src/makeup-templates/makeup-template-generation.service.spec.ts`
- Modify: `backend/src/makeup-templates/makeup-template.mapper.ts`
- Modify: `backend/src/makeup-templates/dto/makeup-template-response.dto.ts`
- Modify: `backend/src/makeup-templates/makeup-templates.module.ts`

- [ ] **Step 1: Update generation service test expectations**

In `backend/src/makeup-templates/makeup-template-generation.service.spec.ts`, update `buildService` to construct the new services:

```ts
import { StandardTemplateLibraryService } from './template-library/standard-template-library.service';
import { TemplateBlueprintAdapterService } from './template-library/template-blueprint-adapter.service';
import { TemplateMatchProfileService } from './template-library/template-match-profile.service';
import { TemplateMatchingService } from './template-library/template-matching.service';
import { TemplateModelClientService } from './template-library/template-model-client.service';
```

Replace `new MakeupTemplateGenerationService(...)` with:

```ts
  const libraryService = new StandardTemplateLibraryService();
  const modelClient = {
    embedText: jest.fn().mockResolvedValue({ status: 'unavailable', vector: [] }),
    rerank: jest.fn().mockResolvedValue({ status: 'unavailable', scores: [] }),
  } as unknown as TemplateModelClientService;

  return new MakeupTemplateGenerationService(
    prisma as unknown as PrismaService,
    new MakeupTemplateIntentService(),
    new MakeupTemplateSlotMatchingService(
      () => new Date('2026-05-10T00:00:00.000Z'),
    ),
    new MakeupTemplateSnapshotService(prisma as unknown as PrismaService),
    new MakeupTemplateEventService(prisma as unknown as PrismaService),
    new TemplateMatchProfileService(),
    new TemplateMatchingService(libraryService, modelClient),
    new TemplateBlueprintAdapterService(),
  );
```

In the first test, after `templateCreate` expectations, add:

```ts
    expect(templateCreate.templateType).toBe('hybrid_matching');
    expect(templateCreate.sourceStandardTemplateId).toBe('std_daily_clear_commute');
    expect(templateCreate.matchScore).toEqual(expect.any(Number));
    expect(templateCreate.matchTraceId).toMatch(/^mtrace_/);
```

Add `templateMatchTrace` to the Prisma mock:

```ts
    templateMatchTrace: {
      create: jest.fn(({ data }) =>
        Promise.resolve({
          ...data,
          createdAt: now,
        }),
      ),
    },
```

Run:

```bash
cd backend
npm test -- makeup-templates/makeup-template-generation.service.spec.ts --runInBand
```

Expected: fail because constructor and persistence logic have not been updated.

- [ ] **Step 2: Extend response DTO and mapper**

In `backend/src/makeup-templates/dto/makeup-template-response.dto.ts`, add to `GeneratedTemplateStepResponseDto`:

```ts
  @ApiProperty({ example: ['full_face', 't_zone'], type: [String] })
  operationAreas!: string[];
```

Add to `MakeupTemplateResponseDto`:

```ts
  @ApiPropertyOptional({ example: 'std_daily_clear_commute' })
  sourceStandardTemplateId?: string;

  @ApiPropertyOptional({ example: 0.78 })
  matchScore?: number;

  @ApiPropertyOptional({ example: 'mtrace_20260510_ab12cd34' })
  matchTraceId?: string;
```

In `backend/src/makeup-templates/makeup-template.mapper.ts`, add fields to `TemplateWithIncludes`:

```ts
  sourceStandardTemplateId?: string | null;
  matchScore?: number | null;
  matchTraceId?: string | null;
```

Return them in `mapMakeupTemplate`:

```ts
    sourceStandardTemplateId: template.sourceStandardTemplateId ?? undefined,
    matchScore: template.matchScore ?? undefined,
    matchTraceId: template.matchTraceId ?? undefined,
```

Add `operationAreas: string[];` to the step type and map:

```ts
        operationAreas: step.operationAreas ?? [],
```

- [ ] **Step 3: Confirm operation areas persistence**

Task 1 adds this field to `GeneratedTemplateStep`; verify it is present before continuing:

```prisma
  operationAreas     String[]                @map("operation_areas") @default([])
```

Task 1 also adds this SQL:

```sql
ALTER TABLE "generated_template_steps" ADD COLUMN "operation_areas" TEXT[] DEFAULT ARRAY[]::TEXT[];
```

If either line is missing, stop and add a new migration before integrating the matcher.

- [ ] **Step 4: Integrate matcher in generation service**

Update constructor in `backend/src/makeup-templates/makeup-template-generation.service.ts`:

```ts
    private readonly profileService: TemplateMatchProfileService,
    private readonly matchingService: TemplateMatchingService,
    private readonly blueprintAdapter: TemplateBlueprintAdapterService,
```

Add imports:

```ts
import { TemplateBlueprintAdapterService } from './template-library/template-blueprint-adapter.service';
import { TemplateMatchProfileService } from './template-library/template-match-profile.service';
import { TemplateMatchingService } from './template-library/template-matching.service';
```

Replace:

```ts
    const stepBlueprints = this.buildStepBlueprints(intent);
```

with:

```ts
    const matchProfile = this.profileService.build({
      user,
      rawUserInput: input.rawUserInput,
      scene: intent.parsedScene,
      styleTags: intent.parsedStyleTags,
      effectTags: intent.parsedEffectTags,
      constraints: intent.parsedConstraints,
      products: userProducts,
    });
    const matchResult = await this.matchingService.match(matchProfile);
    const stepBlueprints = this.blueprintAdapter.adapt({
      template: matchResult.selected.template,
      profile: matchResult.profile,
    });
```

Inside the transaction, after snapshots are created and before `generatedMakeupTemplate.create`, create trace:

```ts
      const matchTrace = await tx.templateMatchTrace.create({
        data: {
          id: createMakeupTemplateId('matchTrace'),
          userId: input.userId,
          requestId: request.id,
          rawUserInput: input.rawUserInput,
          profile: matchResult.profile,
          selectedTemplateId: matchResult.selected.template.id,
          selectedTemplateScore: matchResult.selected.score,
          candidateCount: matchResult.candidates.length,
          candidates: matchResult.candidates.map((candidate) => ({
            templateId: candidate.template.id,
            displayName: candidate.template.displayName,
            score: candidate.score,
            reasons: candidate.reasons,
            breakdown: candidate.breakdown,
          })),
          scoreBreakdown: matchResult.selected.breakdown,
          modelStatus: matchResult.modelStatus,
          degraded: matchResult.degraded,
        },
      });
```

Set generated template fields:

```ts
          templateType: 'hybrid_matching',
          sourceStandardTemplateId: matchResult.selected.template.id,
          matchScore: matchResult.selected.score,
          matchTraceId: matchTrace.id,
```

When creating steps, add:

```ts
              operationAreas: step.operationAreas,
```

Update `buildDisplayName`, `buildOverallEffect`, and `buildPersonalizationReasons` calls to prefer match result:

```ts
          displayName: matchResult.selected.template.displayName.replace('标准模板', '妆'),
          overallEffect: `${matchResult.selected.template.displayName}，${matchResult.selected.reasons.join(' ')}`,
          personalizationReasons: [
            ...this.buildPersonalizationReasons(intent, stats.productCoverageRate, stats.missingProductTypes),
            ...matchResult.selected.reasons,
          ],
```

- [ ] **Step 5: Register providers and controller**

In `backend/src/makeup-templates/makeup-templates.module.ts`, import and add providers:

```ts
import { StandardTemplateLibraryService } from './template-library/standard-template-library.service';
import { TemplateBlueprintAdapterService } from './template-library/template-blueprint-adapter.service';
import { TemplateMatchProfileService } from './template-library/template-match-profile.service';
import { TemplateMatchingService } from './template-library/template-matching.service';
import { TemplateModelClientService } from './template-library/template-model-client.service';
```

Add to `providers`:

```ts
    StandardTemplateLibraryService,
    TemplateBlueprintAdapterService,
    TemplateMatchProfileService,
    TemplateMatchingService,
    TemplateModelClientService,
```

- [ ] **Step 6: Run focused generation tests**

Run:

```bash
cd backend
npm test -- makeup-templates/makeup-template-generation.service.spec.ts --runInBand
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add backend/src/makeup-templates backend/prisma/schema.prisma backend/prisma/migrations
git commit -m "feat: generate templates through hybrid matching"
```

## Task 9: Add Internal Template Library Debug Endpoints

**Files:**
- Create: `backend/src/makeup-templates/template-library/template-library.controller.ts`
- Modify: `backend/src/makeup-templates/makeup-templates.module.ts`
- Test: `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`

- [ ] **Step 1: Write controller tests**

Create `backend/src/makeup-templates/template-library/template-library.controller.spec.ts`:

```ts
import { TemplateLibraryController } from './template-library.controller';
import { StandardTemplateLibraryService } from './standard-template-library.service';
import { TemplateMatchProfileService } from './template-match-profile.service';
import { TemplateMatchingService } from './template-matching.service';

describe('TemplateLibraryController', () => {
  it('returns styles for internal debugging', () => {
    const controller = new TemplateLibraryController(
      new StandardTemplateLibraryService(),
      {} as TemplateMatchProfileService,
      {} as TemplateMatchingService,
    );

    expect(controller.styles().items).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ family: 'DAILY_COMMUTE' }),
      ]),
    );
  });

  it('returns match debug candidates', async () => {
    const library = new StandardTemplateLibraryService();
    const matching = {
      match: jest.fn().mockResolvedValue({
        selected: {
          template: {
            id: 'std_daily_clear_commute',
            styleFamily: 'DAILY_COMMUTE',
          },
          score: 0.8,
        },
        candidates: [],
        modelStatus: { embedding: 'unavailable', reranker: 'unavailable', vlm: 'skipped' },
        degraded: true,
      }),
    } as unknown as TemplateMatchingService;
    const profileService = {
      build: jest.fn().mockReturnValue({
        rawUserInput: '清透通勤妆',
        scene: 'COMMUTE',
        styleTags: ['CLEAR'],
        effectTags: ['GOOD_COMPLEXION'],
        constraints: ['OWNED_PRODUCTS_FIRST'],
        skillLevel: 'beginner',
        preferredProductCategories: [],
      }),
    } as unknown as TemplateMatchProfileService;
    const controller = new TemplateLibraryController(library, profileService, matching);

    const result = await controller.matchDebug(
      { id: 'user-001' },
      { rawUserInput: '清透通勤妆' },
    );

    expect(result.selectedTemplateId).toBe('std_daily_clear_commute');
    expect(result.selectedFamily).toBe('DAILY_COMMUTE');
    expect(result.degraded).toBe(true);
  });
});
```

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/template-library.controller.spec.ts --runInBand
```

Expected: fail because controller does not exist.

- [ ] **Step 2: Implement controller**

Create `backend/src/makeup-templates/template-library/template-library.controller.ts`:

```ts
import { Body, Controller, Get, Post, UseGuards } from '@nestjs/common';
import { ApiBearerAuth, ApiTags } from '@nestjs/swagger';

import type { AuthenticatedUser } from '../../common/auth/authenticated-user.type';
import { CurrentUser } from '../../common/auth/current-user.decorator';
import { DemoAuthGuard } from '../../common/auth/demo-auth.guard';
import { DEMO_BEARER_SCHEME } from '../../common/constants/demo-auth.constants';
import { StandardTemplateLibraryService } from './standard-template-library.service';
import { TemplateMatchProfileService } from './template-match-profile.service';
import { TemplateMatchingService } from './template-matching.service';

@ApiTags('makeup-template-library')
@ApiBearerAuth(DEMO_BEARER_SCHEME)
@UseGuards(DemoAuthGuard)
@Controller('makeup-template-library')
export class TemplateLibraryController {
  constructor(
    private readonly library: StandardTemplateLibraryService,
    private readonly profileService: TemplateMatchProfileService,
    private readonly matchingService: TemplateMatchingService,
  ) {}

  @Get('styles')
  styles() {
    return { items: this.library.listStyles() };
  }

  @Post('match-debug')
  async matchDebug(
    @CurrentUser() user: AuthenticatedUser,
    @Body() body: { rawUserInput: string },
  ) {
    const profile = this.profileService.build({
      user: {
        id: user.id,
        nickname: user.id,
        skinType: 'unknown',
        makeupPreference: 'natural',
        commonScenarios: [],
        createdAt: new Date(),
        updatedAt: new Date(),
      },
      rawUserInput: body.rawUserInput,
      scene: body.rawUserInput.includes('通勤') ? 'COMMUTE' : 'DAILY',
      styleTags: body.rawUserInput.includes('清透') ? ['CLEAR'] : ['NATURAL'],
      effectTags: ['GOOD_COMPLEXION'],
      constraints: ['OWNED_PRODUCTS_FIRST'],
      products: [],
    });
    const result = await this.matchingService.match(profile);

    return {
      selectedTemplateId: result.selected.template.id,
      selectedFamily: result.selected.template.styleFamily,
      selectedScore: result.selected.score,
      degraded: result.degraded,
      modelStatus: result.modelStatus,
      candidates: result.candidates.map((candidate) => ({
        templateId: candidate.template.id,
        displayName: candidate.template.displayName,
        styleFamily: candidate.template.styleFamily,
        score: candidate.score,
        reasons: candidate.reasons,
        breakdown: candidate.breakdown,
      })),
    };
  }
}
```

- [ ] **Step 3: Register controller**

In `backend/src/makeup-templates/makeup-templates.module.ts`, import:

```ts
import { TemplateLibraryController } from './template-library/template-library.controller';
```

Change controllers:

```ts
  controllers: [MakeupTemplatesController, TemplateLibraryController],
```

- [ ] **Step 4: Run controller test**

Run:

```bash
cd backend
npm test -- makeup-templates/template-library/template-library.controller.spec.ts --runInBand
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add backend/src/makeup-templates/template-library/template-library.controller.ts backend/src/makeup-templates/template-library/template-library.controller.spec.ts backend/src/makeup-templates/makeup-templates.module.ts
git commit -m "feat: expose template library debug endpoints"
```

## Task 10: Add Offline Template Matching Eval

**Files:**
- Create: `eval/template_matching/cases.json`
- Create: `eval/template_matching/run_template_matching_eval.py`

- [ ] **Step 1: Add case file**

Create `eval/template_matching/cases.json`:

```json
[
  {
    "id": "daily_clear_commute",
    "rawUserInput": "明天上班想画清透白开水通勤妆，十分钟内完成",
    "expectedTemplateId": "std_daily_clear_commute",
    "expectedFamily": "DAILY_COMMUTE"
  },
  {
    "id": "sweet_date",
    "rawUserInput": "周末约会想要韩系甜妹水光妆",
    "expectedFamily": "KOREAN_JAPANESE_GIRL"
  },
  {
    "id": "elegant_interview",
    "rawUserInput": "面试需要轻熟知性优雅妆，不要太浓",
    "expectedFamily": "ELEGANT_LUXURY"
  },
  {
    "id": "western_camera",
    "rawUserInput": "拍照想要轻欧美截断眼妆和哑光底妆",
    "expectedFamily": "WESTERN"
  },
  {
    "id": "specific_y2k",
    "rawUserInput": "今晚想试 Y2K 辣妹女团上镜妆",
    "expectedTemplateId": "std_specific_y2k_spicy",
    "expectedFamily": "SPECIFIC_VISUAL"
  }
]
```

- [ ] **Step 2: Add evaluator script**

Create `eval/template_matching/run_template_matching_eval.py`:

```python
#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from urllib import request, error


def post_json(url: str, token: str, payload: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", default="http://127.0.0.1:13000")
    parser.add_argument("--token", default="demo-token")
    parser.add_argument("--cases", default=str(Path(__file__).with_name("cases.json")))
    args = parser.parse_args()

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    passed = 0
    failures = []

    for case in cases:
        try:
            result = post_json(
                f"{args.backend_url.rstrip('/')}/makeup-template-library/match-debug",
                args.token,
                {"rawUserInput": case["rawUserInput"]},
            )
        except error.URLError as exc:
            print(f"request failed for {case['id']}: {exc}", file=sys.stderr)
            return 2

        selected = result["selectedTemplateId"]
        family = result.get("selectedFamily")
        expected_template = case.get("expectedTemplateId")
        expected_family = case.get("expectedFamily")
        template_ok = expected_template is None or selected == expected_template
        family_ok = expected_family is None or family == expected_family

        if template_ok and family_ok:
            passed += 1
        else:
            failures.append(
                {
                    "id": case["id"],
                    "selected": selected,
                    "family": family,
                    "expectedTemplate": expected_template,
                    "expectedFamily": expected_family,
                }
            )

    print(json.dumps({"passed": passed, "total": len(cases), "failures": failures}, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: Run syntax check**

Run:

```bash
python -m py_compile eval/template_matching/run_template_matching_eval.py
```

Expected: no output.

- [ ] **Step 4: Commit**

```bash
git add eval/template_matching/cases.json eval/template_matching/run_template_matching_eval.py
git commit -m "test: add template matching eval cases"
```

## Task 11: Document GPU and Model Configuration

**Files:**
- Modify: `docs/team-runbook.md`
- Modify: `backend/README.md`

- [ ] **Step 1: Add runbook section**

Append this section to `docs/team-runbook.md`:

```markdown
## MMU 模板库智能匹配

模板匹配默认不独占 GPU。在线链路优先使用标准模板库、已构建索引和规则重排；只有配置了 `TEMPLATE_EMBEDDING_BASE_URL` 或 `TEMPLATE_RERANKER_BASE_URL` 时才调用模型服务。

建议资源预算：

- GPU 0-3：3090，可承载轻量 embedding/reranker 或离线批处理。
- GPU 4-7：48G 4090，优先留给 VLM、妆容预览和实时跟妆。
- 模板匹配不启动新的 72B 常驻服务；72B 只用于离线标注或批量构建。

可选环境变量：

```bash
TEMPLATE_EMBEDDING_BASE_URL=http://127.0.0.1:18080/v1
TEMPLATE_EMBEDDING_MODEL=Qwen3-Embedding-4B
TEMPLATE_RERANKER_BASE_URL=http://127.0.0.1:18081
TEMPLATE_RERANKER_MODEL=Qwen3-Reranker-8B
TEMPLATE_MODEL_TIMEOUT_MS=2500
```

模型缺失时，优先使用：

```bash
HF_ENDPOINT=https://hf-mirror.com python /storage/nvme3/shushanfu/checkpoint/down_load.py ...
```

镜像失败再加 7890 代理。
```

- [ ] **Step 2: Add backend README note**

Append a short note to `backend/README.md`:

```markdown
### Template library matching

`/makeup-templates/generate` uses the standard MMU template library and hybrid matching service. Embedding/reranker services are optional. If `TEMPLATE_EMBEDDING_BASE_URL` and `TEMPLATE_RERANKER_BASE_URL` are unset, the backend falls back to deterministic lexical scoring and still returns a generated 3-5 step template.
```

- [ ] **Step 3: Commit**

```bash
git add docs/team-runbook.md backend/README.md
git commit -m "docs: document template matching model configuration"
```

## Task 12: Full Verification

**Files:**
- Verify backend and docs only

- [ ] **Step 1: Run focused template tests**

Run:

```bash
cd backend
npm test -- makeup-templates --runInBand
```

Expected: all makeup-template specs pass.

- [ ] **Step 2: Run recommendation compatibility tests**

Run:

```bash
cd backend
npm test -- recommendations.service.spec.ts --runInBand
```

Expected: pass. `/recommendations/generate` still maps generated templates into recommendation steps.

- [ ] **Step 3: Validate Prisma and build**

Run:

```bash
cd backend
npx prisma validate
npm run build
```

Expected: Prisma schema valid and Nest build exits 0.

- [ ] **Step 4: Run full backend tests**

Run:

```bash
cd backend
npm test -- --runInBand
```

Expected: all suites pass.

- [ ] **Step 5: Optional API smoke**

Start backend on a temporary port:

```bash
cd backend
PORT=13011 npm run start:dev
```

In another shell:

```bash
curl -fsS http://127.0.0.1:13011/health
curl -fsS -H 'Authorization: Bearer demo-token' http://127.0.0.1:13011/makeup-template-library/styles
curl -fsS -H 'Authorization: Bearer demo-token' -H 'Content-Type: application/json' \
  -d '{"rawUserInput":"明天通勤想画清透白开水妆"}' \
  http://127.0.0.1:13011/makeup-template-library/match-debug
```

Expected:

- `/health` returns healthy JSON.
- `/styles` returns the eight style families.
- `/match-debug` returns `selectedTemplateId` with `std_daily_clear_commute`.

- [ ] **Step 6: Commit any verification-only fixes**

If verification revealed small fixes, commit them:

```bash
git status --short
git add backend/src backend/prisma docs eval
git commit -m "fix: stabilize template matching verification"
```

If there were no fixes, do not create an empty commit.

## Self-Review Checklist

- Spec coverage:
  - Standard taxonomy: Tasks 2, 6, 11.
  - Embedding/reranker-style algorithm: Tasks 4, 5.
  - GPU-safe fallback: Tasks 4, 5, 11.
  - Existing generated template compatibility: Tasks 1, 8, 12.
  - Product slot matching: Task 7.
  - Debuggability and evaluation: Tasks 9, 10.
- Placeholder scan: searched for placeholder markers and vague implementation language; none remain outside this review note.
- Type consistency:
  - `TemplateMatchProfile`, `TemplateMatchResult`, `MakeupStepBlueprint`, and `ProductSlotBlueprint` are defined before they are consumed.
  - `sourceStandardTemplateId`, `matchScore`, and `matchTraceId` appear in schema, mapper, DTO, and generation service.
  - `operationAreas` appears in blueprint type, generated step persistence, mapper, and response DTO.
