# Template Library Production Ops Design

## Source Of Truth

For template structure, style taxonomy, and long-term product direction:

- `docs/MMU模板库标准构建(1).docx` is the primary source of truth.
- `docs/妆容生成搭建模板.docx` is supporting context.

This spec is narrower. It does not redesign MMU. It defines the work required
to move the current template library from a roadshow-capable state into a state
where operators can use it at scale without relying on engineers or direct
database inspection.

## Current Snapshot

This snapshot reflects the live system state observed on 2026-05-14.

- Standard template library rows: `139`
- Published templates: `108`
- Archived templates: `31`
- Draft templates: `0`
- `qualityTier` counts in ops summary: `P1=0`, `P2=0`, `P3=0`
- Pending quality review count: `139`
- Pending generated-result count: `107`
- Matching stack health: embedding, reranker, VLM, ASR, and ComfyUI are all
  healthy
- Core user path health:
  - recommendation generation works
  - template matching works
  - makeup preview smoke works
  - five-step voice evaluation works

The current blocker is not model availability. The blocker is that the formal
template library contains many machine-published rows that have not passed an
operator-controlled quality gate.

## Problem Statement

The system currently has platform capability, but not production operating
discipline.

Today the main risks are:

1. Unreviewed public-video templates are already in `published` state.
2. Matching can still see too much noisy machine content unless stronger
   production eligibility rules are applied.
3. Operators do not yet have a backlog-first workflow or batch actions for
   cleaning large queues.
4. Generated results have a pending backlog but no explicit operator
   disposition state for rejection, deferment, or archive.
5. The current ops UI is suitable for demonstrations, not for sustained daily
   template operations.

If operators start using the current system at scale, they will spend time
fighting queue noise, and production matching quality will drift.

## Decision

Adopt a **production-safety-first operator model**.

That means:

1. A template is not production-eligible just because it is `published`.
2. Production matching must read from a stricter live subset of the library.
3. Machine-generated and generated-result backlog handling must become
   operator-driven, batch-capable, and auditable.
4. P0 focuses on preventing bad content from reaching matching and making the
   backlog operable.
5. P1 focuses on improving operator throughput, ranking quality, and content
   hygiene after the production gate exists.

## Alternatives Considered

### Option A: Keep the current model and ask operators to review one by one

Pros:

- almost no code change

Cons:

- not viable for 139+ templates and 107+ generated results
- noisy published templates remain risky before review finishes
- operators still depend on engineers for cleanup and triage

Rejected.

### Option B: Minimal production hardening plus batch operator tooling

Pros:

- directly addresses launch risk
- reuses current schema and current module boundaries
- keeps implementation scoped to a realistic next slice

Cons:

- still leaves more advanced ranking and analytics work for follow-up

Recommended.

### Option C: Build a full workflow engine with approval pipelines and complex task orchestration

Pros:

- future-proof

Cons:

- too large for the current launch window
- would delay the real risk reduction work

Out of scope for this slice.

## Goals

### Primary Goal

Allow operators to use the formal template library as a real operating surface
starting tomorrow, without shipping unreviewed templates into production
matching.

### P0 Goal

Make the current library safe and operable.

### P1 Goal

Improve quality, throughput, and explainability after the safety gate is in
place.

## Non-Goals

This slice does not include:

1. Multi-stage approval workflows.
2. Role configuration UI.
3. Full BI dashboards.
4. Automated legal review of external media.
5. Rebuilding the template editor from scratch.
6. Replacing the existing matching stack with a new model pipeline.

## Scope Overview

The work is split into P0 and P1.

### P0: Required Before Operators Use The Library At Scale

1. Production eligibility gate for matching.
2. One-shot data backfill and queue normalization.
3. Backlog-first operator UI defaults.
4. Batch quality and archive operations.
5. Generated-result operator disposition and queue cleanup.
6. End-to-end operator UAT and launch runbook.

### P1: Immediately After P0

1. Template deduplication and family diversity cleanup.
2. Ranking-quality priors on top of the mandatory model path.
3. Better audit visibility and evidence navigation.
4. Better ingestion failure recovery and replay UX.
5. Higher-throughput queue ergonomics.

## P0 Design

## P0.1 Production Eligibility Gate

### Decision

Production matching must no longer read all active published templates.

Instead, a template is **production-eligible** only when all of the following
are true:

- `status = published`
- `visibility != private`
- `qualityReviewStatus = reviewed`
- `qualityTier in (P1, P2)`

`P3` templates remain stored in the formal library but are excluded from the
default recommendation and matching path. They may still be available for
debugging, ops review, or explicit internal experiments.

