from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from mimu_eval.models import EvalCase, RunMetadata
from mimu_eval.scoring import score_case


class ScoringTests(unittest.TestCase):
    def test_missing_output_is_generation_failed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            case = EvalCase("case_0001", "u.jpg", "t.jpg", "style", {})
            metadata = RunMetadata(case_id=case.id, status="failed", duration_seconds=0.1, error="boom")

            score = score_case(case, metadata, dataset_root=root, run_dir=root)

            self.assertEqual(score.failure_type, "generation_failed")
            self.assertEqual(score.scores["artifact_score"], 5)
            self.assertEqual(score.scores["overall_score"], 1)

    def test_makeup_region_delta_rewards_output_closer_to_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            (run_dir / "outputs").mkdir(parents=True)
            user = root / "u.jpg"
            template = root / "t.jpg"
            transferred = run_dir / "outputs/transferred.png"
            unchanged = run_dir / "outputs/unchanged.png"
            self._write_face(user, eye=(90, 90, 90), lip=(100, 100, 100))
            self._write_face(template, eye=(30, 130, 235), lip=(210, 70, 110))
            self._write_face(transferred, eye=(30, 130, 235), lip=(210, 70, 110))
            self._write_face(unchanged, eye=(90, 90, 90), lip=(100, 100, 100))
            case = EvalCase("case_0001", "u.jpg", "t.jpg", "style", {})

            transferred_score = score_case(
                case,
                RunMetadata(case.id, "success", 1.0, output_image="outputs/transferred.png"),
                dataset_root=root,
                run_dir=run_dir,
            )
            unchanged_score = score_case(
                case,
                RunMetadata(case.id, "success", 1.0, output_image="outputs/unchanged.png"),
                dataset_root=root,
                run_dir=run_dir,
            )

            self.assertGreater(
                transferred_score.scores["makeup_transfer_score"],
                unchanged_score.scores["makeup_transfer_score"],
            )
            self.assertGreaterEqual(transferred_score.scores["overall_score"], 3)
            self.assertEqual(transferred_score.failure_type, "none")

    def test_makeup_region_delta_accepts_visible_change_even_when_not_template_exact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_dir = root / "run"
            (run_dir / "outputs").mkdir(parents=True)
            user = root / "u.jpg"
            template = root / "t.jpg"
            output = run_dir / "outputs/changed.png"
            self._write_face(user, eye=(90, 90, 90), lip=(100, 100, 100))
            self._write_face(template, eye=(240, 20, 20), lip=(20, 220, 20))
            self._write_face(output, eye=(30, 130, 235), lip=(210, 70, 110))
            case = EvalCase("case_0001", "u.jpg", "t.jpg", "style", {})

            score = score_case(
                case,
                RunMetadata(case.id, "success", 1.0, output_image="outputs/changed.png"),
                dataset_root=root,
                run_dir=run_dir,
            )

            self.assertGreaterEqual(score.scores["makeup_transfer_score"], 3)
            self.assertEqual(score.failure_type, "none")

    def _write_face(self, path: Path, eye: tuple[int, int, int], lip: tuple[int, int, int]) -> None:
        image = Image.new("RGB", (512, 512), (180, 160, 145))
        draw = ImageDraw.Draw(image)
        draw.rectangle((120, 170, 220, 225), fill=eye)
        draw.rectangle((292, 170, 392, 225), fill=eye)
        draw.rectangle((205, 330, 307, 372), fill=lip)
        image.save(path)


if __name__ == "__main__":
    unittest.main()
