"""Frozen 8-request / 24-level Starter Code verification. Dry-run by default."""
import argparse
from collections import Counter
from functools import lru_cache
import json
import os
from pathlib import Path
import time
import tempfile
from datetime import datetime, timezone

from dotenv import load_dotenv
from fastapi.testclient import TestClient

from app.database import BACKEND_DIR, SessionLocal
from app.llm.base import STARTER_CODE_POLICY_VERSION, ProviderOutputError
from app.llm.starter_batch import LEVEL_KEYS, model_context, validate_level, validate_starter_batch
from app.llm.starter_diagnostics import starter_observer, starter_raw_capture
from app.llm.starter_syntax import check_syntax
from app.main import app
from app.services.problem_repository import find_problem_context
from evaluation.correctness import _sandbox_run, probe_sandbox


# One call per row; every successful row returns L1, L2 and L3.
MATRIX = (
    ("two-sum", "hash-map", "python"),
    ("3sum", "sort-and-two-pointers", "java"),
    ("binary-search", "binary-search", "cpp"),
    ("min-stack", "paired-minimums", "javascript"),
    ("reverse-linked-list", "iterative-pointers", "python"),
    ("maximum-depth-of-binary-tree", "depth-first-search", "java"),
    ("number-of-islands", "depth-first-flood-fill", "cpp"),
    ("climbing-stairs", "memoized-recursion", "javascript"),
)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--live", action="store_true")
    mode.add_argument("--dry-run", action="store_true")
    parser.add_argument("--max-calls", type=int, default=8)
    parser.add_argument("--pace-seconds", type=float, default=12)
    parser.add_argument("--capture-raw", action="store_true")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    if not 0 <= args.max_calls <= 8: parser.error("--max-calls must be between 0 and 8")
    if args.pace_seconds < 0: parser.error("--pace-seconds must be nonnegative")
    if args.capture_raw and not args.live: parser.error("--capture-raw requires --live")
    return args


@lru_cache(maxsize=1)
def _sandbox_available():
    return probe_sandbox()[0]


def offline_syntax(code, language):
    result = check_syntax(code, language)
    if result["status"] != "NOT_RUN" or language != "cpp" or not _sandbox_available(): return result
    # Offline evaluator only. Compile in the existing isolated WSL sandbox;
    # never run the resulting source or binary.
    with tempfile.TemporaryDirectory() as directory:
        compiled = _sandbox_run("#include <bits/stdc++.h>\nusing namespace std;\n" + code, "cpp",
            "ulimit -t 5; ulimit -v 786432; g++ -std=c++17 -fsyntax-only /work/case.cpp 2>&1 && "
            "printf 'COMPILE_OK\\nLEETCOACH_RESULT=\\nPASS\\n'", Path(directory), [{"syntax": True}])
    return {"status": compiled["status"], "summary": "Isolated C++ syntax-only compilation"}


def evaluate_levels(raw, context, language):
    levels = []
    for number, key in enumerate(LEVEL_KEYS, 1):
        code = raw.get(key) if isinstance(raw, dict) else None
        result = {"level": number, "structure": "NOT_RUN", "reason": None, "syntax": None,
                  "answerLeakage": "NEEDS_REVIEW", "incompletePathSafety": "NEEDS_REVIEW"}
        if code:
            try:
                validate_level(code, context, language, number)
                result["structure"] = "PASS"
            except ProviderOutputError as exc:
                result.update(structure="FAIL", reason=getattr(exc, "reason", "UNKNOWN_FAILURE"))
            result["syntax"] = offline_syntax(code, language) if isinstance(code, str) and len(code) <= 20000 else None
            if result["reason"] in {"APPARENT_COMPLETE_SOLUTION", "COMMENTED_OUT_ALGORITHM"}:
                result["answerLeakage"] = "FAIL"
            if result["reason"] in {"UNSAFE_UNFINISHED_LOOP", "UNREACHABLE_PLACEHOLDER", "SILENT_UNFINISHED_METHOD"}:
                result["incompletePathSafety"] = "FAIL"
        levels.append(result)
    try:
        validate_starter_batch(raw, context, language, check_compilers=False)
        progression = "HEURISTICS_PASS_NEEDS_REVIEW"
    except ProviderOutputError as exc:
        progression = getattr(exc, "reason", "UNKNOWN_FAILURE")
    return levels, progression


