import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app.models import Problem, ProblemConstraint, ProblemExample, ProblemSubmissionTemplate
from app.llm.mock_provider import MockLLMProvider
from app.seed import seed_data
from app.services.problem_repository import find_problem_context
from app.services.problem_repository import find_hint_problem_context
from app.stable_data import CURATED_PROBLEM_SPECS, CURATED_PROBLEMS


# Independently recorded from the public LeetCode problem pages. These counts
# catch a missing official example or constraint even if seed and DB agree.
OFFICIAL_COUNTS = {
    "two-sum": (1, 3, 4),
    "contains-duplicate": (217, 3, 2),
    "valid-anagram": (242, 2, 2),
    "group-anagrams": (49, 3, 3),
    "valid-palindrome": (125, 3, 2),
    "two-sum-ii-input-array-is-sorted": (167, 3, 5),
    "3sum": (15, 3, 2),
    "best-time-to-buy-and-sell-stock": (121, 2, 2),
    "longest-substring-without-repeating-characters": (3, 3, 2),
    "longest-repeating-character-replacement": (424, 2, 3),
    "valid-parentheses": (20, 5, 2),
    "min-stack": (155, 1, 3),
    "daily-temperatures": (739, 3, 2),
    "binary-search": (704, 2, 4),
    "search-in-rotated-sorted-array": (33, 3, 5),
    "reverse-linked-list": (206, 3, 2),
    "merge-two-sorted-lists": (21, 3, 3),
    "maximum-depth-of-binary-tree": (104, 2, 2),
    "number-of-islands": (200, 2, 4),
    "climbing-stairs": (70, 2, 1),
}


