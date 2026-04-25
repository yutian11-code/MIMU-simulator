#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path

from mimu_eval.vlm import write_vlm_scores


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Judge MIMU makeup evaluation outputs with a VLM adapter.")
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--mode", choices=["skip", "mock"], default="skip")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output = write_vlm_scores(args.manifest, run_dir=args.run_dir, mode=args.mode)
    print(output)


if __name__ == "__main__":
    main()
