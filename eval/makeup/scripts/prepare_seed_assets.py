#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from mimu_eval.assets import prepare_starter_dataset


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare starter MIMU makeup evaluation assets.")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-root", type=Path, default=Path("eval/makeup"))
    parser.add_argument("--case-count", type=int, default=90)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_root = args.output_root
    if not output_root.is_absolute():
        output_root = args.project_root / output_root

    manifest_path = prepare_starter_dataset(
        project_root=args.project_root,
        output_root=output_root,
        case_count=args.case_count,
    )
    print(manifest_path)


if __name__ == "__main__":
    main()
