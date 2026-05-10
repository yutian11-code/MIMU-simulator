# Formal Makeup Template Library Platform Design

## Background

The current MVP already proves the core direction from the product documents:

```text
user demand + user products + user profile + standard template structure
= personalized makeup template
```

The next step is to turn the current code-backed standard template library into a formal platform:

- Standard template definitions are stored in PostgreSQL, not hard-coded constants.
- Users can edit and publish templates directly.
- Review state is reserved for later, but it does not block publishing in this version.
- Templates are versioned and can be rolled back.
- The frontend includes a complete management experience, not only API/Swagger access.
- Recommendation and template matching read published DB templates while preserving the generated-result library.

This design follows:

- `docs/妆容生成搭建模板.docx`
- `docs/MMU模板库标准构建(1).docx`
- The approved implementation option: **Full Slice**.

## Goals

1. Store the product-standard template library in the database.
2. Seed the initial library from the two product documents.
3. Preserve the existing generated template data model and recommendation flow.
4. Move template matching from code constants to published database templates.
5. Allow users to create, edit, publish, archive, and roll back standard templates.
6. Provide a frontend management page for template operations.
7. Keep review/audit state extensible without implementing an approval workflow now.
8. Keep the online matching path stable with clear fallback behavior.

## Non-Goals

1. No multi-person approval workflow in this version.
2. No role-based permission matrix beyond the current authenticated user model.
3. No heavy analytics dashboard in the first formal slice.
4. No bulk Excel import UI unless the seed script later needs it.
5. No new GPU-resident model service dedicated only to template management.
6. No replacement of the user-facing generated-result library.

## Product Model

The platform separates two concepts:

### Standard Template Library

This is the editable, versioned source library created from product standards. It contains style families, standard steps, product slots, face areas, face shapes, difficulty rules, and reusable template structures.

It answers:

- What standard makeup structures exist?
- Which templates are published and matchable?
- Which products and steps does each template require?
- Which version is currently active?

### Generated Result Library

This is the existing user-specific output library. It stores personalized generated templates, product matches, generation requests, snapshots, match traces, execution events, and feedback.

It answers:

- What did this user ask for?
- Which standard template version was used?
- Which user products were matched or missing?
- Did the user complete, skip, edit, replace, or dislike anything?

The standard library feeds generation; it is not the final product shown to users as a fixed template catalog.

## Data Model

### Enums

Add Prisma enums or equivalent string constraints:

- `TemplateStatus`: `draft`, `published`, `archived`
- `TemplateReviewStatus`: `not_required`, `pending`, `approved`, `rejected`
- `TemplateVersionStatus`: `draft`, `published`, `superseded`, `rolled_back`, `archived`
- `TemplateVisibility`: `private`, `team`, `public`
- `TemplateSource`: `seed`, `user_created`, `user_edited`, `rollback`

Review defaults to `not_required`. Publishing is allowed when review is `not_required`.

### StandardMakeupStyle

Stores standardized style families and aliases from `MMU模板库标准构建(1).docx`.

Key fields:

- `id`
- `styleCode`
- `displayName`
- `family`
- `aliases`
- `positiveTags`
- `negativeTags`
- `baseFinish`
- `colorPalette`
- `intensityLevel`
- `defaultDifficulty`
- `typicalScenes`
- `isActive`
- `createdAt`
- `updatedAt`

Initial seed includes 8 families:

- daily commute
- Korean/Japanese girl
- elegant luxury
- Asian mixed
- Chinese style
- Western
- stage creative
- specific visual

### StandardMakeupTemplate

Stores the logical template identity. This is the object listed in the management page.

Key fields:

- `id`
- `templateCode`
- `ownerUserId`
- `currentVersionId`
- `displayName`
- `description`
- `status`
- `reviewStatus`
- `visibility`
- `source`
- `createdBy`
- `updatedBy`
- `publishedAt`
- `archivedAt`
- `createdAt`
- `updatedAt`

`templateCode` follows the accepted rule:

```text
std_<style_family_or_business_slug>
```

Examples:

- `std_daily_clear_commute`
- `std_elegant_luxury`
- `std_korean_japanese_girl`

### StandardMakeupTemplateVersion

Stores immutable-ish version snapshots. Editing a published template creates or updates a draft version. Publishing marks the draft as current.

Key fields:

- `id`
- `templateId`
- `version`
- `status`
- `displayName`
- `styleId`
- `styleFamily`
- `primaryScene`
- `styleTags`
- `effectTags`
- `difficultyBaseScore`
- `minSkillLevel`
- `estimatedTimeMinutes`
- `templateDescription`
- `visualDescription`
- `templatePayload`
- `changeSummary`
- `createdBy`
- `publishedBy`
- `publishedAt`
- `createdAt`
- `updatedAt`

`templatePayload` stores the canonical JSON snapshot for rollback and future diffing. It should include steps, slots, difficulty config, face rules, and operation areas.

