# Public Video Template Library Design

## Decision

Build a public-video-driven template ingestion pipeline for MIMU that can:

- collect public makeup tutorial videos from multiple platforms,
- preserve raw source evidence locally,
- automatically convert videos into 5-step executable template drafts aligned with MMU standard step codes,
- automatically publish at least 30 machine-approved templates into the current formal template library without requiring human intervention before launch,
- keep a larger candidate pool for later manual verification and expansion.

This phase treats public videos as evidence sources, not as the final product asset. The final deliverable is a structured template library that the current backend, recommendation flow, and 5-step execution flow can use directly.

The user confirmed these constraints:

- public sources may come from domestic and overseas platforms,
- raw original video files must be retained locally for traceability,
- human review is required eventually, but launch readiness must not depend on human review,
- tomorrow's hard requirement is:

```text
AutoReady30 >= 30
```

Where `AutoReady30` means at least 30 templates that are automatically generated, automatically validated, written into the current formal template library, and directly usable by the current product flow.

## Scope

In scope:

- build a multi-platform public video candidate collection flow,
- retain raw source evidence and local original files,
- extract frames, audio, OCR hints, ASR text, and visual summaries,
- generate structured 5-step MMU-aligned template drafts,
- auto-score and auto-filter drafts into launch-ready templates,
- write launch-ready templates into the current formal template library schema,
- keep a larger draft and candidate pool for future manual verification,
- support more than 30 final templates if enough good candidates are found,
- prioritize styles useful for current demo, recommendation, and evaluation flows.

Out of scope:

- publishing source videos inside the product as a long-term licensed media catalog,
- building a full legal rights management system,
- using private or login-only content as a required input path,
- creating a perfect final editorial library before launch,
- replacing the current 5-step execution flow with 14 visible steps,
- training new foundation models.

## Success Criteria

The implementation is successful only if all of the following are true.

### Launch readiness

- At least 30 templates are automatically ingested into the formal template library.
- These templates can be returned by the current backend library APIs.
- These templates can be used by the current matching and recommendation flow.
- These templates are structurally valid for the current 5-step execution UI.
- No human approval step is required before the first 30 templates become usable.

### Evidence retention

- Every usable template can be traced back to at least one retained public source video.
- Each retained source has platform, URL, author, title, crawl timestamp, local raw file path, and accessibility status.
- Each template stores references to evidence frames and extraction metadata.

### Coverage

- Templates cover multiple style families rather than clustering in one category.
- P1 and P2 templates are both produced.
- P3 templates may also be generated, but are hidden from default product presentation.

### Quality bar

Each auto-ready template must satisfy all of these:

- complete 5-step execution structure,
- every step mapped to MMU standard step codes,
- every step has at least one evidence frame,
- style family confidence passes threshold,
- duplicate or near-duplicate templates are filtered,
- product slot suggestions meet a minimum executable threshold,
- template survives API and smoke validation.

## Operating Model

The system should separate four layers clearly.

### 1. Source candidate pool

This is the public video discovery layer.

It stores:

- platform,
- public URL,
- author name,
- title,
- publish time when available,
- crawl time,
- raw video retention status,
- raw local file path when downloaded,
- visibility status,
- source notes,
- machine pre-screen result.

This layer is intentionally larger and noisier than the final formal library.

### 2. Extraction evidence layer

This is the machine-readable evidence package produced from a downloaded source.

It stores:

- key frames,
- sampled timeline frames,
- extracted audio,
- ASR transcript,
- OCR text,
- shot segmentation,
- visual summary,
- candidate style signals,
- candidate step segmentation,
- extraction errors and latency.

This layer supports reproducibility and debugging.

### 3. Template draft pool

This is where the system translates evidence into structured MIMU/MMU templates.

It stores:

- 5-step draft template,
- MMU standard step code mapping,
- style family,
- scene,
- difficulty estimate,
- product slot suggestions,
- evidence frame references,
- auto-quality score,
- dedup score,
- launch priority class,
- publish eligibility state.

### 4. Formal template library

Only machine-approved templates that pass launch thresholds are written into the existing formal library:

- `StandardMakeupTemplate`
- `StandardMakeupTemplateVersion`
- `StandardTemplateStepBlock`
- `StandardTemplateProductSlot`

This avoids polluting the formal library with low-confidence draft content.

