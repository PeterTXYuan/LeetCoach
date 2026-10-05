"""Run after `alembic upgrade head`: python -m app.seed.

Sync curated child records in one transaction. Re-running refreshes their
content without changing retained IDs or duplicating rows. Stale approaches,
related cards, and bullet positions are removed within seeded problems only.
Problems outside the curated dataset and their children are left alone.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine
from app.models import (
    Approach, Problem, ProblemConstraint, ProblemExample, ProblemSubmissionTemplate,
    RecognitionSignalBullet, RecognitionSignals, RelatedProblem,
)
from app.stable_data import (
    CURATED_PROBLEMS, CURATED_PROBLEM_SPECS, CURATED_RELATED_PROBLEMS, validate_curated_data,
)


def seed_data(session: Session, problems=None, related_problems=None, problem_specs=None):
    """The caller owns the transaction; no schema creation or implicit commit."""
    problems = CURATED_PROBLEMS if problems is None else problems
    related_problems = CURATED_RELATED_PROBLEMS if related_problems is None else related_problems
    problem_specs = CURATED_PROBLEM_SPECS if problem_specs is None else problem_specs
    validate_curated_data(problems, related_problems, problem_specs)
    for slug, data in problems.items():
        spec = problem_specs[slug]
        problem = session.scalar(select(Problem).where(Problem.slug == slug))
        if problem is None:
            problem = Problem(slug=slug, title=spec["title"], difficulty=spec["difficulty"], summary=spec["summary"])
            session.add(problem)
            session.flush()
        problem.title = spec["title"]
        problem.difficulty = spec["difficulty"]
        problem.summary = spec["summary"]

        existing_constraints = {item.display_order: item for item in problem.constraints}
        for order, text in enumerate(spec["constraints"], start=1):
            item = existing_constraints.get(order)
            if item is None:
                item = ProblemConstraint(display_order=order)
                problem.constraints.append(item)
            item.text = text
        for order, item in existing_constraints.items():
            if order > len(spec["constraints"]):
                problem.constraints.remove(item)

        existing_examples = {item.display_order: item for item in problem.examples}
        for order, source in enumerate(spec["examples"], start=1):
            item = existing_examples.get(order)
            if item is None:
                item = ProblemExample(display_order=order)
                problem.examples.append(item)
            item.input_text = source["input"]
            item.output_text = source["output"]
            item.explanation = source.get("explanation")
        for order, item in existing_examples.items():
            if order > len(spec["examples"]):
                problem.examples.remove(item)

        existing_templates = {item.language: item for item in problem.submission_templates}
        for language, code in spec["submissionTemplates"].items():
            item = existing_templates.get(language)
            if item is None:
                item = ProblemSubmissionTemplate(language=language)
                problem.submission_templates.append(item)
            item.code = code
        for language, item in existing_templates.items():
            if language not in spec["submissionTemplates"]:
                problem.submission_templates.remove(item)
        existing_approaches = {a.approach_key: a for a in problem.approaches}
        source_approach_keys = {a["id"] for a in data["approaches"]}
        for key, approach in existing_approaches.items():
            if key not in source_approach_keys:
                # delete-orphan also removes the approach's recognition metadata.
                problem.approaches.remove(approach)
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
        source_related_slugs = {
            card["slug"] for cards in related_problems[slug].values() for card in cards
        }
        for related_slug, related in existing_related.items():
            if related_slug not in source_related_slugs:
                problem.related_problems.remove(related)
        for category, cards in related_problems[slug].items():
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
    approach_count = sum(len(p["approaches"]) for p in CURATED_PROBLEMS.values())
    related_count = sum(len(cards) for groups in CURATED_RELATED_PROBLEMS.values() for cards in groups.values())
    print(f"Synced {len(CURATED_PROBLEMS)} problems, {approach_count} approaches, and {related_count} related problems.")


if __name__ == "__main__":
    main()
