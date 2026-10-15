"""Reassess saved endpoint responses without making another Groq request."""
import argparse
import json
from pathlib import Path

from app.database import SessionLocal
from app.services.problem_repository import find_problem_context
from evaluation.cases import EvaluationCase
from evaluation.reporting import write_reports
from evaluation.run_evaluation import _classify
from evaluation.validators import evaluate_hints, evaluate_progression, evaluate_solution, evaluate_starter


def reassess(input_json: Path, observations_json: Path | None = None) -> tuple[Path, Path]:
    run = json.loads(input_json.read_text(encoding="utf-8"))
    if observations_json:
        notes = json.loads(observations_json.read_text(encoding="utf-8"))
        if not isinstance(notes, list) or any(not isinstance(note, dict) or
                                               not {"case_id", "status", "observation"} <= note.keys()
                                               for note in notes):
            raise ValueError("Editorial observations must be a list of case notes")
        run["editorial_observations"] = notes
    for record in run["records"]:
        payload = record.get("response")
        if record.get("http_status") != 200 or not isinstance(payload, dict):
            continue
        saved = record["case"]
        case = EvaluationCase(saved["feature"], saved["slug"], saved["approach_id"],
                              saved.get("language"), saved.get("level"))
        if case.feature == "hints":
            record["validation"] = evaluate_hints(payload, case)
        else:
            with SessionLocal() as session:
                context = find_problem_context(session, case.slug, case.approach_id, case.language)
            if context is None:
                raise ValueError(f"Seeded context disappeared for {case.key}")
            template = context["problem"]["submissionTemplate"]["code"]
            record["validation"] = (evaluate_starter(payload, case, template, input_json.parent)
                                    if case.feature == "starter" else
                                    evaluate_solution(payload, case, template, input_json.parent))
        record["failure_categories"] = []
        _classify(record)
    evaluate_progression(run["records"])
    run.setdefault("run_notes", []).append("Reassessed saved responses without new generation requests")
    return write_reports(run, input_json.parent)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path)
    parser.add_argument("--observations-json", type=Path)
    args = parser.parse_args()
    json_path, markdown_path = reassess(args.input_json, args.observations_json)
    print(f"No Groq requests sent. Updated reports: {json_path}, {markdown_path}")


if __name__ == "__main__":
    main()
