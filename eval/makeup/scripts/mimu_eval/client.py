from __future__ import annotations

from contextlib import ExitStack
from pathlib import Path
import time
from typing import Any
from urllib.parse import urlparse, urlunparse

import requests

from .models import EvalCase, RunMetadata


class MakeupBackendClient:
    def __init__(
        self,
        base_url: str,
        timeout_seconds: int = 420,
        session: requests.Session | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

    def run_case(self, case: EvalCase, dataset_root: Path, run_dir: Path) -> RunMetadata:
        started = time.monotonic()
        try:
            payload = self._submit_case(case, dataset_root)
            image_url = str(payload.get("imageUrl") or "")
            if not image_url:
                raise RuntimeError("Backend response did not include imageUrl")
            prompt_id = payload.get("promptId")
            output_name = self._output_filename(case, payload)
            output_path = run_dir / "outputs" / output_name
            output_path.parent.mkdir(parents=True, exist_ok=True)
            self._download_result(image_url, output_path)

            return RunMetadata(
                case_id=case.id,
                status="success",
                duration_seconds=round(time.monotonic() - started, 3),
                prompt_id=str(prompt_id) if prompt_id else None,
                image_url=self._normalize_result_url(image_url),
                output_image=output_path.relative_to(run_dir).as_posix(),
                error=None,
            )
        except Exception as exc:  # noqa: BLE001 - this records per-case failures and lets the batch continue.
            return RunMetadata(
                case_id=case.id,
                status="failed",
                duration_seconds=round(time.monotonic() - started, 3),
                error=str(exc),
            )

    def _submit_case(self, case: EvalCase, dataset_root: Path) -> dict[str, Any]:
        user_path = case.user_path(dataset_root)
        template_path = case.template_path(dataset_root)

        with ExitStack() as stack:
            user_handle = stack.enter_context(user_path.open("rb"))
            template_handle = stack.enter_context(template_path.open("rb"))
            files = {
                "userImage": (user_path.name, user_handle, _mime_for(user_path)),
                "templateImage": (template_path.name, template_handle, _mime_for(template_path)),
            }
            response = self.session.post(
                f"{self.base_url}/makeup",
                files=files,
                timeout=self.timeout_seconds,
            )

        payload = _json_or_empty(response)
        if not (200 <= response.status_code < 300):
            raise RuntimeError(_error_message(payload, f"Backend returned HTTP {response.status_code}"))
        return payload

    def _download_result(self, image_url: str, output_path: Path) -> None:
        normalized_url = self._normalize_result_url(image_url)
        response = self.session.get(normalized_url, timeout=self.timeout_seconds)
        if not (200 <= response.status_code < 300):
            raise RuntimeError(f"Failed to download result image: HTTP {response.status_code}")
        output_path.write_bytes(response.content)

    def _normalize_result_url(self, image_url: str) -> str:
        result_parts = urlparse(image_url)
        if result_parts.hostname not in {"127.0.0.1", "localhost"}:
            return image_url

        base_parts = urlparse(self.base_url)
        return urlunparse(
            (
                base_parts.scheme,
                base_parts.netloc,
                result_parts.path,
                result_parts.params,
                result_parts.query,
                result_parts.fragment,
            )
        )

    def _output_filename(self, case: EvalCase, payload: dict[str, Any]) -> str:
        output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
        filename = str(output.get("filename") or "")
        suffix = Path(filename).suffix or ".png"
        return f"{case.id}{suffix}"


def _json_or_empty(response: Any) -> dict[str, Any]:
    try:
        payload = response.json()
    except Exception:  # noqa: BLE001
        return {}
    return payload if isinstance(payload, dict) else {}


def _error_message(payload: dict[str, Any], fallback: str) -> str:
    message = payload.get("message")
    if isinstance(message, list) and message:
        return str(message[0])
    if isinstance(message, str) and message:
        return message
    return fallback


def _mime_for(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".png":
        return "image/png"
    return "application/octet-stream"
