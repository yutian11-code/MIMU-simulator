# Template Matching Eval

This suite checks whether MMU template matching selects the expected standard
template family for fixed intent cases. Cases are stored in `cases.json` with a
small structured fixture: user input, profile, lightweight owned products,
optional reference image metadata, expected template, expected family, and
required MMU step codes.

## Run

Start the backend first, then run:

```bash
python eval/template_matching/run_template_matching_eval.py \
  --backend-url http://127.0.0.1:13000 \
  --mode match-debug \
  --output eval/template_matching/report.local.json
```

`--mode match-debug` calls:

```text
POST /makeup-template-library/match-debug
```

`--mode recommendation` calls:

```text
POST /recommendations/generate
```

Both modes print the JSON summary to stdout. `--output` writes the same summary
to a JSON file. Prefer ignored local paths such as
`eval/template_matching/report.local.json`, `eval/template_matching/*.report.json`,
or a `/tmp/...` path. Do not commit generated reports.

`referenceImage` in a case must be either `null` or a safe `data:` URL. The
evaluator sends supported data URLs as `referenceImageDataUrl`; it rejects other
values instead of forwarding unsupported fields to the backend.

`--mode recommendation` is an end-to-end recommendation smoke test. It sends
`rawUserInput` as `scenarioDetails`; `scenario` comes from an optional case
`scenario` field, otherwise from the input text. The case `profile` and
`ownedProducts` entries are included only as text requirements signals. They do
not replace or seed the backend database user profile or asset fixtures.

The report includes each case's `requiredStepCodes`,
`missingRequiredStepCodes`, and `stepCodeCheck`. Recommendation responses that
include `steps[].standardStepCodes` are checked against required codes. Modes or
responses without step-code fields, such as a match-debug summary, mark the
check as `skipped` rather than failing only because the response has no step
codes.

Request, timeout, or JSON parse failures are preserved as per-case errors and
counted in `infrastructureFailureCount`. The script exits with code `2` when any
infrastructure failure occurs, `1` for ordinary eval mismatches, and `0` when all
cases pass.

## Mock vs Real Model

For local smoke testing, use the mock template model services described in
`docs/team-runbook.md`. Mock mode is deterministic and verifies the integration
contract, trace fields, family coverage, and report shape.

For route/demo validation, point the backend template model environment
variables at the real embedding, reranker, and VLM services. Real model results
exercise the production scoring path and may fail when model services are down,
timed out, or seeded templates differ from the expected standard library.

The eval never reads local human face images. If a case needs visual guidance,
store either a non-sensitive reference string/path for the backend contract or a
synthetic `data:` URL fixture that is safe to keep in source control.
