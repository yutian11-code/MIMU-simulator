from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from mimu_eval.models import append_jsonl, load_cases, make_run_dir, read_jsonl


class ModelIoTests(unittest.TestCase):
    def test_load_cases_requires_existing_images_and_preserves_attributes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user = root / "assets/users/u001.jpg"
            template = root / "assets/templates/t001.jpg"
            manifest = root / "manifests/regression_30.jsonl"
            user.parent.mkdir(parents=True)
            template.parent.mkdir(parents=True)
            manifest.parent.mkdir(parents=True)
            user.write_bytes(b"user")
            template.write_bytes(b"template")
            manifest.write_text(
                json.dumps(
                    {
                        "id": "case_0001",
                        "user_image": "assets/users/u001.jpg",
                        "template_image": "assets/templates/t001.jpg",
                        "style": "blue_eye_makeup",
                        "attributes": {"difficulty": "easy"},
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            cases = load_cases(manifest, dataset_root=root)

            self.assertEqual(len(cases), 1)
            self.assertEqual(cases[0].id, "case_0001")
            self.assertEqual(cases[0].style, "blue_eye_makeup")
            self.assertEqual(cases[0].attributes["difficulty"], "easy")
            self.assertEqual(cases[0].user_path(root), user)
            self.assertEqual(cases[0].template_path(root), template)

    def test_load_cases_rejects_duplicate_ids(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            user = root / "u.jpg"
            template = root / "t.jpg"
            manifest = root / "cases.jsonl"
            user.write_bytes(b"user")
            template.write_bytes(b"template")
            record = {
                "id": "case_dup",
                "user_image": "u.jpg",
                "template_image": "t.jpg",
                "style": "natural",
                "attributes": {},
            }
            manifest.write_text(
                json.dumps(record, ensure_ascii=False)
                + "\n"
                + json.dumps(record, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "Duplicate case id"):
                load_cases(manifest, dataset_root=root)

    def test_jsonl_append_and_read_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "run/metadata.jsonl"

            append_jsonl(path, {"case_id": "case_0001", "status": "success"})
            append_jsonl(path, {"case_id": "case_0002", "status": "failed"})

            self.assertEqual(
                read_jsonl(path),
                [
                    {"case_id": "case_0001", "status": "success"},
                    {"case_id": "case_0002", "status": "failed"},
                ],
            )

    def test_make_run_dir_uses_supplied_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = make_run_dir(Path(tmp), run_id="manual_run")

            self.assertEqual(run_dir.name, "manual_run")
            self.assertTrue((run_dir / "outputs").is_dir())


if __name__ == "__main__":
    unittest.main()
