from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PIL import Image, ImageChops, ImageStat

from .models import EvalCase, RunMetadata, ScoreRecord, append_jsonl, load_cases, read_jsonl


MAKEUP_REGIONS = (
    (120, 170, 220, 225),
    (292, 170, 392, 225),
    (205, 330, 307, 372),
)


def score_case(case: EvalCase, metadata: RunMetadata | None, dataset_root: Path, run_dir: Path) -> ScoreRecord:
    if not metadata or metadata.status != "success" or not metadata.output_image:
        return ScoreRecord(
            case_id=case.id,
            scores=_failed_scores(),
            failure_type="generation_failed",
            reason=(metadata.error if metadata else "missing metadata") or "generation failed",
        )

    output_path = run_dir / metadata.output_image
    if not output_path.exists():
        return ScoreRecord(
            case_id=case.id,
            scores=_failed_scores(),
            failure_type="generation_failed",
            reason=f"missing output image: {metadata.output_image}",
        )

    try:
        with Image.open(case.user_path(dataset_root)) as user_src:
            user = user_src.convert("RGB").resize((512, 512))
        with Image.open(case.template_path(dataset_root)) as template_src:
            template = template_src.convert("RGB").resize((512, 512))
        with Image.open(output_path) as output_src:
            output = output_src.convert("RGB").resize((512, 512))
    except Exception as exc:  # noqa: BLE001
        return ScoreRecord(
            case_id=case.id,
            scores=_failed_scores(),
            failure_type="invalid_image",
            reason=str(exc),
        )

    identity = _identity_proxy_score(user, output)
    makeup_transfer = _makeup_transfer_score(user, template, output)
    naturalness = _naturalness_score(output)
    artifact = _artifact_score(output)
    overall = _overall_score(identity, makeup_transfer, naturalness, artifact)

    failure_type = "none"
    reason = "auto score passed"
    if artifact >= 4:
        failure_type = "dirty_artifact"
        reason = "output image quality proxy is poor"
    elif makeup_transfer <= 2:
        failure_type = "makeup_missing"
        reason = "output makeup regions did not move toward template"
    elif identity <= 2:
        failure_type = "identity_changed"
        reason = "output differs strongly from user image"

    return ScoreRecord(
        case_id=case.id,
        scores={
            "identity_score": identity,
            "makeup_transfer_score": makeup_transfer,
            "naturalness_score": naturalness,
            "artifact_score": artifact,
            "overall_score": overall,
        },
        failure_type=failure_type,
        reason=reason,
    )


def score_cases(manifest_path: Path, dataset_root: Path, run_dir: Path) -> list[ScoreRecord]:
    metadata_by_case = {
        str(record.get("case_id")): _metadata_from_record(record)
        for record in read_jsonl(run_dir / "metadata.jsonl")
    }
    scores = [
        score_case(case, metadata_by_case.get(case.id), dataset_root=dataset_root, run_dir=run_dir)
        for case in load_cases(manifest_path, dataset_root=dataset_root)
    ]
    return scores


def write_auto_scores(manifest_path: Path, dataset_root: Path, run_dir: Path) -> Path:
    output_path = run_dir / "auto_scores.jsonl"
    if output_path.exists():
        output_path.unlink()
    for score in score_cases(manifest_path, dataset_root=dataset_root, run_dir=run_dir):
        append_jsonl(output_path, score.to_record())
    return output_path


def _metadata_from_record(record: dict) -> RunMetadata:
    return RunMetadata(
        case_id=str(record.get("case_id", "")),
        status=str(record.get("status", "")),
        duration_seconds=float(record.get("duration_seconds") or 0),
        prompt_id=record.get("prompt_id"),
        image_url=record.get("image_url"),
        output_image=record.get("output_image"),
        error=record.get("error"),
    )


def _failed_scores() -> dict[str, float]:
    return {
        "identity_score": 1,
        "makeup_transfer_score": 1,
        "naturalness_score": 1,
        "artifact_score": 5,
        "overall_score": 1,
    }


def _identity_proxy_score(user: Image.Image, output: Image.Image) -> float:
    distance = _mean_abs_distance(user, output)
    return _bounded(5 - min(4, (distance / 70) * 4))


def _makeup_transfer_score(user: Image.Image, template: Image.Image, output: Image.Image) -> float:
    baseline = _mean_region_distance(user, template, MAKEUP_REGIONS)
    if baseline < 1:
        return 3
    output_distance = _mean_region_distance(output, template, MAKEUP_REGIONS)
    improvement = max(0, min(1, (baseline - output_distance) / baseline))
    return _bounded(1 + 4 * improvement)


def _naturalness_score(output: Image.Image) -> float:
    stat = ImageStat.Stat(output.convert("L"))
    mean = stat.mean[0]
    stddev = stat.stddev[0]
    exposure_penalty = max(0, abs(mean - 128) - 80) / 40
    contrast_penalty = 1.0 if stddev < 8 else 0.0
    return _bounded(5 - exposure_penalty - contrast_penalty)


def _artifact_score(output: Image.Image) -> float:
    stat = ImageStat.Stat(output.convert("L"))
    if output.size[0] < 256 or output.size[1] < 256:
        return 4
    if stat.stddev[0] < 3:
        return 4
    return 1


def _overall_score(identity: float, makeup_transfer: float, naturalness: float, artifact: float) -> float:
    raw = (identity * 0.35) + (makeup_transfer * 0.35) + (naturalness * 0.2) + ((6 - artifact) * 0.1)
    return _bounded(raw)


def _mean_region_distance(a: Image.Image, b: Image.Image, regions: Iterable[tuple[int, int, int, int]]) -> float:
    distances = [_mean_abs_distance(a.crop(region), b.crop(region)) for region in regions]
    return sum(distances) / len(distances)


def _mean_abs_distance(a: Image.Image, b: Image.Image) -> float:
    diff = ImageChops.difference(a, b)
    stat = ImageStat.Stat(diff)
    return sum(stat.mean) / len(stat.mean)


def _bounded(value: float) -> float:
    return round(max(1, min(5, value)), 3)
