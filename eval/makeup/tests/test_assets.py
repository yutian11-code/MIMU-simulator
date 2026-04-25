from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from mimu_eval.assets import prepare_starter_dataset
from mimu_eval.models import load_cases


class StarterAssetTests(unittest.TestCase):
    def test_prepare_starter_dataset_writes_assets_and_regression_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            example = root / "stable-makeup/example_.png"
            example.parent.mkdir(parents=True)
            self._write_example_image(example)

            output_root = root / "eval/makeup"
            manifest_path = prepare_starter_dataset(
                project_root=root,
                output_root=output_root,
                case_count=30,
            )

            self.assertEqual(manifest_path, output_root / "manifests/regression_30.jsonl")
            user_images = sorted((output_root / "assets/users").glob("*.jpg"))
            template_images = sorted((output_root / "assets/templates").glob("*.jpg"))
            self.assertEqual(len(user_images), 10)
            self.assertEqual(len(template_images), 3)

            cases = load_cases(manifest_path, dataset_root=output_root)
            self.assertEqual(len(cases), 30)
            self.assertEqual(cases[0].id, "case_0001")
            self.assertTrue(cases[0].user_path(output_root).exists())
            self.assertTrue(cases[0].template_path(output_root).exists())
            self.assertIn("source", cases[0].attributes)

    def test_prepare_starter_dataset_rejects_missing_example(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            with self.assertRaisesRegex(FileNotFoundError, "stable-makeup/example_.png"):
                prepare_starter_dataset(
                    project_root=root,
                    output_root=root / "eval/makeup",
                    case_count=30,
                )

    def _write_example_image(self, path: Path) -> None:
        image = Image.new("RGB", (1546, 808), (30, 30, 30))
        # Roughly match the two face crop locations used by the real example screenshot.
        image.paste((190, 210, 230), (90, 140, 300, 355))
        image.paste((220, 170, 180), (85, 498, 305, 708))
        image.save(path)


if __name__ == "__main__":
    unittest.main()
