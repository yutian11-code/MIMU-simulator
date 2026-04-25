# Makeup Eval Kit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local MIMU Eval Kit that creates a starter 30-case makeup-transfer regression set, batch-runs `/makeup`, scores outputs, and generates an HTML review report.

**Architecture:** Add a self-contained Python toolchain under `eval/makeup/`. The package owns manifest parsing, deterministic starter asset generation, backend job execution, auto scoring, mock/VLM scoring, and static report generation. Scripts are thin CLI wrappers around tested modules.

**Tech Stack:** Python 3.10+, stdlib `unittest`, Pillow, requests, existing `mimu-comfy` conda environment, current Nest backend `/makeup`, local static HTML.

---

## File Structure

- Create `eval/makeup/scripts/mimu_eval/__init__.py`: package marker.
- Create `eval/makeup/scripts/mimu_eval/models.py`: dataclasses, JSONL load/write, run directory helpers.
- Create `eval/makeup/scripts/mimu_eval/assets.py`: deterministic starter asset generation from the Stable Makeup example screenshot.
- Create `eval/makeup/scripts/mimu_eval/client.py`: multipart `/makeup` client and result image download.
- Create `eval/makeup/scripts/mimu_eval/scoring.py`: deterministic image-quality and transfer proxy scoring.
- Create `eval/makeup/scripts/mimu_eval/vlm.py`: skipped/mock VLM-style JSON judging adapter.
- Create `eval/makeup/scripts/mimu_eval/report.py`: HTML report builder.
- Create `eval/makeup/scripts/prepare_seed_assets.py`: CLI for starter assets and manifests.
- Create `eval/makeup/scripts/run_makeup_eval.py`: CLI for batch backend execution.
- Create `eval/makeup/scripts/score_auto.py`: CLI for auto scores.
- Create `eval/makeup/scripts/judge_with_vlm.py`: CLI for skipped/mock VLM judging.
- Create `eval/makeup/scripts/build_report.py`: CLI for HTML reports.
- Create `eval/makeup/scripts/run_eval_pipeline.py`: CLI orchestrator for the common local flow.
- Create `eval/makeup/prompts/vlm_judge_v1.md`: prompt contract for future real VLM providers.
- Create tests under `eval/makeup/tests/`.

## Task 1: Manifest Models And JSONL IO

**Files:**
- Create: `eval/makeup/tests/test_models.py`
- Create: `eval/makeup/scripts/mimu_eval/__init__.py`
- Create: `eval/makeup/scripts/mimu_eval/models.py`

- [ ] **Step 1: Write failing tests**

Create `eval/makeup/tests/test_models.py` with tests for loading case manifests, writing metadata JSONL, and creating timestamped run directories.

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_models.py -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'mimu_eval'`.

- [ ] **Step 2: Implement models**

Implement dataclasses:

```python
EvalCase(id, user_image, template_image, style, attributes)
RunMetadata(case_id, status, duration_seconds, prompt_id, image_url, output_image, error)
ScoreRecord(case_id, scores, failure_type, reason)
```

Implement:

```python
load_cases(path: Path) -> list[EvalCase]
append_jsonl(path: Path, record: Mapping[str, Any]) -> None
read_jsonl(path: Path) -> list[dict[str, Any]]
make_run_dir(root: Path, run_id: str | None = None) -> Path
```

- [ ] **Step 3: Verify tests pass**

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_models.py -v`

Expected: PASS.

- [ ] **Step 4: Commit**

Run:

```bash
git add eval/makeup/tests/test_models.py eval/makeup/scripts/mimu_eval/__init__.py eval/makeup/scripts/mimu_eval/models.py
git commit -m "feat: add makeup eval manifest models"
```

## Task 2: Starter Asset And Manifest Generator

**Files:**
- Create: `eval/makeup/tests/test_assets.py`
- Create: `eval/makeup/scripts/mimu_eval/assets.py`
- Create: `eval/makeup/scripts/prepare_seed_assets.py`

- [ ] **Step 1: Write failing tests**

Create tests that call `prepare_starter_dataset(project_root, output_root, case_count=30)` against a temporary directory and assert:

- `assets/users/` contains deterministic user images.
- `assets/templates/` contains deterministic template images.
- `manifests/regression_30.jsonl` contains exactly 30 records.
- Each record references existing files.

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_assets.py -v`

Expected: FAIL with `ImportError` for `mimu_eval.assets`.

- [ ] **Step 2: Implement asset generation**

Use the existing Stable Makeup screenshot at `stable-makeup/example_.png`. Crop the clean face and makeup reference face, resize to 512x512, and create deterministic color/contrast variants. Write relative manifest paths under `eval/makeup/`.

- [ ] **Step 3: Add CLI**

`prepare_seed_assets.py` accepts:

```text
--project-root /storage/nvme3/shushanfu/MIMU-colleague
--output-root eval/makeup
--case-count 30
```

- [ ] **Step 4: Verify tests pass**

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_assets.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add eval/makeup/tests/test_assets.py eval/makeup/scripts/mimu_eval/assets.py eval/makeup/scripts/prepare_seed_assets.py
git commit -m "feat: generate starter makeup eval assets"
```

