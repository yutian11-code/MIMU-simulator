# Formal Template Library and Frontend Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the product-document first formal version: expand the standard makeup template library, make matching explanations visible in frontend, and verify the full user journey from natural-language request to executable steps.

**Architecture:** Keep the backend as the source of truth for template matching and generated templates. Extend the existing `RecommendationResult` contract so frontend pages can render template family, coverage, missing products, product slot status, completion criteria, failure feedback, and detection areas without adding a separate template app. Avoid new always-on GPU services; embedding/reranker remain optional.

**Tech Stack:** NestJS, Prisma, Jest, Expo React Native, TypeScript, TanStack Query, Zustand.

---

## File Structure

Backend:

- Modify `backend/src/makeup-templates/template-library/standard-template-library.data.ts`: expand styles, slots, step blocks, display metadata.
- Modify `backend/src/makeup-templates/template-library/standard-template-library.service.spec.ts`: assert formal library coverage.
- Modify `backend/src/makeup-templates/template-library/template-matching.service.spec.ts`: add broader matching cases.
- Modify `backend/src/makeup-templates/makeup-template-intent.service.ts`: add missing style/scene/effect terms from product docs.
- Modify `backend/src/makeup-templates/makeup-template-intent.service.spec.ts`: protect the new terms.
- Modify `backend/src/recommendations/recommendation.mapper.ts`: expose generated template metadata and slot fields through the existing recommendation response.
- Modify `backend/src/recommendations/dto/recommendation-response.dto.ts` and `backend/src/recommendations/dto/recommendation-step-response.dto.ts`: Swagger/types for new fields.
- Modify `backend/src/recommendations/recommendations.service.spec.ts`: verify generated metadata maps to frontend contract.
- Modify `eval/template_matching/cases.json`: expand smoke eval.

Frontend:

- Modify `frontend/types/recommendation.ts`: add fields rendered by UI.
- Modify `frontend/app/recommendation/result.tsx`: render template family, coverage, missing products, algorithm explanation.
- Modify `frontend/app/recommendation/products.tsx`: render product slot cards with matched/substitutable/missing states.
- Modify `frontend/app/recommendation/execution.tsx`: render completion criteria, failure feedback, AI detection area for current step.

Docs:

- Modify `docs/template-matching-test-guide.md`: update user journey and expected visible UI fields.

## Task 1: Backend formal library coverage

**Files:**
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.data.ts`
- Modify: `backend/src/makeup-templates/template-library/standard-template-library.service.spec.ts`

- [ ] **Step 1: Write failing library coverage tests**

Add tests that assert:

```ts
it('covers all formal style families with aliases and active templates', () => {
  const service = new StandardTemplateLibraryService();
  const styles = service.listStyles();
  const templates = service.listActiveTemplates();

  expect(styles.map((style) => style.family).sort()).toEqual([
    'ASIAN_MIXED',
    'CHINESE_STYLE',
    'DAILY_COMMUTE',
    'ELEGANT_LUXURY',
    'KOREAN_JAPANESE_GIRL',
    'SPECIFIC_VISUAL',
    'STAGE_CREATIVE',
    'WESTERN',
  ]);
  expect(styles.every((style) => style.aliases.length >= 4)).toBe(true);
  expect(templates).toHaveLength(8);
});

