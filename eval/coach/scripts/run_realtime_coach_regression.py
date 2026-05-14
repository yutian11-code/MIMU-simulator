#!/usr/bin/env python3
"""Run local realtime coach regression checks for tomorrow's demo.

The script uses local evaluation images and audio samples, calls the local
backend HTTP coach endpoints, and performs a WebSocket wake-mode handshake. It
does not send raw media directly to third-party services; the backend decides
which already configured local model service to call.
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import mimetypes
import shutil
import ssl
import subprocess
import tempfile
import time
import wave
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests
import websockets


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_EVAL_IMAGE_DIR = ROOT / "eval/data/评测集"
DEFAULT_FALLBACK_IMAGE_DIR = ROOT / "eval/makeup/assets/users"
DEFAULT_AUDIO_DIR = ROOT / "eval/coach/assets/audio"
DEFAULT_FFMPEG = ROOT / "backend/node_modules/ffmpeg-static/ffmpeg"


STEP_HINTS = [
    ("底妆", "BASE", "少量多次铺开粉底，肤色整体均匀。", "肤色整体均匀，没有明显斑驳或厚重堆积。"),
    ("眉毛", "BROW", "顺着毛流填补眉毛空缺。", "眉形完整，左右大体对称。"),
    ("眼妆", "EYE", "完成浅色眼影和自然眼线。", "眼周有浅色修饰，眼线或睫毛存在感自然。"),
    ("腮红", "BLUSH", "少量腮红提升气色。", "苹果肌附近有自然气色，边界没有明显色块。"),
    ("唇妆", "LIP", "完成自然唇色。", "唇色均匀，边缘自然。"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-url", default="http://127.0.0.1:13001")
    parser.add_argument("--token", default="demo-token")
    parser.add_argument("--image-limit", type=int, default=4)
    parser.add_argument("--video-limit", type=int, default=2)
    parser.add_argument("--video-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--audio-dir", type=Path, default=DEFAULT_AUDIO_DIR)
    parser.add_argument("--output", type=Path, default=Path("/tmp/mimu-coach-regression.json"))
    parser.add_argument("--timeout", type=float, default=90.0)
    parser.add_argument("--ffmpeg", type=Path, default=None)
    return parser.parse_args()


def data_url(path: Path) -> str:
    mime_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime_type};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def list_images(limit: int) -> list[Path]:
    candidates: list[Path] = []
    if DEFAULT_EVAL_IMAGE_DIR.is_dir():
        candidates.extend(
            path
            for path in sorted(DEFAULT_EVAL_IMAGE_DIR.rglob("*"))
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )
    if not candidates and DEFAULT_FALLBACK_IMAGE_DIR.is_dir():
        candidates.extend(
            path
            for path in sorted(DEFAULT_FALLBACK_IMAGE_DIR.glob("*"))
            if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}
        )
    return candidates[: max(0, limit)]


def list_audio(audio_dir: Path) -> list[Path]:
    if not audio_dir.is_dir():
        return []
    return [
        path
        for path in sorted(audio_dir.rglob("*"))
        if path.suffix.lower() in {".wav", ".mp3", ".m4a", ".webm", ".ogg"}
    ]


def list_videos(video_dir: Path, limit: int) -> list[Path]:
    if limit <= 0 or not video_dir.is_dir():
        return []

    return [
        path
        for path in sorted(video_dir.rglob("*"))
        if path.suffix.lower() in {".mp4", ".mov", ".m4v", ".webm", ".avi"}
    ][:limit]


def resolve_ffmpeg(configured: Path | None) -> Path | None:
    if configured and configured.exists():
        return configured
    if DEFAULT_FFMPEG.exists():
        return DEFAULT_FFMPEG
    system_ffmpeg = shutil.which("ffmpeg")
    return Path(system_ffmpeg) if system_ffmpeg else None


def extract_video_frame(video: Path, ffmpeg: Path, output_dir: Path, index: int) -> Path:
    output = output_dir / f"video_frame_{index + 1:02d}.jpg"
    command = [
        str(ffmpeg),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        "1.0",
        "-i",
        str(video),
        "-frames:v",
        "1",
        "-vf",
        "scale='min(960,iw)':-2",
        str(output),
    ]
    subprocess.run(command, check=True, capture_output=True, text=True)
    return output


def inspect_wav_audio(path: Path) -> dict[str, Any] | None:
    if path.suffix.lower() != ".wav":
        return None

    try:
        with wave.open(str(path), "rb") as wav:
            frame_count = wav.getnframes()
            frame_rate = wav.getframerate()
            sample_width = wav.getsampwidth()
            frames = wav.readframes(frame_count)
    except wave.Error:
        return {"durationSeconds": 0, "rms": 0, "invalid": True}

    duration = frame_count / frame_rate if frame_rate else 0
    sample_count = len(frames) // sample_width if sample_width else 0
    if sample_count == 0:
        return {"durationSeconds": duration, "rms": 0, "invalid": True}

    square_sum = 0.0
    if sample_width == 1:
        for value in frames:
            sample = value - 128
            square_sum += sample * sample
    elif sample_width in {2, 4}:
        for offset in range(0, len(frames) - sample_width + 1, sample_width):
            sample = int.from_bytes(frames[offset : offset + sample_width], "little", signed=True)
            square_sum += sample * sample
    else:
        return {"durationSeconds": duration, "rms": 0, "invalid": True}

    rms = int((square_sum / sample_count) ** 0.5)
    return {"durationSeconds": round(duration, 3), "rms": rms, "invalid": False}


def audio_skip_reason(path: Path) -> tuple[str | None, dict[str, Any] | None]:
    metadata = inspect_wav_audio(path)
    if metadata is None:
        return None, None
    if metadata.get("invalid"):
        return "invalid_wav", metadata
    duration = float(metadata.get("durationSeconds") or 0)
    rms = int(metadata.get("rms") or 0)
    if rms < 50:
        return f"low_rms_no_speech:rms={rms}", metadata
    if duration > 30 and rms < 200:
        return f"long_low_energy_sample:duration={duration}s,rms={rms}", metadata
    return None, metadata


def post_json(
    session: requests.Session,
    url: str,
    token: str,
    payload: dict[str, Any],
    timeout: float,
) -> tuple[int, Any, int, str | None]:
    started = time.perf_counter()
    try:
        response = session.post(
            url,
            json=payload,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
        )
        latency_ms = round((time.perf_counter() - started) * 1000)
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        return response.status_code, body, latency_ms, None
    except Exception as exc:  # noqa: BLE001 - regression report should capture all endpoint failures.
        latency_ms = round((time.perf_counter() - started) * 1000)
        return 0, None, latency_ms, str(exc)


def build_step_payload(image: Path, index: int) -> dict[str, Any]:
    title, code, instruction, criteria = STEP_HINTS[index % len(STEP_HINTS)]
    return {
        "scenario": "明日上线回归",
        "stepTitle": title,
        "stepInstruction": instruction,
        "completedStepTitles": [item[0] for item in STEP_HINTS[: index % len(STEP_HINTS)]],
        "totalSteps": 5,
        "userQuestion": "请判断当前画面能不能进入下一步。",
        "imageDataUrl": data_url(image),
        "generatedTemplateId": "regression_generated_template",
        "stepId": f"regression_step_{index + 1}",
        "stepCode": code,
        "completionCriteria": criteria,
    }


def run_image_cases(args: argparse.Namespace, session: requests.Session) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for index, image in enumerate(list_images(args.image_limit)):
        payload = build_step_payload(image, index)
        status, body, latency_ms, error = post_json(
            session,
            f"{args.backend_url.rstrip('/')}/makeup/coach/step-evaluate",
            args.token,
            payload,
            args.timeout,
        )
        response = body if isinstance(body, dict) else {}
        passed = (
            error is None
            and status == 200
            and isinstance(body, dict)
            and isinstance(response.get("canAutoAdvance"), bool)
            and isinstance(response.get("voiceText"), str)
        )
        cases.append(
            {
                "type": "image_step_evaluate",
                "endpoint": "/makeup/coach/step-evaluate",
                "source": str(image.relative_to(ROOT)),
                "stepTitle": payload["stepTitle"],
                "statusCode": status,
                "latencyMs": latency_ms,
                "passed": passed,
                "voiceAction": None,
                "canAutoAdvance": response.get("canAutoAdvance"),
                "error": error,
            }
        )
    return cases


def run_video_frame_cases(args: argparse.Namespace, session: requests.Session) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    videos = list_videos(args.video_dir, args.video_limit)
    if not videos:
        return cases

    ffmpeg = resolve_ffmpeg(args.ffmpeg)
    if not ffmpeg:
        return [
            {
                "type": "video_frame_step_evaluate",
                "endpoint": "/makeup/coach/step-evaluate",
                "source": str(video.relative_to(ROOT)),
                "stepTitle": "底妆",
                "statusCode": None,
                "latencyMs": 0,
                "passed": True,
                "skipped": True,
                "skipReason": "ffmpeg_unavailable",
                "voiceAction": None,
                "canAutoAdvance": None,
                "error": None,
            }
            for video in videos
        ]

    with tempfile.TemporaryDirectory(prefix="mimu-coach-video-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        for index, video in enumerate(videos):
            title, code, instruction, criteria = STEP_HINTS[index % len(STEP_HINTS)]
            try:
                frame = extract_video_frame(video, ffmpeg, temp_dir, index)
                payload = {
                    "scenario": "明日上线真人视频回归",
                    "stepTitle": title,
                    "stepInstruction": instruction,
                    "completedStepTitles": [item[0] for item in STEP_HINTS[: index % len(STEP_HINTS)]],
                    "totalSteps": 5,
                    "userQuestion": "这是用户实测视频抽帧，请判断当前画面能不能进入下一步。",
                    "imageDataUrl": data_url(frame),
                    "generatedTemplateId": "regression_video_generated_template",
                    "stepId": f"regression_video_step_{index + 1}",
                    "stepCode": code,
                    "completionCriteria": criteria,
                }
                status, body, latency_ms, error = post_json(
                    session,
                    f"{args.backend_url.rstrip('/')}/makeup/coach/step-evaluate",
                    args.token,
                    payload,
                    args.timeout,
                )
                response = body if isinstance(body, dict) else {}
                passed = (
                    error is None
                    and status == 200
                    and isinstance(body, dict)
                    and isinstance(response.get("canAutoAdvance"), bool)
                    and isinstance(response.get("voiceText"), str)
                )
                cases.append(
                    {
                        "type": "video_frame_step_evaluate",
                        "endpoint": "/makeup/coach/step-evaluate",
                        "source": str(video.relative_to(ROOT)),
                        "stepTitle": title,
                        "statusCode": status,
                        "latencyMs": latency_ms,
                        "passed": passed,
                        "skipped": False,
                        "frameSecond": 1.0,
                        "voiceAction": None,
                        "canAutoAdvance": response.get("canAutoAdvance"),
                        "error": error,
                    }
                )
            except Exception as exc:  # noqa: BLE001 - regression report should capture video failures.
                cases.append(
                    {
                        "type": "video_frame_step_evaluate",
                        "endpoint": "/makeup/coach/step-evaluate",
                        "source": str(video.relative_to(ROOT)),
                        "stepTitle": title,
                        "statusCode": 0,
                        "latencyMs": 0,
                        "passed": False,
                        "skipped": False,
                        "frameSecond": 1.0,
                        "voiceAction": None,
                        "canAutoAdvance": None,
                        "error": str(exc),
                    }
                )
    return cases


def run_audio_cases(args: argparse.Namespace, session: requests.Session) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for index, audio in enumerate(list_audio(args.audio_dir)[:3]):
        skip_reason, audio_metadata = audio_skip_reason(audio)
        title, code, instruction, criteria = STEP_HINTS[index % len(STEP_HINTS)]
        if skip_reason:
            cases.append(
                {
                    "type": "voice_coach",
                    "endpoint": "/makeup/coach/voice",
                    "source": str(audio.relative_to(ROOT)),
                    "stepTitle": title,
                    "statusCode": None,
                    "latencyMs": 0,
                    "passed": True,
                    "skipped": True,
                    "skipReason": skip_reason,
                    "audio": audio_metadata,
                    "voiceAction": None,
                    "canAutoAdvance": None,
                    "error": None,
                }
            )
            continue
        payload = {
            "scenario": "明日上线语音回归",
            "stepTitle": title,
            "stepInstruction": instruction,
            "completedStepTitles": [],
            "totalSteps": 5,
            "userQuestion": "请结合语音确认是否进入下一步。",
            "audioDataUrl": data_url(audio),
            "audioMimeType": mimetypes.guess_type(audio.name)[0] or "audio/wav",
            "interactionMode": "tap",
            "clientTurnId": f"regression_audio_{index + 1}",
            "generatedTemplateId": "regression_generated_template",
            "stepId": f"regression_audio_step_{index + 1}",
            "stepCode": code,
            "completionCriteria": criteria,
        }
        images = list_images(1)
        if images:
            payload["imageDataUrl"] = data_url(images[0])
        status, body, latency_ms, error = post_json(
            session,
            f"{args.backend_url.rstrip('/')}/makeup/coach/voice",
            args.token,
            payload,
            args.timeout,
        )
        response = body if isinstance(body, dict) else {}
        passed = (
            error is None
            and status == 200
            and isinstance(body, dict)
            and isinstance(response.get("transcript"), str)
            and response.get("voiceAction") in {"ask_guidance", "confirm_step", "previous_step", "repeat", "stop", "unknown"}
        )
        cases.append(
            {
                "type": "voice_coach",
                "endpoint": "/makeup/coach/voice",
                "source": str(audio.relative_to(ROOT)),
                "stepTitle": title,
                "statusCode": status,
                "latencyMs": latency_ms,
                "passed": passed,
                "skipped": False,
                "audio": audio_metadata,
                "voiceAction": response.get("voiceAction"),
                "canAutoAdvance": response.get("canAutoAdvance"),
                "error": error,
            }
        )
    return cases


def websocket_url(backend_url: str) -> str:
    parsed = urlparse(backend_url.rstrip("/"))
    scheme = "wss" if parsed.scheme == "https" else "ws"
    return urlunparse((scheme, parsed.netloc, "/makeup/coach/realtime/wake", "", "", ""))


async def run_websocket_case(args: argparse.Namespace) -> dict[str, Any]:
    url = websocket_url(args.backend_url)
    started = time.perf_counter()
    ssl_context = ssl._create_unverified_context() if url.startswith("wss://") else None
    try:
        async with websockets.connect(url, ssl=ssl_context, open_timeout=8, close_timeout=2) as socket:
            await socket.send(
                json.dumps(
                    {
                        "type": "start",
                        "payload": {
                            "scenario": "明日上线 WebSocket 回归",
                            "stepTitle": "底妆",
                            "stepInstruction": "少量多次铺开粉底。",
                            "completedStepTitles": [],
                            "totalSteps": 5,
                            "wakeWordMode": True,
                            "wakeActivationMs": 15000,
                            "generatedTemplateId": "regression_generated_template",
                            "stepId": "regression_ws_step_1",
                            "stepCode": "BASE",
                            "completionCriteria": "肤色整体均匀。",
                        },
                    },
                    ensure_ascii=False,
                )
            )
            seen: list[str] = []
            deadline = time.perf_counter() + 8
            while time.perf_counter() < deadline:
                event = json.loads(await asyncio.wait_for(socket.recv(), timeout=deadline - time.perf_counter()))
                seen.append(str(event.get("type")))
                if event.get("type") in {"session_ready", "listening"}:
                    return {
                        "type": "websocket_wake_handshake",
                        "endpoint": "/makeup/coach/realtime/wake",
                        "source": url,
                        "statusCode": 101,
                        "latencyMs": round((time.perf_counter() - started) * 1000),
                        "passed": True,
                        "events": seen,
                        "voiceAction": None,
                        "canAutoAdvance": None,
                        "error": None,
                    }
            raise TimeoutError("no session_ready/listening event")
    except Exception as exc:  # noqa: BLE001 - report endpoint failure.
        return {
            "type": "websocket_wake_handshake",
            "endpoint": "/makeup/coach/realtime/wake",
            "source": url,
            "statusCode": 0,
            "latencyMs": round((time.perf_counter() - started) * 1000),
            "passed": False,
            "events": [],
            "voiceAction": None,
            "canAutoAdvance": None,
            "error": str(exc),
        }


def main() -> int:
    args = parse_args()
    started_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    session = requests.Session()
    cases = run_image_cases(args, session)
    cases.extend(run_video_frame_cases(args, session))
    cases.extend(run_audio_cases(args, session))
    cases.append(asyncio.run(run_websocket_case(args)))
    completed_at = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    failed = [case for case in cases if not case["passed"]]
    report = {
        "startedAt": started_at,
        "completedAt": completed_at,
        "backendUrl": args.backend_url,
        "passed": len(failed) == 0,
        "total": len(cases),
        "failed": len(failed),
        "cases": cases,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"passed": report["passed"], "total": report["total"], "failed": report["failed"], "output": str(args.output)}, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