### Important Clarification

The schema currently has both `reviewStatus` and `qualityReviewStatus`.

For this production-ops slice:

- `qualityReviewStatus` is the operational gate used by matching and operator
  backlog handling.
- `reviewStatus` remains reserved and should not become a second competing
  production gate in this slice.

### Expected Backend Changes

Apply the eligibility predicate inside the formal library read path used by:

- recommendation matching
- template debug matching
- any frontend experience that claims to show the live production library

The implementation should remain compatible with the current fallback behavior:

- primary pool: `P1 + P2`, `reviewed`, production-eligible
- fallback: empty result is allowed and must be explicit
- debug endpoints may optionally expose non-production candidates when the
  caller is backoffice, but the default production path must not do so

## P0.2 One-Shot Data Backfill And Queue Normalization

### Problem

The current state is internally inconsistent:

- many machine-generated templates are already `published`
- none have quality tiers filled
- all appear as pending review

Operators need a normalized backlog before they can work efficiently.

### Decision

Run a one-shot backfill that converts the current library into a clean
starting state.

### Backfill Rules

#### Standard curated templates

For the hand-curated seed / standard MMU baseline templates:

- assign initial `qualityTier` from the known baseline taxonomy
- set `qualityReviewStatus = reviewed`
- keep `status = published`
- keep non-private visibility

This forms the initial trusted production pool.

#### Machine-generated public-video templates

For current machine-generated public-video templates:

- default to `qualityReviewStatus = pending`
- default to `qualityTier = P3` unless explicitly whitelisted
- set `visibility = private` or archive if the title/source is obviously
  unsuitable
- keep source evidence and lineage metadata intact

This prevents them from silently remaining live while still preserving them for
future operator review.

#### Obvious low-signal or unsafe templates

Templates with clear low-value or unsuitable signals should be archived in the
backfill itself, for example:

- irrelevant audience or content domain
- duplicate or near-duplicate low-information titles
- clearly non-target makeup scenarios for the current product
- malformed evidence or broken extraction payloads

### Deliverable

A repeatable admin script or Nest script that can be run once on the current
database and re-run safely in staging.

## P0.3 Backlog-First Operator UX

### Problem

The quality queue page currently defaults to a filter combination that can hide
most of the real backlog.

### Decision

Change the operator UX from “browse the library” to “clear the backlog”.

### Required UX Behavior

#### Quality queue default view

Default filters should show:

- `qualityReviewStatus = pending`
- `status = published`
- `tier = all`

The first page must never look empty when there is real work to do.

#### Required filters

Operators must be able to filter by:

- `qualityReviewStatus`
- `qualityTier`
- `status`
- `sourcePlatform`
- `styleFamily`
- `primaryScene`
- keyword

#### List density

The queue list should show enough information for triage without opening each
detail page:

- display name
- style family
- scene
- source platform
- current quality tier
- review state
- evidence available
- operator note summary

## P0.4 Batch Operations

### Problem

Single-row quality edits are insufficient for a queue of this size.

### Decision

Add narrow, explicit batch actions instead of a generic bulk workflow engine.

### Required Batch Actions

1. Batch update quality tier.
2. Batch update quality review status.
3. Batch set operator note.
4. Batch archive templates.
5. Batch restore from archive is optional for P0 and can remain detail-only.

### Backend Shape

Add focused backoffice endpoints, for example:

- `POST /makeup-template-library/templates/batch-quality`
- `POST /makeup-template-library/templates/batch-archive`

Payloads should carry:

- `templateIds`
- requested action
- optional shared operator note

Each batch action must emit per-template audit events or a batch audit payload
that preserves the changed IDs.

### Frontend Shape

Add selection mode to:

- quality queue
- formal template list

Operators should be able to select rows, apply a batch action, then refetch the
queue and see counts drop immediately.

## P0.5 Generated Result Disposition

### Problem

Generated results are currently treated as pending if they are not linked to a
formal template. That is not enough for real operations.

Operators need to distinguish:

- worth materializing
- already published
- rejected
- deferred
- archived

### Decision

Add a minimal operator disposition state to `GeneratedMakeupTemplate`.

### Required New State

Introduce a generated-result ops state, for example:

- `pending`
- `deferred`
- `materialized`
- `published`
- `rejected`
- `archived`

Also add:

- `operatorNote`
- `reviewedById`
- `reviewedAt`

This is intentionally minimal. It is not a full approval system.

### Queue Rules

- `pending` items appear in the generated-result ops queue
- `deferred` items leave the hot queue but remain filterable for later revisit
- `materialized` items are linked to a formal draft and no longer count as
  pending
