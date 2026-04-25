from __future__ import annotations

from html import escape
from pathlib import Path
import os

from .models import load_cases, read_jsonl


def build_report(manifest_path: Path, dataset_root: Path, run_dir: Path, output: Path | None = None) -> Path:
    output = output or run_dir / "report.html"
    cases = load_cases(manifest_path, dataset_root=dataset_root)
    metadata = _by_case(read_jsonl(run_dir / "metadata.jsonl"))
    auto_scores = _by_case(read_jsonl(run_dir / "auto_scores.jsonl"))
    vlm_scores = _by_case(read_jsonl(run_dir / "vlm_scores.jsonl"))

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        _render_html(cases, metadata, auto_scores, vlm_scores, dataset_root=dataset_root, run_dir=run_dir),
        encoding="utf-8",
    )
    return output


def _render_html(cases, metadata, auto_scores, vlm_scores, dataset_root: Path, run_dir: Path) -> str:
    total = len(cases)
    successes = sum(1 for case in cases if metadata.get(case.id, {}).get("status") == "success")
    success_rate = (successes / total * 100) if total else 0
    durations = [
        float(metadata.get(case.id, {}).get("duration_seconds") or 0)
        for case in cases
        if metadata.get(case.id, {}).get("status") == "success"
    ]
    avg_duration = sum(durations) / len(durations) if durations else 0
    overall_scores = [
        float(auto_scores.get(case.id, {}).get("scores", {}).get("overall_score") or 0)
        for case in cases
        if auto_scores.get(case.id, {}).get("scores")
    ]
    avg_overall = sum(overall_scores) / len(overall_scores) if overall_scores else 0

    rows = "\n".join(
        _render_row(case, metadata.get(case.id, {}), auto_scores.get(case.id, {}), vlm_scores.get(case.id, {}), dataset_root, run_dir)
        for case in cases
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>MIMU Makeup Eval Report</title>
  <style>
    body {{ margin: 0; font-family: Arial, sans-serif; background: #f7f5f2; color: #1d1b19; }}
    main {{ max-width: 1440px; margin: 0 auto; padding: 28px; }}
    h1 {{ font-size: 28px; margin: 0 0 20px; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, minmax(160px, 1fr)); gap: 12px; margin-bottom: 22px; }}
    .metric {{ background: #fff; border: 1px solid #e2ddd7; border-radius: 8px; padding: 14px; }}
    .metric span {{ display: block; color: #766c64; font-size: 12px; margin-bottom: 8px; }}
    .metric strong {{ font-size: 22px; }}
    table {{ width: 100%; border-collapse: collapse; background: #fff; border: 1px solid #e2ddd7; }}
    th, td {{ border-bottom: 1px solid #eee7e0; padding: 10px; text-align: left; vertical-align: top; font-size: 13px; }}
    th {{ background: #eee7e0; position: sticky; top: 0; }}
    img {{ width: 148px; height: 148px; object-fit: cover; border-radius: 6px; border: 1px solid #ddd; background: #eee; }}
    .score {{ white-space: pre-line; line-height: 1.45; }}
    .fail {{ color: #9a2d2d; font-weight: 700; }}
    .ok {{ color: #2b6b3f; font-weight: 700; }}
  </style>
</head>
<body>
<main>
  <h1>MIMU Makeup Eval Report</h1>
  <section class="summary">
    <div class="metric"><span>Total Cases</span><strong>{total}</strong></div>
    <div class="metric"><span>Success Rate</span><strong>{success_rate:.1f}%</strong></div>
    <div class="metric"><span>Avg Duration</span><strong>{avg_duration:.1f}s</strong></div>
    <div class="metric"><span>Avg Auto Overall</span><strong>{avg_overall:.2f}</strong></div>
  </section>
  <table>
    <thead>
      <tr>
        <th>Case</th>
        <th>User</th>
        <th>Template</th>
        <th>Output</th>
        <th>Auto</th>
        <th>VLM</th>
        <th>Metadata</th>
      </tr>
    </thead>
    <tbody>
      {rows}
    </tbody>
  </table>
</main>
</body>
</html>
"""


def _render_row(case, metadata: dict, auto: dict, vlm: dict, dataset_root: Path, run_dir: Path) -> str:
    output_image = metadata.get("output_image")
    output_cell = ""
    if output_image:
        output_cell = _img(_rel(run_dir / str(output_image), run_dir), str(output_image))

    auto_failure = str(auto.get("failure_type") or "missing")
    vlm_failure = str(vlm.get("failure_type") or "missing")
    auto_class = "ok" if auto_failure == "none" else "fail"
    vlm_class = "ok" if vlm_failure == "none" else "fail"

    return f"""<tr>
  <td><strong>{escape(case.id)}</strong><br />{escape(case.style)}<br />{escape(str(case.attributes))}</td>
  <td>{_img(_rel(dataset_root / case.user_image, run_dir), case.user_image)}</td>
  <td>{_img(_rel(dataset_root / case.template_image, run_dir), case.template_image)}</td>
  <td>{output_cell}</td>
  <td class="score"><span class="{auto_class}">{escape(auto_failure)}</span><br />{escape(_score_text(auto))}<br />{escape(str(auto.get("reason") or ""))}</td>
  <td class="score"><span class="{vlm_class}">{escape(vlm_failure)}</span><br />{escape(_score_text(vlm))}<br />{escape(str(vlm.get("reason") or ""))}</td>
  <td>Status: {escape(str(metadata.get("status") or "missing"))}<br />Duration: {escape(str(metadata.get("duration_seconds") or ""))}<br />Error: {escape(str(metadata.get("error") or ""))}</td>
</tr>"""


def _img(src: str, alt: str) -> str:
    return f'<img src="{escape(src)}" alt="{escape(alt)}" title="{escape(alt)}" />'


def _score_text(record: dict) -> str:
    scores = record.get("scores") if isinstance(record.get("scores"), dict) else {}
    return "\n".join(f"{key}: {value}" for key, value in scores.items())


def _rel(path: Path, base: Path) -> str:
    return os.path.relpath(path, start=base)


def _by_case(records: list[dict]) -> dict[str, dict]:
    return {str(record.get("case_id")): record for record in records}
