# Stable Makeup Local Patch

This directory stores the local compatibility patch required by the current
MIMU colleague demo environment.

## Patch

- `0001-fix-support-current-diffusers-controlnet-import.patch`

The patch updates Stable Makeup's `pipeline_sd15.py` import path for recent
Diffusers versions, where `MultiControlNetModel` moved under the current
controlnet package layout. It also preserves the local `.gitignore` entries used
for generated Python cache files.

## Apply To A Fresh Checkout

```bash
cd /storage/nvme3/shushanfu/MIMU-colleague/stable-makeup
git am /storage/nvme3/shushanfu/MIMU-colleague/patches/stable-makeup/0001-fix-support-current-diffusers-controlnet-import.patch
```

If the patch was already applied, `git am` will stop with an empty-patch or
already-applied message. In that case, abort the patch session:

```bash
git am --abort
```

## Verify

Start ComfyUI with the `mimu-comfy` conda environment and check:

```bash
curl -fsS http://127.0.0.1:8188/system_stats
curl -fsS -X POST http://127.0.0.1:13000/makeup \
  -F userImage=@eval/makeup/assets/users/u001_front_light.jpg \
  -F templateImage=@eval/makeup/assets/templates/t001_blue_eye.jpg \
  -F scenario=patch-check
```

The second command should return JSON with `promptId`, `imageUrl`, and `output`.
