"""Independent catalog identity and submission-contract checks for phase 1."""

import ast
import hashlib
import json
from sqlalchemy import select
from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app.models import Problem
from app.seed import seed_data
from app.services.problem_repository import find_problem_context, find_hint_problem_context
from app.stable_data import CURATED_PROBLEMS, CURATED_PROBLEM_SPECS


# Recorded from the pre-expansion catalog. The stable IDs must not change.
ORIGINAL_KEYS = {
    "two-sum": ("brute-force", "hash-map"),
    "contains-duplicate": ("brute-force", "hash-set"),
    "valid-anagram": ("sorting", "frequency-count"),
    "group-anagrams": ("sorted-key", "frequency-signature"),
    "valid-palindrome": ("clean-and-reverse", "two-pointers"),
    "two-sum-ii-input-array-is-sorted": ("binary-search-complement", "two-pointers"),
    "3sum": ("brute-force", "sort-and-two-pointers"),
    "best-time-to-buy-and-sell-stock": ("brute-force", "running-minimum"),
    "longest-substring-without-repeating-characters": (
        "brute-force-substrings", "sliding-window-set", "sliding-window-index-map"),
    "longest-repeating-character-replacement": ("brute-force-windows", "sliding-window-frequency"),
    "valid-parentheses": ("replace-pairs", "stack"),
    "min-stack": ("scan-for-minimum", "paired-minimums"),
    "daily-temperatures": ("forward-scan", "monotonic-stack"),
    "binary-search": ("linear-scan", "binary-search"),
    "search-in-rotated-sorted-array": ("linear-scan", "modified-binary-search"),
    "reverse-linked-list": ("iterative-pointers", "recursive-unwind"),
    "merge-two-sorted-lists": ("iterative-merge", "recursive-merge"),
    "maximum-depth-of-binary-tree": ("depth-first-search", "breadth-first-search"),
    "number-of-islands": ("depth-first-flood-fill", "breadth-first-flood-fill"),
    "climbing-stairs": ("memoized-recursion", "rolling-dynamic-programming"),
}


# Four-language entry points independently transcribed from official snippets.
NEW_ENTRY_POINTS = {
    "product-of-array-except-self": ("productExceptSelf", 2),
    "top-k-frequent-elements": ("topKFrequent", 3),
    "longest-consecutive-sequence": ("longestConsecutive", 2),
    "valid-sudoku": ("isValidSudoku", 2),
    "container-with-most-water": ("maxArea", 2),
    "evaluate-reverse-polish-notation": ("evalRPN", 2),
    "generate-parentheses": ("generateParenthesis", 2),
    "car-fleet": ("carFleet", 4),
    "find-minimum-in-rotated-sorted-array": ("findMin", 2),
    "search-a-2d-matrix": ("searchMatrix", 3),
    "koko-eating-bananas": ("minEatingSpeed", 3),
    "time-based-key-value-store": ("TimeMap", 0),
    "permutation-in-string": ("checkInclusion", 3),
    "invert-binary-tree": ("invertTree", 2),
    "same-tree": ("isSameTree", 3),
    "diameter-of-binary-tree": ("diameterOfBinaryTree", 2),
    "balanced-binary-tree": ("isBalanced", 2),
    "rotting-oranges": ("orangesRotting", 2),
    "house-robber": ("rob", 2),
    "coin-change": ("coinChange", 3),
}


# Independently captured from official LeetCode metadata on 2026-10-22 UTC.
# Each digest covers ordered constraints plus every official example's input
# and output; editorial explanations are intentionally not copied verbatim.
OFFICIAL_FACT_DIGESTS = {
    "product-of-array-except-self": "d1526fbb95a02ed9fddf",
    "top-k-frequent-elements": "6a3378dec70463dbe8bd",
    "longest-consecutive-sequence": "ede7c94f1473725936eb",
    "valid-sudoku": "cf7885942d3a873c1b07",
    "container-with-most-water": "22044180e859d8588470",
    "evaluate-reverse-polish-notation": "d1b1981f8e653a40ab14",
    "generate-parentheses": "4a06862744caf53ee5ca",
    "car-fleet": "ec9c5f7399f85f42b8f0",
    "find-minimum-in-rotated-sorted-array": "0cd6b4c2cfbd2eaae9cf",
    "search-a-2d-matrix": "9caba98df75caade76d3",
    "koko-eating-bananas": "76f47f7ad69a27e22638",
    "time-based-key-value-store": "5450cf0b55638e98d9fb",
    "permutation-in-string": "e77612dc0f1d691cf0db",
    "invert-binary-tree": "f6ecb4a35825e37f56a6",
    "same-tree": "77fe1a782045a5bf0d87",
    "diameter-of-binary-tree": "a41e92c7021d33903897",
    "balanced-binary-tree": "a06096d982f6cb5374cb",
    "rotting-oranges": "6dcb70a3543d53eb8a28",
    "house-robber": "00c61b761d9e57795ef7",
    "coin-change": "ccd6adf9f09b365961d1",
}

