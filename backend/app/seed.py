"""Run after `alembic upgrade head`: python -m app.seed.

Upsert the curated records in one transaction. Re-running refreshes their
content without changing internal IDs or duplicating rows. Unrelated records
are left alone; obsolete bullet positions in a seeded signal set are removed.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.mock_data import PROBLEM_ANALYSES, validate_problem_dataset
from app.models import Approach, Problem, RecognitionSignalBullet, RecognitionSignals, RelatedProblem
from app.services.related_problem_service import RELATED_PROBLEMS


def seed_data(session: Session):
    """The caller owns the transaction; no schema creation or implicit commit."""
    validate_problem_dataset(PROBLEM_ANALYSES)
    for slug, data in PROBLEM_ANALYSES.items():
        problem = session.scalar(select(Problem).where(Problem.slug == slug))
        if problem is None:
            problem = Problem(slug=slug)
            session.add(problem)
            session.flush()
        existing_approaches = {a.approach_key: a for a in problem.approaches}
        for source in data["approaches"]:
            approach = existing_approaches.get(source["id"])
            if approach is None:
                approach = Approach(approach_key=source["id"])
                problem.approaches.append(approach)
            approach.name = source["name"]
            approach.pattern = source["pattern"]
            approach.summary = source["summary"]
            approach.is_primary = source["isPrimary"]
            approach.display_order = source["displayOrder"]
            approach.thinking_steps = list(source["thinkingSteps"])
            source_signals = source.get("recognitionSignals")
            if source_signals is None:
                approach.recognition_signals = None
                continue
            if approach.recognition_signals is None:
                approach.recognition_signals = RecognitionSignals()
            signals = approach.recognition_signals
            signals.quote = source_signals.get("quote")
            existing_bullets = {b.display_order: b for b in signals.bullets}
            for order, text in enumerate(source_signals["bullets"], start=1):
                bullet = existing_bullets.get(order)
                if bullet is None:
                    bullet = RecognitionSignalBullet(display_order=order)
                    signals.bullets.append(bullet)
                bullet.text = text
            for bullet in list(signals.bullets):
                if bullet.display_order > len(source_signals["bullets"]):
                    signals.bullets.remove(bullet)
        existing_related = {r.slug: r for r in problem.related_problems}
        for category, cards in RELATED_PROBLEMS[slug].items():
            for order, card in enumerate(cards, start=1):
                related = existing_related.get(card["slug"])
                if related is None:
                    related = RelatedProblem(slug=card["slug"])
                    problem.related_problems.append(related)
                related.category = category
                related.display_order = order
                related.title = card["title"]
                related.difficulty = card["difficulty"]
                related.reason = card.get("reason")
    session.flush()


def main():
    with Session(engine) as session, session.begin():
        seed_data(session)
    print("Seeded 3 problems, 7 approaches with recognition signals, and 9 related problems.")


if __name__ == "__main__":
    main()
