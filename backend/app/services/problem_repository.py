"""Database reads and serializers for the existing public API contracts."""
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
        "problem": {
            "slug": problem.slug,
            "title": problem.title,
            "difficulty": problem.difficulty,
            "summary": problem.summary,
            "constraints": [item.text for item in problem.constraints],
            "examples": [
                {
                    "input": item.input_text,
                    "output": item.output_text,
                    "explanation": item.explanation,
                }
                for item in problem.examples
            ],
            "submissionTemplate": {"language": template.language, "code": template.code},
        },
        "approach": serialize_approach(approach),
    }
