from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from mimu_eval.models import append_jsonl
from mimu_eval.report import build_report


class ReportTests(unittest.TestCase):
    def test_build_report_contains_summary_case_images_and_failures(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            dataset_root = root / "eval/makeup"
            run_dir = dataset_root / "runs/manual"
            (dataset_root / "assets/users").mkdir(parents=True)
            (dataset_root / "assets/templates").mkdir(parents=True)
            (run_dir / "outputs").mkdir(parents=True)
            self._write_image(dataset_root / "assets/users/u.jpg")
            self._write_image(dataset_root / "assets/templates/t.jpg")
            self._write_image(run_dir / "outputs/case_0001.png")
            manifest = dataset_root / "manifests/regression_1.jsonl"
            append_jsonl(
                manifest,
                {
                    "id": "case_0001",
                    "user_image": "assets/users/u.jpg",
                    "template_image": "assets/templates/t.jpg",
                    "style": "blue_eye_makeup",
                    "attributes": {"difficulty": "easy"},
                },
            )
            append_jsonl(
                run_dir / "metadata.jsonl",
                {
                    "case_id": "case_0001",
                    "status": "success",
                    "duration_seconds": 3.2,
                    "output_image": "outputs/case_0001.png",
                },
            )
            append_jsonl(
                run_dir / "auto_scores.jsonl",
                {
                    "case_id": "case_0001",
                    "failure_type": "none",
                    "reason": "auto score passed",
                    "scores": {"overall_score": 4.2, "artifact_score": 1},
                },
            )
            append_jsonl(
                run_dir / "vlm_scores.jsonl",
                {
                    "case_id": "case_0001",
                    "failure_type": "none",
                    "reason": "mock VLM",
                    "scores": {"overall_score": 4.1},
                },
            )

            output = build_report(manifest, dataset_root=dataset_root, run_dir=run_dir)
            html = output.read_text(encoding="utf-8")

            self.assertIn("MIMU Makeup Eval Report", html)
            self.assertIn("case_0001", html)
            self.assertIn("blue_eye_makeup", html)
            self.assertIn("assets/users/u.jpg", html)
            self.assertIn("outputs/case_0001.png", html)
            self.assertIn("Success Rate", html)

    def _write_image(self, path: Path) -> None:
        Image.new("RGB", (32, 32), (120, 120, 120)).save(path)


if __name__ == "__main__":
    unittest.main()