OFFICIAL_TITLES_AND_DIFFICULTIES = {
    "product-of-array-except-self": ("Product of Array Except Self", "Medium"),
    "top-k-frequent-elements": ("Top K Frequent Elements", "Medium"),
    "longest-consecutive-sequence": ("Longest Consecutive Sequence", "Medium"),
    "valid-sudoku": ("Valid Sudoku", "Medium"),
    "container-with-most-water": ("Container With Most Water", "Medium"),
    "evaluate-reverse-polish-notation": ("Evaluate Reverse Polish Notation", "Medium"),
    "generate-parentheses": ("Generate Parentheses", "Medium"),
    "car-fleet": ("Car Fleet", "Medium"),
    "find-minimum-in-rotated-sorted-array": ("Find Minimum in Rotated Sorted Array", "Medium"),
    "search-a-2d-matrix": ("Search a 2D Matrix", "Medium"),
    "koko-eating-bananas": ("Koko Eating Bananas", "Medium"),
    "time-based-key-value-store": ("Time Based Key-Value Store", "Medium"),
    "permutation-in-string": ("Permutation in String", "Medium"),
    "invert-binary-tree": ("Invert Binary Tree", "Easy"),
    "same-tree": ("Same Tree", "Easy"),
    "diameter-of-binary-tree": ("Diameter of Binary Tree", "Easy"),
    "balanced-binary-tree": ("Balanced Binary Tree", "Easy"),
    "rotting-oranges": ("Rotting Oranges", "Medium"),
    "house-robber": ("House Robber", "Medium"),
    "coin-change": ("Coin Change", "Medium"),
}