## Task 3: Backend Runner

**Files:**
- Create: `eval/makeup/tests/test_client.py`
- Create: `eval/makeup/scripts/mimu_eval/client.py`
- Create: `eval/makeup/scripts/run_makeup_eval.py`

- [ ] **Step 1: Write failing tests**

Create tests using a fake session object. Assert `MakeupBackendClient.run_case()` posts `userImage` and `templateImage`, downloads the result image, and records a failed status when the backend returns non-2xx.

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_client.py -v`

Expected: FAIL with `ImportError` for `mimu_eval.client`.

- [ ] **Step 2: Implement client**

Implement:

```python
class MakeupBackendClient:
    def __init__(self, base_url: str, timeout_seconds: int = 420, session: requests.Session | None = None): ...
    def run_case(self, case: EvalCase, project_root: Path, output_dir: Path) -> RunMetadata: ...
```

Use `POST {base_url}/makeup` with multipart fields `userImage` and `templateImage`. Normalize returned loopback result URLs to the configured backend host before downloading.

- [ ] **Step 3: Add batch CLI**

`run_makeup_eval.py` accepts:

```text
--manifest eval/makeup/manifests/regression_30.jsonl
--run-dir eval/makeup/runs/<run_id>
--backend-url http://127.0.0.1:13000
--limit 30
```

Write `metadata.jsonl` and output PNGs.

- [ ] **Step 4: Verify tests pass**

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_client.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add eval/makeup/tests/test_client.py eval/makeup/scripts/mimu_eval/client.py eval/makeup/scripts/run_makeup_eval.py
git commit -m "feat: add makeup eval backend runner"
```

## Task 4: Auto Scoring

**Files:**
- Create: `eval/makeup/tests/test_scoring.py`
- Create: `eval/makeup/scripts/mimu_eval/scoring.py`
- Create: `eval/makeup/scripts/score_auto.py`

- [ ] **Step 1: Write failing tests**

Create tests using generated solid/gradient images. Assert scoring returns bounded 1-5 values, marks missing output as `generation_failed`, and gives higher makeup-region delta when output differs from user image in eye/lip regions.

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_scoring.py -v`

Expected: FAIL with `ImportError` for `mimu_eval.scoring`.

- [ ] **Step 2: Implement scoring**

Implement deterministic fallback metrics:

- `image_load_success`
- `identity_proxy_score`
- `makeup_transfer_score`
- `naturalness_score`
- `artifact_score`
- `overall_score`
- `failure_type`

Use Pillow only in the first version. Keep optional InsightFace for a later task.

- [ ] **Step 3: Add CLI**

`score_auto.py` accepts `--manifest`, `--run-dir`, and writes `auto_scores.jsonl`.

- [ ] **Step 4: Verify tests pass**

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_scoring.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add eval/makeup/tests/test_scoring.py eval/makeup/scripts/mimu_eval/scoring.py eval/makeup/scripts/score_auto.py
git commit -m "feat: add makeup eval auto scoring"
```

## Task 5: VLM Judge Adapter

**Files:**
- Create: `eval/makeup/tests/test_vlm.py`
- Create: `eval/makeup/scripts/mimu_eval/vlm.py`
- Create: `eval/makeup/scripts/judge_with_vlm.py`
- Create: `eval/makeup/prompts/vlm_judge_v1.md`

- [ ] **Step 1: Write failing tests**

Create tests that assert `mode=skip` writes skipped records and `mode=mock` returns JSON records with the required fields and bounded scores.

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_vlm.py -v`

Expected: FAIL with `ImportError` for `mimu_eval.vlm`.

- [ ] **Step 2: Implement skip/mock judge**

Implement:

```python
judge_cases(manifest, run_dir, mode: Literal["skip", "mock"]) -> list[ScoreRecord]
```

Skip mode produces `failure_type="vlm_skipped"`. Mock mode derives VLM-like scores from `auto_scores.jsonl` so reports can be exercised without sending private images to external APIs.

- [ ] **Step 3: Add prompt contract**

Write `vlm_judge_v1.md` with the exact JSON schema and scoring rubric from the design doc.

- [ ] **Step 4: Verify tests pass**

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_vlm.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add eval/makeup/tests/test_vlm.py eval/makeup/scripts/mimu_eval/vlm.py eval/makeup/scripts/judge_with_vlm.py eval/makeup/prompts/vlm_judge_v1.md
git commit -m "feat: add makeup eval vlm judge adapter"
```

