# Makeup Productionization Design

## Goal

Complete the five remaining core work items for the colleague-based MIMU demo:
frontend end-to-end verification, makeup task queueing, expanded evaluation set,
reproducible Stable Makeup patching, and privacy/internal-test documentation.

## Scope

This design targets a single-machine internal demo and team test environment.
It does not introduce Redis, persistent job storage, user billing, or production
observability. Those are later productization steps.

## Backend Queue

The backend keeps the existing synchronous `POST /makeup` contract for current
evaluation scripts and manual smoke tests. Internally it submits work through a
single in-memory queue, so synchronous and asynchronous callers share the same
GPU concurrency limit and retry behavior.

New frontend-facing APIs:

- `POST /makeup/jobs`: enqueue one makeup preview job and return a `jobId`
- `GET /makeup/jobs/:jobId`: return job status, progress, retry count, errors,
  and the final image URL when available
- `GET /makeup/jobs`: return recent jobs for lightweight debugging

The queue runs one GPU job at a time by default. Failed ComfyUI jobs are retried
once by default. Completed and failed jobs are retained in memory for a bounded
TTL and then pruned.

## Frontend Flow

The try-on panel uses `POST /makeup/jobs` and polls `GET /makeup/jobs/:jobId`.
The UI shows queued, running, retrying, success, and failure states. The existing
image upload and template media flow stays intact. If camera access fails, users
can still choose from the image library.

## Evaluation Set

The starter evaluation dataset expands from 30 to 90 cases by generating
additional deterministic user/template image variants from the existing
authorized Stable Makeup example asset. This remains a regression dataset, not a
full product-quality benchmark. It is enough to catch obvious pipeline failures
and scoring regressions while the team prepares a larger authorized real/synthetic
benchmark.

## Stable Makeup Reproducibility

The local Stable Makeup compatibility fix is exported as a patch under
`patches/stable-makeup/` with a short README. A fresh checkout can apply the
patch without depending on this exact working tree.

## Privacy And Internal Test Rules

Internal testing documentation states that user face images are sensitive data,
should not be committed, should be cleaned after test runs, and should not be
sent to external VLM/LLM services without explicit approval. Current generated
ComfyUI outputs remain local machine artifacts.

## Verification

Verification requires:

- backend build, unit tests, and e2e tests
- frontend TypeScript and lint checks
- evaluation unit tests and a 90-case smoke/regression run
- backend health, ComfyUI health, frontend HTTP 200
- one direct `/makeup` smoke test and one async `/makeup/jobs` smoke test