### StandardTemplateStepBlock

Stores the 14-step standard system and compressed execution blocks.

Key fields:

- `id`
- `versionId`
- `stepCode`
- `stepOrder`
- `sectionCode`
- `stepName`
- `standardStepCodes`
- `operationAreas`
- `stepGoal`
- `instructionTemplate`
- `visualChange`
- `aiDetectionArea`
- `completionCriteria`
- `failureFeedback`
- `nextStepCondition`
- `difficultyScore`
- `editableByUser`

The management page edits these fields.

### StandardProductSlotSpec

Stores product slot requirements attached to a template version and step block.

Key fields:

- `id`
- `versionId`
- `stepBlockId`
- `slotCode`
- `category`
- `subCategory`
- `acceptableSubCategories`
- `substituteSlotCodes`
- `requiredLevel`
- `desiredEffect`
- `desiredColorFamily`
- `desiredFinish`
- `fallbackInstruction`
- `sortOrder`

These records replace the current code-only `slotsFor(styleId)` output.

### TemplateTaxonomy Tables

To avoid overfitting the first migration, use compact taxonomy tables:

- `TemplateProductCategory`
- `TemplateOperationArea`
- `TemplateFaceShape`
- `TemplateDifficultyRule`

They store the standards from the second document:

- product categories and subcategories
- face operation areas
- standardized face shapes
- action difficulty base scores
- special technique bonus rules

The first implementation can seed these tables and use them in validation and dropdowns.

### Generated Template Linkage

Extend existing generated result rows to keep version provenance:

- `GeneratedMakeupTemplate.sourceStandardTemplateId`
- `GeneratedMakeupTemplate.sourceStandardTemplateVersionId`
- `GeneratedMakeupTemplate.matchScore`
- `GeneratedMakeupTemplate.matchTraceId`

This lets future analytics answer which standard template version produced successful generated results.

## Versioning And Rollback

### Editing

1. If the current template is draft, update the current draft version.
2. If the template is published, create a new draft version from the current published version.
3. The editor modifies the draft version.
4. The published version remains matchable until the draft is published.

### Publishing

Publishing a draft version:

1. Validates required fields, steps, and slots.
2. Marks the previous published version as `superseded`.
3. Marks the draft version as `published`.
4. Updates `StandardMakeupTemplate.currentVersionId`.
5. Sets template status to `published`.
6. Writes a template event/audit row.

Review status is checked only to support future policy:

- `not_required`: publish allowed.
- `approved`: publish allowed.
- `pending`, `rejected`: reserved for future; first version may block only if explicitly set by admin data.

Default behavior creates `not_required`, so users can publish directly.

### Rollback

Rollback does not mutate old versions. It creates a new version copied from the selected historical version:

```text
v5 rollback from v2 -> create v6 with sourceVersionId = v2, status = published
```

This preserves auditability and keeps version numbers monotonic.

## Backend API

All routes live under a new admin-facing namespace:

```text
/makeup-template-library
```

The current user auth can protect the routes. Fine-grained roles are not part of this slice.

### Public/Management Reads

- `GET /makeup-template-library/styles`
- `GET /makeup-template-library/taxonomy`
- `GET /makeup-template-library/templates`
- `GET /makeup-template-library/templates/:templateId`
- `GET /makeup-template-library/templates/:templateId/versions`
- `GET /makeup-template-library/templates/:templateId/versions/:versionId`

List filters:

- `status`
- `reviewStatus`
- `styleFamily`
- `scene`
- `keyword`
- `ownerUserId`

### Management Writes

- `POST /makeup-template-library/templates`
- `PUT /makeup-template-library/templates/:templateId/draft`
- `POST /makeup-template-library/templates/:templateId/publish`
- `POST /makeup-template-library/templates/:templateId/archive`
- `POST /makeup-template-library/templates/:templateId/rollback`
- `POST /makeup-template-library/seed`

`/seed` is idempotent and intended for local/dev/staging setup. It should not overwrite user-created templates unless explicitly requested.

### Matching Debug

Keep or evolve the existing debug route:

- `POST /makeup-template-library/match-debug`

It should return:

- selected template ID
- selected version ID
- candidate list
- score breakdown
- degraded/model status
- user profile used for matching

## Matching Algorithm Changes

The existing `TemplateMatchingService` becomes database-backed.

### Candidate Source

Current:

```text
STANDARD_MAKEUP_TEMPLATES constant
```

New:

```text
published StandardMakeupTemplateVersion rows
```

The service maps DB rows into the existing `StandardMakeupTemplate` domain type for a low-risk migration.

### Score Formula

Keep the current mixed scoring formula:

```text
embedding similarity
reranker relevance
style match
scene match
product coverage
user profile fit
history preference
difficulty penalty
missing required slot penalty
```

The DB-backed service must include `templateVersionId` in candidates and traces.

### Fallback

If no published DB template exists:

