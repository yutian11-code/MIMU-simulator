from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from mimu_eval.models import append_jsonl
from mimu_eval.vlm import judge_cases, write_vlm_scores


class VlmJudgeTests(unittest.TestCase):
    def test_skip_mode_marks_all_cases_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            manifest = self._write_manifest(Path(tmp), ["case_0001", "case_0002"])

            scores = judge_cases(manifest, run_dir=Path(tmp) / "run", mode="skip")

            self.assertEqual(len(scores), 2)
            self.assertTrue(all(score.failure_type == "vlm_skipped" for score in scores))

    def test_mock_mode_uses_auto_scores_and_keeps_bounded_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._write_manifest(root, ["case_0001"])
            run_dir = root / "run"
            append_jsonl(
                run_dir / "auto_scores.jsonl",
                {
                    "case_id": "case_0001",
                    "failure_type": "none",
                    "reason": "auto score passed",
                    "scores": {
                        "identity_score": 4.2,
                        "makeup_transfer_score": 4.8,
                        "naturalness_score": 4.0,
                        "artifact_score": 1.0,
                        "overall_score": 4.4,
                    },
                },
            )

            output = write_vlm_scores(manifest, run_dir=run_dir, mode="mock")
            records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]

            self.assertEqual(records[0]["case_id"], "case_0001")
            self.assertEqual(records[0]["failure_type"], "none")
            for value in records[0]["scores"].values():
                self.assertGreaterEqual(value, 1)
                self.assertLessEqual(value, 5)

    def _write_manifest(self, root: Path, case_ids: list[str]) -> Path:
        manifest = root / "manifest.jsonl"
        for case_id in case_ids:
            append_jsonl(
                manifest,
                {
                    "id": case_id,
                    "user_image": "u.jpg",
                    "template_image": "t.jpg",
                    "style": "style",
                    "attributes": {},
                },
            )
        return manifest


if __name__ == "__main__":
    unittest.main()
