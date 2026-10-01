from copy import deepcopy
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app.mock_data import PROBLEM_ANALYSES
from app.models import Approach, Problem, RecognitionSignalBullet, RecognitionSignals, RelatedProblem
from app.seed import seed_data
from app.services.related_problem_service import RELATED_PROBLEMS


class SeedSyncTests(DatabaseTestCase):
    def snapshot_ids(self):
        with Session(self.engine) as session:
            return {
                model: set(session.scalars(select(model.id)))
                for model in (Problem, Approach, RecognitionSignals, RecognitionSignalBullet, RelatedProblem)
            }

    def run_seed(self, problems, related):
        with patch("app.seed.PROBLEM_ANALYSES", problems), patch("app.seed.RELATED_PROBLEMS", related):
            with Session(self.engine) as session, session.begin():
                seed_data(session)

    def test_seeding_twice_creates_no_duplicates_or_replacement_ids(self):
        # setUp performs the initial seed; this is the second run.
        before = self.snapshot_ids()
        self.run_seed(PROBLEM_ANALYSES, RELATED_PROBLEMS)
        self.assertEqual(self.snapshot_ids(), before)
        self.assertEqual([len(ids) for ids in before.values()], [3, 7, 7, 16, 9])

    def test_source_content_changes_update_existing_rows_in_place(self):
        problems, related = deepcopy(PROBLEM_ANALYSES), deepcopy(RELATED_PROBLEMS)
        before = self.snapshot_ids()
        for problem in problems.values():
            for approach in problem["approaches"]:
                approach["summary"] = f"Updated {approach['id']} summary"
                approach["recognitionSignals"]["quote"] = "Updated quote"
                approach["recognitionSignals"]["bullets"][0] = "Updated first signal"
        for groups in related.values():
            for cards in groups.values():
                for card in cards:
                    card["title"] += " updated"
                    card["reason"] = "Updated reason"
            # A category change must preserve identity by target slug.
            groups["similar"].insert(0, groups["easier"].pop())
        self.run_seed(problems, related)
        self.assertEqual(self.snapshot_ids(), before)
        with Session(self.engine) as session:
            for problem in session.scalars(select(Problem)):
                for approach in problem.approaches:
                    self.assertEqual(approach.summary, f"Updated {approach.approach_key} summary")
                    self.assertEqual(approach.recognition_signals.quote, "Updated quote")
                    self.assertEqual(approach.recognition_signals.bullets[0].text, "Updated first signal")
                cards_by_slug = {r.slug: r for r in problem.related_problems}
                for category, cards in related[problem.slug].items():
                    for order, card in enumerate(cards, 1):
                        row = cards_by_slug[card["slug"]]
                        self.assertEqual((row.title, row.reason, row.category, row.display_order),
                                         (card["title"], card["reason"], category, order))

    def test_removed_children_are_deleted_only_within_current_seeded_problems(self):
        problems, related = deepcopy(PROBLEM_ANALYSES), deepcopy(RELATED_PROBLEMS)
        # This previously seeded problem is now outside the curated dataset:
        # its problem row AND all its existing children must remain untouched.
        del problems["valid-parentheses"]
        del related["valid-parentheses"]
        expected_ids = self.snapshot_ids()
        with Session(self.engine) as session:
            untouched = session.scalar(select(Problem).where(Problem.slug == "valid-parentheses"))
            untouched_approaches = {a.approach_key: a.id for a in untouched.approaches}
            untouched_related = {r.slug: r.id for r in untouched.related_problems}
            for slug, source in problems.items():
                problem = session.scalar(select(Problem).where(Problem.slug == slug))
                removed = next(a for a in source["approaches"] if not a["isPrimary"])
                source["approaches"].remove(removed)
                row = next(a for a in problem.approaches if a.approach_key == removed["id"])
                expected_ids[Approach].remove(row.id)
                expected_ids[RecognitionSignals].remove(row.recognition_signals.id)
                expected_ids[RecognitionSignalBullet].difference_update(b.id for b in row.recognition_signals.bullets)
                # Cover both a partial removal and an entirely empty collection.
                related[slug]["easier"].clear()
                if slug == "two-sum":
                    for cards in related[slug].values():
                        cards.clear()
                retained_slugs = {card["slug"] for cards in related[slug].values() for card in cards}
                expected_ids[RelatedProblem].difference_update(
                    r.id for r in problem.related_problems if r.slug not in retained_slugs
                )
                # Existing cleanup of obsolete signal positions must still work.
                retained_source = next(a for a in source["approaches"] if a["isPrimary"])
                retained_row = next(a for a in problem.approaches if a.approach_key == retained_source["id"])
                retained_source["recognitionSignals"]["bullets"].pop()
                expected_ids[RecognitionSignalBullet].remove(retained_row.recognition_signals.bullets[-1].id)
        self.run_seed(problems, related)
        self.assertEqual(self.snapshot_ids(), expected_ids)
        # Repeating the reduced seed must not resurrect deleted children.
        self.run_seed(problems, related)
        self.assertEqual(self.snapshot_ids(), expected_ids)
        with Session(self.engine) as session:
            for slug, source in problems.items():
                problem = session.scalar(select(Problem).where(Problem.slug == slug))
                self.assertEqual({a.approach_key for a in problem.approaches},
                                 {a["id"] for a in source["approaches"]})
                self.assertEqual({r.slug for r in problem.related_problems},
                                 {card["slug"] for cards in related[slug].values() for card in cards})
            untouched = session.scalar(select(Problem).where(Problem.slug == "valid-parentheses"))
            self.assertEqual({a.approach_key: a.id for a in untouched.approaches}, untouched_approaches)
            self.assertEqual({r.slug: r.id for r in untouched.related_problems}, untouched_related)