1. Return a clear application error in management/debug routes.
2. For user recommendation generation, fall back to seeded in-memory emergency templates only if configured.
3. Emit degraded model status in `TemplateMatchTrace`.

Production expectation is that DB seed exists; fallback is for local resilience.

## Frontend Management Experience

Add a management entry that fits the existing Expo Router app. A practical route group:

```text
app/template-library/index.tsx
app/template-library/[templateId].tsx
app/template-library/[templateId]/versions.tsx
app/template-library/new.tsx
```

If nested dynamic routes are too risky in the current router setup, use query-param routes:

```text
app/template-library/index.tsx
app/template-library/detail.tsx
app/template-library/versions.tsx
app/template-library/new.tsx
```

### List Page

Shows:

- template name
- style family
- status
- review status
- current version
- published time
- owner/editor
- coverage of steps and slots

Actions:

- create template
- open detail
- filter by status/style/search

### Detail/Edit Page

Sections:

- basic info
- style and scene
- difficulty and time
- steps
- product slots
- operation areas
- detection and completion criteria

Actions:

- save draft
- publish
- archive
- open version history

Validation appears inline.

### Version History Page

Shows:

- version number
- status
- change summary
- created by
- published by
- published at

Actions:

- view version snapshot
- rollback to this version

### UX Constraints

This is an operational tool, not a marketing page. It should be dense, clear, and fast:

- no decorative hero page
- no card-within-card layouts
- stable table/list dimensions
- clear icon buttons with labels where needed
- no white-on-white controls
- all mutation states show loading and errors

## Data Flow

### Seed Flow

1. Seed styles and taxonomy from both product documents.
2. Seed 8 standard templates.
3. For each template, create version 1.
4. Create 5 compressed user-facing step blocks from the 14-step standard.
5. Create product slots from the standardized product category system.
6. Publish the seeded version by default.

### User Recommendation Flow

1. User generates recommendation.
2. Backend parses intent and snapshots user/profile/product data.
3. Matching service reads published DB template versions.
4. Matching service selects one version and records trace.
5. Blueprint adapter converts standard version into generated steps.
6. Slot matcher matches user products.
7. Generated result library stores personalized output.
8. Existing recommendation response includes generated template fields.

### Management Flow

1. User opens template management list.
2. User edits draft or creates new template.
3. User saves draft.
4. User publishes directly.
5. Matching immediately sees the new published version.
6. If needed, user rolls back to a historical version.

## Error Handling

- Missing seed data: management routes return 404/empty state; recommendation route uses configured fallback or returns a clear service error.
- Invalid publish request: return validation errors for missing steps, missing slots, invalid style, or empty display name.
- Concurrent edit: use `updatedAt` or version ID checks to prevent silently overwriting another draft.
- Rollback to missing version: return 404.
- Rollback to archived template: require unarchive or return a clear validation error.
- Matching model timeout: mark `degraded = true` and fall back to lexical/rule score.
- Frontend mutation failure: keep draft data on screen and show retry action.

## Testing

### Backend

- Prisma migration validates.
- Seed is idempotent.
- Seed creates 8 templates, 8 current published versions, steps, slots, style rows, taxonomy rows.
- Create template writes draft version.
- Edit published template creates a new draft version.
- Publish supersedes old published version and updates current version.
- Rollback creates a new version from history and publishes it.
- Matching reads DB templates, not constants.
- Recommendation generation still writes `GeneratedMakeupTemplate`, steps, slots, match trace, and recommendation.
- Existing template event tests continue to pass.

### Frontend

- TypeScript passes.
- Template list renders seeded templates.
- Detail page can edit and save draft.
- Publish action updates status.
- Version page lists historical versions.
- Rollback action updates current version.
- Error states are visible and controls remain clickable.

### End-to-End Smoke

1. Run seed.
2. Open template management page.
3. Edit `std_elegant_luxury` display name or step copy as a draft.
4. Publish the draft.
5. Generate a recommendation for "面试轻熟知性妆，不要太浓".
6. Confirm the generated template points to the published DB template version.
7. Roll back `std_elegant_luxury`.
8. Generate again and confirm trace uses the new current version.

## Acceptance Criteria

The formal platform is considered complete when:

1. Standard templates are stored in PostgreSQL and no longer only in source constants.
2. Initial templates are seeded from the two product documents.
3. Users can edit and publish templates without review.
4. Review status is present for future workflow.
5. Users can roll back a template to a previous version.
6. Frontend management pages support list, detail edit, publish, versions, and rollback.
7. Matching service uses published DB templates.
8. Generated user templates preserve source template and source version provenance.
9. Existing recommendation and execution flows still work.
10. Backend and frontend verification commands pass.

## Implementation Notes

The safest implementation order is:

1. Add DB schema and seed data.
2. Add service layer and admin API.
3. Switch matching service to DB-backed library.
4. Add frontend service/types.
5. Build management pages.
6. Add regression tests and update the user journey document.

This keeps the current generated-result chain usable while the formal library is introduced.
