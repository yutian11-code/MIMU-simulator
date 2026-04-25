from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from mimu_eval.client import MakeupBackendClient
from mimu_eval.models import EvalCase


class FakeResponse:
    def __init__(self, status_code: int, payload: dict | None = None, content: bytes = b"") -> None:
        self.status_code = status_code
        self._payload = payload or {}
        self.content = content
        self.text = str(self._payload)
        self.ok = 200 <= status_code < 300

    def json(self) -> dict:
        return self._payload


class FakeSession:
    def __init__(self) -> None:
        self.posts: list[dict] = []
        self.gets: list[str] = []

    def post(self, url: str, files: dict, timeout: int) -> FakeResponse:
        self.posts.append({"url": url, "files": files, "timeout": timeout})
        return FakeResponse(
            200,
            {
                "promptId": "prompt-1",
                "imageUrl": "http://127.0.0.1:13000/makeup/result?filename=x.png&subfolder=stable_makeup&type=output",
                "output": {"filename": "x.png", "subfolder": "stable_makeup", "type": "output"},
            },
        )

    def get(self, url: str, timeout: int) -> FakeResponse:
        self.gets.append(url)
        return FakeResponse(200, content=b"png-bytes")


class FailingSession(FakeSession):
    def post(self, url: str, files: dict, timeout: int) -> FakeResponse:
        self.posts.append({"url": url, "files": files, "timeout": timeout})
        return FakeResponse(502, {"message": "ComfyUI workflow validation failed"})


class ClientTests(unittest.TestCase):
    def test_run_case_posts_images_and_downloads_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user = root / "assets/users/u.jpg"
            template = root / "assets/templates/t.jpg"
            run_dir = root / "runs/manual"
            user.parent.mkdir(parents=True)
            template.parent.mkdir(parents=True)
            (run_dir / "outputs").mkdir(parents=True)
            user.write_bytes(b"user")
            template.write_bytes(b"template")
            case = EvalCase("case_0001", "assets/users/u.jpg", "assets/templates/t.jpg", "style", {})
            session = FakeSession()

            metadata = MakeupBackendClient(
                "http://10.246.1.70:13000",
                timeout_seconds=123,
                session=session,
            ).run_case(case, dataset_root=root, run_dir=run_dir)

            self.assertEqual(metadata.status, "success")
            self.assertEqual(metadata.prompt_id, "prompt-1")
            self.assertEqual(metadata.output_image, "outputs/case_0001.png")
            self.assertEqual((run_dir / "outputs/case_0001.png").read_bytes(), b"png-bytes")
            self.assertEqual(session.posts[0]["url"], "http://10.246.1.70:13000/makeup")
            self.assertIn("userImage", session.posts[0]["files"])
            self.assertIn("templateImage", session.posts[0]["files"])
            self.assertTrue(session.gets[0].startswith("http://10.246.1.70:13000/makeup/result"))

    def test_run_case_records_backend_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user = root / "u.jpg"
            template = root / "t.jpg"
            run_dir = root / "run"
            user.write_bytes(b"user")
            template.write_bytes(b"template")
            (run_dir / "outputs").mkdir(parents=True)
            case = EvalCase("case_0001", "u.jpg", "t.jpg", "style", {})

            metadata = MakeupBackendClient(
                "http://127.0.0.1:13000",
                session=FailingSession(),
            ).run_case(case, dataset_root=root, run_dir=run_dir)

            self.assertEqual(metadata.status, "failed")
            self.assertIn("ComfyUI workflow validation failed", metadata.error or "")
            self.assertIsNone(metadata.output_image)


if __name__ == "__main__":
    unittest.main()
