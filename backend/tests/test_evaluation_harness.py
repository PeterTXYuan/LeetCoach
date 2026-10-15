"""Evaluation matrix, no-live guard, reporting, and independent fixture checks."""
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from evaluation.cases import CASES, validate_matrix
from evaluation.correctness import execute_solution, probe_sandbox
from evaluation.reporting import write_reports
from evaluation.run_evaluation import _empty_record, run


class EvaluationHarnessTests(DatabaseTestCase):
    def test_fixed_matrix_matches_seeded_sqlite_and_budget(self):
        self.assertEqual(len(CASES), 31)
        self.assertEqual([sum(case.feature == feature for case in CASES)
                          for feature in ("hints", "starter", "solution")], [10, 9, 12])
        with Session(self.engine) as session:
            self.assertEqual(validate_matrix(session), [])
            changed = list(CASES)
            changed[0] = changed[0].__class__("hints", "two-sum", "made-up-approach")
            self.assertIn("canonical approach absent", validate_matrix(session, changed)[0])

    def test_default_and_explicit_dry_run_never_open_generation_client(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary)
            with patch("evaluation.run_evaluation.validate_matrix", return_value=[]), \
                 patch("evaluation.run_evaluation.probe_sandbox", return_value=(False, "unavailable")), \
                 patch("evaluation.run_evaluation.TestClient") as client:
                self.assertEqual(run(["--output-dir", str(output)]), 0)
                client.assert_not_called()
                self.assertEqual(run(["--dry-run", "--output-dir", str(output)]), 0)
                client.assert_not_called()
            data = json.loads((output / "mvp_evaluation.json").read_text(encoding="utf-8"))
            self.assertEqual(data["metrics"]["real_generation_requests"], 0)
            self.assertEqual(data["recommendation"], "INCONCLUSIVE")
            self.assertEqual(len(data["records"]), 31)

    def test_report_generation_with_synthetic_failure_categories(self):
        with tempfile.TemporaryDirectory() as temporary:
            record = _empty_record(CASES[0])
            record.update(request_status="EXECUTED", http_status=200, duration_ms=123,
                          response={"hints": ["Question one?", "Question two?", "Question three?"]},
                          failure_categories=["pedagogical_quality"])
            data = {"run_id": "synthetic", "timestamp_utc": "2026-10-14T00:00:00+00:00",
                    "git_commit": None, "mode": "live", "model": "test-model",
                    "config": {"pace_seconds": 0, "max_calls": 1}, "records": [record]}
            json_path, md_path = write_reports(data, Path(temporary))
            parsed = json.loads(json_path.read_text(encoding="utf-8"))
            report = md_path.read_text(encoding="utf-8")
            self.assertEqual(parsed["metrics"]["failure_categories"], {"pedagogical_quality": 1})
            self.assertIn("Question one?", report)
            self.assertIn("MVP readiness recommendation", report)

    def test_live_flag_with_missing_key_blocks_before_generation(self):
        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {"GROQ_API_KEY": "", "LEETCOACH_LLM_MODEL": "test-model"}), \
                 patch("evaluation.run_evaluation.validate_matrix", return_value=[]), \
                 patch("evaluation.run_evaluation.probe_sandbox", return_value=(False, "unavailable")), \
                 patch("evaluation.run_evaluation.TestClient") as client:
                result = run(["--live", "--max-calls", "1", "--output-dir", temporary])
                self.assertEqual(result, 2)
                client.assert_not_called()
            data = json.loads((Path(temporary) / "mvp_evaluation.json").read_text(encoding="utf-8"))
            self.assertEqual(data["metrics"]["real_generation_requests"], 0)
            self.assertEqual(data["records"][0]["request_status"], "BLOCKED")

    def test_live_call_cap_is_enforced_with_a_fake_api_client(self):
        calls = []

        class FakeClient:
            def __init__(self, _app):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def get(self, path):
                calls.append(path)
                return SimpleNamespace(status_code=200, json=lambda: {
                    "slug": "two-sum", "approachId": "brute-force",
                    "hints": ["What makes a pair valid?", "Which numbers might work together?",
                              "Could you test another possible pair?"]
                })

        with tempfile.TemporaryDirectory() as temporary:
            with patch.dict(os.environ, {"GROQ_API_KEY": "test-only", "LEETCOACH_LLM_MODEL": "test-model"}), \
                 patch("evaluation.run_evaluation.validate_matrix", return_value=[]), \
                 patch("evaluation.run_evaluation.probe_sandbox", return_value=(False, "unavailable")), \
                 patch("evaluation.run_evaluation.TestClient", FakeClient):
                self.assertEqual(run(["--live", "--feature", "hints", "--max-calls", "1",
                                      "--pace-seconds", "0", "--output-dir", temporary]), 0)
            data = json.loads((Path(temporary) / "mvp_evaluation.json").read_text(encoding="utf-8"))
            self.assertEqual(len(calls), 1)
            self.assertEqual(data["metrics"]["real_generation_requests"], 1)
            self.assertEqual(data["metrics"]["request_status"]["NOT_RUN"], 9)
            with patch.dict(os.environ, {"GROQ_API_KEY": "test-only", "LEETCOACH_LLM_MODEL": "test-model"}), \
                 patch("evaluation.run_evaluation.validate_matrix", return_value=[]), \
                 patch("evaluation.run_evaluation.probe_sandbox", return_value=(False, "unavailable")), \
                 patch("evaluation.run_evaluation.TestClient", FakeClient):
                self.assertEqual(run(["--live", "--feature", "hints", "--max-calls", "2",
                                      "--pace-seconds", "0", "--resume-json",
                                      str(Path(temporary) / "mvp_evaluation.json")]), 0)
            resumed = json.loads((Path(temporary) / "mvp_evaluation.json").read_text(encoding="utf-8"))
            self.assertEqual(len(calls), 2)
            self.assertEqual(resumed["metrics"]["real_generation_requests"], 2)

    def test_independent_python_oracle_isolated_when_sandbox_available(self):
        ready, _ = probe_sandbox()
        if not ready:
            self.skipTest("WSL bubblewrap is unavailable on this test host")
        correct = """class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for index, value in enumerate(nums):
            if target - value in seen:
                return [seen[target - value], index]
            seen[value] = index
        return []
"""
        incorrect = """class Solution:
    def twoSum(self, nums, target):
        return [0, 0]
"""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self.assertEqual(execute_solution("two-sum", "python", correct, root, ready)["status"], "PASS")
            failed = execute_solution("two-sum", "python", incorrect, root, ready)
            self.assertEqual(failed["status"], "FAIL")
            self.assertEqual(len(failed["cases"]), 4)


if __name__ == "__main__":
    unittest.main()
