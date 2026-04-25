# Internal Test And Privacy Rules

This project processes face images. Treat all user, colleague, and evaluator
photos as sensitive data during internal tests.

## Allowed Test Images

- AI-generated portraits created for this project.
- Public demo images whose license allows local model testing.
- Real photos only when the person explicitly approved this internal test use.
- Existing `eval/makeup/assets/` images, which are deterministic crops/variants
  from the Stable Makeup example asset and are used only for regression checks.

## Do Not Commit

- Raw user uploads.
- Real-person test photos.
- ComfyUI input/output folders.
- Evaluation run outputs under `eval/makeup/runs/`.
- Browser screenshots that contain real faces.

## Local Retention

- Backend queue metadata is in memory and is pruned after the configured
  `MAKEUP_JOB_RETENTION_MS` window.
- ComfyUI generated files remain local ComfyUI artifacts. Before sharing a
  machine or handing off a demo environment, clear generated input/output files
  that contain real faces.
- Evaluation reports under `eval/makeup/runs/` may be kept for model debugging
  only when they use authorized or generated images.

Use the cleanup helper in dry-run mode first:

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague
bash scripts/cleanup-local-artifacts.sh --dry-run
```

After confirming the listed files are safe to remove:

```bash
bash scripts/cleanup-local-artifacts.sh --apply
```

## External Model Use

Do not send real face images to external VLM, LLM, scoring, analytics, or logging
services without explicit approval for that specific test. The current default
evaluation mode is `--vlm-mode mock`, which sends no images outside the machine.

## Internal Demo Checklist

1. Use generated or explicitly approved test photos.
2. Confirm frontend points to the intended backend IP.
3. Confirm backend points to the intended local ComfyUI URL.
4. Run one async `/makeup/jobs` smoke test.
5. Delete local real-person uploads and outputs after the demo.
