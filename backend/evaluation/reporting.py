"""Machine-readable and reviewer-facing reports from the same run records."""
import json
from collections import Counter
from pathlib import Path


def metrics(records: list[dict]) -> dict:
    requested = [record for record in records if record["request_status"] == "EXECUTED"]
    by_status = Counter(record["request_status"] for record in records)
    category_counts = Counter(category for record in records
                              for category in set(record.get("failure_categories", [])))
    correctness = [record["correctness"] for record in records
                   if record["case"]["feature"] == "solution"]
    executable_cases = [item for result in correctness for item in result.get("cases", [])]
    structural = Counter(record.get("validation", {}).get("structure", "NOT_RUN") for record in records)
    starter_records = [record for record in records if record["case"]["feature"] == "starter"]
    starter_executed = [record for record in starter_records if record["request_status"] == "EXECUTED"]
    starter_fallbacks = [record for record in starter_executed if
                         (record.get("response") or {}).get("usedFallback") is True]
    starter_reasons = Counter((record.get("starter_diagnostic") or {}).get("reason", "UNKNOWN_FAILURE")
                              for record in starter_fallbacks)
    fallback_valid = sum(record.get("validation", {}).get("structure") == "PASS" and
                         (record.get("validation", {}).get("syntax") or {}).get("status") != "FAIL"
                         for record in starter_fallbacks)
    return {
        "matrix_cases": len(records),
        "real_generation_requests": len(requested),
        "http_success": sum(record.get("http_status") == 200 for record in requested),
        "http_failed": sum(record.get("http_status") != 200 for record in requested),
        "request_status": dict(by_status),
        "failure_categories": dict(category_counts),
        "structural_validation": dict(structural),
        "starter_live_ai_accepted": sum(record.get("response") is not None and
                                        record["response"].get("isAiGenerated") is True
                                        for record in starter_records),
        "starter_fallbacks": sum(record.get("response") is not None and
                                 record["response"].get("usedFallback") is True
                                 for record in starter_records),
        "starter_diagnostics": {
            "executed_requests": len(starter_executed),
            "live_ai_accepted": sum((record.get("response") or {}).get("isAiGenerated") is True
                                    for record in starter_executed),
            "fallbacks": len(starter_fallbacks),
            "fallback_reasons": dict(starter_reasons),
            "fallback_structure_and_syntax_valid": fallback_valid,
            "student_visible_structure_and_syntax_valid": sum(
                record.get("validation", {}).get("structure") == "PASS" and
                (record.get("validation", {}).get("syntax") or {}).get("status") != "FAIL"
                for record in starter_executed if record.get("response")),
            "student_visible_human_review_required": sum(bool(record.get("validation", {}).get("human_review"))
                                                         for record in starter_executed),
        },
        "blocked_by_api": sum(record["request_status"] == "EXECUTED" and
                              record.get("http_status") != 200 for record in records),
        "not_executed": sum(record["request_status"] != "EXECUTED" for record in records),
        "solution_correctness": {
            "generated_solutions": len(correctness),
            "passed": sum(item["status"] == "PASS" for item in correctness),
            "failed": sum(item["status"] == "FAIL" for item in correctness),
            "not_run": sum(item["status"] == "NOT_RUN" for item in correctness),
            "fixture_passed": sum(item["status"] == "PASS" for item in executable_cases),
            "fixture_failed": sum(item["status"] == "FAIL" for item in executable_cases),
        },
        "human_review_cases": sum(bool(record.get("validation", {}).get("human_review"))
                                  for record in records),
    }


