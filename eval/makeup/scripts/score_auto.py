#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from mimu_eval.scoring import write_auto_scores


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score MIMU makeup evaluation outputs with deterministic metrics.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = args.dataset_root or args.manifest.parent.parent
    output = write_auto_scores(args.manifest, dataset_root=dataset_root, run_dir=args.run_dir)
    print(output)


if __name__ == "__main__":
    main()
