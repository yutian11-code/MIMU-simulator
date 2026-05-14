# MIMU Roadshow Integration

This repository is the integration workspace for the MIMU roadshow stack. It
keeps shared documentation, evaluation assets, local deployment scripts, and the
ASR service in one place, while the frontend and backend stay in their original
GitHub repositories.

## Repository Layout

- `backend/`: cloned from `https://github.com/GreFir/mymakeup-backend.git`,
  branch `feature-ssf`. This directory is ignored by the integration repo.
- `frontend/`: cloned from `https://github.com/GreFir/my-make-up.git`, branch
  `feature-ssf`. This directory is ignored by the integration repo.
- `services/asr_service/`: local Qwen3-ASR FastAPI service used by voice coach.
- `scripts/`: LAN HTTPS gateway, Qwen-VL launch script, download helpers, and
  cleanup tools.
- `docs/`: technical plans, runbooks, privacy rules, and implementation notes.
- `eval/makeup/`: small deterministic evaluation set and scoring pipeline.
- `patches/`: local patches needed by external components.

Large local dependencies and artifacts are intentionally not tracked:

- `ComfyUI/`
- `stable-makeup/`
- `data/`
- `var/`
- `backend/`
- `frontend/`

## First Setup

Clone this integration repo, then pull the two application repositories:

```bash
git clone https://github.com/Shanfu2021/MIMU.git
cd MIMU
bash pull.sh
```

The script clones or updates:

- backend `feature-ssf`
- frontend `feature-ssf`

It refuses to pull over dirty frontend/backend worktrees, so local edits are not
silently overwritten.

## Runtime Entry

The roadshow browser entry is:

```text
https://10.246.1.70:19443
```

Core local services:

- frontend: `0.0.0.0:19006`
- backend: `0.0.0.0:13000`
- HTTPS gateway: `0.0.0.0:19443`
- Qwen3-ASR: `0.0.0.0:8020`
- Qwen-VL 32B vLLM: `0.0.0.0:8010`
- ComfyUI: `0.0.0.0:8188`

See `docs/team-runbook.md` for full startup and verification commands.

## Public Video Template Library

The formal template library now supports machine-published templates generated
from public tutorial videos. The default seed manifest lives at:

```text
backend/data/public-video-template-library/public-video-seeds.json
```

Run the ingestion smoke from the repo root:

```bash
bash scripts/run-public-video-template-library.sh --limit 2 --max-publish-count 2
```

Detailed operator steps are in `docs/public-video-template-library-runbook.md`.

## Model And Data Policy

Do not commit model weights, generated outputs, real user uploads, downloaded
video resources, or private test photos. Use `docs/internal-test-and-privacy.md`
before sharing this workspace.

For model downloads, use the project download helper and mirror configuration
described in the runbook. Do not rely on ad hoc proxy traffic for large
HuggingFace downloads.
