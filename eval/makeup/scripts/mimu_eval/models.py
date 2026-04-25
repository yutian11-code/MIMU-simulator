from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class EvalCase:
    id: str
    user_image: str
    template_image: str
    style: str
    attributes: dict[str, Any] = field(default_factory=dict)

    def user_path(self, dataset_root: Path) -> Path:
        return dataset_root / self.user_image

    def template_path(self, dataset_root: Path) -> Path:
        return dataset_root / self.template_image

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RunMetadata:
    case_id: str
    status: str
    duration_seconds: float
    prompt_id: str | None = None
    image_url: str | None = None
    output_image: str | None = None
    error: str | None = None

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScoreRecord:
    case_id: str
    scores: dict[str, float]
    failure_type: str
    reason: str

    def to_record(self) -> dict[str, Any]:
        return asdict(self)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on {path}:{line_number}: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"JSONL record must be an object on {path}:{line_number}")
            records.append(payload)
    return records


def append_jsonl(path: Path, record: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def load_cases(path: Path, dataset_root: Path | None = None) -> list[EvalCase]:
    dataset_root = dataset_root or path.parent.parent
    cases: list[EvalCase] = []
    seen_ids: set[str] = set()

    for record in read_jsonl(path):
        case = EvalCase(
            id=str(record["id"]),
            user_image=str(record["user_image"]),
            template_image=str(record["template_image"]),
            style=str(record.get("style", "")),
            attributes=dict(record.get("attributes") or {}),
        )

        if case.id in seen_ids:
            raise ValueError(f"Duplicate case id: {case.id}")
        seen_ids.add(case.id)

        if not case.user_path(dataset_root).exists():
            raise FileNotFoundError(f"Missing user image for {case.id}: {case.user_path(dataset_root)}")
        if not case.template_path(dataset_root).exists():
            raise FileNotFoundError(
                f"Missing template image for {case.id}: {case.template_path(dataset_root)}"
            )

        cases.append(case)

    return cases


def make_run_dir(root: Path, run_id: str | None = None) -> Path:
    run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = root / run_id
    (run_dir / "outputs").mkdir(parents=True, exist_ok=True)
    return run_dir
