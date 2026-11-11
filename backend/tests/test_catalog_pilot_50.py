"""Reviewed JSON pilots against temporary migrated databases; providers are mocked."""
import json
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from test_catalog_import import legacy_snapshot, row_values

from app.catalog_import import apply_catalog, load_catalog, plan_catalog
from app.models import Problem, ProblemSubmissionTemplate
from app.services.problem_repository import find_problem_context


PILOT_DIR = Path(__file__).resolve().parents[1] / "catalog" / "problems"
STAGED_60_DIR = PILOT_DIR.parent / "staged_60"
NEW_60_SLUGS = {
    "add-two-numbers", "asteroid-collision", "jump-game",
    "lowest-common-ancestor-of-a-binary-search-tree", "lru-cache",
    "minimum-size-subarray-sum", "set-matrix-zeroes", "symmetric-tree",
    "trapping-rain-water", "word-search",
}


def subset(batch, slugs):
    return {section: {slug: data for slug, data in values.items() if slug in slugs}
            for section, values in batch.items()}


def catalog_snapshot(engine):
    """Capture every Problem and owned child row, including stable DB IDs."""
    with Session(engine) as session:
        return {problem.slug: (
            row_values(problem),
            tuple(row_values(item) for item in problem.constraints),
            tuple(row_values(item) for item in problem.examples),
            tuple(row_values(item) for item in problem.submission_templates),
            tuple((row_values(approach),
                   row_values(approach.recognition_signals) if approach.recognition_signals else None,
                   tuple(row_values(item) for item in approach.recognition_signals.bullets)
                   if approach.recognition_signals else ()) for approach in problem.approaches),
            tuple(row_values(item) for item in problem.related_problems),
        ) for problem in session.scalars(select(Problem).order_by(Problem.slug))}