def recommendation(run: dict) -> tuple[str, str]:
    stats = run["metrics"]
    if run["mode"] != "live" or stats["real_generation_requests"] == 0:
        return "INCONCLUSIVE", "No real Groq responses were evaluated."
    if stats["failure_categories"].get("algorithm_correctness", 0) > 0:
        return "NO-GO", "At least one generated full solution failed an independent correctness fixture."
    if stats["http_failed"] or stats["failure_categories"].get("structural_output", 0):
        return "NO-GO", "The first-round API or structural pipeline had failures; fix and rerun before ingestion."
    if stats["real_generation_requests"] < stats["matrix_cases"]:
        return "INCONCLUSIVE", "The planned matrix was not fully executed."
    if stats["solution_correctness"]["not_run"] or stats["human_review_cases"]:
        return "INCONCLUSIVE", "Some algorithm checks were not run or teaching quality still needs human review."
    return "CONDITIONAL GO", "The small first round met automated checks; inspect scope limits before ingestion."


def _table(records: list[dict]) -> str:
    lines = ["| Feature | Problem | Approach | Language/level | HTTP | Result | Categories |",
             "| --- | --- | --- | --- | ---: | --- | --- |"]
    for record in records:
        case = record["case"]
        option = (case["language"] or "—") + (f" / L{case['level']}" if case["level"] else "")
        status = record["request_status"]
        if status == "EXECUTED":
            status = "PASS" if not record["failure_categories"] else "FAIL/REVIEW"
        lines.append(f"| {case['feature']} | {case['slug']} | {case['approach_id']} | {option} | "
                     f"{record.get('http_status') or '—'} | {status} | "
                     f"{', '.join(record['failure_categories']) or '—'} |")
    return "\n".join(lines)


def _hint_batches(records: list[dict]) -> str:
    batches = []
    for record in records:
        if record["case"]["feature"] != "hints" or not record.get("response"):
            continue
        hints = record["response"].get("hints", [])
        if not isinstance(hints, list):
            continue
        batches.append(f"**{record['case']['slug']} / {record['case']['approach_id']}**\n\n" +
                       "\n".join(f"{number}. {hint}" for number, hint in enumerate(hints, 1)))
    return "\n\n".join(batches) if batches else "No live hint batches were returned."


def _failure_detail(record: dict) -> str:
    failed_check = next((check["detail"] for check in record.get("validation", {}).get("quality", [])
                         if check["status"] == "FAIL"), None)
    return (record.get("error_summary") or failed_check or
            (record.get("correctness") or {}).get("summary") or "See JSON record.")


