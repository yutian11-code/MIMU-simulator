#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path


SOURCE_PAGES = [
    "https://vimeo.com/groups/832370",
    "https://vimeo.com/channels/901161",
    "https://vimeo.com/channels/1729077",
    "https://vimeo.com/channels/beautytutorials",
    "https://vimeo.com/kitkatsandclarte",
    "https://vimeo.com/kitkatsandclarte/videos",
]

KEEP_KEYWORDS = [
    ("smokey", (["smokey eye", "glam"], ["date"], "P1")),
    ("smoky", (["smokey eye", "glam"], ["date"], "P1")),
    ("bridal", (["bridal makeup", "natural glam"], ["wedding"], "P1")),
    ("wedding", (["bridal makeup", "natural glam"], ["wedding"], "P1")),
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
    ("skincare", (["prep", "clean"], ["camera"], "P2")),
    ("skin", (["prep", "clean"], ["camera"], "P2")),
    ("face", (["daily makeup"], ["camera"], "P2")),
    ("makeup tutorial", (["makeup"], ["camera"], "P2")),
    ("makeup", (["makeup"], ["camera"], "P2")),
]

BLOCK_KEYWORDS = [
    "pony tail",
    "kirby grips",
    "brush myths",
    "clean your makeup brushes",
    "label makeup brushes",
    "absolute collagen",
    "loved yourself",
    "special occasions",
    "prick",
    "marine biologist",
    "dos equis",
    "powerade",
    "colgate",
    "honda",
    "chrysler",
    "schweppes",
    "ford",
    "kisskill",
    "vance joy",
    "mortal kombat",
]


def normalize_url(url: str) -> str:
    parts = urllib.parse.urlparse(url)
    vid = parts.path.rstrip("/").split("/")[-1]
    return f"https://vimeo.com/{vid}"


def load_existing_urls() -> set[str]:
    existing = set()
    source_path = Path("/tmp/current_public_video_source_urls.txt")
    if source_path.exists():
      for line in source_path.read_text().splitlines():
        line = line.strip()
        if line:
          existing.add(line)
    return existing


def enumerate_page(page_url: str) -> list[dict]:
    proc = subprocess.run(
        ["yt-dlp", "--flat-playlist", "--print", "%(id)s\t%(title)s\t%(webpage_url)s", page_url],
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    rows: list[dict] = []
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        _id, title, webpage_url = parts
        rows.append(
            {
                "title": html.unescape(title).strip(),
                "url": normalize_url(webpage_url.strip()),
                "sourcePage": page_url,
            }
        )
    return rows


def classify(title: str):
    lowered = title.lower()
    for blocked in BLOCK_KEYWORDS:
        if blocked in lowered:
            return None
    for keyword, payload in KEEP_KEYWORDS:
        if keyword in lowered:
            return payload
    return None


def fetch_duration(url: str) -> int | None:
    endpoint = "https://vimeo.com/api/oembed.json?url=" + urllib.parse.quote(url, safe="")
    with urllib.request.urlopen(endpoint, timeout=30) as resp:
        data = json.load(resp)
    duration = data.get("duration")
    return int(duration) if isinstance(duration, int) else None


def main() -> None:
    existing_urls = load_existing_urls()
    discovered: list[dict] = []
    seen = set(existing_urls)

    for page in SOURCE_PAGES:
        for row in enumerate_page(page):
            if row["url"] in seen:
                continue
            seen.add(row["url"])
            discovered.append(row)

    manifest = []
    report = []
    for row in discovered:
        classified = classify(row["title"])
        if not classified:
            continue
        try:
            duration = fetch_duration(row["url"])
        except Exception as exc:  # noqa: BLE001
            report.append({**row, "duration": None, "error": str(exc)})
            continue
        report.append({**row, "duration": duration})
        if duration is None or duration > 360:
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
                "notes": f"Validated by Vimeo public listing + oEmbed duration filter. Source page: {row['sourcePage']}.",
                "metadata": {
                    "discoveryQuery": row["sourcePage"],
                    "durationSeconds": duration,
                },
            }
        )
        time.sleep(0.05)

    out_path = Path("backend/data/public-video-template-library/public-video-100-expansion.json")
    report_path = Path("backend/data/public-video-template-library/public-video-100-expansion.report.json")
    out_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(out_path)
    print(report_path)
    print(json.dumps({"manifestCount": len(manifest), "reportCount": len(report)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
