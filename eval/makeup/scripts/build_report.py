#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from mimu_eval.report import build_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a static MIMU makeup evaluation HTML report.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--dataset-root", type=Path)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    dataset_root = args.dataset_root or args.manifest.parent.parent
    output = build_report(args.manifest, dataset_root=dataset_root, run_dir=args.run_dir, output=args.output)
    print(output)


if __name__ == "__main__":
    main()
