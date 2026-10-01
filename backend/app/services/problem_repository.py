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