class ProblemSpecTests(DatabaseTestCase):
    def test_source_audit_has_all_official_examples_and_constraints(self):
        self.assertEqual(set(CURATED_PROBLEM_SPECS), set(OFFICIAL_COUNTS))
        self.assertEqual(set(CURATED_PROBLEMS), set(OFFICIAL_COUNTS))
        with Session(self.engine) as session:
            for slug, (number, example_count, constraint_count) in OFFICIAL_COUNTS.items():
                with self.subTest(slug=slug):
                    source = CURATED_PROBLEM_SPECS[slug]
                    problem = session.scalar(select(Problem).where(Problem.slug == slug))
                    self.assertEqual(source["leetcodeNumber"], number)
                    self.assertEqual(len(source["examples"]), example_count)
                    self.assertEqual(len(source["constraints"]), constraint_count)
                    self.assertEqual(len(problem.examples), example_count)
                    self.assertEqual(len(problem.constraints), constraint_count)
                    self.assertEqual(source["descriptionSourceUrl"],
                                     f"https://leetcode.com/problems/{slug}/")
                    self.assertEqual(source["descriptionSourceType"], "curated_restatement")
                    self.assertIsNone(source["timeLimitMs"])
                    self.assertIsNone(source["memoryLimitMb"])
        self.assertEqual(
            [(item["input"], item["output"]) for item in CURATED_PROBLEM_SPECS["two-sum"]["examples"]],
            [("nums = [2,7,11,15], target = 9", "[0,1]"),
             ("nums = [3,2,4], target = 6", "[1,2]"),
             ("nums = [3,3], target = 6", "[0,1]")],
        )
        self.assertIn("Optional follow-up", CURATED_PROBLEM_SPECS["two-sum"]["timeComplexityInstruction"])
        self.assertIn("Required", CURATED_PROBLEM_SPECS["two-sum-ii-input-array-is-sorted"]["spaceComplexityInstruction"])
        for slug in ("min-stack", "binary-search", "search-in-rotated-sorted-array"):
            self.assertIn("Required", CURATED_PROBLEM_SPECS[slug]["timeComplexityInstruction"])

    def test_mocked_generation_receives_shared_facts_and_one_language_template(self):
        class CapturingProvider(MockLLMProvider):
            def __init__(self):
                self.calls = []

            def generate_hints(self, context):
                self.calls.append(("hints", context))
                return super().generate_hints(context)

            def generate_starter_code(self, context, language, level):
                self.calls.append(("starter", context))
                return super().generate_starter_code(context, language, level)

            def generate_solution(self, context, language):
                self.calls.append(("solution", context))
                return super().generate_solution(context, language)

        provider = CapturingProvider()
        with patch("app.main.get_llm_provider", return_value=provider):
            hint = self.client.get("/api/problems/two-sum/approaches/hash-map/hints")
            starter = self.client.post("/api/problems/two-sum/approaches/hash-map/starter-code",
                                       json={"language": "python", "level": 2})
            solution = self.client.post("/api/problems/two-sum/approaches/hash-map/solution",
                                        json={"language": "python"})
        self.assertEqual([response.status_code for response in (hint, starter, solution)], [200, 200, 200])
        self.assertEqual([kind for kind, _ in provider.calls], ["hints", "starter", "solution"])
        facts = [{key: value for key, value in context["problem"].items()
                  if key != "submissionTemplate"} for _, context in provider.calls]
        self.assertEqual(facts[0], facts[1])
        self.assertEqual(facts[1], facts[2])
        self.assertNotIn("submissionTemplate", provider.calls[0][1]["problem"])
        for _, context in provider.calls[1:]:
            self.assertEqual(context["problem"]["submissionTemplate"], {
                "language": "python",
                "code": CURATED_PROBLEM_SPECS["two-sum"]["submissionTemplates"]["python"],
            })
            self.assertEqual(context["approach"]["id"], "hash-map")
        self.assertEqual(provider.calls[0][1]["approach"]["id"], "hash-map")

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
                    self.assertEqual(problem.leetcode_number, source["leetcodeNumber"])
                    self.assertEqual(problem.description, source["description"])
                    self.assertEqual(problem.description_source_url, source["descriptionSourceUrl"])
                    self.assertEqual(problem.description_source_type, "curated_restatement")
                    self.assertEqual(problem.description_verified_at.date().isoformat(), "2026-10-18")
                    self.assertIsNone(problem.time_limit_ms)
                    self.assertIsNone(problem.memory_limit_mb)
                    self.assertEqual(problem.time_complexity_instruction, source["timeComplexityInstruction"])
                    self.assertEqual(problem.space_complexity_instruction, source["spaceComplexityInstruction"])
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
            self.assertEqual(context["problem"]["description"], CURATED_PROBLEM_SPECS["two-sum"]["description"])
            self.assertEqual(context["problem"]["leetcodeNumber"], 1)
            self.assertIsNone(context["problem"]["timeLimitMs"])
            self.assertEqual(context["problem"]["descriptionSourceType"], "curated_restatement")
            self.assertEqual(context["problem"]["descriptionVerifiedAt"], "2026-10-18T05:45:28+00:00")
            hint_context = find_hint_problem_context(session, "two-sum")
            self.assertNotIn("submissionTemplate", hint_context["problem"])
            self.assertEqual({key: value for key, value in context["problem"].items()
                              if key != "submissionTemplate"}, hint_context["problem"])
            alternative = find_problem_context(session, "two-sum", "brute-force", "python")
            self.assertEqual({key: value for key, value in alternative["problem"].items()
                              if key != "submissionTemplate"}, hint_context["problem"])
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
        inspector = inspect(self.engine)
        self.assertNotIn("description", {column["name"] for column in inspector.get_columns("problems")})
        self.migrate("upgrade", "0003")
        with Session(self.engine) as session, session.begin():
            seed_data(session)
        inspector = inspect(self.engine)
        self.assertIn("problem_submission_templates", inspector.get_table_names())
        self.assertIn("title", {column["name"] for column in inspector.get_columns("problems")})
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(Problem).where(Problem.slug == "two-sum")).title, "Two Sum")

    def test_0003_migrates_existing_rows_and_reseed_preserves_ids(self):
        with Session(self.engine) as session, session.begin():
            session.add(Problem(slug="unrelated-local", title="Local", difficulty="Easy", summary="Local summary"))
        with Session(self.engine) as session:
            old_ids = {problem.slug: problem.id for problem in session.scalars(select(Problem))}
        self.migrate("downgrade", "0002")
        inspector = inspect(self.engine)
        self.assertNotIn("description", {column["name"] for column in inspector.get_columns("problems")})
        self.migrate("upgrade", "0003")
        with Session(self.engine) as session:
            untouched = session.scalar(select(Problem).where(Problem.slug == "unrelated-local"))
            self.assertEqual(untouched.id, old_ids["unrelated-local"])
            self.assertIsNone(untouched.description)
        with Session(self.engine) as session, session.begin():
            seed_data(session)
        with Session(self.engine) as session:
            current = {problem.slug: problem for problem in session.scalars(select(Problem))}
            self.assertEqual({slug: problem.id for slug, problem in current.items()}, old_ids)
            self.assertEqual(current["two-sum"].description, CURATED_PROBLEM_SPECS["two-sum"]["description"])
            self.assertIsNone(current["unrelated-local"].description)


if __name__ == "__main__":
    unittest.main()
