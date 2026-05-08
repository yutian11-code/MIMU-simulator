#!/usr/bin/env python3
"""Build the AI coach five-step synthetic sequence dataset.

The source image is a five-panel contact sheet. The script crops one panel per
makeup step, then creates ten camera-condition groups from those five frames.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from PIL import Image, ImageEnhance, ImageFilter


STEP_DEFS = [
    {
        "index": 1,
        "key": "base",
        "id": "tpl-sweet-5-step-001",
        "title": "底妆",
        "instruction": "先完成妆前保湿、唇部打底和美瞳，再处理肤色矫正、遮瑕、粉底和散粉。重点让肤色均匀透亮、黑眼圈减轻，保留自然奶油肌。",
        "detectedAnyOf": ["底妆", "粉底"],
    },
    {
        "index": 2,
        "key": "brow",
        "id": "tpl-sweet-5-step-002",
        "title": "眉毛",
        "instruction": "顺着毛流梳顺眉毛，用灰棕色眉笔填补空缺，眉尾微微拉长，眉头晕淡，最后用染眉膏统一颜色。",
        "detectedAnyOf": ["眉毛", "眉妆"],
    },
    {
        "index": 3,
        "key": "eye",
        "id": "tpl-sweet-5-step-003",
        "title": "眼妆",
        "instruction": "用自然眼影轻扫眼皮和眼尾后三角，保持清淡不烟熏；夹翘睫毛后刷 1-2 层睫毛膏，重点增强睫毛根部存在感。",
        "detectedAnyOf": ["眼妆", "眼影", "睫毛"],
    },
    {
        "index": 4,
        "key": "blush",
        "id": "tpl-sweet-5-step-004",
        "title": "腮红",
        "instruction": "腮红轻扫在苹果肌偏上、靠近眼下的位置，少量多次晕染，让面中更饱满并增加甜妹氛围。",
        "detectedAnyOf": ["腮红"],
    },
    {
        "index": 5,
        "key": "lip",
        "id": "tpl-sweet-5-step-005",
        "title": "唇妆",
        "instruction": "口红从嘴唇内侧向外晕染，边缘自然过渡，不需要锋利唇线，呈现温柔豆沙感并完成整体妆容。",
        "detectedAnyOf": ["唇妆", "口红"],
    },
]


@dataclass(frozen=True)
class GroupTransform:
    group_id: str
    label: str
    description: str
    apply: Callable[[Image.Image, int], Image.Image]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def add_tint(image: Image.Image, color: tuple[int, int, int], alpha: float) -> Image.Image:
    overlay = Image.new("RGB", image.size, color)
    return Image.blend(image, overlay, alpha)


def center_crop_fraction(image: Image.Image, fraction: float, x_shift: float = 0.0, y_shift: float = 0.0) -> Image.Image:
    width, height = image.size
    crop_w = int(width * fraction)
    crop_h = int(height * fraction)
    max_x = width - crop_w
    max_y = height - crop_h
    x0 = int(max_x / 2 + max_x * x_shift)
    y0 = int(max_y / 2 + max_y * y_shift)
    x0 = max(0, min(max_x, x0))
    y0 = max(0, min(max_y, y0))
    return image.crop((x0, y0, x0 + crop_w, y0 + crop_h)).resize(image.size, Image.Resampling.LANCZOS)


def jpeg_round_trip(image: Image.Image, quality: int) -> Image.Image:
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB")


def build_transforms() -> list[GroupTransform]:
    return [
        GroupTransform("group_001", "canonical", "原始清晰正面帧", lambda image, _: image.copy()),
        GroupTransform(
            "group_002",
            "warm_vanity_light",
            "暖色梳妆台灯光",
            lambda image, _: ImageEnhance.Color(add_tint(image, (255, 224, 190), 0.08)).enhance(1.04),
        ),
        GroupTransform(
            "group_003",
            "cool_bathroom_light",
            "偏冷浴室灯光",
            lambda image, _: ImageEnhance.Color(add_tint(image, (205, 225, 255), 0.08)).enhance(0.96),
        ),
        GroupTransform(
            "group_004",
            "low_light",
            "低照度摄像头画面",
            lambda image, _: ImageEnhance.Contrast(ImageEnhance.Brightness(image).enhance(0.78)).enhance(1.08),
        ),
        GroupTransform(
            "group_005",
            "bright_vanity_light",
            "亮灯轻微过曝画面",
            lambda image, _: ImageEnhance.Brightness(ImageEnhance.Contrast(image).enhance(0.97)).enhance(1.12),
        ),
        GroupTransform(
            "group_006",
            "soft_motion_blur",
            "轻微手持模糊",
            lambda image, _: image.filter(ImageFilter.GaussianBlur(radius=0.55)),
        ),
        GroupTransform(
            "group_007",
            "close_crop",
            "用户靠近摄像头",
            lambda image, _: center_crop_fraction(image, 0.91, y_shift=-0.08),
        ),
        GroupTransform(
            "group_008",
            "left_shift_crop",
            "脸部略偏左的摄像头构图",
            lambda image, _: center_crop_fraction(image, 0.94, x_shift=-0.28),
        ),
        GroupTransform(
            "group_009",
            "webcam_compression",
            "视频通话压缩画质",
            lambda image, _: jpeg_round_trip(image, quality=58),
        ),
        GroupTransform(
            "group_010",
            "soft_focus_webcam",
            "柔焦摄像头画面",
            lambda image, _: ImageEnhance.Sharpness(image.filter(ImageFilter.GaussianBlur(radius=0.28))).enhance(0.82),
        ),
    ]


def crop_step_panels(source: Image.Image) -> list[Image.Image]:
    width, height = source.size
    panels: list[Image.Image] = []

    for index in range(5):
        left = round(index * width / 5)
        right = round((index + 1) * width / 5)
        margin_left = 2 if index > 0 else 0
        margin_right = 2 if index < 4 else 0
        panel = source.crop((left + margin_left, 0, right - margin_right, height)).convert("RGB")
        panels.append(panel)

    return panels


def build_record(
    group: GroupTransform,
    group_index: int,
    step_index: int,
    image_path: str,
    source_sha256: str,
) -> dict:
    step = STEP_DEFS[step_index]
    completed = [item["title"] for item in STEP_DEFS[:step_index]]
    next_step = STEP_DEFS[step_index + 1] if step_index + 1 < len(STEP_DEFS) else None

    return {
        "id": f"syn_demo_5step_{group_index:02d}_{step['index']:02d}_{step['key']}_complete",
        "groupId": group.group_id,
        "sequenceIndex": group_index,
        "image": image_path,
        "templateId": "tpl-sweet-5",
        "flow": "demo_5step_ai_coach_sequence",
        "scenario": "万能甜美嫩妹妆五步版",
        "stepId": step["id"],
        "stepTitle": step["title"],
        "stepInstruction": step["instruction"],
        "completedStepTitles": completed,
        "totalSteps": 5,
        "userQuestion": f"请根据当前画面判断{step['title']}是否完成，是否可以进入下一步。",
        "expected": {
            "currentStepDetectedAnyOf": step["detectedAnyOf"],
            "shouldProceed": True,
            "detectedIssues": [],
            "autoAdvance": True,
            "nextStepId": next_step["id"] if next_step else None,
            "nextStepTitle": next_step["title"] if next_step else None,
            "isFinalStep": next_step is None,
        },
        "labels": {
            "caseType": "demo_step_positive" if next_step else "demo_finish_positive",
            "targetStep": step["key"],
            "makeupState": "complete",
            "issueType": "none",
            "synthetic": True,
            "identityPolicy": "same_source_person_with_group_camera_augments",
            "cameraCondition": group.label,
            "humanReviewRequired": True,
        },
        "source": {
            "contactSheet": "source/same_person_five_step_contact_sheet.png",
            "contactSheetSha256": source_sha256,
            "sourcePanel": step["index"],
            "groupTransform": group.description,
            "generator": "openai-imagegen",
        },
    }


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True))
            fh.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("eval/data/ai_makeup_coach_synthetic/source/same_person_five_step_contact_sheet.png"),
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("eval/data/ai_makeup_coach_synthetic"),
    )
    args = parser.parse_args()

    source_path = args.source
    output_root = args.output_root
    image_root = output_root / "images" / "demo_5step_same_person_10groups"
    manifest_path = output_root / "manifests" / "demo_5step_same_person_10groups.jsonl"
    group_manifest_path = output_root / "manifests" / "demo_5step_same_person_10groups.groups.jsonl"

    source = Image.open(source_path).convert("RGB")
    panels = crop_step_panels(source)
    transforms = build_transforms()
    source_sha256 = sha256_file(source_path)
    records: list[dict] = []
    group_records: list[dict] = []

    for group_index, group in enumerate(transforms, start=1):
        group_dir = image_root / group.group_id
        group_dir.mkdir(parents=True, exist_ok=True)
        group_images: list[str] = []

        for step_index, panel in enumerate(panels):
            step = STEP_DEFS[step_index]
            output_path = group_dir / f"step_{step['index']:02d}_{step['key']}_complete.png"
            group.apply(panel, step_index).save(output_path, format="PNG", optimize=True)
            relative_path = output_path.relative_to(output_root).as_posix()
            group_images.append(relative_path)
            records.append(build_record(group, group_index, step_index, relative_path, source_sha256))

        group_records.append(
            {
                "groupId": group.group_id,
                "sequenceIndex": group_index,
                "cameraCondition": group.label,
                "description": group.description,
                "templateId": "tpl-sweet-5",
                "flow": "demo_5step_ai_coach_sequence",
                "stepTitles": [step["title"] for step in STEP_DEFS],
                "images": group_images,
                "sameIdentityAcrossSteps": True,
                "sameSourcePersonAcrossGroups": True,
                "humanReviewRequired": True,
            }
        )

    write_jsonl(manifest_path, records)
    write_jsonl(group_manifest_path, group_records)
    print(f"wrote {len(records)} records to {manifest_path}")
    print(f"wrote {len(group_records)} groups to {group_manifest_path}")


if __name__ == "__main__":
    main()
