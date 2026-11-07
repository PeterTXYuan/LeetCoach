"""Synthetic-only importer tests; no new real catalog entries or provider calls."""
import io
import json
import tempfile
from contextlib import redirect_stdout
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app import catalog_import
from app.models import Problem
from app.seed import seed_data
from app.services.problem_repository import find_problem_context
from app.stable_data import CURATED_PROBLEMS


REVIEWED_AT = "2026-11-07T00:00:00+00:00"


def synthetic_record(slug: str, number: int, kind: str = "array") -> dict:
    if kind == "tree":
        templates = {
            "python": "class Solution:\n    def inspectTree(self, root: TreeNode | None) -> int:\n        pass",
            "java": "class Solution { public int inspectTree(TreeNode root) { } }",
            "javascript": "var inspectTree = function(root) { };",
            "cpp": "class Solution { public: int inspectTree(TreeNode* root) { } };",
        }
    elif kind == "design":
        templates = {
            "python": "class SampleBox:\n    def __init__(self):\n        pass\n    def read(self) -> int:\n        pass",
            "java": "class SampleBox { public SampleBox() { } public int read() { } }",
            "javascript": "var SampleBox = function() { }; SampleBox.prototype.read = function() { };",
            "cpp": "class SampleBox { public: SampleBox() { } int read() { } };",
        }
    else:
        templates = {
            "python": "class Solution:\n    def inspectArray(self, nums: list[int]) -> int:\n        pass",
            "java": "class Solution { public int inspectArray(int[] nums) { } }",
            "javascript": "var inspectArray = function(nums) { };",
            "cpp": "class Solution { public: int inspectArray(vector<int>& nums) { } };",
        }
    url = f"https://leetcode.com/problems/{slug}/"
    return {
        "slug": slug,
        "spec": {
            "title": f"Synthetic {kind.title()} Check", "difficulty": "Easy",
            "summary": "A synthetic fixture used only to test catalog import.",
            "leetcodeNumber": number,
            "description": "Given a small synthetic input, return its designated test result.",
            "descriptionSourceUrl": url, "descriptionSourceType": "curated_restatement",
            "descriptionVerifiedAt": REVIEWED_AT,
            "timeLimitMs": None, "memoryLimitMb": None,
            "timeComplexityInstruction": None, "spaceComplexityInstruction": None,
            "constraints": ["The synthetic input is nonempty."],
            "examples": [{"input": "sample = [1]", "output": "1", "explanation": "Synthetic example."}],
            "submissionTemplates": templates,
        },
        "approaches": [{
            "id": "direct-check", "name": "Direct Check", "pattern": "Synthetic Pattern",
            "summary": "Inspect the synthetic input directly.", "isPrimary": True, "displayOrder": 1,
            "thinkingSteps": ["Read the input.", "Compute the designated result."],
            "recognitionSignals": {"quote": None, "bullets": [
                "The result depends on the supplied input.", "A direct check is enough for this fixture."
            ]},
        }],
        "related": {"easier": [], "similar": [{
            "slug": "two-sum", "title": "Two Sum", "difficulty": "Easy",
            "reason": "An existing supported problem used to test related-card identity."
        }], "harder": []},
        "provenance": {
            "reviewed": True, "reviewedBy": "Synthetic test editor", "reviewedAt": REVIEWED_AT,
            "sourceUrl": url, "collectionMethod": "manual_review",
            "reuseBasis": "original_editorial",
            "permissionNote": "Synthetic fixture text authored for importer tests only."
        },
    }


def write_record(directory: Path, record: dict) -> None:
    (directory / f"{record['slug']}.json").write_text(json.dumps(record), encoding="utf-8")


def row_values(item):
    return tuple((column.key, getattr(item, column.key)) for column in inspect(item).mapper.column_attrs)


def legacy_snapshot(engine):
    """Compare every original Problem row and all owned children, IDs and content."""
    with Session(engine) as session:
        problems = session.scalars(select(Problem).where(Problem.slug.in_(CURATED_PROBLEMS))).all()
        result = {}
        for problem in problems:
            result[problem.slug] = (
                row_values(problem),
                tuple(row_values(item) for item in problem.constraints),
                tuple(row_values(item) for item in problem.examples),
                tuple(row_values(item) for item in problem.submission_templates),
                tuple((row_values(approach),
                       row_values(approach.recognition_signals) if approach.recognition_signals else None,
                       tuple(row_values(item) for item in approach.recognition_signals.bullets)
                       if approach.recognition_signals else ()) for approach in problem.approaches),
                tuple(row_values(item) for item in problem.related_problems),
            )
        return result