## Task 6: HTML Report

**Files:**
- Create: `eval/makeup/tests/test_report.py`
- Create: `eval/makeup/scripts/mimu_eval/report.py`
- Create: `eval/makeup/scripts/build_report.py`

- [ ] **Step 1: Write failing tests**

Create tests that build a report from a tiny manifest, metadata, auto scores, and VLM scores. Assert the HTML contains summary metrics, case IDs, image paths, and failure labels.

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_report.py -v`

Expected: FAIL with `ImportError` for `mimu_eval.report`.

- [ ] **Step 2: Implement report builder**

Generate static `report.html` with:

- Summary cards.
- Table rows for each case.
- Three image columns: user, template, output.
- Auto and VLM score columns.
- Failure type and reason.

- [ ] **Step 3: Add CLI**

`build_report.py` accepts `--manifest`, `--run-dir`, and `--output report.html`.

- [ ] **Step 4: Verify tests pass**

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest eval/makeup/tests/test_report.py -v`

Expected: PASS.

- [ ] **Step 5: Commit**

Run:

```bash
git add eval/makeup/tests/test_report.py eval/makeup/scripts/mimu_eval/report.py eval/makeup/scripts/build_report.py
git commit -m "feat: add makeup eval html report"
```

## Task 7: Pipeline Orchestrator And Local Smoke Run

**Files:**
- Create: `eval/makeup/scripts/run_eval_pipeline.py`
- Modify: `eval/makeup/README.md`

- [ ] **Step 1: Add orchestrator**

Implement an orchestrator that runs:

```text
prepare_seed_assets.py
run_makeup_eval.py
score_auto.py
judge_with_vlm.py --mode mock
build_report.py
```

It should accept `--limit` so smoke runs can process 1-2 cases before full regression runs.

- [ ] **Step 2: Add README**

Document:

- Required running services.
- Commands for smoke and full runs.
- Output locations.
- How to add real authorized assets later.

- [ ] **Step 3: Verify all unit tests**

Run: `/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python -m unittest discover -s eval/makeup/tests -v`

Expected: all tests PASS.

- [ ] **Step 4: Run smoke pipeline**

Run:

```bash
/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python eval/makeup/scripts/run_eval_pipeline.py --project-root /storage/nvme3/shushanfu/MIMU-colleague --backend-url http://127.0.0.1:13000 --limit 2 --vlm-mode mock
```

Expected:

- `metadata.jsonl` contains 2 records.
- `auto_scores.jsonl` contains 2 records.
- `vlm_scores.jsonl` contains 2 records.
- `report.html` exists.

- [ ] **Step 5: Commit**

Run:

```bash
git add eval/makeup/scripts/run_eval_pipeline.py eval/makeup/README.md eval/makeup/assets eval/makeup/manifests
git commit -m "feat: add makeup eval pipeline entrypoint"
```

## Task 8: Full Regression Run

**Files:**
- Create run output under `eval/makeup/runs/<run_id>/`.

- [ ] **Step 1: Run 30-case regression**

Run:

```bash
/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python eval/makeup/scripts/run_eval_pipeline.py --project-root /storage/nvme3/shushanfu/MIMU-colleague --backend-url http://127.0.0.1:13000 --limit 30 --vlm-mode mock
```

Expected: script exits 0 and writes a full report.

- [ ] **Step 2: Review report output**

Check:

```bash
ls -lh eval/makeup/runs/<run_id>/report.html
wc -l eval/makeup/runs/<run_id>/metadata.jsonl eval/makeup/runs/<run_id>/auto_scores.jsonl eval/makeup/runs/<run_id>/vlm_scores.jsonl
```

Expected: each JSONL file has 30 lines.

- [ ] **Step 3: Commit run summary**

Do not commit output PNGs by default. Commit only small manifest/assets if acceptable and keep `runs/` ignored unless the user asks to archive a specific report.

Run:

```bash
git status --short
git commit --allow-empty -m "test: run makeup eval regression"
```

## Self-Review

Spec coverage:

- Starter dataset: Tasks 2 and 7.
- Batch `/makeup` execution: Task 3 and Task 8.
- Auto scoring: Task 4.
- VLM/mock scoring: Task 5.
- HTML report: Task 6.
- Human review support: report fields and JSONL outputs in Tasks 5-6; full UI is intentionally out of first implementation.
- Version comparison: output layout supports separate run directories; visual diff UI is intentionally deferred.

No placeholders remain in task descriptions. Function names are consistent across tasks.
