#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import time
import urllib.parse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup


USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)

DEFAULT_QUERIES = [
    ("bridal makeup tutorial Vimeo", ["bridal makeup", "natural glam"], ["wedding"], "P1"),
    ("smokey eye makeup tutorial Vimeo", ["smokey eye", "glam"], ["date"], "P1"),
    ("daily makeup tutorial Vimeo", ["daily makeup", "beginner makeup"], ["commute"], "P2"),
    ("contour highlight makeup tutorial Vimeo", ["contour", "highlight"], ["camera"], "P2"),
    ("halloween makeup tutorial Vimeo", ["halloween makeup", "creative"], ["stage"], "P2"),
    ("red lip makeup tutorial Vimeo", ["red lip", "retro"], ["date"], "P2"),
    ("glow makeup tutorial Vimeo", ["glow makeup", "clean"], ["camera"], "P2"),
    ("luxury beauty masterclass makeup Vimeo", ["luxury beauty", "elegant"], ["camera"], "P2"),
]

VIMEO_URL_RE = re.compile(r"https?://(?:www\.)?vimeo\.com/(?:channels/[^/]+/|groups/[^/]+/videos/)?(\d+)")


@dataclass
class Candidate:
    url: str
    title: str
    query: str
    style_hints: list[str]
    scene_hints: list[str]
    priority_hint: str
    validated: bool = False
    validation_error: str | None = None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="backend/data/public-video-template-library/public-video-seeds-expanded.json",
    )
    parser.add_argument("--target-count", type=int, default=100)
    parser.add_argument("--per-query", type=int, default=25)
    parser.add_argument("--sleep-seconds", type=float, default=1.0)
    parser.add_argument("--validate-timeout", type=int, default=40)
    parser.add_argument("--no-validate", action="store_true")
    parser.add_argument("--only-discover", action="store_true")
    return parser.parse_args()


def load_existing_urls() -> set[str]:
    seed_path = Path("backend/data/public-video-template-library/public-video-seeds.json")
    if not seed_path.exists():
      return set()
    rows = json.loads(seed_path.read_text())
    urls = set()
    for row in rows:
        url = normalize_vimeo_url(row.get("url") or row.get("sourceUrl") or "")
        if url:
            urls.add(url)
    return urls


def normalize_vimeo_url(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    match = VIMEO_URL_RE.search(value)
    if not match:
        return None
    return f"https://vimeo.com/{match.group(1)}"


def search_duckduckgo(query: str, limit: int) -> list[tuple[str, str]]:
    response = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    results: list[tuple[str, str]] = []
    for anchor in soup.select("a.result__a"):
        href = anchor.get("href") or ""
        title = html.unescape(anchor.get_text(" ", strip=True))
        parsed = urllib.parse.urlparse(href)
        if parsed.netloc == "duckduckgo.com" and parsed.path == "/l/":
            target = urllib.parse.parse_qs(parsed.query).get("uddg", [""])[0]
        else:
            target = href
        normalized = normalize_vimeo_url(target)
        if normalized:
            results.append((normalized, title))
        if len(results) >= limit:
            break
    return results


def expand_from_vimeo_channel(channel_url: str, limit: int) -> list[tuple[str, str]]:
    command = [
        "yt-dlp",
        "--flat-playlist",
        "--print",
        "%(title)s\t%(webpage_url)s",
        channel_url,
    ]
    completed = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    if completed.returncode != 0:
        return []
    rows: list[tuple[str, str]] = []
    for line in completed.stdout.splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        title, url = parts
        normalized = normalize_vimeo_url(url)
        if normalized:
            rows.append((normalized, html.unescape(title)))
        if len(rows) >= limit:
            break
    return rows


def validate_url(url: str, timeout_seconds: int) -> tuple[bool, str | None]:
    command = [
        "yt-dlp",
        "--simulate",
        "--no-playlist",
        "--skip-download",
        url,
    ]
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)

    if completed.returncode == 0:
        return True, None
    message = (completed.stderr or completed.stdout or "").strip()
    return False, message or f"yt-dlp exit code {completed.returncode}"


def dedupe_candidates(candidates: Iterable[Candidate]) -> list[Candidate]:
    deduped: dict[str, Candidate] = {}
    for candidate in candidates:
        deduped.setdefault(candidate.url, candidate)
    return list(deduped.values())


def build_seed_rows(candidates: list[Candidate]) -> list[dict]:
    rows = []
    for candidate in candidates:
        rows.append(
            {
                "platform": "vimeo",
                "url": candidate.url,
                "title": candidate.title[:300],
                "author": "Vimeo public source",
                "styleHints": candidate.style_hints,
                "sceneHints": candidate.scene_hints,
                "priorityHint": candidate.priority_hint,
                "notes": (
                    "Validated by yt-dlp anonymous simulate."
                    if candidate.validated
                    else f"Unvalidated candidate. {candidate.validation_error or ''}".strip()
                ),
                "metadata": {
                    "discoveryQuery": candidate.query,
                    "validationError": candidate.validation_error,
                },
            }
        )
    return rows


def main() -> None:
    args = parse_args()
    existing_urls = load_existing_urls()
    candidates: list[Candidate] = []

    for query, style_hints, scene_hints, priority in DEFAULT_QUERIES:
        discovered = search_duckduckgo(query, args.per_query)
        for url, title in discovered:
            if url in existing_urls:
                continue
            candidates.append(
                Candidate(
                    url=url,
                    title=title or url,
                    query=query,
                    style_hints=style_hints,
                    scene_hints=scene_hints,
                    priority_hint=priority,
                )
            )
        time.sleep(args.sleep_seconds)

    channel_sources = [
        ("https://vimeo.com/channels/901161", ["smokey eye", "glam"], ["camera"], "P2"),
        ("https://vimeo.com/channels/1729077", ["retro makeup", "editorial"], ["camera"], "P3"),
    ]
    for channel_url, style_hints, scene_hints, priority in channel_sources:
        discovered = expand_from_vimeo_channel(channel_url, args.per_query)
        for url, title in discovered:
            if url in existing_urls:
                continue
            candidates.append(
                Candidate(
                    url=url,
                    title=title or url,
                    query=channel_url,
                    style_hints=style_hints,
                    scene_hints=scene_hints,
                    priority_hint=priority,
                )
            )

    candidates = dedupe_candidates(candidates)

    if not args.no_validate and not args.only_discover:
        for candidate in candidates:
            ok, error_message = validate_url(candidate.url, args.validate_timeout)
            candidate.validated = ok
            candidate.validation_error = error_message

    validated = [candidate for candidate in candidates if candidate.validated]
    if args.only_discover:
        selected = candidates[: args.target_count]
    elif len(validated) < args.target_count:
        selected = validated
    else:
        selected = validated[: args.target_count]

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(build_seed_rows(selected), ensure_ascii=False, indent=2))

    report_path = output_path.with_suffix(".report.json")
    report_path.write_text(
        json.dumps(
            {
                "existingSeedCount": len(existing_urls),
                "candidateCount": len(candidates),
                "validatedCount": len(validated),
                "selectedCount": len(selected),
                "selectedUrls": [candidate.url for candidate in selected],
                "sampleCandidates": [asdict(candidate) for candidate in candidates[:20]],
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    print(output_path)
    print(report_path)
    print(
        json.dumps(
            {
                "existingSeedCount": len(existing_urls),
                "candidateCount": len(candidates),
                "validatedCount": len(validated),
                "selectedCount": len(selected),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
