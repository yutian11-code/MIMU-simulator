#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path
from urllib import error, request


def post_json(url: str, token: str, payload: dict) -> dict:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=utf-8",
        },
        method="POST",
    )

    with request.urlopen(req, timeout=10) as response:
        response_body = response.read().decode("utf-8")
        return json.loads(response_body)


def load_cases(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as handle:
        cases = json.load(handle)
    if not isinstance(cases, list):
        raise ValueError("cases file must contain a JSON array")
    return cases


def evaluate_case(backend_url: str, token: str, case: dict) -> tuple[bool, dict | None]:
    result = post_json(
        f"{backend_url.rstrip('/')}/makeup-template-library/match-debug",
        token,
        {"rawUserInput": case["rawUserInput"]},
    )

    selected_template_id = result.get("selectedTemplateId")
    selected_family = result.get("selectedFamily")
    expected_template_id = case.get("expectedTemplateId")
    expected_family = case.get("expectedFamily")

    template_ok = expected_template_id is None or selected_template_id == expected_template_id
    family_ok = expected_family is None or selected_family == expected_family

    if template_ok and family_ok:
        return True, None

    return False, {
        "id": case.get("id"),
        "selectedTemplateId": selected_template_id,
        "selectedFamily": selected_family,
        "expectedTemplateId": expected_template_id,
        "expectedFamily": expected_family,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run offline template matching eval cases.")
    parser.add_argument("--backend-url", default="http://127.0.0.1:13000")
    parser.add_argument("--token", default="demo-token")
    parser.add_argument("--cases", default=str(Path(__file__).with_name("cases.json")))
    args = parser.parse_args()

    try:
        cases = load_cases(Path(args.cases))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"failed to load cases: {exc}", file=sys.stderr)
        return 2

    passed = 0
    failures = []

    for case in cases:
        try:
            ok, failure = evaluate_case(args.backend_url, args.token, case)
        except (KeyError, error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            case_id = case.get("id", "<unknown>")
            print(f"request failed for {case_id}: {exc}", file=sys.stderr)
            return 2

        if ok:
            passed += 1
        elif failure is not None:
            failures.append(failure)

    summary = {"passed": passed, "total": len(cases), "failures": failures}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
