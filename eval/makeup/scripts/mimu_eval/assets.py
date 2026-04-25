from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageEnhance, ImageOps

from .models import EvalCase


USER_CROP = (90, 140, 300, 355)
TEMPLATE_CROP = (85, 498, 305, 708)


def prepare_starter_dataset(project_root: Path, output_root: Path, case_count: int = 30) -> Path:
    example_path = project_root / "stable-makeup/example_.png"
    if not example_path.exists():
        raise FileNotFoundError(f"Missing stable-makeup/example_.png at {example_path}")

    output_root.mkdir(parents=True, exist_ok=True)
    users_dir = output_root / "assets/users"
    templates_dir = output_root / "assets/templates"
    manifests_dir = output_root / "manifests"
    users_dir.mkdir(parents=True, exist_ok=True)
    templates_dir.mkdir(parents=True, exist_ok=True)
    manifests_dir.mkdir(parents=True, exist_ok=True)

    with Image.open(example_path) as source:
        image = source.convert("RGB")
        user_base = _crop_face(image, USER_CROP)
        template_base = _crop_face(image, TEMPLATE_CROP)

    user_specs = [
        ("u001_front_light", 1.00, 1.00, 1.00, False),
        ("u002_front_warm", 1.06, 1.04, 1.10, False),
        ("u003_front_cool", 0.96, 1.05, 0.90, False),
        ("u004_front_bright", 1.12, 1.02, 1.00, False),
        ("u005_front_soft", 0.94, 0.92, 1.00, False),
        ("u006_front_flip", 1.00, 1.00, 1.00, True),
        ("u007_front_flip_warm", 1.05, 1.06, 1.08, True),
        ("u008_front_flip_cool", 0.97, 1.08, 0.92, True),
        ("u009_front_high_contrast", 1.03, 1.18, 1.00, False),
        ("u010_front_low_contrast", 0.98, 0.84, 1.00, True),
    ]
    template_specs = [
        ("t001_blue_eye", 1.00, 1.00, 1.00, False, "blue_eye_makeup"),
        ("t002_blue_eye_bright", 1.08, 1.08, 1.04, False, "blue_eye_bright"),
        ("t003_blue_eye_flip", 1.00, 1.05, 1.00, True, "blue_eye_flip"),
    ]

    user_paths = _write_variants(user_base, users_dir, user_specs)
    template_paths = _write_variants(template_base, templates_dir, template_specs)

    cases = _build_cases(output_root, user_paths, template_paths, case_count)
    manifest_path = manifests_dir / f"regression_{case_count}.jsonl"
    _write_cases(manifest_path, cases)

    smoke_path = manifests_dir / "smoke_2.jsonl"
    _write_cases(smoke_path, cases[:2])

    return manifest_path


def _crop_face(image: Image.Image, crop_box: tuple[int, int, int, int]) -> Image.Image:
    return image.crop(crop_box).resize((512, 512), Image.Resampling.LANCZOS)


def _write_variants(
    base: Image.Image,
    output_dir: Path,
    specs: Iterable[tuple[Any, ...]],
) -> list[Path]:
    paths: list[Path] = []
    for spec in specs:
        name, brightness, contrast, color, flip, *_ = spec
        image = base.copy()
        if flip:
            image = ImageOps.mirror(image)
        image = ImageEnhance.Brightness(image).enhance(brightness)
        image = ImageEnhance.Contrast(image).enhance(contrast)
        image = ImageEnhance.Color(image).enhance(color)
        path = output_dir / f"{name}.jpg"
        image.save(path, format="JPEG", quality=94)
        paths.append(path)
    return paths


def _build_cases(output_root: Path, user_paths: list[Path], template_paths: list[Path], case_count: int) -> list[EvalCase]:
    cases: list[EvalCase] = []
    template_styles = ["blue_eye_makeup", "blue_eye_bright", "blue_eye_flip"]
    for user_index, user_path in enumerate(user_paths):
        for template_index, template_path in enumerate(template_paths):
            if len(cases) >= case_count:
                return cases
            case_id = f"case_{len(cases) + 1:04d}"
            difficulty = "easy" if user_index < 4 else "medium"
            cases.append(
                EvalCase(
                    id=case_id,
                    user_image=user_path.relative_to(output_root).as_posix(),
                    template_image=template_path.relative_to(output_root).as_posix(),
                    style=template_styles[template_index % len(template_styles)],
                    attributes={
                        "source": "stable-makeup/example_.png crop variants",
                        "difficulty": difficulty,
                        "face_angle": "front",
                        "lighting": "derived",
                        "user_variant": user_path.stem,
                        "template_variant": template_path.stem,
                    },
                )
            )
    return cases


def _write_cases(path: Path, cases: list[EvalCase]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for case in cases:
            handle.write(json.dumps(case.to_record(), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
