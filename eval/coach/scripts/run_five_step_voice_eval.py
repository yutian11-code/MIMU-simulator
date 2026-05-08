#!/usr/bin/env python3
"""Run the five-step AI makeup coach voice evaluation.

The script reads the synthetic five-step manifest, pairs each step image with
its matching voice sample, calls /makeup/coach/voice, and writes a JSONL result
stream plus a summary file under eval/data.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import requests


DEFAULT_DATA_ROOT = Path("eval/data/ai_makeup_coach_synthetic")
DEFAULT_MANIFEST = DEFAULT_DATA_ROOT / "manifests/demo_5step_same_person_10groups.jsonl"
DEFAULT_AUDIO_DIR = DEFAULT_DATA_ROOT / "audio/five_step"

STEP_AUDIO = {
    "底妆": {
        "filename": "step_01_base_confirm.mp3",
        "text": "我底妆画好了，可以进入下一步了吗？",
        "expected_keywords": ["底妆", "下一步"],
    },
    "眉毛": {
        "filename": "step_02_brow_confirm.mp3",
        "text": "我眉毛画好了，可以进入下一步了吗？",
        "expected_keywords": ["眉毛", "下一步"],
    },
    "眼妆": {
        "filename": "step_03_eye_confirm.mp3",
        "text": "我眼妆画好了，可以进入下一步了吗？",
        "expected_keywords": ["眼妆", "下一步"],
    },
    "腮红": {
        "filename": "step_04_blush_confirm.mp3",
        "text": "我腮红画好了，可以进入下一步了吗？",
        "expected_keywords": ["腮红", "下一步"],
    },
    "唇妆": {
        "filename": "step_05_lip_finish.mp3",
        "text": "我唇妆画好了，可以完成了吗？",
        "expected_keywords": ["唇妆", "完成"],
    },
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line_number, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{line_number} is not valid JSONL") from exc
    return records


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")


def data_url(path: Path, mime_type: str) -> str:
    return f"data:{mime_type};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def normalize_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"[\s，。！？、,.!?;；:：\"'“”‘’（）()]+", "", value).lower()


def check_transcript(transcript: Any, expected_keywords: list[str]) -> bool:
    normalized = normalize_text(transcript)
    return bool(normalized) and all(normalize_text(keyword) in normalized for keyword in expected_keywords)


def current_step_matches(response: dict[str, Any], expected: dict[str, Any]) -> bool:
    detected = normalize_text(response.get("currentStepDetected"))
    accepted = expected.get("currentStepDetectedAnyOf")
    if not isinstance(accepted, list) or not accepted:
        return bool(detected)
    return any(normalize_text(item) in detected for item in accepted)


def detected_issues_match(response: dict[str, Any], expected: dict[str, Any]) -> bool:
    expected_issues = expected.get("detectedIssues")
    actual_issues = response.get("detectedIssues")
    if expected_issues == []:
        return isinstance(actual_issues, list) and len(actual_issues) == 0
    return isinstance(actual_issues, list)


def build_payload(record: dict[str, Any], data_root: Path, audio_dir: Path) -> dict[str, Any]:
    step_title = record["stepTitle"]
    audio_spec = STEP_AUDIO.get(step_title)
    if audio_spec is None:
        raise KeyError(f"No audio sample configured for stepTitle={step_title!r}")

    image_path = data_root / record["image"]
    audio_path = audio_dir / audio_spec["filename"]
    if not image_path.is_file():
        raise FileNotFoundError(f"Missing image: {image_path}")
    if not audio_path.is_file():
        raise FileNotFoundError(f"Missing audio: {audio_path}")

    return {
        "scenario": record["scenario"],
        "stepTitle": step_title,
        "stepInstruction": record["stepInstruction"],
        "completedStepTitles": record.get("completedStepTitles", []),
        "totalSteps": record.get("totalSteps", 5),
        "audioDataUrl": data_url(audio_path, "audio/mpeg"),
        "audioMimeType": "audio/mpeg",
        "imageDataUrl": data_url(image_path, "image/png"),
        "interactionMode": "conversation",
        "clientTurnId": record["id"],
    }


def call_voice_coach(
    session: requests.Session,
    backend_url: str,
    payload: dict[str, Any],
    timeout: float,
) -> tuple[int, dict[str, Any] | str]:
    response = session.post(
        f"{backend_url.rstrip('/')}/makeup/coach/voice",
        json=payload,
        timeout=timeout,
    )
    try:
        body: dict[str, Any] | str = response.json()
    except ValueError:
        body = response.text
    return response.status_code, body


def evaluate_response(record: dict[str, Any], body: Any, status_code: int) -> dict[str, bool]:
    expected = record.get("expected", {})
    step_audio = STEP_AUDIO[record["stepTitle"]]
    response = body if isinstance(body, dict) else {}
    should_proceed = response.get("shouldProceed")

    return {
        "httpOk": status_code == 200 and isinstance(body, dict),
        "asrOk": check_transcript(response.get("transcript"), step_audio["expected_keywords"]),
        "voiceActionOk": response.get("voiceAction") in {"ask_guidance", "confirm_step"},
        "currentStepOk": current_step_matches(response, expected),
        "shouldProceedOk": should_proceed is expected.get("shouldProceed"),
        "detectedIssuesOk": detected_issues_match(response, expected),
    }


def build_result(
    record: dict[str, Any],
    status_code: int,
    body: Any,
    latency_ms: int,
    error: str | None,
) -> dict[str, Any]:
    audio_spec = STEP_AUDIO[record["stepTitle"]]
    checks = evaluate_response(record, body, status_code) if error is None else {
        "httpOk": False,
        "asrOk": False,
        "voiceActionOk": False,
        "currentStepOk": False,
        "shouldProceedOk": False,
        "detectedIssuesOk": False,
    }

    return {
        "id": record["id"],
        "groupId": record["groupId"],
        "sequenceIndex": record["sequenceIndex"],
        "stepId": record["stepId"],
        "stepTitle": record["stepTitle"],
        "image": record["image"],
        "audio": {
            "filename": audio_spec["filename"],
            "text": audio_spec["text"],
        },
        "expected": record.get("expected", {}),
        "statusCode": status_code,
        "latencyMs": latency_ms,
        "checks": checks,
        "passed": all(checks.values()),
        "error": error,
        "response": body,
    }


def summarize(
    results: list[dict[str, Any]],
    started_at: str,
    completed_at: str,
    backend_url: str,
    manifest: Path,
    audio_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    check_failures: Counter[str] = Counter()
    by_step: dict[str, Counter[str]] = defaultdict(Counter)
    by_group: dict[str, Counter[str]] = defaultdict(Counter)
    voice_actions: Counter[str] = Counter()
    providers: Counter[str] = Counter()
    models: Counter[str] = Counter()
    failures: list[dict[str, Any]] = []

    for result in results:
        step_title = result["stepTitle"]
        group_id = result["groupId"]
        passed = bool(result["passed"])
        by_step[step_title]["total"] += 1
        by_group[group_id]["total"] += 1
        by_step[step_title]["passed" if passed else "failed"] += 1
        by_group[group_id]["passed" if passed else "failed"] += 1

        response = result.get("response")
        if isinstance(response, dict):
            voice_actions[str(response.get("voiceAction", "missing"))] += 1
            providers[str(response.get("provider", "missing"))] += 1
            models[str(response.get("model", "missing"))] += 1

        for check_name, ok in result["checks"].items():
            if not ok:
                check_failures[check_name] += 1

        if not passed:
            response_dict = response if isinstance(response, dict) else {}
            failures.append(
                {
                    "id": result["id"],
                    "groupId": group_id,
                    "stepTitle": step_title,
                    "image": result["image"],
                    "audio": result["audio"]["filename"],
                    "failedChecks": [
                        check_name for check_name, ok in result["checks"].items() if not ok
                    ],
                    "statusCode": result["statusCode"],
                    "transcript": response_dict.get("transcript"),
                    "currentStepDetected": response_dict.get("currentStepDetected"),
                    "shouldProceed": response_dict.get("shouldProceed"),
                    "detectedIssues": response_dict.get("detectedIssues"),
                    "guidance": response_dict.get("guidance"),
                    "error": result.get("error"),
                }
            )

    total = len(results)
    passed_count = sum(1 for result in results if result["passed"])

    return {
        "startedAt": started_at,
        "completedAt": completed_at,
        "backendUrl": backend_url,
        "manifest": manifest.as_posix(),
        "audioDir": audio_dir.as_posix(),
        "outputDir": output_dir.as_posix(),
        "total": total,
        "passed": passed_count,
        "failed": total - passed_count,
        "checkFailures": dict(sorted(check_failures.items())),
        "voiceActions": dict(sorted(voice_actions.items())),
        "providers": dict(sorted(providers.items())),
        "models": dict(sorted(models.items())),
        "byStep": {
            key: dict(value) for key, value in sorted(by_step.items(), key=lambda item: item[0])
        },
        "byGroup": {
            key: dict(value) for key, value in sorted(by_group.items(), key=lambda item: item[0])
        },
        "failures": failures,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend-url", default=os.environ.get("COACH_BACKEND_URL", "http://127.0.0.1:13001"))
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--group-id", action="append", default=[])
    parser.add_argument("--step-title", action="append", default=[])
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--sleep-sec", type=float, default=0.1)
    parser.add_argument("--fail-fast", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = args.output_dir or DEFAULT_DATA_ROOT / "runs" / f"five_step_voice_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    records = read_jsonl(args.manifest)
    if args.group_id:
        allowed = set(args.group_id)
        records = [record for record in records if record.get("groupId") in allowed]
    if args.step_title:
        allowed = set(args.step_title)
        records = [record for record in records if record.get("stepTitle") in allowed]
    if args.limit is not None:
        records = records[: args.limit]

    if not records:
        raise SystemExit("No records selected for evaluation.")

    audio_manifest = {
        "generatedFor": "five_step_voice_eval",
        "voice": "zh-CN-XiaoxiaoNeural",
        "audioDir": args.audio_dir.as_posix(),
        "samples": {
            step_title: {
                "filename": spec["filename"],
                "text": spec["text"],
                "expectedKeywords": spec["expected_keywords"],
            }
            for step_title, spec in STEP_AUDIO.items()
        },
    }
    write_json(args.audio_dir / "manifest.json", audio_manifest)

    results_path = output_dir / "voice_coach_results.jsonl"
    results: list[dict[str, Any]] = []
    session = requests.Session()

    with results_path.open("w", encoding="utf-8") as results_file:
        for index, record in enumerate(records, start=1):
            started = time.perf_counter()
            status_code = 0
            body: Any = {}
            error: str | None = None

            try:
                payload = build_payload(record, args.data_root, args.audio_dir)
                status_code, body = call_voice_coach(session, args.backend_url, payload, args.timeout)
            except Exception as exc:  # Keep the eval stream alive and record the failure.
                error = f"{type(exc).__name__}: {exc}"

            latency_ms = round((time.perf_counter() - started) * 1000)
            result = build_result(record, status_code, body, latency_ms, error)
            results.append(result)
            results_file.write(json.dumps(result, ensure_ascii=False, sort_keys=True))
            results_file.write("\n")
            results_file.flush()

            status = "PASS" if result["passed"] else "FAIL"
            print(
                f"[{index:03d}/{len(records):03d}] {status} "
                f"{record['groupId']} {record['stepTitle']} {latency_ms}ms",
                flush=True,
            )

            if args.fail_fast and not result["passed"]:
                break
            if args.sleep_sec > 0:
                time.sleep(args.sleep_sec)

    completed_at = datetime.now().astimezone().isoformat(timespec="seconds")
    summary = summarize(
        results=results,
        started_at=started_at,
        completed_at=completed_at,
        backend_url=args.backend_url,
        manifest=args.manifest,
        audio_dir=args.audio_dir,
        output_dir=output_dir,
    )
    write_json(output_dir / "summary.json", summary)
    write_json(output_dir / "failures.json", summary["failures"])

    print(f"results: {results_path}")
    print(f"summary: {output_dir / 'summary.json'}")
    print(f"passed: {summary['passed']}/{summary['total']}")
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
