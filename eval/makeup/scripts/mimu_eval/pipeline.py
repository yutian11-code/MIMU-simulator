from __future__ import annotations

from pathlib import Path
from typing import Protocol

from .assets import prepare_starter_dataset
from .client import MakeupBackendClient
from .models import EvalCase, RunMetadata, append_jsonl, load_cases, make_run_dir
from .report import build_report
from .scoring import write_auto_scores
from .vlm import JudgeMode, write_vlm_scores


class CaseRunner(Protocol):
    def run_case(self, case: EvalCase, dataset_root: Path, run_dir: Path) -> RunMetadata:
        ...


def run_eval_pipeline(
    project_root: Path,
    output_root: Path,
    backend_url: str,
    limit: int | None = None,
    case_count: int = 90,
    vlm_mode: JudgeMode = "mock",
    run_id: str | None = None,
    client: CaseRunner | None = None,
) -> Path:
    manifest = prepare_starter_dataset(
        project_root=project_root,
        output_root=output_root,
        case_count=case_count,
    )
    run_dir = make_run_dir(output_root / "runs", run_id=run_id)
    metadata_path = run_dir / "metadata.jsonl"
    if metadata_path.exists():
        metadata_path.unlink()

    cases = load_cases(manifest, dataset_root=output_root)
    if limit is not None:
        cases = cases[:limit]

    run_manifest = run_dir / "run_manifest.jsonl"
    if run_manifest.exists():
        run_manifest.unlink()
    for case in cases:
        append_jsonl(run_manifest, case.to_record())

    runner = client or MakeupBackendClient(backend_url)
    for case in cases:
        metadata = runner.run_case(case, dataset_root=output_root, run_dir=run_dir)
        append_jsonl(metadata_path, metadata.to_record())
        print(f"{case.id}: {metadata.status}")

    write_auto_scores(run_manifest, dataset_root=output_root, run_dir=run_dir)
    write_vlm_scores(run_manifest, run_dir=run_dir, mode=vlm_mode)
    build_report(run_manifest, dataset_root=output_root, run_dir=run_dir)

    return run_dir
