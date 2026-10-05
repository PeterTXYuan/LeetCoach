import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app.models import Problem, ProblemConstraint, ProblemExample, ProblemSubmissionTemplate
from app.seed import seed_data
from app.services.problem_repository import find_problem_context
from app.stable_data import CURATED_PROBLEM_SPECS, CURATED_PROBLEMS


class ProblemSpecTests(DatabaseTestCase):
    def test_all_twenty_problems_persist_complete_ordered_specs(self):
        with Session(self.engine) as session:
            problems = list(session.scalars(select(Problem).order_by(Problem.slug)))
            self.assertEqual(len(problems), 20)
            for problem in problems:
                with self.subTest(slug=problem.slug):
                    source = CURATED_PROBLEM_SPECS[problem.slug]
                    self.assertEqual(
                        (problem.title, problem.difficulty, problem.summary),
                        (source["title"], source["difficulty"], source["summary"]),
                    )
                    self.assertEqual([item.text for item in problem.constraints], source["constraints"])
                    self.assertEqual(
                        [(item.input_text, item.output_text, item.explanation) for item in problem.examples],
                        [(item["input"], item["output"], item.get("explanation")) for item in source["examples"]],
                    )
                    templates = {item.language: item.code for item in problem.submission_templates}
                    self.assertEqual(templates, source["submissionTemplates"])
                    self.assertEqual(set(templates), {"python", "java", "javascript", "cpp"})

    def test_submission_template_language_is_unique_per_problem(self):
        with Session(self.engine) as session:
            problem = session.scalar(select(Problem).where(Problem.slug == "two-sum"))
            problem_id = problem.id
        for template in (
            ProblemSubmissionTemplate(problem_id=problem_id, language="python", code="duplicate"),
            ProblemSubmissionTemplate(problem_id=problem_id, language="ruby", code="unsupported"),
        ):
            with self.subTest(language=template.language), self.assertRaises(IntegrityError):
                with Session(self.engine) as session, session.begin():
                    session.add(template)

    def test_spec_table_constraints_reject_invalid_rows(self):
        with Session(self.engine) as session:
            problem_id = session.scalar(select(Problem.id).where(Problem.slug == "two-sum"))
        invalid_rows = (
            Problem(slug="bad-difficulty", title="Bad", difficulty="Unknown", summary="Bad."),
            ProblemConstraint(problem_id=problem_id, text="Duplicate order", display_order=1),
            ProblemConstraint(problem_id=problem_id, text="Bad order", display_order=0),
            ProblemExample(problem_id=problem_id, input_text="x", output_text="y", display_order=1),
            ProblemExample(problem_id=problem_id, input_text="x", output_text="y", display_order=0),
        )
        for row in invalid_rows:
            with self.subTest(row=type(row).__name__), self.assertRaises(IntegrityError):
                with Session(self.engine) as session, session.begin():
                    session.add(row)

    def test_internal_context_loader_combines_facts_template_and_canonical_approach(self):
        with Session(self.engine) as session:
            context = find_problem_context(session, "two-sum", "hash-map", "java")
            self.assertEqual(context["problem"]["title"], "Two Sum")
            self.assertEqual(context["problem"]["constraints"], CURATED_PROBLEM_SPECS["two-sum"]["constraints"])
            self.assertEqual(context["problem"]["submissionTemplate"], {
                "language": "java",
                "code": CURATED_PROBLEM_SPECS["two-sum"]["submissionTemplates"]["java"],
            })
            self.assertEqual(context["approach"]["id"], "hash-map")
            self.assertIsNone(find_problem_context(session, "two-sum", "missing", "java"))
            self.assertIsNone(find_problem_context(session, "two-sum", "hash-map", "ruby"))

    def test_0002_upgrade_and_downgrade_preserve_0001_problem_rows(self):
        self.migrate("downgrade", "0001")
        inspector = inspect(self.engine)
        self.assertNotIn("problem_constraints", inspector.get_table_names())
        self.assertNotIn("title", {column["name"] for column in inspector.get_columns("problems")})
        with Session(self.engine) as session:
            self.assertEqual(len(session.execute(select(Problem.slug)).all()), 20)

        self.migrate("upgrade", "0002")
        with Session(self.engine) as session, session.begin():
            seed_data(session)
        inspector = inspect(self.engine)
        self.assertIn("problem_submission_templates", inspector.get_table_names())
        self.assertIn("title", {column["name"] for column in inspector.get_columns("problems")})
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(Problem).where(Problem.slug == "two-sum")).title, "Two Sum")


if __name__ == "__main__":
    unittest.main()