- `published` items are linked to a production template and no longer count as
  pending
- `rejected` and `archived` items leave the pending queue but remain auditable

### Required Operator Actions

1. Materialize to formal draft.
2. Publish directly when safe.
3. Reject with note.
4. Archive with note.
5. Defer with note for later review.

### Required Cleanup

Use this new state to clear the existing 107 pending generated results backlog.

Historical clearly wrong generations, such as prior bad commute-to-bridal
matches, should be rejected or archived rather than left in the live backlog.

If the generated-result backlog remains above operator-friendly size after the
first cleanup pass, add the same batch selection pattern used by the quality
queue for:

- batch reject
- batch archive
- batch defer

## P0.6 UAT And Launch Gate

P0 is not complete until one operator-facing UAT pass succeeds.

### Required UAT Flow

1. Operator opens the quality queue and sees the real backlog immediately.
2. Operator batch-updates at least one set of templates.
3. Operator archives at least one unsuitable template.
4. Operator reviews one generated result and either publishes or rejects it.
5. Frontend generates a recommendation.
6. Matching returns a reviewed `P1/P2` template only.
7. Makeup preview runs successfully.
8. Five-step voice evaluation remains green.
9. Ops workbench shows the relevant audit trail.

### Hard Launch Gate

Operators may start large-scale usage only if all of the following are true:

- no unreviewed template can enter production matching
- at least one reviewed trusted live pool exists
- batch ops work from the UI
- generated-result backlog can be reduced through supported states
- the full UAT path is documented and reproducible

## P1 Design

## P1.1 Template Deduplication And Family Hygiene

Add post-ingestion cleanup to reduce noisy repetition across public-video
templates.

Required capabilities:

- title and source near-duplicate detection
- same-family overconcentration detection
- low-information title suppression
- family diversity scoring for operator prioritization

This improves queue quality and reduces matching clutter.

## P1.2 Ranking Priors On Top Of Mandatory Model Matching

The embedding + reranker stack remains mandatory.

P1 adds stronger non-model priors after shortlist selection:

- reviewed content prior
- curated-source prior
- source-platform prior
- family diversity prior
- duplicate suppression prior

This is an additive ranking policy, not a replacement for model matching.

## P1.3 Better Evidence Navigation

Operators should be able to open a template and quickly see:

- raw source URL
- local raw asset path
- extracted evidence frames
- extraction summary
- ingestion run ID
- publish history
- recommendation consumption history

This makes template review defensible and faster.

## P1.4 Better Replay And Recovery

Public-video ingestion should provide better operator recovery:

- run-level retry entry points
- per-run failure reason clarity
- manifest linkage
- rerun safety notes

The current retry path exists, but the surrounding UX and observability are not
yet strong enough for large-scale operator use.

## P1.5 Higher-Throughput Queue Ergonomics

After P0, improve operator speed with:

- saved filters
- keyboard-friendly batch review flow
- bulk note presets
- queue sort by confidence, source, family, and recency
- direct drill-through from ops workbench cards into filtered queues

## Data And API Principles

1. Reuse existing `StandardMakeupTemplate` and `GeneratedMakeupTemplate`
   models wherever possible.
2. Keep audit logs append-only.
3. Do not overload `published` to mean “production-safe”.
4. Do not create a generic workflow engine in this slice.
5. Prefer explicit, narrow backoffice endpoints over highly abstract mutation
   APIs.

## Success Criteria

The spec is successful only if the implemented system satisfies all of the
following.

### P0 Success

1. Unreviewed templates cannot be selected by production matching.
2. Curated reviewed templates remain selectable and healthy.
3. Operators can see and reduce the real backlog from the UI.
4. Operators can batch-review and batch-archive templates.
5. Generated results can be rejected or archived, not only published.
6. Ops workbench counts reflect real queue state.
7. Recommendation, preview, and five-step voice validation all still pass.

### P1 Success

1. Duplicate and low-value machine templates are easier to suppress.
2. Candidate quality is visibly better in operator queues and matching results.
3. Operators can navigate from a template to its evidence and audit trail
   without database access.

## Implementation Notes

This spec deliberately favors a narrow implementation shape:

- keep existing NestJS module boundaries
- add small schema extensions only where queue state is impossible without them
- prioritize deterministic policy over clever automation

The system already proved it can generate recommendations, previews, and voice
guidance. This slice is about making the library trustworthy and operable.

## Recommended Next Step

After this spec is approved, write one implementation plan with P0 as the
first execution wave and P1 as the immediate follow-up wave.