class CatalogPilot50Tests(DatabaseTestCase):
    def test_reviewed_pilot_import_reimport_and_policy9_context(self):
        all_records = load_catalog(PILOT_DIR)
        self.assertEqual(len(all_records["problems"]), 20)
        batch = subset(all_records, set(all_records["problems"]) - NEW_60_SLUGS)
        self.assertEqual(len(batch["problems"]), 10)
        before = legacy_snapshot(self.engine)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Problem)), 40)
            self.assertEqual(len(plan_catalog(session, batch)["create"]), 10)

        first = apply_catalog(batch, self.engine)
        self.assertEqual(len(first["create"]), 10)
        self.assertEqual(first["update"], [])
        self.assertEqual(legacy_snapshot(self.engine), before)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(Problem)), 50)
            imported = session.scalars(select(Problem).where(Problem.slug.in_(batch["problems"]))).all()
            first_ids = {problem.slug: problem.id for problem in imported}
            self.assertEqual(len(first_ids), 10)
            self.assertEqual(sum(len(problem.approaches) for problem in imported), 12)
            self.assertTrue(all(sum(approach.is_primary for approach in problem.approaches) == 1
                                for problem in imported))
            self.assertEqual(session.scalar(select(func.count()).select_from(ProblemSubmissionTemplate)), 200)
            self.assertEqual(session.execute(text("PRAGMA foreign_key_check")).all(), [])
            for problem in imported:
                primary = next(approach for approach in problem.approaches if approach.is_primary)
                for language in ("python", "java", "javascript", "cpp"):
                    context = find_problem_context(session, problem.slug, primary.approach_key, language)
                    self.assertEqual(context["problem"]["submissionTemplate"]["language"], language)
                    self.assertEqual(context["problem"]["leetcodeNumber"],
                                     batch["specs"][problem.slug]["leetcodeNumber"])
                    self.assertEqual(context["approach"]["id"], primary.approach_key)

        second = apply_catalog(batch, self.engine)
        self.assertEqual(len(second["unchanged"]), 10)
        self.assertEqual(second["create"], [])
        self.assertEqual(second["update"], [])
        with Session(self.engine) as session:
            self.assertEqual({problem.slug: problem.id for problem in session.scalars(
                select(Problem).where(Problem.slug.in_(batch["problems"])))}, first_ids)
            self.assertEqual(session.scalar(select(func.count()).select_from(Problem)), 50)
            self.assertEqual(session.execute(text("PRAGMA foreign_key_check")).all(), [])
        self.assertEqual(legacy_snapshot(self.engine), before)

        # Exercise the public DB-backed routes and a Policy 9 route with a fake provider.
        analysis = self.client.get("/api/problems/subsets")
        self.assertEqual(analysis.status_code, 200, analysis.text)
        self.assertEqual([item["id"] for item in analysis.json()["approaches"]],
                         ["backtracking", "iterative-expansion"])
        related = self.client.get("/api/problems/subsets/related")
        self.assertEqual(related.status_code, 200, related.text)
        self.assertEqual(related.json()["similar"][0]["slug"], "combination-sum")
        hints = self.client.get("/api/problems/subsets/approaches/backtracking/hints")
        self.assertEqual(hints.status_code, 200, hints.text)

        captured = []

        class FakeProvider:
            is_ai_generated = True

            def generate_guidance_bundle(self, context, language):
                captured.append((context, language))
                return {"output": {"level1": "L1", "level2": "L2", "level3": "L3",
                                   "solution": {"code": "full"}},
                        "usage": {"promptTokens": 1, "completionTokens": 1,
                                  "totalTokens": 2, "latencyMs": 1,
                                  "outputChars": 8, "finishReason": "stop"}}

        with patch("app.main.get_llm_provider", return_value=FakeProvider()), patch(
            "app.main.validate_linked_bundle",
            side_effect=lambda output, context, language: {**output, "warnings": []}
        ), patch("app.main.check_linked_correctness",
                 return_value={"status": "NOT_RUN", "summary": "No fixture in this integration test"}):
            response = self.client.post(
                "/api/problems/move-zeroes/approaches/write-pointer/guidance",
                json={"language": "python"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["policyVersion"], 9)
        self.assertEqual(response.json()["kind"], "linked")
        self.assertEqual(len(captured), 1)
        self.assertEqual(captured[0][1], "python")
        self.assertEqual(captured[0][0]["problem"]["slug"], "move-zeroes")
        self.assertEqual(captured[0][0]["approach"]["id"], "write-pointer")
        self.assertIn("def moveZeroes", captured[0][0]["problem"]["submissionTemplate"]["code"])

    def test_approved_second_pilot_preserves_first_50_and_reimports_cleanly(self):
        all_records = load_catalog(PILOT_DIR)
        self.assertEqual(len(all_records["problems"]), 20)
        first_50 = subset(all_records, set(all_records["problems"]) - NEW_60_SLUGS)
        next_10 = subset(all_records, NEW_60_SLUGS)
        self.assertEqual(len(first_50["problems"]), len(next_10["problems"]))
        for slug in NEW_60_SLUGS:
            approved = json.loads((PILOT_DIR / f"{slug}.json").read_text(encoding="utf-8"))
            staged = json.loads((STAGED_60_DIR / f"{slug}.json").read_text(encoding="utf-8"))
            self.assertTrue(approved["provenance"]["reviewed"])
            self.assertFalse(staged["provenance"]["reviewed"])
            self.assertEqual({key: approved[key] for key in ("slug", "spec", "approaches", "related")},
                             {key: staged[key] for key in ("slug", "spec", "approaches", "related")})

        apply_catalog(first_50, self.engine)
        original_50 = catalog_snapshot(self.engine)
        self.assertEqual(len(original_50), 50)
        with Session(self.engine) as session:
            self.assertEqual(len(plan_catalog(session, next_10)["create"]), 10)
        first = apply_catalog(next_10, self.engine)
        self.assertEqual(len(first["create"]), 10)
        all_60 = catalog_snapshot(self.engine)
        self.assertEqual(len(all_60), 60)
        self.assertEqual({slug: all_60[slug] for slug in original_50}, original_50)
        with Session(self.engine) as session:
            self.assertEqual(session.scalar(select(func.count()).select_from(ProblemSubmissionTemplate)), 240)
            self.assertEqual(session.execute(text("PRAGMA foreign_key_check")).all(), [])
            for slug in NEW_60_SLUGS:
                problem = session.scalar(select(Problem).where(Problem.slug == slug))
                primary = [approach for approach in problem.approaches if approach.is_primary]
                self.assertEqual(len(primary), 1)
                for language in ("python", "java", "javascript", "cpp"):
                    context = find_problem_context(session, slug, primary[0].approach_key, language)
                    self.assertEqual(context["problem"]["submissionTemplate"]["language"], language)
                    self.assertEqual(context["approach"]["id"], primary[0].approach_key)

        second = apply_catalog(next_10, self.engine)
        self.assertEqual(len(second["unchanged"]), 10)
        self.assertEqual(second["create"], [])
        self.assertEqual(second["update"], [])
        self.assertEqual(catalog_snapshot(self.engine), all_60)
        for slug in NEW_60_SLUGS:
            analysis = self.client.get(f"/api/problems/{slug}")
            self.assertEqual(analysis.status_code, 200, analysis.text)
            self.assertEqual(analysis.json()["slug"], slug)
            self.assertEqual(self.client.get(f"/api/problems/{slug}/related").status_code, 200)

        captured = []

        class FakeProvider:
            is_ai_generated = True

            def generate_guidance_bundle(self, context, language):
                captured.append((context, language))
                return {"output": {"level1": "L1", "level2": "L2", "level3": "L3",
                                   "solution": {"code": "full"}},
                        "usage": {"promptTokens": 1, "completionTokens": 1,
                                  "totalTokens": 2, "latencyMs": 1,
                                  "outputChars": 8, "finishReason": "stop"}}

        with patch("app.main.get_llm_provider", return_value=FakeProvider()), patch(
            "app.main.validate_linked_bundle",
            side_effect=lambda output, context, language: {**output, "warnings": []}
        ), patch("app.main.check_linked_correctness",
                 return_value={"status": "NOT_RUN", "summary": "No fixture in this integration test"}):
            response = self.client.post(
                "/api/problems/lru-cache/approaches/hash-map-doubly-linked-list/guidance",
                json={"language": "javascript"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["policyVersion"], 9)
        self.assertEqual(len(captured), 1)
        self.assertIn("LRUCache.prototype.get", captured[0][0]["problem"]["submissionTemplate"]["code"])
