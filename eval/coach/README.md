# AI Coach Eval Helpers

This folder contains helpers for the `/makeup/coach` realtime makeup guidance
flow. It is separate from `eval/makeup`, which targets the makeup-transfer API.

## Build Same-Person Five-Step Demo Set

The generated image data lives under the ignored `eval/data/` tree.

```bash
python eval/coach/scripts/build_five_step_sequence_dataset.py
```

Default input:

- `eval/data/ai_makeup_coach_synthetic/source/same_person_five_step_contact_sheet.png`

Default outputs:

- `eval/data/ai_makeup_coach_synthetic/images/demo_5step_same_person_10groups/`
- `eval/data/ai_makeup_coach_synthetic/manifests/demo_5step_same_person_10groups.jsonl`
- `eval/data/ai_makeup_coach_synthetic/manifests/demo_5step_same_person_10groups.groups.jsonl`

## Run Five-Step Voice Eval

The generated voice samples live under the ignored `eval/data/` tree:

- `eval/data/ai_makeup_coach_synthetic/audio/five_step/`

Run all 10 groups x 5 steps against the backend voice coach endpoint:

```bash
python eval/coach/scripts/run_five_step_voice_eval.py
```

Useful overrides:

```bash
COACH_BACKEND_URL=http://127.0.0.1:13001 python eval/coach/scripts/run_five_step_voice_eval.py
python eval/coach/scripts/run_five_step_voice_eval.py --group-id group_001
python eval/coach/scripts/run_five_step_voice_eval.py --step-title 眼妆
```

Default outputs:

- `eval/data/ai_makeup_coach_synthetic/audio/five_step/manifest.json`
- `eval/data/ai_makeup_coach_synthetic/runs/five_step_voice_<timestamp>/voice_coach_results.jsonl`
- `eval/data/ai_makeup_coach_synthetic/runs/five_step_voice_<timestamp>/summary.json`
- `eval/data/ai_makeup_coach_synthetic/runs/five_step_voice_<timestamp>/failures.json`
