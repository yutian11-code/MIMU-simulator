# MIMU Makeup Eval Kit

This toolkit creates a starter makeup-transfer regression set, runs the current backend `/makeup` API, computes deterministic auto scores, writes mock/skipped VLM scores, and builds a static HTML report.

## Services

Start these services before running live evaluation:

- Backend: `http://127.0.0.1:13000`
- ComfyUI: `http://127.0.0.1:8188`

The frontend is not required for evaluation.

## Smoke Run

```bash
/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python eval/makeup/scripts/run_eval_pipeline.py \
  --project-root /storage/nvme3/shushanfu/MIMU-colleague \
  --backend-url http://127.0.0.1:13000 \
  --limit 2 \
  --vlm-mode mock
```

The script prints the run directory. Open `report.html` in that directory to review results.

## Full Starter Regression

```bash
/home/shushanfu/software/Anaconda/envs/mimu-comfy/bin/python eval/makeup/scripts/run_eval_pipeline.py \
  --project-root /storage/nvme3/shushanfu/MIMU-colleague \
  --backend-url http://127.0.0.1:13000 \
  --limit 30 \
  --vlm-mode mock
```

Generated run outputs are written under `eval/makeup/runs/` and are ignored by git.

## Data

The first manifest is generated from `stable-makeup/example_.png` crop variants:

- `eval/makeup/assets/users/`
- `eval/makeup/assets/templates/`
- `eval/makeup/manifests/regression_30.jsonl`
- `eval/makeup/manifests/smoke_2.jsonl`

This is a starter regression set for pipeline and model-route checks. Replace or extend it with AI-generated portraits or explicitly authorized real photos before using the scores as product-quality evidence.

## VLM Mode

- `--vlm-mode skip`: writes skipped records and sends no images anywhere.
- `--vlm-mode mock`: derives VLM-like scores from auto scores so reports stay complete without an external model.

Real VLM provider integration should follow `eval/makeup/prompts/vlm_judge_v1.md` and must not send real authorized photos to external APIs without explicit approval.
