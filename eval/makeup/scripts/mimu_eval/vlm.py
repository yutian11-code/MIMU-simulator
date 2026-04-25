from __future__ import annotations

from pathlib import Path
from typing import Literal

from .models import ScoreRecord, append_jsonl, read_jsonl

JudgeMode = Literal["skip", "mock"]


def judge_cases(manifest_path: Path, run_dir: Path, mode: JudgeMode = "skip") -> list[ScoreRecord]:
    case_ids = [str(record["id"]) for record in read_jsonl(manifest_path)]
    if mode == "skip":
        return [
            ScoreRecord(case_id=case_id, scores={}, failure_type="vlm_skipped", reason="VLM judge not configured")
            for case_id in case_ids
        ]
    if mode == "mock":
        return _mock_judge(case_ids, run_dir)
    raise ValueError(f"Unsupported VLM judge mode: {mode}")


def write_vlm_scores(manifest_path: Path, run_dir: Path, mode: JudgeMode = "skip") -> Path:
    output_path = run_dir / "vlm_scores.jsonl"
    if output_path.exists():
        output_path.unlink()
    for score in judge_cases(manifest_path, run_dir=run_dir, mode=mode):
        append_jsonl(output_path, score.to_record())
    return output_path


def _mock_judge(case_ids: list[str], run_dir: Path) -> list[ScoreRecord]:
    auto_by_case = {str(record.get("case_id")): record for record in read_jsonl(run_dir / "auto_scores.jsonl")}
    scores: list[ScoreRecord] = []
    for case_id in case_ids:
        auto = auto_by_case.get(case_id)
        if not auto:
            scores.append(
                ScoreRecord(
                    case_id=case_id,
                    scores=_fallback_scores(),
                    failure_type="vlm_missing_auto",
                    reason="mock VLM could not find auto score record",
                )
            )
            continue

        auto_scores = dict(auto.get("scores") or {})
        scores.append(
            ScoreRecord(
                case_id=case_id,
                scores={key: _bounded(float(value)) for key, value in auto_scores.items()},
                failure_type=str(auto.get("failure_type") or "none"),
                reason=f"mock VLM derived from auto scores: {auto.get('reason') or 'no auto reason'}",
            )
        )
    return scores


def _fallback_scores() -> dict[str, float]:
    return {
        "identity_score": 1,
        "makeup_transfer_score": 1,
        "naturalness_score": 1,
        "artifact_score": 5,
        "overall_score": 1,
    }


def _bounded(value: float) -> float:
    return round(max(1, min(5, value)), 3)
