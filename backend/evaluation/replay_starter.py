"""Replay a locally captured Starter Code response without a provider request.

Usage: py -m evaluation.replay_starter RAW_FILE --slug two-sum --approach hash-map
       --language python --level 1
"""
import argparse
import json
from pathlib import Path

from app.database import SessionLocal
from app.llm.base import ProviderOutputError
from app.llm.groq_provider import GroqLLMProvider
from app.llm.starter_diagnostics import failure_metadata
from app.services.problem_repository import find_problem_context


def replay(content: str, context: dict, language: str, level: int) -> dict:
    try:
        # Historical Phase 1/3 captures used the retired full-file contract.
        # Replay them offline without re-enabling it for production requests.
        try:
            parsed = json.loads(content)
        except ValueError:
            parsed = None
        GroqLLMProvider.parse_starter_content(
            content, context, language, level,
            allow_legacy=isinstance(parsed, dict) and "code" in parsed,
        )
    except ProviderOutputError as exc:
        return {"accepted": False, **failure_metadata(exc)}
    return {"accepted": True, "stage": "accepted", "reason": None, "certainty": "confirmed"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Offline replay through the production parser and validator")
    parser.add_argument("raw_file", type=Path)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--approach", required=True)
    parser.add_argument("--language", required=True, choices=("python", "java", "javascript", "cpp"))
    parser.add_argument("--level", required=True, type=int, choices=(1, 2, 3))
    args = parser.parse_args(argv)
    with SessionLocal() as session:
        context = find_problem_context(session, args.slug, args.approach, args.language)
    if context is None:
        parser.error("Canonical problem, approach, or language template not found")
    result = replay(args.raw_file.read_text(encoding="utf-8"), context, args.language, args.level)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
