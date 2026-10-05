from copy import deepcopy
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app.models import (
    Approach, Problem, ProblemConstraint, ProblemExample, ProblemSubmissionTemplate,
    RecognitionSignalBullet, RecognitionSignals, RelatedProblem,
)
from app.seed import seed_data
from app.stable_data import CURATED_PROBLEMS, CURATED_PROBLEM_SPECS, CURATED_RELATED_PROBLEMS


class SeedSyncTests(DatabaseTestCase):
    def snapshot_ids(self):
        with Session(self.engine) as session:
            return {
                model: set(session.scalars(select(model.id)))
                for model in (
                    Problem, Approach, RecognitionSignals, RecognitionSignalBullet, RelatedProblem,
                    ProblemConstraint, ProblemExample, ProblemSubmissionTemplate,
                )
            }

    def run_seed(self, problems, related, specs):
        with Session(self.engine) as session, session.begin():
            seed_data(session, problems, related, specs)

    def test_seeding_twice_creates_no_duplicates_or_replacement_ids(self):
        # setUp performs the initial seed; this is the second run.
        before = self.snapshot_ids()
        self.run_seed(CURATED_PROBLEMS, CURATED_RELATED_PROBLEMS, CURATED_PROBLEM_SPECS)
        self.assertEqual(self.snapshot_ids(), before)
        self.assertEqual(len(before[Problem]), 20)

    def test_source_content_changes_update_existing_rows_in_place(self):
        problems = deepcopy(CURATED_PROBLEMS)
        related = deepcopy(CURATED_RELATED_PROBLEMS)
        specs = deepcopy(CURATED_PROBLEM_SPECS)
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
            # A category change must preserve identity by target slug, including
            # sources whose Easier group is intentionally empty.
            source_category = next(category for category, cards in groups.items() if cards)
            target_category = next(category for category in groups if category != source_category)
            groups[target_category].insert(0, groups[source_category].pop())
        for spec in specs.values():
            spec["title"] += " updated"
            spec["summary"] += " Updated."
            spec["constraints"][0] = "Updated constraint"
            spec["examples"][0]["output"] = "updated output"
            spec["submissionTemplates"]["python"] += "\n# updated"
        self.run_seed(problems, related, specs)
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
                spec = specs[problem.slug]
                self.assertEqual((problem.title, problem.summary), (spec["title"], spec["summary"]))
                self.assertEqual(problem.constraints[0].text, "Updated constraint")
                self.assertEqual(problem.examples[0].output_text, "updated output")
                templates = {item.language: item.code for item in problem.submission_templates}
                self.assertEqual(templates["python"], spec["submissionTemplates"]["python"])

    def test_removed_children_are_deleted_only_within_current_seeded_problems(self):
        problems = deepcopy(CURATED_PROBLEMS)
        related = deepcopy(CURATED_RELATED_PROBLEMS)
        specs = deepcopy(CURATED_PROBLEM_SPECS)
        # This previously seeded problem is now outside the curated dataset:
        # its problem row AND all its existing children must remain untouched.
        del problems["valid-parentheses"]
        del related["valid-parentheses"]
        del specs["valid-parentheses"]
        expected_ids = self.snapshot_ids()
        with Session(self.engine) as session:
            untouched = session.scalar(select(Problem).where(Problem.slug == "valid-parentheses"))
            untouched_approaches = {a.approach_key: a.id for a in untouched.approaches}
            untouched_related = {r.slug: r.id for r in untouched.related_problems}
            for slug, source in problems.items():
                problem = session.scalar(select(Problem).where(Problem.slug == slug))
                removed = next(a for a in source["approaches"] if not a["isPrimary"])
                source["approaches"].remove(removed)
                for order, retained in enumerate(source["approaches"], 1):
                    retained["displayOrder"] = order
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
                specs[slug]["constraints"].pop()
                expected_ids[ProblemConstraint].remove(problem.constraints[-1].id)
                if len(specs[slug]["examples"]) > 1:
                    specs[slug]["examples"].pop()
                    expected_ids[ProblemExample].remove(problem.examples[-1].id)
                del specs[slug]["submissionTemplates"]["cpp"]
                cpp_template = next(t for t in problem.submission_templates if t.language == "cpp")
                expected_ids[ProblemSubmissionTemplate].remove(cpp_template.id)
        self.run_seed(problems, related, specs)
        self.assertEqual(self.snapshot_ids(), expected_ids)
        # Repeating the reduced seed must not resurrect deleted children.
        self.run_seed(problems, related, specs)
        self.assertEqual(self.snapshot_ids(), expected_ids)
        with Session(self.engine) as session:
            for slug, source in problems.items():
                problem = session.scalar(select(Problem).where(Problem.slug == slug))
                self.assertEqual({a.approach_key for a in problem.approaches},
                                 {a["id"] for a in source["approaches"]})
                self.assertEqual({r.slug for r in problem.related_problems},
                                 {card["slug"] for cards in related[slug].values() for card in cards})
                self.assertEqual(len(problem.constraints), len(specs[slug]["constraints"]))
                self.assertEqual(len(problem.examples), len(specs[slug]["examples"]))
                self.assertEqual({t.language for t in problem.submission_templates},
                                 set(specs[slug]["submissionTemplates"]))
            untouched = session.scalar(select(Problem).where(Problem.slug == "valid-parentheses"))
            self.assertEqual({a.approach_key: a.id for a in untouched.approaches}, untouched_approaches)
            self.assertEqual({r.slug: r.id for r in untouched.related_problems}, untouched_related)