## Source Policy

The selected source policy is:

```text
public multi-platform collection
with internal-use evidence retention
and formal-library publication of structured templates only
```

Because the current use level is internal algorithm and product testing, the system should:

- preserve original raw video files locally,
- preserve public source metadata,
- preserve crawl-time access status,
- not require source video rendering in the product,
- not assume perpetual public availability of the source URL,
- treat the source as evidentiary input rather than product media.

The pipeline should attempt sources in this order:

1. public, high-signal, accessible video pages,
2. professional creators and official/brand accounts when available,
3. broader creator pools when needed for diversity and volume.

The implementation must not depend on any single platform being stable.

## Coverage Strategy

The goal is not just 30 templates. The goal is a usable and diverse launch set.

### Style families

The auto-ready set should aim to cover at least these families already reflected by the MMU taxonomy:

- daily commute / clear natural,
- Korean or Japanese sweet,
- elegant luxury / light mature,
- Asian mixed / Thai-inspired,
- Chinese style / retro,
- western glam / smokey,
- stage creative,
- specific visual / camera-ready / idol / Y2K.

### Priority classes

All three classes are produced, but only P1 and P2 are meant for immediate presentation.

- `P1`: immediate launch/demo/eval priority. High confidence, highly readable, strong 5-step execution value.
- `P2`: good quality, displayable, useful for expansion and testing, but not necessarily first-wave highlight content.
- `P3`: retained in the draft or extended pool, useful for later growth, not shown by default.

The user explicitly wants P1, P2, and P3 all to be produced. P2 can be displayed. P3 should default to hidden.

### Quantity targets

Recommended target ranges:

- candidate pool: 80-120 public videos,
- extraction-complete pool: 60-90 sources,
- template draft pool: 45-60 drafts,
- formal auto-ready pool: at least 30 templates.

The system may exceed 30 final templates if quality remains acceptable.

## End-To-End Pipeline

The pipeline has six stages.

### Stage 1: Candidate discovery

Collect candidate public videos and lightweight metadata before full download.

Selection heuristics:

- makeup tutorial or makeup demonstration,
- face visible enough for step interpretation,
- visible progression across multiple steps,
- not pure product ad stills,
- not slideshow-only unless the step sequence is strong,
- not too short to infer the 5-step structure,
- not too chaotic for automatic parsing.

Outputs:

- `source_candidate` records,
- platform metadata,
- crawl snapshot metadata,
- initial quality heuristics.

### Stage 2: Raw source retention

Download the raw original file for candidates that pass pre-screening.

Requirements:

- deterministic source IDs,
- persistent raw file storage outside git,
- checksum or content hash,
- retry-safe and idempotent naming,
- failure status when download becomes unavailable.

Recommended storage layout:

```text
/storage/nvme3/shushanfu/MIMU-colleague/data/template_sources/
  raw_videos/<platform>/<source_id>.<ext>
  metadata/<source_id>.json
  frames/<source_id>/
  audio/<source_id>/
  ocr/<source_id>.json
  asr/<source_id>.json
  drafts/<draft_id>.json
```

### Stage 3: Multimodal extraction

Generate an evidence package from the retained video.

Recommended automatic operations:

- probe duration, resolution, fps,
- sample timeline frames,
- detect shot boundaries or major visual transitions,
- extract audio,
- run local ASR,
- run OCR on selected frames when text overlays exist,
- run VLM or visual summarization on key frames or step windows,
- derive style signal candidates.

Outputs:

- evidence frames,
- transcript summary,
- OCR summary,
- candidate step windows,
- visual style signals,
- extraction confidence.

### Stage 4: Draft template generation

Convert the evidence package into a 5-step executable draft.

The draft generator must:

- compress the observed tutorial into 5 user-facing blocks,
- map each block back to MMU standard step codes,
- assign operation areas,
- derive step goals,
- derive completion criteria,
- derive failure feedback,
- derive next-step conditions,
- infer product slot categories and recommended subcategories,
- estimate style family, scene, difficulty, and estimated execution time.

This stage should prefer structured outputs and explicit confidence values over free-form text.

### Stage 5: Automatic quality gating

This is the key stage for tomorrow's launch target.

Only drafts that pass machine gates enter `AutoReady30`.

Suggested gates:

