#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from mimu_eval.pipeline import run_eval_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local MIMU makeup evaluation pipeline.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, default=Path("eval/makeup"))
    parser.add_argument("--backend-url", default="http://127.0.0.1:13000")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--vlm-mode", choices=["skip", "mock"], default="mock")
    parser.add_argument("--run-id")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = args.output_root
    if not output_root.is_absolute():
        output_root = args.project_root / output_root

    run_dir = run_eval_pipeline(
        project_root=args.project_root,
        output_root=output_root,
        backend_url=args.backend_url,
        limit=args.limit,
        vlm_mode=args.vlm_mode,
        run_id=args.run_id,
    )
    print(run_dir)


if __name__ == "__main__":
    main()