class CatalogImporterTests(DatabaseTestCase):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.input_dir = Path(temporary.name)
        self.fixtures = [
            synthetic_record("synthetic-array-check", 900001),
            synthetic_record("synthetic-tree-check", 900002, "tree"),
            synthetic_record("synthetic-design-check", 900003, "design"),
        ]

    def write(self, count=3):
        for record in self.fixtures[:count]:
            write_record(self.input_dir, record)

    def test_three_synthetic_fixtures_validate_and_cli_validate_does_not_write(self):
        before = legacy_snapshot(self.engine)
        self.write()
        batch = catalog_import.load_catalog(self.input_dir)
        self.assertEqual(set(batch["problems"]), {item["slug"] for item in self.fixtures})
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(catalog_import.main(["validate", "--input-dir", str(self.input_dir)]), 0)
        self.assertIn("Validated 3 reviewed", output.getvalue())
        self.assertEqual(legacy_snapshot(self.engine), before)
        with Session(self.engine) as session:
            self.assertIsNone(session.scalar(select(Problem).where(Problem.slug == self.fixtures[0]["slug"])))

    def test_cli_plan_and_apply_use_the_configured_database(self):
        self.write(2)
        arguments = ["--input-dir", str(self.input_dir)]
        with patch.object(catalog_import, "engine", self.engine):
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(catalog_import.main(["plan", *arguments]), 0)
            self.assertEqual(json.loads(output.getvalue())["create"],
                             sorted(item["slug"] for item in self.fixtures[:2]))
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(catalog_import.main(["apply", *arguments]), 0)
            self.assertEqual(len(json.loads(output.getvalue())["create"]), 2)
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(catalog_import.main(["plan", *arguments]), 0)
            self.assertEqual(len(json.loads(output.getvalue())["unchanged"]), 2)

    def test_rejects_unreviewed_invalid_and_duplicate_records(self):
        first, second = deepcopy(self.fixtures[:2])
        first["provenance"]["reviewed"] = False
        write_record(self.input_dir, first)
        with self.assertRaisesRegex(catalog_import.CatalogImportError, "explicitly reviewed"):
            catalog_import.load_catalog(self.input_dir)
        first["provenance"]["reviewed"] = True
        del first["spec"]["submissionTemplates"]["cpp"]
        write_record(self.input_dir, first)
        with self.assertRaisesRegex(catalog_import.CatalogImportError, "four language"):
            catalog_import.load_catalog(self.input_dir)
        first = deepcopy(self.fixtures[0])
        write_record(self.input_dir, first)
        second["spec"]["leetcodeNumber"] = first["spec"]["leetcodeNumber"]
        write_record(self.input_dir, second)
        with self.assertRaisesRegex(catalog_import.CatalogImportError, "repeated LeetCode number"):
            catalog_import.load_catalog(self.input_dir)
        second["spec"]["leetcodeNumber"] = 900002
        second["related"]["similar"][0]["title"] = "Wrong title"
        write_record(self.input_dir, second)
        with self.assertRaisesRegex(catalog_import.CatalogImportError, "disagrees with the supported catalog"):
            catalog_import.load_catalog(self.input_dir)
        self.fixtures[0]["slug"] = "two-sum"
        write_record(self.input_dir, self.fixtures[0])
        with self.assertRaisesRegex(catalog_import.CatalogImportError, "collides"):
            catalog_import.load_catalog(self.input_dir)

    def test_plan_apply_reseed_and_missing_file_preserve_original_40(self):
        self.write()
        baseline = legacy_snapshot(self.engine)
        batch = catalog_import.load_catalog(self.input_dir)
        with Session(self.engine) as session:
            self.assertEqual(catalog_import.plan_catalog(session, batch)["create"],
                             sorted(item["slug"] for item in self.fixtures))
        self.assertEqual(legacy_snapshot(self.engine), baseline)
        self.assertEqual(catalog_import.apply_catalog(batch, self.engine)["create"],
                         sorted(item["slug"] for item in self.fixtures))
        with Session(self.engine) as session:
            imported_ids = {item.slug: item.id for item in session.scalars(
                select(Problem).where(Problem.slug.in_(item["slug"] for item in self.fixtures)))}
            self.assertEqual(catalog_import.plan_catalog(session, batch)["unchanged"],
                             sorted(item["slug"] for item in self.fixtures))
            for language in ("python", "java", "javascript", "cpp"):
                context = find_problem_context(session, self.fixtures[0]["slug"], "direct-check", language)
                self.assertEqual(context["problem"]["submissionTemplate"], {
                    "language": language, "code": self.fixtures[0]["spec"]["submissionTemplates"][language]
                })
                self.assertEqual(context["approach"]["id"], "direct-check")
        self.assertEqual(catalog_import.apply_catalog(batch, self.engine)["unchanged"],
                         sorted(item["slug"] for item in self.fixtures))
        (self.input_dir / f"{self.fixtures[2]['slug']}.json").unlink()
        reduced = catalog_import.load_catalog(self.input_dir)
        self.assertEqual(catalog_import.apply_catalog(reduced, self.engine)["unchanged"],
                         sorted(item["slug"] for item in self.fixtures[:2]))
        with Session(self.engine) as session:
            self.assertEqual({item.slug: item.id for item in session.scalars(
                select(Problem).where(Problem.slug.in_(item["slug"] for item in self.fixtures)))}, imported_ids)
        self.assertEqual(legacy_snapshot(self.engine), baseline)

    def test_failed_import_rolls_back_all_new_rows(self):
        self.write(2)
        baseline = legacy_snapshot(self.engine)
        batch = catalog_import.load_catalog(self.input_dir)

        def fail_after_seed(*args):
            seed_data(*args)
            raise RuntimeError("synthetic failure after flush")

        with patch.object(catalog_import, "seed_data", side_effect=fail_after_seed):
            with self.assertRaisesRegex(RuntimeError, "synthetic failure"):
                catalog_import.apply_catalog(batch, self.engine)
        with Session(self.engine) as session:
            self.assertEqual(set(session.scalars(select(Problem.slug))), set(CURATED_PROBLEMS))
        self.assertEqual(legacy_snapshot(self.engine), baseline)

    def test_reviewed_update_keeps_ids_and_database_number_collision_stops(self):
        self.write(1)
        baseline = legacy_snapshot(self.engine)
        batch = catalog_import.load_catalog(self.input_dir)
        catalog_import.apply_catalog(batch, self.engine)
        with Session(self.engine) as session:
            current = session.scalar(select(Problem).where(Problem.slug == self.fixtures[0]["slug"]))
            retained = (current.id, current.approaches[0].id, current.approaches[0].recognition_signals.id)

        self.fixtures[0]["spec"]["summary"] = "Updated synthetic summary."
        self.fixtures[0]["approaches"][0]["recognitionSignals"]["bullets"][0] = "Updated synthetic cue."
        self.fixtures[0]["related"]["similar"].clear()
        write_record(self.input_dir, self.fixtures[0])
        batch = catalog_import.load_catalog(self.input_dir)
        with Session(self.engine) as session:
            plan = catalog_import.plan_catalog(session, batch)
            self.assertEqual(plan["update"], [self.fixtures[0]["slug"]])
            self.assertEqual(plan["deleteChildren"][self.fixtures[0]["slug"]]["related"], ["two-sum"])
        catalog_import.apply_catalog(batch, self.engine)
        with Session(self.engine) as session:
            current = session.scalar(select(Problem).where(Problem.slug == self.fixtures[0]["slug"]))
            self.assertEqual((current.id, current.approaches[0].id,
                              current.approaches[0].recognition_signals.id), retained)
            self.assertEqual(current.summary, "Updated synthetic summary.")
            self.assertEqual(current.approaches[0].recognition_signals.bullets[0].text,
                             "Updated synthetic cue.")
            self.assertEqual(current.related_problems, [])

        second = deepcopy(self.fixtures[1])
        write_record(self.input_dir, second)
        with Session(self.engine) as session, session.begin():
            session.add(Problem(slug="unrelated-local", leetcode_number=900002,
                                title="Local", difficulty="Easy", summary="Unrelated row."))
        with Session(self.engine) as session:
            with self.assertRaisesRegex(catalog_import.CatalogImportError, "already belongs"):
                catalog_import.plan_catalog(session, catalog_import.load_catalog(self.input_dir))
        self.assertEqual(legacy_snapshot(self.engine), baseline)

    def test_existing_database_slug_with_different_number_is_not_overwritten(self):
        self.write(1)
        with Session(self.engine) as session, session.begin():
            session.add(Problem(slug=self.fixtures[0]["slug"], leetcode_number=900004,
                                title="Local row", difficulty="Easy", summary="Keep this row."))
        with Session(self.engine) as session:
            with self.assertRaisesRegex(catalog_import.CatalogImportError, "different LeetCode number"):
                catalog_import.plan_catalog(session, catalog_import.load_catalog(self.input_dir))
            row = session.scalar(select(Problem).where(Problem.slug == self.fixtures[0]["slug"]))
            self.assertEqual((row.leetcode_number, row.summary), (900004, "Keep this row."))
