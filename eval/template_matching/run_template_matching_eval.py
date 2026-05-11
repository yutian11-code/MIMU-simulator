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
    for index, case in enumerate(cases):
        validate_case(case, index)
    return cases


def validate_case(case: dict, index: int) -> None:
    required_fields = [
        "id",
        "rawUserInput",
        "profile",
        "ownedProducts",
        "referenceImage",
        "expectedTemplateId",
        "expectedFamily",
        "requiredStepCodes",
    ]
    missing = [field for field in required_fields if field not in case]
    if missing:
        raise ValueError(f"case at index {index} missing fields: {', '.join(missing)}")

    profile = case["profile"]
    if not isinstance(profile, dict):
        raise ValueError(f"case {case['id']} profile must be an object")
    for field in ["skinType", "faceShape", "skillLevel"]:
        if field not in profile:
            raise ValueError(f"case {case['id']} profile missing {field}")

    if not isinstance(case["ownedProducts"], list):
        raise ValueError(f"case {case['id']} ownedProducts must be an array")
    if not isinstance(case["requiredStepCodes"], list):
        raise ValueError(f"case {case['id']} requiredStepCodes must be an array")
    reference_image = case.get("referenceImage")
    if reference_image is not None and not (
        isinstance(reference_image, str) and reference_image.startswith("data:")
    ):
        raise ValueError(
            f"case {case['id']} referenceImage must be null or a data: URL"
        )


def build_match_debug_payload(case: dict) -> dict:
    payload = {"rawUserInput": case["rawUserInput"]}
    reference_image = case.get("referenceImage")
    if reference_image:
        payload["referenceImageDataUrl"] = reference_image
    return payload


def build_recommendation_payload(case: dict) -> dict:
    raw_user_input = str(case["rawUserInput"])
    payload = {
        "userId": "user-001",
        "scenario": case.get("scenario") or raw_user_input[:40] or "妆容匹配评测",
        "scenarioDetails": raw_user_input,
        "requirements": [
            f"skinType:{case['profile']['skinType']}",
            f"faceShape:{case['profile']['faceShape']}",
            f"skillLevel:{case['profile']['skillLevel']}",
            *[
                f"ownedProduct:{product.get('category', '')}/{product.get('subCategory', '')}/{product.get('finish', '')}"
                for product in case.get("ownedProducts", [])
            ],
        ],
    }
    reference_image = case.get("referenceImage")
    if reference_image:
        payload["referenceImageDataUrl"] = reference_image
    return payload


def evaluate_case(backend_url: str, token: str, case: dict, mode: str) -> dict:
    if mode == "recommendation":
        result = post_json(
            f"{backend_url.rstrip('/')}/recommendations/generate",
            token,
            build_recommendation_payload(case),
        )
        selected_template_id = result.get("sourceStandardTemplateId")
        selected_family = result.get("templateFamily")
    else:
        result = post_json(
            f"{backend_url.rstrip('/')}/makeup-template-library/match-debug",
            token,
            build_match_debug_payload(case),
        )
        selected_template_id = result.get("selectedTemplateId")
        selected_family = result.get("selectedFamily")

    return build_result(case, result, selected_template_id, selected_family, mode)


def build_result(
    case: dict,
    response: dict,
    selected_template_id: str | None,
    selected_family: str | None,
    mode: str = "",
    failure_reason: str = "",
    infrastructure_failure: bool = False,
) -> dict:
    expected_template_id = case.get("expectedTemplateId")
    expected_family = case.get("expectedFamily")
    required_step_codes = case.get("requiredStepCodes", [])
    step_code_check, missing_required_step_codes = evaluate_required_step_codes(
        response, required_step_codes
    )
    template_ok = expected_template_id is None or selected_template_id == expected_template_id
    family_ok = expected_family is None or selected_family == expected_family
    step_codes_ok = not missing_required_step_codes
    passed = template_ok and family_ok and step_codes_ok and not failure_reason

    if not failure_reason and not passed:
        mismatches = []
        if not template_ok:
            mismatches.append("selected template mismatch")
        if not family_ok:
            mismatches.append("selected family mismatch")
        if not step_codes_ok:
            mismatches.append("required step codes missing")
        failure_reason = ", ".join(mismatches)

    return {
        "id": case["id"],
        "mode": mode,
        "passed": passed,
        "selectedTemplateId": selected_template_id,
        "selectedFamily": selected_family,
        "expectedTemplateId": expected_template_id,
        "expectedFamily": expected_family,
        "requiredStepCodes": required_step_codes,
        "missingRequiredStepCodes": missing_required_step_codes,
        "stepCodeCheck": step_code_check,
        "templateTraceId": response.get("templateTraceId"),
        "modelStatus": response.get("modelStatus", {}),
        "scoreBreakdown": response.get("scoreBreakdown", {}),
        "failureReason": failure_reason,
        "infrastructureFailure": infrastructure_failure,
    }