it('provides formal 5-step execution metadata and product slots for every template', () => {
  const service = new StandardTemplateLibraryService();

  for (const template of service.listActiveTemplates()) {
    expect(template.stepBlocks).toHaveLength(5);
    expect(template.stepBlocks.every((step) => step.operationAreas.length > 0)).toBe(true);
    expect(template.stepBlocks.every((step) => step.completionCriteria.length > 0)).toBe(true);
    expect(template.productSlots.length).toBeGreaterThanOrEqual(7);
    expect(template.productSlots.some((slot) => slot.slotCode === 'BASE_FOUNDATION')).toBe(true);
    expect(template.productSlots.some((slot) => slot.slotCode === 'SETTING_PRODUCT')).toBe(true);
    expect(template.productSlots.some((slot) => slot.slotCode === 'LIP_COLOR')).toBe(true);
  }
});
```

- [ ] **Step 2: Run tests and confirm RED**

Run: `npm test -- standard-template-library.service.spec.ts --runInBand`

Expected: FAIL because templates currently have only 5 slots and limited formal coverage assertions are missing.

- [ ] **Step 3: Expand formal template data**

Update `STANDARD_MAKEUP_STYLES` aliases/tags for all 8 families using the product docs. Expand `slotsFor()` to include at least:

```ts
BASE_PRIMER
BASE_FOUNDATION
BASE_CONCEALER
SETTING_PRODUCT
BROW_PENCIL
EYE_SHADOW_OR_LINER
CHEEK_BLUSH
CONTOUR_HIGHLIGHT
LIP_COLOR
MAKEUP_TOOL
```

Adjust `desiredEffect`, `desiredFinish`, `acceptableSubCategories`, and `fallbackInstruction` per style family.

- [ ] **Step 4: Run tests and confirm GREEN**

Run: `npm test -- standard-template-library.service.spec.ts --runInBand`

Expected: PASS.

- [ ] **Step 5: Commit backend library coverage**

```bash
git -C backend add src/makeup-templates/template-library/standard-template-library.data.ts src/makeup-templates/template-library/standard-template-library.service.spec.ts
git -C backend commit --amend --no-edit
```

## Task 2: Backend matching breadth and metadata mapping

**Files:**
- Modify: `backend/src/makeup-templates/makeup-template-intent.service.ts`
- Modify: `backend/src/makeup-templates/makeup-template-intent.service.spec.ts`
- Modify: `backend/src/makeup-templates/template-library/template-matching.service.spec.ts`
- Modify: `backend/src/recommendations/recommendation.mapper.ts`
- Modify: `backend/src/recommendations/dto/recommendation-response.dto.ts`
- Modify: `backend/src/recommendations/dto/recommendation-step-response.dto.ts`
- Modify: `backend/src/recommendations/recommendations.service.spec.ts`
- Modify: `eval/template_matching/cases.json`

- [ ] **Step 1: Write failing intent and matching tests**

Add tests for:

```ts
'新中式复古港风红唇妆' -> CHINESE_STYLE
'轻欧美截断眼妆和哑光底妆' -> WESTERN
'万圣节朋克舞台妆' -> STAGE_CREATIVE
'韩系水光甜妹约会妆' -> KOREAN_JAPANESE_GIRL
```

Expected selected families in matcher tests:

```ts
std_chinese_style
std_western
std_stage_creative
std_korean_japanese_girl
```

- [ ] **Step 2: Run tests and confirm RED**

Run:

```bash
npm test -- makeup-template-intent.service.spec.ts template-matching.service.spec.ts --runInBand
```

Expected: FAIL for missing or weak intent tags.

- [ ] **Step 3: Extend parser and matcher profile terms**

Add scene/style/effect terms:

```ts
RETRO, CHINESE, RED_LIP, CUT_CREASE, SMOKY, STAGE, CREATIVE, PUNK,
KOREAN, JAPANESE, DEWY, SOFT_EYE, CONTOUR, HIGH_INTENSITY
```

Keywords should include:

```text
新中式, 国风, 古典, 港风, 复古, 红唇, 轻欧美, 欧美截断, 截断, 烟熏,
朋克, 万圣节, 舞台, cosplay, 哥特, 韩系, 日系, 水光, 初恋, 纯欲
```

- [ ] **Step 4: Expose generated template metadata in recommendation response**

Ensure `RecommendationResult` includes:

```ts
generatedTemplateId
templateFamily
sourceStandardTemplateId
matchScore
productCoverageRate
missingProductTypes
personalizationReasons
```

Ensure each `RecommendationResultStep` includes:

```ts
sectionCode
stepGoal
visualChange
aiDetectionArea
completionCriteria
failureFeedback
productSlots
```

- [ ] **Step 5: Expand eval cases**

Add 10-12 cases across all 8 families to `eval/template_matching/cases.json`.

- [ ] **Step 6: Run tests and eval**

Run:

```bash
npm test -- makeup-templates recommendations.service.spec.ts --runInBand
python eval/template_matching/run_template_matching_eval.py --backend-url http://127.0.0.1:13001 --token demo-token
```

Expected: Jest PASS and eval total cases PASS.

- [ ] **Step 7: Commit backend matching**

```bash
git -C backend add src/makeup-templates src/recommendations
git -C backend commit --amend --no-edit
git add eval/template_matching/cases.json
git commit --amend --no-edit
```

## Task 3: Frontend result page visible algorithm explanation

**Files:**
- Modify: `frontend/types/recommendation.ts`
- Modify: `frontend/app/recommendation/result.tsx`

- [ ] **Step 1: Add TypeScript fields**

Extend frontend types with backend metadata:

```ts
templateFamily?: string;
sourceStandardTemplateId?: string;
matchScore?: number;
productCoverageRate?: number;
missingProductTypes?: string[];
personalizationReasons?: string[];
```

- [ ] **Step 2: Render visible template evidence on result page**

On `result.tsx`, add a compact panel near `ReasonCard` showing:

```text
命中模板：轻熟千金 / 特定视觉 / ...
产品覆盖：80%
缺失产品：散粉、眼线
算法依据：用户需求、已有产品、标准模板库
```

Use existing colors and avoid adding a new landing-like section.

- [ ] **Step 3: Run frontend typecheck**

Run: `npx tsc --noEmit`

Expected: PASS.

- [ ] **Step 4: Commit frontend result experience**

```bash
git -C frontend add types/recommendation.ts app/recommendation/result.tsx
git -C frontend commit --amend --no-edit
```

## Task 4: Frontend product slot and execution visibility

**Files:**
- Modify: `frontend/app/recommendation/products.tsx`
- Modify: `frontend/app/recommendation/execution.tsx`

- [ ] **Step 1: Render product slot states**

On product list page, render `productSlots` grouped under steps. Each slot should show:

```text
slotCode / subCategory
matched | substitutable | missing
matchReason
fallbackInstruction
```

Missing slots must be visible even when a step has no matched product.

- [ ] **Step 2: Render execution criteria**

On execution page, for the active step show:

```text
完成标准 completionCriteria
易错提醒 failureFeedback
AI 检测区域 aiDetectionArea
视觉变化 visualChange
```

- [ ] **Step 3: Run frontend checks**

Run:

```bash
npx tsc --noEmit
npm run lint
```

Expected: PASS.

- [ ] **Step 4: Commit frontend execution visibility**

```bash
git -C frontend add app/recommendation/products.tsx app/recommendation/execution.tsx
git -C frontend commit --amend --no-edit
```

## Task 5: End-to-end verification and docs

**Files:**
- Modify: `docs/template-matching-test-guide.md`

- [ ] **Step 1: Update docs**

Document the now-visible frontend panels:

```text
推荐结果页：命中模板、覆盖率、缺失产品、推荐理由
产品清单页：产品槽位状态和 fallback
执行页：完成标准、错误反馈、AI 检测区域
```

- [ ] **Step 2: Run backend full verification**

Run:

```bash
cd backend
npm test -- makeup-templates --runInBand
npm test -- recommendations.service.spec.ts --runInBand
npm run build
npm test -- --runInBand
```

Expected: PASS.

- [ ] **Step 3: Run frontend full verification**

Run:

```bash
cd frontend
npx tsc --noEmit
npm run lint
```

Expected: PASS.

- [ ] **Step 4: Run API smoke**

Run:

```bash
python eval/template_matching/run_template_matching_eval.py --backend-url http://127.0.0.1:13001 --token demo-token
curl -fsS -H 'Authorization: Bearer demo-token' -H 'Content-Type: application/json' -d '{"rawUserInput":"面试需要轻熟知性优雅妆，不要太浓","generationSource":"manual-test"}' http://127.0.0.1:13001/makeup-templates/generate | python -m json.tool | sed -n '1,120p'
```

Expected: eval PASS and generated template includes source standard template, coverage, missing product types, steps, product slots, completion criteria, failure feedback.

- [ ] **Step 5: Commit docs**

```bash
git add docs/template-matching-test-guide.md docs/superpowers/plans/2026-05-10-formal-template-library-frontend.md
git commit --amend --no-edit
```

## Self-Review

- Scope matches user-approved items 1-5: formal library, algorithm enhancement, frontend complete visible experience, user journey, tests.
- VLM/reference image parsing and full admin CMS are intentionally excluded.
- The plan preserves the existing one-commit-per-repo shape by amending the current feature commits.
- Frontend work is visible in existing pages rather than hidden in types only.
