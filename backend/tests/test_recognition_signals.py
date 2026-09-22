import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.main import app, PROBLEM_ANALYSES


class RecognitionSignalTests(unittest.TestCase):
    def test_every_seeded_approach_serves_its_own_structured_signals(self):
        count = 0
        with TestClient(app) as client:
            for slug, problem in PROBLEM_ANALYSES.items():
                with self.subTest(slug=slug):
                    response = client.get(f"/api/problems/{slug}")
                    self.assertEqual(response.status_code, 200)
                    served = {approach["id"]: approach for approach in response.json()["approaches"]}
                    distinct_bullets = set()
                    for approach in problem["approaches"]:
                        count += 1
                        signals = served[approach["id"]]["recognitionSignals"]
                        self.assertEqual(signals, approach["recognitionSignals"])
                        self.assertIsInstance(signals["bullets"], list)
                        self.assertIn(len(signals["bullets"]), (2, 3))
                        for bullet in signals["bullets"]:
                            self.assertIsInstance(bullet, str)
                            self.assertTrue(bullet.strip())
                        self.assertIsInstance(signals["quote"], str)
                        self.assertTrue(signals["quote"].strip())
                        distinct_bullets.add(tuple(signals["bullets"]))
                        self.assertNotIn("hints", served[approach["id"]])
                    self.assertEqual(len(distinct_bullets), len(problem["approaches"]))
        self.assertEqual(count, 7)


if __name__ == "__main__":
    unittest.main()
