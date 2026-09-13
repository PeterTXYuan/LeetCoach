"""Regression checks for the actual Python snippets served to learners."""
import runpy
import unittest
from pathlib import Path


SOLUTIONS = runpy.run_path(
    str(Path(__file__).resolve().parents[1] / "app/services/solution_service.py")
)["MOCK_SOLUTIONS"]


class MockSolutionTests(unittest.TestCase):
    def test_all_python_examples_compile(self):
        for key, solution in SOLUTIONS.items():
            with self.subTest(approach=key):
                compile(solution["code"]["python"], str(key), "exec")

    def test_pair_removal_handles_valid_and_invalid_nesting(self):
        namespace = {}
        exec(SOLUTIONS[("valid-parentheses", "replace-pairs")]["code"]["python"], namespace)
        solver = namespace["Solution"]()
        for text, expected in [
            ("", True), ("()[]{}", True), ("{[()]}", True),
            ("([)]", False), ("(]", False), ("((", False), ("]", False)
        ]:
            with self.subTest(text=text):
                self.assertEqual(solver.isValid(text), expected)


if __name__ == "__main__":
    unittest.main()