- full 5-step structure present,
- no empty `standardStepCodes`,
- no empty step names or step goals,
- evidence frame count per step above minimum,
- style-family confidence above threshold,
- product slots meet minimum executable coverage,
- dedup similarity below threshold,
- not flagged as corrupted, unavailable, or structurally incomplete.

Suggested statuses:

- `draft_failed`
- `draft_needs_review`
- `auto_ready`
- `published_hidden`
- `published_visible`

### Stage 6: Formal publish

Machine-approved drafts are written to the formal template library automatically.

Publishing behavior:

- create or update a machine-owned standard template,
- create a version entry with source references,
- write 5 step blocks,
- write product slots,
- attach source trace references,
- assign priority class,
- set default visibility based on priority class.

Default visibility:

- P1: visible
- P2: visible
- P3: hidden

## AutoReady30 Contract

This contract exists specifically to remove ambiguity from tomorrow's launch requirement.

`AutoReady30` is defined as:

```text
count(
  machine-published formal templates
  where source evidence exists
  and template passes structural validation
  and template passes launch quality gates
  and template is readable by current APIs
  and template is executable by current 5-step flow
) >= 30
```

A template does not count toward `AutoReady30` if any of the following is true:

- raw video is missing,
- source metadata is missing,
- fewer than 5 execution steps are generated,
- one or more steps have no MMU mapping,
- one or more steps lack evidence frames,
- product slot structure is unusable,
- DB publish fails,
- recommendation/template APIs cannot read it,
- smoke validation fails.

## Database And Storage Design

The formal template schema already exists. New ingestion-specific persistence should remain separate from formal template tables.

### New ingestion-oriented entities

Recommended new entities:

- `PublicVideoSource`
- `PublicVideoAsset`
- `PublicVideoExtraction`
- `PublicVideoTemplateDraft`
- `PublicVideoTemplateEvidence`
- `PublicVideoPublishRun`

Suggested responsibilities:

- `PublicVideoSource`: canonical source URL and metadata.
- `PublicVideoAsset`: local raw file info and checksum.
- `PublicVideoExtraction`: technical extraction outputs and status.
- `PublicVideoTemplateDraft`: generated 5-step structured draft and scores.
- `PublicVideoTemplateEvidence`: step-level frame references and evidence links.
- `PublicVideoPublishRun`: batch-level publish and validation run records.

These can later be collapsed or adjusted during implementation, but the design intent is to keep:

- source provenance,
- extraction state,
- draft state,
- publish state,

as distinct concerns.

### Formal library mapping

Each published machine-generated template should store:

- source source ID,
- source platform,
- source URL,
- source crawl timestamp,
- draft ID,
- publish run ID,
- machine publish flag,
- priority class,
- auto-quality score,
- dedup cluster or source-family reference.

This can be stored either in dedicated columns where justified or in version metadata / JSON fields if that is more compatible with the current schema.

## Product And API Behavior

The current system already supports formal template management and generated template usage. This phase should extend that system without changing the current user-facing 5-step contract.

Required capabilities:

- candidate and draft data must stay internal by default,
- formal published templates must be visible through existing template APIs,
- recommendation and matching flows must be able to consume the new formal templates,
- frontend template management should be able to distinguish:
  - machine-generated template,
  - priority class,
  - source evidence presence,
  - visibility status.

Recommended API additions or extensions:

- internal ingestion run status endpoint,
- internal source/draft browse endpoint,
- internal publish summary endpoint,
- template response fields for:
  - `sourcePlatform`
  - `sourceUrl`
  - `priorityClass`
  - `machineGenerated`
  - `autoQualityScore`
  - `evidenceAvailable`

These additions are for operator visibility, not end-user exposure by default.

## Model And GPU Strategy

The user allowed GPU 0-7 and suggested using subagents for sidecar tasks.

Recommended resource strategy:

- use lightweight CPU or low-overhead workers for candidate crawling and metadata fetch,
- use shared local ASR for transcript generation,
- use shared VLM models from `/storage/nvme3/shushanfu/checkpoint` for visual summaries and draft generation support,
- reserve heavier VLM calls for key frames or step windows rather than whole-video dense inference,
- use parallel workers for extraction, but limit per-run concurrency to avoid starving preview, coach, and other business services.

The pipeline must support degradation:

- if OCR fails, continue,
- if ASR fails, continue with vision-only draft generation but lower confidence,
- if a platform fetch fails, mark source unavailable and continue the batch,
- if one source fails extraction, do not block the publish run.

## Subagent Work Decomposition

The user explicitly allowed delegated frame extraction and sidecar work.

Recommended decomposition for implementation:

- `source discovery worker`: platform-specific candidate collection and metadata normalization.
- `download worker`: raw video retention, checksum, and file layout.
- `extraction worker`: frames, audio, ASR, OCR, shot segmentation.
- `draft generation worker`: style classification, step compression, MMU mapping, slot suggestions.
- `publish/validation worker`: DB writes, structural checks, dedup checks, API smoke tests.
- main orchestration layer: batching, retries, quality thresholds, summary, and failure accounting.

These workers should have disjoint ownership boundaries so they can run in parallel safely.

## Quality Rules

Machine quality gating should be explicit and reproducible.

### Structural rules

- exactly 5 execution blocks,
- every block has a non-empty title,
- every block has non-empty `standardStepCodes`,
- every block has `stepGoal`,
- every block has `completionCriteria`,
- every block has `nextStepCondition`,
- product slot data is present for executable categories.

### Evidence rules

- each step has at least one evidence frame,
- source URL and local raw file path are present,
- extraction timestamps and batch IDs are retained,
- the source remains traceable even if the public URL later becomes unavailable.

### Diversity rules

- no large cluster of near-duplicate templates in the auto-ready set,
- same creator or same video family should not dominate the first 30,
- at least multiple style families must be represented.

### Launch priority rules

- P1: top quality, immediately demo/eval friendly.
- P2: solid quality, displayable, useful for breadth.
- P3: retained but hidden by default.

All P1, P2, and P3 should be produced. Only P3 is hidden by default.

## Validation And Testing

This phase needs both data-pipeline validation and product validation.

### Pipeline validation

- candidate collection can produce a large enough candidate pool,
- raw video files are retained,
- extraction artifacts are generated deterministically,
- draft generation completes with structured outputs,
- publish run can create formal templates automatically.

### Product validation

For templates counted in `AutoReady30`, run automated checks that verify:

- template list APIs return them,
- template detail APIs return them,
- recommendation flow can reference them,
- 5-step execution payload shape is valid,
- MMU standard step code mapping is present,
- frontend template list and detail pages can render them without shape errors.

### Batch acceptance check

A publish run is considered launch-ready only if:

```text
AutoReady30 >= 30
```

and:

- zero fatal schema errors,
- zero unreadable published templates,
- zero broken step mappings,
- source evidence exists for every counted template.

## Risks

### Platform instability

Public platforms may rate-limit, change markup, or block download methods.

Mitigation:

- isolate platform adapters,
- support retries and unavailable status,
- do not depend on one platform.

### Weak automatic parsing

Some videos will be visually noisy, heavily edited, or poorly narrated.

Mitigation:

- large candidate pool,
- strict quality gating,
- evidence-backed draft scoring,
- no direct publish from low-confidence drafts.

### Quantity failure before launch

The system may collect many candidates but fail to publish 30 usable templates.

Mitigation:

- over-collect candidates,
- allow P2 displayable templates into the launch set,
- batch publish iteratively until `AutoReady30` passes threshold,
- prioritize sources with clearer step structure first.

### Deduplication failure

Large candidate pools may produce many near-identical daily makeup templates.

Mitigation:

- dedup by source hash,
- dedup by visual-textual similarity,
- style-family diversity caps in the auto-ready set.

## Rollout Strategy

Phase 1 for tomorrow's launch:

- build candidate ingestion,
- retain raw sources,
- run extraction,
- generate drafts,
- auto-publish at least 30 machine-approved formal templates,
- validate current APIs and UI compatibility.

Phase 2 after launch:

- add richer operator review tools,
- improve style balancing and dedup logic,
- expand candidate pool and source adapters,
- promote more P2 templates and selectively review P3.

## Final Requirement Summary

The system to be built is not a manual curation helper. It is an automated ingestion and publication pipeline with traceable evidence retention.

The hard launch requirement is:

```text
Tomorrow, without human intervention in the approval loop, the system must automatically produce and publish at least 30 directly usable formal makeup templates for the current MIMU product flow.
```

Human review remains important for long-term quality, but it is not a precondition for the first launch-ready 30 templates.
