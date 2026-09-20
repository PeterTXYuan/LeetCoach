import ast
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient
from app.main import app, PROBLEM_ANALYSES
from app.services.starter_code_service import STARTER_BODIES, SUPPORTED_LANGUAGES
from app.services.solution_service import MOCK_SOLUTIONS


class StarterCodeTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        self.client.close()

    def request(self, slug="two-sum", approach="hash-map", language="python", level=1):
        return self.client.post(
            f"/api/problems/{slug}/approaches/{approach}/starter-code",
            json={"language": language, "level": level},
        )

    def test_complete_canonical_coverage_and_progression(self):
        keys = {(slug, a["id"]) for slug, p in PROBLEM_ANALYSES.items() for a in p["approaches"]}
        self.assertEqual(set(STARTER_BODIES), keys)
        self.assertEqual(SUPPORTED_LANGUAGES, {"python", "java", "javascript", "cpp"})
        for slug, approach in sorted(keys):
            for language in sorted(SUPPORTED_LANGUAGES):
                codes = []
                for level in (1, 2, 3):
                    with self.subTest(slug=slug, approach=approach, language=language, level=level):
                        response = self.request(slug, approach, language, level)
                        self.assertEqual(response.status_code, 200)
                        data = response.json()
                        self.assertEqual((data["slug"], data["approachId"], data["language"], data["level"]),
                                         (slug, approach, language, level))
                        self.assertFalse(data["isAiGenerated"])
                        self.assertIn("TODO", data["code"])
                        self.assertNotEqual(data["code"], MOCK_SOLUTIONS[(slug, approach)]["code"][language])
                        codes.append(data["code"])
                self.assertEqual(len(set(codes)), 3)
                self.assertLess(len(codes[0]), len(codes[1]))
                self.assertLess(len(codes[1]), len(codes[2]))

    def test_python_templates_parse_and_remain_unfinished(self):
        samples = {
            "two-sum": ([2, 7, 11, 15], 9),
            "valid-parentheses": ("([)]",),
            "longest-substring-without-repeating-characters": ("abba",),
        }
        methods = {"two-sum": "twoSum", "valid-parentheses": "isValid",
                   "longest-substring-without-repeating-characters": "lengthOfLongestSubstring"}
        for slug, approach in STARTER_BODIES:
            for level in (1, 2, 3):
                with self.subTest(slug=slug, approach=approach, level=level):
                    code = self.request(slug, approach, level=level).json()["code"]
                    tree = ast.parse(code)
                    loops = [n for n in ast.walk(tree) if isinstance(n, (ast.For, ast.While))]
                    self.assertEqual(bool(loops), level == 3)
                    namespace = {}
                    exec(compile(tree, "starter", "exec"), namespace)
                    with self.assertRaises(NotImplementedError):
                        getattr(namespace["Solution"](), methods[slug])(*samples[slug])

    def test_java_hash_map_has_structure_but_no_lookup_or_insertion(self):
        minimal = self.request(language="java", level=1).json()["code"]
        guided = self.request(language="java", level=2).json()["code"]
        strong = self.request(language="java", level=3).json()["code"]
        self.assertIn("public int[] twoSum(int[] nums, int target)", minimal)
        self.assertNotIn("HashMap", minimal)
        self.assertIn("Map<Integer, Integer> seen = new HashMap<>();", guided)
        self.assertNotIn("for (", guided)
        self.assertIn("for (int i = 0; i < nums.length; i++)", strong)
        self.assertIn("int complement = target - nums[i];", strong)
        self.assertNotIn("seen.put(", strong)
        self.assertNotIn("seen.containsKey(", strong)
        brute = self.request(approach="brute-force", language="java", level=3).json()["code"]
        self.assertIn("for (int j = i + 1; j < n; j++)", brute)
        self.assertNotIn("HashMap", brute)

    def test_problem_and_approach_membership_validation(self):
        for slug, approach in [("missing", "hash-map"), ("two-sum", "missing"), ("two-sum", "stack")]:
            with self.subTest(slug=slug, approach=approach):
                self.assertEqual(self.request(slug, approach).status_code, 404)

    def test_language_validation(self):
        self.assertEqual(self.request(language="ruby").status_code, 400)
        self.assertEqual(self.request(language="JAVA").json()["language"], "java")

    def test_level_is_required_and_strictly_one_two_or_three(self):
        for level in [0, 4, -1, "2", 2.0, 1.5, True, False, None, [], {}]:
            with self.subTest(level=level):
                self.assertEqual(self.request(level=level).status_code, 422)
        endpoint = "/api/problems/two-sum/approaches/hash-map/starter-code"
        for body in [{}, {"language": "java"}, {"level": 2}, {"language": None, "level": 1}]:
            with self.subTest(body=body):
                self.assertEqual(self.client.post(endpoint, json=body).status_code, 422)


if __name__ == "__main__":
    unittest.main()
