#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from mimu_eval.client import MakeupBackendClient
from mimu_eval.models import append_jsonl, load_cases, make_run_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run MIMU makeup evaluation cases through the backend.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--runs-root", type=Path, default=Path("eval/makeup/runs"))
    parser.add_argument("--run-id")
    parser.add_argument("--backend-url", default="http://127.0.0.1:13000")
    parser.add_argument("--timeout-seconds", type=int, default=420)
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = args.dataset_root or args.manifest.parent.parent
    run_dir = args.run_dir or make_run_dir(args.runs_root, args.run_id)
    (run_dir / "outputs").mkdir(parents=True, exist_ok=True)

    metadata_path = run_dir / "metadata.jsonl"
    if metadata_path.exists():
        metadata_path.unlink()

    cases = load_cases(args.manifest, dataset_root=dataset_root)
    if args.limit is not None:
        cases = cases[: args.limit]

    client = MakeupBackendClient(args.backend_url, timeout_seconds=args.timeout_seconds)
    for case in cases:
        metadata = client.run_case(case, dataset_root=dataset_root, run_dir=run_dir)
        append_jsonl(metadata_path, metadata.to_record())
        print(f"{case.id}: {metadata.status}")

    print(run_dir)


if __name__ == "__main__":
    main()
