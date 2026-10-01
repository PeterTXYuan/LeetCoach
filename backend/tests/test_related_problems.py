import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.main import app, PROBLEM_ANALYSES
from app.services.related_problem_service import RELATED_PROBLEMS
from db_test_support import DatabaseTestCase


class RelatedProblemTests(DatabaseTestCase):
    def test_all_seeded_problems_have_valid_grouped_related_problems(self):
        self.assertEqual(set(RELATED_PROBLEMS), set(PROBLEM_ANALYSES))
        with TestClient(app) as client:
            for slug in PROBLEM_ANALYSES:
                with self.subTest(slug=slug):
                    response = client.get(f"/api/problems/{slug}/related")
                    self.assertEqual(response.status_code, 200)
                    data = response.json()
                    self.assertEqual(data["slug"], slug)
                    self.assertEqual(set(data), {"slug", "easier", "similar", "harder"})
                    seen = {slug}
                    for group in ("easier", "similar", "harder"):
                        self.assertIsInstance(data[group], list)
                        self.assertTrue(data[group])
                        for problem in data[group]:
                            self.assertRegex(problem["slug"], r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
                            self.assertNotIn(problem["slug"], seen)
                            seen.add(problem["slug"])
                            self.assertTrue(problem["title"].strip())
                            self.assertIn(problem["difficulty"], {"Easy", "Medium", "Hard"})
                            if "reason" in problem:
                                self.assertIsInstance(problem["reason"], str)

    def test_unknown_problem_returns_404(self):
        with TestClient(app) as client:
            self.assertEqual(client.get("/api/problems/not-seeded/related").status_code, 404)


if __name__ == "__main__":
    unittest.main()
