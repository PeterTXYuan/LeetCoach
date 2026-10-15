"""Run `py -m evaluation.run_evaluation` from backend/; dry-run is the default."""
import argparse
import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app.database import BACKEND_DIR, SessionLocal
from app.llm.starter_diagnostics import starter_observer, starter_raw_capture
from app.main import app
from app.services.problem_repository import find_problem_context
from evaluation.cases import CASES, PREVIOUS_STARTER_FALLBACK_IDS, validate_matrix
from evaluation.correctness import execute_solution, probe_sandbox
from evaluation.reporting import write_reports
from evaluation.validators import evaluate_hints, evaluate_progression, evaluate_solution, evaluate_starter


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Opt-in evaluation through the existing FastAPI endpoints")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate matrix and write planned reports (default)")
    mode.add_argument("--live", action="store_true", help="Permit real Groq generation requests")
    parser.add_argument("--max-calls", type=int, default=31, help="Hard cap on live generation calls (default: 31)")
    parser.add_argument("--pace-seconds", type=float, default=5.0, help="Pause between live calls (default: 5)")
    parser.add_argument("--output-dir", type=Path, help="Local report directory; default is backend/evaluation_runs/<run-id>")
    parser.add_argument("--resume-json", type=Path, help="Continue NOT_RUN cases from a previous live JSON report")
    parser.add_argument("--feature", action="append", choices=("hints", "starter", "solution"),
                        help="Repeat to select features; default is all three")
    parser.add_argument("--previous-starter-fallbacks", action="store_true",
                        help="Select exactly the seven Starter Code cases that fell back in the baseline")
    parser.add_argument("--capture-raw", action="store_true",
                        help="Save raw Starter Code model text to the ignored local evaluation directory")
    args = parser.parse_args(argv)
    if args.max_calls < 0 or args.pace_seconds < 0:
        parser.error("--max-calls and --pace-seconds must be nonnegative")
    if args.resume_json and not args.live:
        parser.error("--resume-json requires explicit --live")
    if args.capture_raw and not args.live:
        parser.error("--capture-raw requires explicit --live")
    if args.previous_starter_fallbacks and args.feature and args.feature != ["starter"]:
        parser.error("--previous-starter-fallbacks only supports --feature starter")
    if args.previous_starter_fallbacks and args.max_calls > 7:
        parser.error("Targeted reproduction requires --max-calls 7 or less")
    return args


def _git_commit() -> str | None:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], cwd=BACKEND_DIR,
                                capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return None
    return result.stdout.strip() if result.returncode == 0 else None


def _empty_record(case, status="NOT_RUN", reason="Not executed") -> dict:
    return {
        "case": case.to_dict(), "request_status": status, "http_status": None,
        "duration_ms": None, "token_usage": None, "response": None,
        "validation": {"structure": "NOT_RUN", "syntax": None, "quality": [], "human_review": []},
        "correctness": {"status": "NOT_RUN", "cases": [], "summary": reason}
        if case.feature == "solution" else None,
        "failure_categories": [], "error_summary": reason,
        "starter_diagnostic": None, "raw_artifact": None,
    }


def _classify(record: dict) -> None:
    validation = record["validation"]
    categories = record["failure_categories"]
    if validation["structure"] == "FAIL" or (validation["syntax"] and
                                               validation["syntax"]["status"] == "FAIL"):
        categories.append("structural_output")
    if record["case"]["feature"] == "starter" and (record.get("response") or {}).get("usedFallback"):
        diagnostic = record.get("starter_diagnostic") or {}
        if diagnostic.get("stage") in {"response", "parsing", "validation"}:
            categories.append("structural_output")
        elif diagnostic.get("stage") == "provider":
            categories.append("api_provider")
        else:
            categories.append("evaluation_limitation")
    if any(check["status"] == "FAIL" and check["criterion"] != "live AI scaffold"
           for check in validation["quality"] if check["criterion"] not in {
               "three bounded hints and canonical identity", "API identity, signature, and unfinished scaffold",
               "API identity, signatures, and completed fields", "syntax or compilation"}):
        categories.append("pedagogical_quality")
    correctness = record.get("correctness")
    if correctness:
        if correctness["status"] == "FAIL":
            categories.append("structural_output" if correctness["summary"] == "Compilation failed"
                              else "algorithm_correctness")
        elif correctness["status"] == "NOT_RUN":
            categories.append("evaluation_limitation")
    record["failure_categories"] = sorted(set(categories))


