from __future__ import annotations

import argparse
import base64
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from threading import Lock
from typing import Any

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


DEFAULT_MODEL_PATH = (
    "/storage/nvme3/shushanfu/checkpoint/huggingface/Qwen/Qwen3-ASR-0.6B"
)


@dataclass(frozen=True)
class ParsedAudio:
    mime_type: str
    suffix: str
    content: bytes


class TranscribeRequest(BaseModel):
    audioDataUrl: str = Field(min_length=1)
    audioMimeType: str | None = None


class TranscribeResponse(BaseModel):
    text: str
    provider: str
    model: str
    language: str | None = None


class HealthResponse(BaseModel):
    status: str
    provider: str
    model: str
    loaded: bool
    device: str
    language: str | None = None


def resolve_model_path() -> str:
    configured = os.getenv("MIMU_ASR_MODEL", "").strip()

    if configured:
        return configured

    if Path(DEFAULT_MODEL_PATH).exists():
        return DEFAULT_MODEL_PATH

    return "Qwen/Qwen3-ASR-0.6B"


def resolve_torch_dtype() -> torch.dtype:
    configured = os.getenv("MIMU_ASR_DTYPE", "float16").strip().lower()

    if configured in {"bf16", "bfloat16"}:
        return torch.bfloat16

    if configured in {"fp32", "float32"}:
        return torch.float32

    return torch.float16


def resolve_audio_suffix(mime_type: str) -> str:
    normalized = mime_type.lower().split(";")[0].strip()
    suffix_by_mime = {
        "audio/wav": ".wav",
        "audio/wave": ".wav",
        "audio/x-wav": ".wav",
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mpeg": ".mp3",
        "audio/mp3": ".mp3",
        "audio/mp4": ".m4a",
        "audio/x-m4a": ".m4a",
    }

    return suffix_by_mime.get(normalized, ".wav")


def parse_audio_data_url(audio_data_url: str) -> ParsedAudio:
    if not audio_data_url.startswith("data:") or "," not in audio_data_url:
        raise ValueError("audioDataUrl must be a data URL")

    header, encoded = audio_data_url.split(",", 1)
    metadata = header[5:]
    mime_type = metadata.split(";")[0] or "audio/wav"

    if ";base64" not in metadata:
        raise ValueError("audioDataUrl must contain base64 audio")

    try:
        content = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("audioDataUrl contains invalid base64") from exc

    if not content:
        raise ValueError("audioDataUrl is empty")

    return ParsedAudio(
        mime_type=mime_type,
        suffix=resolve_audio_suffix(mime_type),
        content=content,
    )


class QwenAsrRuntime:
    def __init__(self) -> None:
        self.provider = "qwen-asr"
        self.model_path = resolve_model_path()
        self.device = os.getenv("MIMU_ASR_DEVICE", "cuda:0").strip() or "cuda:0"
        self.language = os.getenv("MIMU_ASR_LANGUAGE", "Chinese").strip() or None
        self._model: Any | None = None
        self._lock = Lock()

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def transcribe(self, parsed_audio: ParsedAudio) -> tuple[str, str | None]:
        audio_path = self._write_temp_audio(parsed_audio)

        try:
            model = self._get_model()
            results = model.transcribe(audio=str(audio_path), language=self.language)
            result = results[0] if results else None
            text = str(getattr(result, "text", "") or "").strip()
            language = getattr(result, "language", self.language)

            return text, str(language) if language else None
        finally:
            audio_path.unlink(missing_ok=True)

    def _get_model(self) -> Any:
        with self._lock:
            if self._model is None:
                from qwen_asr import Qwen3ASRModel

                self._model = Qwen3ASRModel.from_pretrained(
                    self.model_path,
                    dtype=resolve_torch_dtype(),
                    device_map=self.device,
                    max_inference_batch_size=int(
                        os.getenv("MIMU_ASR_MAX_BATCH", "1")
                    ),
                    max_new_tokens=int(os.getenv("MIMU_ASR_MAX_NEW_TOKENS", "256")),
                )

            return self._model

    def _write_temp_audio(self, parsed_audio: ParsedAudio) -> Path:
        with tempfile.NamedTemporaryFile(
            suffix=parsed_audio.suffix,
            prefix="mimu-asr-",
            delete=False,
        ) as audio_file:
            audio_file.write(parsed_audio.content)
            return Path(audio_file.name)


runtime = QwenAsrRuntime()
app = FastAPI(title="MIMU ASR Service")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        provider=runtime.provider,
        model=runtime.model_path,
        loaded=runtime.loaded,
        device=runtime.device,
        language=runtime.language,
    )


@app.post("/transcribe", response_model=TranscribeResponse)
def transcribe(request: TranscribeRequest) -> TranscribeResponse:
    try:
        parsed_audio = parse_audio_data_url(request.audioDataUrl)
        text, language = runtime.transcribe(parsed_audio)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"ASR failed: {exc}") from exc

    if not text:
        raise HTTPException(status_code=422, detail="No speech was recognized")

    return TranscribeResponse(
        text=text,
        provider=runtime.provider,
        model=runtime.model_path,
        language=language,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the MIMU ASR service.")
    parser.add_argument("--host", default=os.getenv("MIMU_ASR_HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.getenv("MIMU_ASR_PORT", "8020")))
    args = parser.parse_args()

    import uvicorn

    uvicorn.run("server:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