def write_reports(run: dict, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    run["metrics"] = metrics(run["records"])
    run["recommendation"], run["recommendation_reason"] = recommendation(run)
    json_path = output_dir / "mvp_evaluation.json"
    markdown_path = output_dir / "mvp_evaluation_report.md"
    json_path.write_text(json.dumps(run, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    stats = run["metrics"]
    correctness = stats["solution_correctness"]
    failures = [record for record in run["records"] if record["failure_categories"]]
    representative = "\n".join(
        f"- **{record['case']['id']}** — {', '.join(record['failure_categories'])}: "
        f"{_failure_detail(record)}"
        for record in failures[:8]
    ) or "No automated failures in executed requests."
    observed = ", ".join(f"{key}: {value}" for key, value in sorted(stats["failure_categories"].items())) or "none"
    editorial = run.get("editorial_observations", [])
    editorial_text = "\n".join(
        f"- **{note['case_id']}** ({note['status']}): {note['observation']}"
        for note in editorial
    ) or "No preliminary editorial observations were attached; subjective checks remain open."
    text = f"""# LeetCoach MVP Live LLM Evaluation

## Executive summary

Run `{run['run_id']}` at {run['timestamp_utc']}; mode **{run['mode']}**; commit `{run['git_commit'] or 'unavailable'}`; Groq model `{run['model'] or 'unavailable'}`.
Real generation requests: **{stats['real_generation_requests']}/{stats['matrix_cases']} planned**. HTTP 200: **{stats['http_success']}/{stats['real_generation_requests']} executed**; HTTP failures: **{stats['http_failed']}/{stats['real_generation_requests']}**. Failure categories among cases: {observed}. Token usage and monetary cost are **unavailable** from the current API response.

Structural validation: {json.dumps(stats['structural_validation'], sort_keys=True)}. Starter Code accepted from live AI: **{stats['starter_live_ai_accepted']}/{sum(record['case']['feature'] == 'starter' for record in run['records'])} planned**; offline fallbacks: **{stats['starter_fallbacks']}/{sum(record['case']['feature'] == 'starter' for record in run['records'])}**. API-blocked cases: **{stats['blocked_by_api']}**; not executed: **{stats['not_executed']}**; cases still needing human review: **{stats['human_review_cases']}**.

**Recommendation: {run['recommendation']}** — {run['recommendation_reason']} This small, curated sample cannot establish production-wide reliability.

## Test matrix

{_table(run['records'])}

## Successful and failed requests

Request status counts: {json.dumps(stats['request_status'], sort_keys=True)}. A successful HTTP response is not the same as a passing correctness or teaching-quality test. The JSON file keeps each response, duration, validation, and classification separately.

## Hints teaching-quality assessment

All returned batches are reproduced below for review. Automated checks cover size, length, question form, and obvious code-like text. Progression, approach fidelity, beginner clarity, and solution leakage remain **NEEDS_HUMAN_REVIEW** until a person reads the batches.

{_hint_batches(run['records'])}

## Starter Code teaching-quality assessment

The complete scaffolds and validation checks are in `mvp_evaluation.json`. Exact signatures, unfinished placeholders, and available syntax checks are automated. Level-trio code differences and executable-line counts are heuristics; meaningful setup and central unfinished work require manual review. A `usedFallback` response is recorded as a failed live AI scaffold even when the endpoint serves a valid offline scaffold.

Starter-specific diagnostic measures (executed denominator): {json.dumps(stats['starter_diagnostics'], sort_keys=True)}. `fallback_reasons` classify the rejected live response; `fallback_structure_and_syntax_valid` and `student_visible_structure_and_syntax_valid` assess the separate code that reached students. Human-review counts are not automated quality passes. Raw Groq text, when explicitly captured, is stored only in the ignored local directory and is not embedded in this report.

## Preliminary editorial observations

These are a Codex review of returned artifacts, not independent human sign-off. Keep the cases marked for human review.

{editorial_text}

## Full Solution correctness results

Generated-solution checks: **{correctness['passed']} passed**, **{correctness['failed']} failed**, **{correctness['not_run']} not run**, out of **{correctness['generated_solutions']} planned solution cases**. Independent executable fixtures: **{correctness['fixture_passed']} passed**, **{correctness['fixture_failed']} failed**. Python and C++ run only inside a bounded WSL bubblewrap namespace when available; other languages are syntax/compilation checked where possible and execution is explicitly NOT_RUN. These fixtures cover selected examples and edges, not a proof of correctness.

## API reliability observations

The final invocation used {run['config']['pace_seconds']} seconds between live calls, with a hard total cap of {run['config']['max_calls']} calls and no automatic retries. A 503 stopped that batch; the remaining cases were resumed in a separate explicit invocation after a cooldown. The API sanitizes provider errors and does not expose whether an upstream 429 caused the 503. Observed HTTP statuses and durations are in the JSON records. API, structural, algorithm, and pedagogical classifications are kept separate.

## Representative failure examples

{representative}

## Recommended fixes by priority

1. Investigate any independent correctness or syntax failures before expanding the catalog.
2. Investigate API/structural failures and offline Starter Code fallbacks; rerun the affected cases.
3. Have a human review all hint batches, all three Starter Code progressions, selected-approach fidelity, and complexity claims before a GO decision.

## MVP readiness recommendation

**{run['recommendation']}** — {run['recommendation_reason']} The provisional 95% API/structural, 90% executed correctness, 90% Starter Code quality, and 95% hint non-leakage targets cannot be certified without their appropriate denominators and human review. Continue with targeted verification rather than treating this sample as a statistical guarantee.
"""
    markdown_path.write_text(text, encoding="utf-8")
    return json_path, markdown_path
