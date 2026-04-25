from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from mimu_eval.models import RunMetadata, read_jsonl
from mimu_eval.pipeline import run_eval_pipeline


class FakeClient:
    def run_case(self, case, dataset_root: Path, run_dir: Path) -> RunMetadata:
        output = run_dir / "outputs" / f"{case.id}.png"
        output.parent.mkdir(parents=True, exist_ok=True)
        Image.new("RGB", (512, 512), (140, 100, 120)).save(output)
        return RunMetadata(
            case_id=case.id,
            status="success",
            duration_seconds=0.1,
            prompt_id=f"prompt-{case.id}",
            image_url=f"http://127.0.0.1:13000/makeup/result?filename={case.id}.png",
            output_image=output.relative_to(run_dir).as_posix(),
        )


class PipelineTests(unittest.TestCase):
    def test_run_eval_pipeline_smoke_outputs_all_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp)
            example = project_root / "stable-makeup/example_.png"
            example.parent.mkdir(parents=True)
            Image.new("RGB", (1546, 808), (120, 100, 90)).save(example)

            run_dir = run_eval_pipeline(
                project_root=project_root,
                output_root=project_root / "eval/makeup",
                backend_url="http://127.0.0.1:13000",
                limit=2,
                vlm_mode="mock",
                run_id="test_run",
                client=FakeClient(),
            )

            self.assertEqual(len(read_jsonl(run_dir / "metadata.jsonl")), 2)
            self.assertEqual(len(read_jsonl(run_dir / "auto_scores.jsonl")), 2)
            self.assertEqual(len(read_jsonl(run_dir / "vlm_scores.jsonl")), 2)
            self.assertTrue((run_dir / "report.html").exists())


if __name__ == "__main__":
    unittest.main()
