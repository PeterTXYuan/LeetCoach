"""Database reads and serializers for the existing public API contracts."""
from datetime import timezone

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Approach, Problem, RecognitionSignals


def find_problem_analysis(session: Session, slug: str):
    problem = session.scalar(select(Problem).where(Problem.slug == slug).options(
        selectinload(Problem.approaches)
        .selectinload(Approach.recognition_signals)
        .selectinload(RecognitionSignals.bullets)
    ))
    if problem is None:
        return None
    return {"slug": problem.slug, "approaches": [serialize_approach(a) for a in problem.approaches]}


def serialize_approach(approach: Approach):
    result = {
        "id": approach.approach_key,
        "name": approach.name,
        "pattern": approach.pattern,
        "summary": approach.summary,
        "isPrimary": approach.is_primary,
        "displayOrder": approach.display_order,
        "thinkingSteps": approach.thinking_steps,
    }
    if approach.recognition_signals is not None:
        signals = approach.recognition_signals
        result["recognitionSignals"] = {"bullets": [bullet.text for bullet in signals.bullets]}
        if signals.quote is not None:
            result["recognitionSignals"]["quote"] = signals.quote
    return result


def find_related_problems(session: Session, slug: str):
    problem = session.scalar(select(Problem).where(Problem.slug == slug).options(
        selectinload(Problem.related_problems)
    ))
    if problem is None:
        return None
    result = {"slug": problem.slug, "easier": [], "similar": [], "harder": []}
    for related in problem.related_problems:
        card = {"slug": related.slug, "title": related.title, "difficulty": related.difficulty}
        if related.reason is not None:
            card["reason"] = related.reason
        result[related.category].append(card)
    return result


def find_problem_context(session: Session, slug: str, approach_id: str, language: str):
    """Load factual grounding for a future LLM call without exposing a new API."""
    problem = session.scalar(select(Problem).where(Problem.slug == slug).options(
        selectinload(Problem.constraints),
        selectinload(Problem.examples),
        selectinload(Problem.submission_templates),
        selectinload(Problem.approaches)
        .selectinload(Approach.recognition_signals)
        .selectinload(RecognitionSignals.bullets),
    ))
    if problem is None:
        return None
    approach = next((item for item in problem.approaches if item.approach_key == approach_id), None)
    template = next((item for item in problem.submission_templates if item.language == language), None)
    if approach is None or template is None:
        return None
    return {
        "problem": {**serialize_problem_context(problem),
                    "submissionTemplate": {"language": template.language, "code": template.code}},
        "approach": serialize_approach(approach),
    }


def find_hint_problem_context(session: Session, slug: str):
    """Load DB facts for hints without requiring a language or code template."""
    problem = session.scalar(select(Problem).where(Problem.slug == slug).options(
        selectinload(Problem.constraints),
        selectinload(Problem.examples),
        selectinload(Problem.approaches)
        .selectinload(Approach.recognition_signals)
        .selectinload(RecognitionSignals.bullets),
    ))
    if problem is None:
        return None
    return {
        "problem": serialize_problem_context(problem),
        "approaches": [serialize_approach(approach) for approach in problem.approaches],
    }


def serialize_problem_context(problem: Problem) -> dict:
    """One factual shape for Hints, Starter Code, and Full Solution."""
    verified_at = problem.description_verified_at
    if verified_at is not None and verified_at.tzinfo is None:
        # SQLite stores the audited UTC timestamp without its timezone offset.
        verified_at = verified_at.replace(tzinfo=timezone.utc)
    return {
        "slug": problem.slug,
        "leetcodeNumber": problem.leetcode_number,
        "title": problem.title,
        "difficulty": problem.difficulty,
        "summary": problem.summary,
        "description": problem.description,
        "descriptionSourceUrl": problem.description_source_url,
        "descriptionSourceType": problem.description_source_type,
        "descriptionVerifiedAt": verified_at.isoformat() if verified_at else None,
        "timeLimitMs": problem.time_limit_ms,
        "memoryLimitMb": problem.memory_limit_mb,
        "timeComplexityInstruction": problem.time_complexity_instruction,
        "spaceComplexityInstruction": problem.space_complexity_instruction,
        "constraints": [item.text for item in problem.constraints],
        "examples": [{"input": item.input_text, "output": item.output_text,
                      "explanation": item.explanation} for item in problem.examples],
    }