def _request(client: TestClient, case) -> tuple[int | None, dict | None, str | None, float]:
    started = time.perf_counter()
    try:
        if case.feature == "hints":
            response = client.get(case.endpoint)
        else:
            body = {"language": case.language}
            if case.level is not None:
                body["level"] = case.level
            response = client.post(case.endpoint, json=body)
        duration = round((time.perf_counter() - started) * 1000, 1)
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if response.status_code != 200:
            detail = payload.get("detail") if isinstance(payload, dict) else None
            return response.status_code, None, str(detail or "API returned an unreadable error")[:250], duration
        if not isinstance(payload, dict):
            return response.status_code, None, "API returned non-object JSON", duration
        return response.status_code, payload, None, duration
    except Exception:
        return None, None, "Local API request failed; inspect backend availability", round(
            (time.perf_counter() - started) * 1000, 1)


def run(argv=None) -> int:
    args = parse_args(argv)
    load_dotenv(BACKEND_DIR / ".env", override=False)
    selected = [case for case in CASES if not args.feature or case.feature in args.feature]
    if args.previous_starter_fallbacks:
        selected = [case for case in CASES if case.key in PREVIOUS_STARTER_FALLBACK_IDS]
    previous = None
    if args.resume_json:
        previous = json.loads(args.resume_json.read_text(encoding="utf-8"))
        if previous.get("mode") != "live" or [item["case"]["id"] for item in previous.get("records", [])] != [
            case.key for case in selected
        ]:
            raise SystemExit("Resume report is not a live run of the same deterministic matrix")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    output_dir = args.output_dir or (args.resume_json.parent if args.resume_json else
                                      BACKEND_DIR / "evaluation_runs" / run_id)
    if not output_dir.is_absolute():
        output_dir = BACKEND_DIR / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    sandbox_available, sandbox_description = probe_sandbox()
    run_data = {
        "run_id": run_id, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_commit(), "mode": "live" if args.live else "dry-run",
        "model": os.environ.get("LEETCOACH_LLM_MODEL", "").strip() or None,
        "config": {"provider": "groq" if args.live else "none (dry-run)",
                   "max_calls": args.max_calls, "pace_seconds": args.pace_seconds,
                   "features": sorted({case.feature for case in selected}),
                   "capture_raw": args.capture_raw,
                   "temperature": {"hints": 0.3, "starter": 0.2, "solution": 0.1},
                   "response_format": "json_object", "provider_timeout_seconds": 20.0,
                   "provider_max_retries": 0,
                   "sandbox": sandbox_description, "token_usage": "unavailable"},
        "matrix_validation": [], "records": [], "run_notes": [],
    }
    if previous:
        run_data["run_id"] = previous["run_id"]
        run_data["timestamp_utc"] = previous["timestamp_utc"]
        run_data["git_commit"] = previous.get("git_commit")
        run_data["run_notes"] = previous.get("run_notes", []) + [
            "Resumed remaining NOT_RUN cases at " + datetime.now(timezone.utc).isoformat()
        ]
        if previous.get("model") != run_data["model"]:
            raise SystemExit("Configured model differs from the prior live run")
    with SessionLocal() as session:
        matrix_errors = validate_matrix(session, selected)
    run_data["matrix_validation"] = matrix_errors
    if matrix_errors:
        run_data["run_notes"].append("SQLite matrix validation failed; no generation requests were sent")
        run_data["records"] = [_empty_record(case, reason="Matrix invalid") for case in selected]
        json_path, report_path = write_reports(run_data, output_dir)
        print(f"Matrix invalid ({len(matrix_errors)} errors). Reports: {json_path}, {report_path}")
        return 2
    print(f"Matrix valid: {len(selected)} cases (hints={sum(c.feature == 'hints' for c in selected)}, "
          f"starter={sum(c.feature == 'starter' for c in selected)}, "
          f"solution={sum(c.feature == 'solution' for c in selected)}).")
    if not args.live:
        run_data["run_notes"].append("Dry-run: no FastAPI generation endpoint or Groq request was called")
        run_data["records"] = [_empty_record(case, reason="Dry-run only") for case in selected]
        json_path, report_path = write_reports(run_data, output_dir)
        print(f"Dry-run complete; 0 real Groq requests. Reports: {json_path}, {report_path}")
        return 0

    if not os.environ.get("GROQ_API_KEY", "").strip() or not run_data["model"]:
        run_data["run_notes"].append("Groq key or model missing; no generation requests were sent")
        run_data["records"] = [_empty_record(case, status="BLOCKED", reason="Groq configuration missing")
                               for case in selected]
        json_path, report_path = write_reports(run_data, output_dir)
        print(f"Live run blocked: Groq configuration missing. Reports: {json_path}, {report_path}")
        return 2

    # The provider factory reads this on each request; force the requested live provider.
    os.environ["LEETCOACH_LLM_PROVIDER"] = "groq"
    stop_reason = None
    previous_records = {item["case"]["id"]: item for item in previous["records"]} if previous else {}
    attempted = sum(item["request_status"] == "EXECUTED" for item in previous_records.values())
    new_attempts = 0
    last_call = None
    try:
        with TestClient(app) as client:
            for index, case in enumerate(selected, 1):
                if previous_records.get(case.key, {}).get("request_status") == "EXECUTED":
                    run_data["records"].append(previous_records[case.key])
                    continue
                if stop_reason or attempted >= args.max_calls:
                    run_data["records"].append(_empty_record(case,
                        reason=stop_reason or "Hard live-request budget reached"))
                    continue
                if last_call is not None:
                    time.sleep(max(0, args.pace_seconds - (time.monotonic() - last_call)))
                print(f"[{index}/{len(selected)}] {case.key} ...", flush=True)
                attempted += 1
                new_attempts += 1
                last_call = time.monotonic()
                events = []
                token = starter_observer.set(events.append if case.feature == "starter" else None)
                raw_token = starter_raw_capture.set(args.capture_raw and case.feature == "starter")
                try:
                    status, payload, error, duration = _request(client, case)
                finally:
                    starter_raw_capture.reset(raw_token)
                    starter_observer.reset(token)
                record = _empty_record(case)
                record.update(request_status="EXECUTED", http_status=status, duration_ms=duration,
                              response=payload, error_summary=error)
                if case.feature == "starter":
                    record["starter_diagnostic"] = next((event for event in events
                        if event["kind"] in {"failure", "accepted"}), None)
                    if args.capture_raw:
                        raw_event = next((event for event in events if event["kind"] == "raw_response"), None)
                        if raw_event is not None and isinstance(raw_event.get("content"), str):
                            raw_dir = BACKEND_DIR / "evaluation_runs" / run_data["run_id"] / "raw_starter"
                            raw_dir.mkdir(parents=True, exist_ok=True)
                            artifact = raw_dir / (case.key + ".txt")
                            artifact.write_bytes(raw_event["content"].encode("utf-8"))
                            record["raw_artifact"] = str(artifact)
                    if record["starter_diagnostic"] is None and payload and payload.get("usedFallback"):
                        record["starter_diagnostic"] = {"kind": "failure", "stage": "unknown",
                            "reason": "UNKNOWN_FAILURE", "certainty": "unknown"}
                    if (record["starter_diagnostic"] or {}).get("reason") == "PROVIDER_RATE_LIMITED":
                        stop_reason = "Stopped after typed Groq rate limit in Starter Code fallback"
                        run_data["run_notes"].append(stop_reason)
                if status != 200 or payload is None:
                    record["failure_categories"].append(
                        "structural_output" if status == 502 or (status == 200 and payload is None)
                        else "api_provider")
                    if status == 503:
                        stop_reason = "Stopped after HTTP 503; inspect typed starter diagnostic when available"
                        run_data["run_notes"].append(stop_reason)
                    print(f"  HTTP {status or 'unavailable'}: {error or 'invalid payload'}", flush=True)
                else:
                    if case.feature == "hints":
                        record["validation"] = evaluate_hints(payload, case)
                    else:
                        with SessionLocal() as session:
                            context = find_problem_context(session, case.slug, case.approach_id, case.language)
                        template = context["problem"]["submissionTemplate"]["code"]
                        record["validation"] = (evaluate_starter(payload, case, template, output_dir)
                                                if case.feature == "starter" else
                                                evaluate_solution(payload, case, template, output_dir))
                    if case.feature == "solution":
                        # A syntax failure precludes execution; a NOT_RUN syntax check
                        # does not preclude isolated C++ compilation and execution.
                        if (record["validation"]["structure"] == "PASS" and
                                (record["validation"]["syntax"] is None or
                                 record["validation"]["syntax"]["status"] != "FAIL")):
                            record["correctness"] = execute_solution(
                                case.slug, case.language, payload.get("code", ""), output_dir,
                                sandbox_available)
                    _classify(record)
                    print(f"  HTTP 200; structure={record['validation']['structure']}; "
                          f"correctness={record['correctness']['status'] if record['correctness'] else 'n/a'}",
                          flush=True)
                run_data["records"].append(record)
    except KeyboardInterrupt:
        stop_reason = "Interrupted by operator"
        run_data["run_notes"].append(stop_reason)
    if len(run_data["records"]) < len(selected):
        run_data["records"].extend(_empty_record(case, reason=stop_reason or "Run interrupted")
                                   for case in selected[len(run_data["records"]):])
    evaluate_progression(run_data["records"])
    json_path, report_path = write_reports(run_data, output_dir)
    print(f"Finished: {attempted} total real generation requests ({new_attempts} in this invocation). "
          f"Reports: {json_path}, {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(run())