def run(argv=None):
    args = parse_args(argv)
    load_dotenv(BACKEND_DIR / ".env", override=False)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output = args.output_dir or BACKEND_DIR / "evaluation_runs" / ("starter_v2_" + timestamp)
    if not output.is_absolute(): output = BACKEND_DIR / output
    output.mkdir(parents=True, exist_ok=True)
    contexts = []
    with SessionLocal() as session:
        for slug, approach, language in MATRIX:
            context = find_problem_context(session, slug, approach, language)
            if context is None: raise SystemExit(f"Missing SQLite context: {slug}/{approach}/{language}")
            model_context(context, language)
            contexts.append(context)
    report = {"mode": "live" if args.live else "dry-run", "policyVersion": STARTER_CODE_POLICY_VERSION,
              "model": os.environ.get("LEETCOACH_LLM_MODEL"), "records": [],
              "metrics": {"realGroqCalls": 0, "plannedRequests": 8, "plannedLevels": 24},
              "comparison": "Prior matrix: 19 single-level requests. New matrix: 8 requests, 24 levels. "
                            "Report both denominators; do not compare acceptance percentages directly.",
              "limitations": "Static checks and compilation do not prove correctness, safety or teaching quality. "
                              "Review all three levels together for approach fidelity, useful progression and leakage."}
    if args.live and (not os.environ.get("GROQ_API_KEY") or not os.environ.get("LEETCOACH_LLM_MODEL")):
        raise SystemExit("Live verification needs Groq key and model configuration")
    previous_provider = os.environ.get("LEETCOACH_LLM_PROVIDER")
    try:
        if args.live: os.environ["LEETCOACH_LLM_PROVIDER"] = "groq"
        # Dry-run never constructs an API client or a Groq provider.
        client = TestClient(app) if args.live and args.max_calls else None
        try:
            attempted = 0
            stopped = False
            for (slug, approach, language), context in zip(MATRIX, contexts):
                record = {"slug": slug, "approachId": approach, "language": language,
                          "status": "NOT_RUN", "httpStatus": None, "latencyMs": None, "providerLatencyMs": None,
                          "groqCalls": 0, "diagnostics": [], "tokenUsage": None, "levels": [],
                          "progression": "NOT_RUN", "usedFallback": False}
                report["records"].append(record)
                if not client or stopped or attempted >= args.max_calls: continue
                attempted += 1
                if report["metrics"]["realGroqCalls"] and args.pace_seconds: time.sleep(args.pace_seconds)
                events = []
                observer = starter_observer.set(events.append)
                capture = starter_raw_capture.set(args.capture_raw)
                started = time.perf_counter()
                try:
                    response = client.post(f"/api/problems/{slug}/approaches/{approach}/starter-code/batch",
                                           json={"language": language})
                finally:
                    starter_raw_capture.reset(capture)
                    starter_observer.reset(observer)
                record.update(status="EXECUTED", httpStatus=response.status_code,
                              latencyMs=round((time.perf_counter() - started) * 1000, 1),
                              groqCalls=sum(event["kind"] == "request" for event in events),
                              providerLatencyMs=next((event["durationMs"] for event in events if event["kind"] == "provider_timing"), None),
                              diagnostics=[event for event in events if event["kind"] == "failure"],
                              tokenUsage=next((event for event in events if event["kind"] == "usage"), None))
                report["metrics"]["realGroqCalls"] += record["groqCalls"]
                raw = next((event["content"] for event in events if event["kind"] == "raw_response"), None)
                payload = response.json()
                record["response"] = payload
                if args.capture_raw and raw is not None:
                    path = output / f"{slug}-{language}-raw.txt"
                    path.write_text(str(raw), encoding="utf-8")
                    record["rawArtifact"] = path.name
                if response.status_code == 200:
                    batch = {key: payload.get(key) for key in LEVEL_KEYS}
                else:
                    try: batch = json.loads(raw) if raw else None
                    except (TypeError, ValueError): batch = None
                record["levels"], record["progression"] = evaluate_levels(batch, context, language)
                record["usedFallback"] = payload.get("usedFallback", False)
                # No retries; stop a failing provider run rather than burning quota.
                if response.status_code in (429, 503): stopped = True
        finally:
            if client: client.close()
    finally:
        if previous_provider is None: os.environ.pop("LEETCOACH_LLM_PROVIDER", None)
        else: os.environ["LEETCOACH_LLM_PROVIDER"] = previous_provider
    executed = [r for r in report["records"] if r["status"] == "EXECUTED"]
    report["metrics"].update(
        executedRequests=len(executed), validBatches=sum(r["httpStatus"] == 200 for r in executed),
        apiFailures=sum(r["httpStatus"] != 200 for r in executed),
        structuralRejections=dict(Counter(d["reason"] for r in executed for d in r["diagnostics"])),
        inspectedLevels=sum(bool(r["levels"]) * 3 for r in executed),
        structurallyValidLevels=sum(level["structure"] == "PASS" for r in executed for level in r["levels"]),
        syntaxResults=dict(Counter(level["syntax"]["status"] for r in executed for level in r["levels"] if level["syntax"])),
    )
    (output / "starter_v2.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    rows = ["# Starter v2 bounded verification", "", f"Mode: {report['mode']}", "",
            "```json", json.dumps(report["metrics"], indent=2), "```", "", report["comparison"], "",
            report["limitations"], "", "| Problem | Language | HTTP | Calls | L1/L2/L3 structure | Progression |",
            "|---|---|---|---:|---|---|"]
    for record in report["records"]:
        levels = "/".join(level["structure"] for level in record["levels"]) or "NOT_RUN"
        rows.append(f"| {record['slug']} | {record['language']} | {record['httpStatus']} | {record['groqCalls']} | {levels} | {record['progression']} |")
    (output / "starter_v2_report.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"{report['mode']}: {report['metrics']['realGroqCalls']} real Groq calls; report: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
