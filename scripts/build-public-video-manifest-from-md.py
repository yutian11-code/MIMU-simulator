#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


KEEPWORDS = [
    ("smokey", (["smokey eye", "glam"], ["date"], "P1")),
    ("smoky", (["smokey eye", "glam"], ["date"], "P1")),
    ("foundation", (["base makeup", "clean"], ["commute"], "P2")),
    ("brow", (["brow", "daily makeup"], ["commute"], "P2")),
    ("blush", (["blush", "daily makeup"], ["camera"], "P2")),
    ("glow", (["glow makeup", "clean"], ["camera"], "P2")),
    ("lipstick", (["red lip", "daily makeup"], ["date"], "P2")),
    ("lip", (["red lip", "daily makeup"], ["date"], "P2")),
    ("mascara", (["eye makeup", "daily makeup"], ["camera"], "P2")),
    ("powder", (["base makeup", "daily makeup"], ["commute"], "P2")),
    ("contouring", (["contour", "daily makeup"], ["camera"], "P2")),
    ("contour", (["contour", "daily makeup"], ["camera"], "P2")),
    ("skin care", (["prep", "clean"], ["camera"], "P2")),
    ("skin", (["prep", "clean"], ["camera"], "P2")),
    ("face", (["daily makeup"], ["camera"], "P2")),
    ("makeup", (["makeup"], ["camera"], "P2")),
]

BLOCKWORDS = [
    "pony tail",
    "kirby grips",
    "brush myths",
    "clean your makeup brushes",
    "label makeup brushes",
    "absolute collagen",
    "loved yourself",
    "argument",
    "special occasions",
    "prick",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input",
        default="docs/vimeo-public-video-candidates.md",
    )
    parser.add_argument(
        "--output",
        default="backend/data/public-video-template-library/public-video-vimeo-batch-2.json",
    )
    return parser.parse_args()


def parse_rows(markdown_text: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in markdown_text.splitlines():
        if not line.startswith("| "):
            continue
        if line.startswith("| Title |") or line.startswith("| ---"):
            continue
        parts = [part.strip() for part in line.strip("|").split("|")]
        if len(parts) < 5:
            continue
        rows.append(
            {
                "title": parts[0],
                "url": parts[1],
                "source": parts[2],
                "validation": parts[3],
                "tags": parts[4],
            }
        )
    return rows


def classify(title: str) -> tuple[list[str], list[str], str] | None:
    lowered = title.lower()
    for blocked in BLOCKWORDS:
        if blocked in lowered:
            return None

    for keyword, payload in KEEPWORDS:
        if keyword in lowered:
            return payload
    return None


def build_manifest(rows: list[dict[str, str]]) -> list[dict]:
    manifest: list[dict] = []
    for row in rows:
        if row["validation"] != "validated":
            continue
        classified = classify(row["title"])
        if not classified:
            continue
        style_hints, scene_hints, priority = classified
        manifest.append(
            {
                "platform": "vimeo",
                "url": row["url"],
                "title": row["title"][:300],
                "author": "Vimeo public source",
                "styleHints": style_hints,
                "sceneHints": scene_hints,
                "priorityHint": priority,
                "notes": f"Validated by yt-dlp anonymous simulate. Discovered from {row['source']}.",
                "metadata": {
                    "discoveryQuery": row["source"],
                    "sourceTags": [tag.strip() for tag in row["tags"].split(",") if tag.strip()],
                },
            }
        )
    return manifest


def main() -> None:
    args = parse_args()
    input_path = Path(args.input)
    output_path = Path(args.output)

    rows = parse_rows(input_path.read_text())
    manifest = build_manifest(rows)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    print(output_path)
    print(json.dumps({"sourceRows": len(rows), "manifestCount": len(manifest)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
