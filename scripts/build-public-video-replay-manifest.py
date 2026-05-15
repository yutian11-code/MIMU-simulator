#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path


QUERY = r"""docker exec mymakeup-postgres psql -U mymakeup -d mymakeup -F ',' -A -c "select s.id, s.platform, s.source_url, s.title, coalesce(s.author_name,''), coalesce(s.source_description,''), coalesce(to_char(s.publish_time at time zone 'UTC','YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'),''), coalesce(to_char(s.crawl_time at time zone 'UTC','YYYY-MM-DD\"T\"HH24:MI:SS\"Z\"'),''), s.visibility_status, s.accessibility_status, coalesce(s.notes,''), a.local_path from public_video_sources s join public_video_assets a on a.source_id=s.id order by s.created_at asc;" """


def infer_hints(title: str) -> tuple[list[str], list[str], str]:
    value = title.lower()

    if any(token in value for token in ["bridal", "wedding", "bride"]):
        return ["bridal makeup", "natural glam"], ["wedding"], "P1"

    if any(token in value for token in ["smokey", "smoky", "contour", "highlight"]):
        return ["smokey eye", "glam"], ["date"], "P1"

    if any(token in value for token in ["halloween", "kitty", "nun", "valak", "possessed"]):
        return ["halloween makeup", "creative"], ["stage"], "P2"

    if any(token in value for token in ["red lip", "strong lip", "lip"]):
        return ["red lip", "retro"], ["date"], "P2"

    if any(token in value for token in ["glow", "perfecting", "base", "everyday", "beginner", "daily"]):
        return ["daily makeup", "beginner makeup"], ["commute"], "P2"

    if any(token in value for token in ["dior", "masterclass", "luxury"]):
        return ["luxury beauty", "elegant"], ["camera"], "P2"

    return ["daily makeup"], ["camera"], "P3"


def main() -> None:
    result = subprocess.run(
        QUERY,
        shell=True,
        capture_output=True,
        text=True,
        check=True,
    )
    lines = [line for line in result.stdout.splitlines() if line.strip() and not line.startswith("(")]
    reader = csv.reader(lines)
    next(reader)

    rows: list[dict] = []
    for row in reader:
        if len(row) < 12:
            continue
        style_hints, scene_hints, priority_hint = infer_hints(row[3])
        rows.append(
            {
                "id": row[0],
                "platform": row[1],
                "url": row[2],
                "title": row[3],
                "author": row[4] or None,
                "sourceDescription": row[5] or None,
                "publishTime": row[6] or None,
                "crawlTime": row[7] or None,
                "visibilityStatus": row[8],
                "accessibilityStatus": row[9],
                "notes": row[10] or None,
                "localAssetPath": row[11],
                "styleHints": style_hints,
                "sceneHints": scene_hints,
                "priorityHint": priority_hint,
            }
        )

    output = Path("backend/data/public-video-template-library/public-video-replay-local-enriched.json")
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2))
    print(output)
    print(len(rows))


if __name__ == "__main__":
    main()