class CatalogExpansionTests(DatabaseTestCase):
    def test_official_source_facts_and_identity(self):
        self.assertEqual(set(OFFICIAL_FACT_DIGESTS), set(NEW_ENTRY_POINTS))
        for slug, digest in OFFICIAL_FACT_DIGESTS.items():
            spec = CURATED_PROBLEM_SPECS[slug]
            with self.subTest(slug=slug):
                self.assertEqual((spec["title"], spec["difficulty"]),
                                 OFFICIAL_TITLES_AND_DIFFICULTIES[slug])
                facts = {"constraints": spec["constraints"], "examples": [
                    {"input": item["input"], "output": item["output"]}
                    for item in spec["examples"]
                ]}
                encoded = json.dumps(facts, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()
                self.assertEqual(hashlib.sha256(encoded).hexdigest()[:20], digest)

    def test_original_keys_and_new_forty_problem_seed_remain_stable(self):
        self.assertEqual(set(CURATED_PROBLEMS), set(ORIGINAL_KEYS) | set(NEW_ENTRY_POINTS))
        self.assertEqual(len(CURATED_PROBLEMS), 40)
        self.assertEqual(sum(len(p["approaches"]) for p in CURATED_PROBLEMS.values()), 64)
        for slug, keys in ORIGINAL_KEYS.items():
            self.assertEqual(tuple(a["id"] for a in CURATED_PROBLEMS[slug]["approaches"]), keys)
        with Session(self.engine) as session:
            ids_before = {(p.slug, a.approach_key): (p.id, a.id)
                          for p in session.scalars(select(Problem)) for a in p.approaches}
        with Session(self.engine) as session, session.begin():
            seed_data(session)
        with Session(self.engine) as session:
            ids_after = {(p.slug, a.approach_key): (p.id, a.id)
                         for p in session.scalars(select(Problem)) for a in p.approaches}
        self.assertEqual(ids_after, ids_before)

    def test_new_submission_entry_points_match_official_shape(self):
        for slug, (name, python_arity) in NEW_ENTRY_POINTS.items():
            with self.subTest(slug=slug):
                spec = CURATED_PROBLEM_SPECS[slug]
                templates = spec["submissionTemplates"]
                self.assertEqual(set(templates), {"python", "java", "javascript", "cpp"})
                tree_problem = slug in {"invert-binary-tree", "same-tree",
                                        "diameter-of-binary-tree", "balanced-binary-tree"}
                if slug == "time-based-key-value-store":
                    self.assertIn("class TimeMap", templates["python"])
                    self.assertIn("class TimeMap", templates["java"])
                    self.assertIn("class TimeMap", templates["cpp"])
                    self.assertIn("var TimeMap = function", templates["javascript"])
                    for method in ("__init__", "set", "get"):
                        self.assertIn(f"def {method}(", templates["python"])
                    for method in ("set", "get"):
                        self.assertIn(f"TimeMap.prototype.{method} = function", templates["javascript"])
                else:
                    tree = ast.parse(templates["python"])
                    solution = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "Solution")
                    method = next(n for n in solution.body if isinstance(n, ast.FunctionDef) and n.name == name)
                    self.assertEqual(len(method.args.args), python_arity)
                    self.assertRegex(templates["java"], rf"\b{name}\(")
                    self.assertIn(f"var {name} = function(", templates["javascript"])
                    self.assertRegex(templates["cpp"], rf"\b{name}\(")
                if tree_problem:
                    for language in templates:
                        self.assertIn("TreeNode", templates[language])
                ast.parse(templates["python"])

    def test_new_contexts_and_representative_mock_routes(self):
        for slug in NEW_ENTRY_POINTS:
            primary = next(a["id"] for a in CURATED_PROBLEMS[slug]["approaches"] if a["isPrimary"])
            with Session(self.engine) as session:
                hint_context = find_hint_problem_context(session, slug)
                self.assertIsNotNone(hint_context)
                self.assertNotIn("submissionTemplate", hint_context["problem"])
                self.assertIn(primary, {item["id"] for item in hint_context["approaches"]})
                for language in ("python", "java", "javascript", "cpp"):
                    context = find_problem_context(session, slug, primary, language)
                    self.assertEqual(context["approach"]["id"], primary)
                    self.assertEqual(context["problem"]["submissionTemplate"], {
                        "language": language,
                        "code": CURATED_PROBLEM_SPECS[slug]["submissionTemplates"][language],
                    })
            self.assertEqual(self.client.get(f"/api/problems/{slug}").status_code, 200)
            self.assertEqual(self.client.get(f"/api/problems/{slug}/related").status_code, 200)
        for slug, language in (("product-of-array-except-self", "javascript"),
                               ("time-based-key-value-store", "cpp"),
                               ("invert-binary-tree", "java")):
            primary = next(a["id"] for a in CURATED_PROBLEMS[slug]["approaches"] if a["isPrimary"])
            path = f"/api/problems/{slug}/approaches/{primary}"
            hints = self.client.get(f"{path}/hints")
            self.assertEqual(hints.status_code, 200)
            self.assertEqual(len(hints.json()["hints"]), 3)
            response = self.client.post(f"{path}/guidance", json={"language": language})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["kind"], "starterOnlyMock")

    def test_required_and_optional_complexity_are_distinct(self):
        for slug in ("product-of-array-except-self", "longest-consecutive-sequence",
                     "find-minimum-in-rotated-sorted-array", "search-a-2d-matrix"):
            self.assertIn("Required", CURATED_PROBLEM_SPECS[slug]["timeComplexityInstruction"])
        self.assertIn("Optional follow-up", CURATED_PROBLEM_SPECS[
            "product-of-array-except-self"]["spaceComplexityInstruction"])
        self.assertIn("Optional follow-up", CURATED_PROBLEM_SPECS[
            "top-k-frequent-elements"]["timeComplexityInstruction"])
        for slug in NEW_ENTRY_POINTS:
            spec = CURATED_PROBLEM_SPECS[slug]
            self.assertIsNone(spec["timeLimitMs"])
            self.assertIsNone(spec["memoryLimitMb"])