def evaluate_required_step_codes(
    response: dict, required_step_codes: list[str]
) -> tuple[str, list[str]]:
    if not required_step_codes:
        return "not_required", []

    observed_step_codes = extract_step_codes(response)
    if observed_step_codes is None:
        return "skipped", []

    observed = set(observed_step_codes)
    missing = [code for code in required_step_codes if code not in observed]
    return "checked", missing


def extract_step_codes(response: dict) -> list[str] | None:
    steps = response.get("steps")
    if not isinstance(steps, list):
        return None

    step_codes: list[str] = []
    saw_step_code_field = False
    for step in steps:
        if not isinstance(step, dict):
            continue
        standard_step_codes = step.get("standardStepCodes")
        if isinstance(standard_step_codes, list):
            saw_step_code_field = True
            step_codes.extend(
                code for code in standard_step_codes if isinstance(code, str)
            )
        standard_step_code = step.get("standardStepCode")
        if isinstance(standard_step_code, str):
            saw_step_code_field = True
            step_codes.append(standard_step_code)
        step_code = step.get("stepCode")
        if isinstance(step_code, str):
            saw_step_code_field = True
            step_codes.append(step_code)

    if not saw_step_code_field:
        return None
    return step_codes


def build_error_result(
    case: dict, exc: Exception, mode: str, infrastructure_failure: bool = False
) -> dict:
    return build_result(
        case,
        {},
        None,
        None,
        mode=mode,
        failure_reason=f"request failed: {exc}",
        infrastructure_failure=infrastructure_failure,
    )


def build_summary(results: list[dict]) -> dict:
    by_family: dict[str, dict[str, int]] = {}
    for item in results:
        family = item.get("expectedFamily") or "UNKNOWN"
        bucket = by_family.setdefault(family, {"passed": 0, "total": 0})
        bucket["total"] += 1
        if item["passed"]:
            bucket["passed"] += 1
    return {
        "passed": sum(1 for item in results if item["passed"]),
        "total": len(results),
        "infrastructureFailureCount": sum(
            1 for item in results if item.get("infrastructureFailure")
        ),
        "byFamily": by_family,
        "results": results,
    }


def write_report(path: Path, summary: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run template matching eval cases.")
    parser.add_argument("--backend-url", default="http://127.0.0.1:13000")
    parser.add_argument("--token", default="demo-token")
    parser.add_argument("--cases", default=str(Path(__file__).with_name("cases.json")))
    parser.add_argument("--output", default="")
    parser.add_argument(
        "--mode",
        choices=["match-debug", "recommendation"],
        default="match-debug",
    )
    args = parser.parse_args()

    try:
        cases = load_cases(Path(args.cases))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"failed to load cases: {exc}", file=sys.stderr)
        return 2

    results = []
    for case in cases:
        try:
            results.append(evaluate_case(args.backend_url, args.token, case, args.mode))
        except (KeyError, error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            results.append(build_error_result(case, exc, args.mode, True))

    summary = build_summary(results)
    if args.output:
        try:
            write_report(Path(args.output), summary)
        except OSError as exc:
            print(f"failed to write report: {exc}", file=sys.stderr)
            return 2

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if summary["infrastructureFailureCount"] > 0:
        return 2
    return 0 if summary["passed"] == summary["total"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
