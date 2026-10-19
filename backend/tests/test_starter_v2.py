"""Current batch-policy regressions. Every Groq response is an offline fake."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from db_test_support import DatabaseTestCase
from app.llm.base import StarterOutputDiagnostic
from app.llm.groq_provider import GroqLLMProvider, STARTER_SYSTEM_PROMPT
from app.llm.mock_provider import MockLLMProvider
from app.llm.starter_batch import validate_level, validate_starter_batch
from app.llm.starter_syntax import check_syntax
from app.models import Problem
from app.services.problem_repository import find_problem_context
from app.stable_data import CURATED_PROBLEMS
from evaluation.correctness import probe_sandbox
from evaluation.starter_v2 import MATRIX, offline_syntax, parse_args, run


TWO_SUM = {
    "level1": '''from typing import List
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = {}
        # TODO: decide what information belongs in seen.
        raise NotImplementedError("Complete the search")''',
    "level2": '''from typing import List
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = {}
        for index, value in enumerate(nums):
            # TODO: determine which earlier value could form a pair.
            raise NotImplementedError("Complete each search step")
        raise NotImplementedError("Handle the result")''',
    "level3": '''from typing import List
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = {}
        for index, value in enumerate(nums):
            complement = target - value
            if complement in seen:
                # TODO: construct the matching indices.
                raise NotImplementedError("Complete the pair result")
            # TODO: record useful information for later values.
            raise NotImplementedError("Complete the state update")
        raise NotImplementedError("Handle the result")''',
}

REPRESENTATIVE = (
    ("two-sum", "hash-map", "python"),
    ("3sum", "sort-and-two-pointers", "java"),
    ("binary-search", "binary-search", "cpp"),
    ("min-stack", "paired-minimums", "javascript"),
    ("reverse-linked-list", "iterative-pointers", "python"),
    ("reverse-linked-list", "iterative-pointers", "java"),
    ("maximum-depth-of-binary-tree", "depth-first-search", "python"),
    ("number-of-islands", "depth-first-flood-fill", "cpp"),
    ("climbing-stairs", "memoized-recursion", "javascript"),
)


class StarterV2Tests(DatabaseTestCase):
    def context(self, slug="two-sum", approach="hash-map", language="python"):
        with Session(self.engine) as session:
            return find_problem_context(session, slug, approach, language)

    def request(self, slug="two-sum", approach="hash-map", language="python"):
        return self.client.post(f"/api/problems/{slug}/approaches/{approach}/starter-code/batch",
                                json={"language": language})

    def fake_provider(self, raw):
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            if isinstance(raw, Exception): raise raw
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=raw))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        return GroqLLMProvider(api_key="offline", model="openai/gpt-oss-120b", client=client), calls

    def test_one_groq_call_authors_three_levels_from_facts_without_a_deterministic_scaffold(self):
        provider, calls = self.fake_provider(json.dumps(TWO_SUM))
        with patch("app.main.get_llm_provider", return_value=provider), \
             patch("app.llm.groq_provider.trusted_starter", side_effect=AssertionError("legacy path called")), \
             patch.object(MockLLMProvider, "generate_starter_code", side_effect=AssertionError("mock called")):
            response = self.request()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(len(calls), 1)
        data = response.json()
        self.assertEqual((data["policyVersion"], data["isAiGenerated"], data["usedFallback"]), (8, True, False))
        self.assertEqual({key: data[key] for key in TWO_SUM}, TWO_SUM)
        sent = json.loads(calls[0]["messages"][1]["content"])
        context = self.context()
        self.assertEqual(sent["problem"]["description"], context["problem"]["description"])
        self.assertEqual(sent["problem"]["examples"], context["problem"]["examples"])
        self.assertEqual(sent["problem"]["constraints"], context["problem"]["constraints"])
        self.assertEqual(sent["approach"]["id"], "hash-map")
        self.assertEqual(sent["submissionTemplate"], context["problem"]["submissionTemplate"]["code"])
        self.assertNotIn("summary", sent["problem"])
        for unwanted in ("descriptionSourceUrl", "descriptionVerifiedAt", "approaches", "baselineScaffold", "editableSlots", "java"):
            self.assertNotIn(unwanted, json.dumps(sent))
        self.assertEqual(calls[0]["response_format"], {"type": "json_object"})
        self.assertEqual(calls[0]["messages"][0]["content"], STARTER_SYSTEM_PROMPT)

    def test_offline_batch_route_reports_current_policy_without_changing_legacy_policy(self):
        with patch("app.main.get_llm_provider", return_value=MockLLMProvider()):
            response = self.request()
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["policyVersion"], 8)
        self.assertEqual(response.json()["usedFallback"], False)

    def test_rejections_are_atomic_sanitized_and_never_retry_or_mock_fallback(self):
        bad = ["{not json", json.dumps({"level1": TWO_SUM["level1"]}),
               json.dumps({**TWO_SUM, "level2": None}),
               json.dumps({**TWO_SUM, "level3": TWO_SUM["level1"]}), TimeoutError("secret")]
        for raw in bad:
            with self.subTest(raw=str(raw)[:30]):
                provider, calls = self.fake_provider(raw)
                with patch("app.main.get_llm_provider", return_value=provider), \
                     patch.object(MockLLMProvider, "generate_starter_batch", side_effect=AssertionError("fallback called")):
                    response = self.request()
                self.assertIn(response.status_code, (502, 503), response.text)
                self.assertEqual(len(calls), 1)
                self.assertNotIn("level1", response.json())
                self.assertNotIn("secret", response.text)
                self.assertIn("reason", response.json()["detail"])

    def test_missing_verified_description_fails_before_request_and_unknown_approach_is_rejected(self):
        with Session(self.engine) as session, session.begin():
            problem = session.scalar(select(Problem).where(Problem.slug == "two-sum"))
            problem.description = None
        provider, calls = self.fake_provider(json.dumps(TWO_SUM))
        with patch("app.main.get_llm_provider", return_value=provider):
            response = self.request()
            missing = self.request(approach="array-position-one")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["reason"], "MISSING_VERIFIED_DESCRIPTION")
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(calls, [])
        self.assertEqual(self.request(language="ruby").status_code, 400)

    def test_wrong_interfaces_missing_methods_constructor_and_extra_entry_points(self):
        python = self.context()
        mutations = [
            TWO_SUM["level2"].replace("target: int", "target: str"),
            TWO_SUM["level2"].replace("-> List[int]", "-> int"),
            TWO_SUM["level2"].replace("    def twoSum", "    @staticmethod\n    def twoSum"),
            TWO_SUM["level2"] + "\n    def solve(self):\n        return 0",
            TWO_SUM["level2"] + "\n    def __init__(self, required):\n        self.required = required",
        ]
        for code in mutations:
            with self.subTest(code=code), self.assertRaises(StarterOutputDiagnostic):
                validate_starter_batch({**TWO_SUM, "level2": code}, python, "python")
        for language in ("java", "javascript", "cpp"):
            context = self.context("min-stack", "paired-minimums", language)
            batch = MockLLMProvider().generate_starter_batch(context, language)
            for token, replacement in (("getMin", "minimum"), ("MinStack()", "MinStack(int x)")):
                if language == "javascript" and token == "MinStack()":
                    token, replacement = "var MinStack = function()", "var MinStack = function(x)"
                changed = batch["level2"].replace(token, replacement)
                self.assertNotEqual(changed, batch["level2"])
                with self.subTest(language=language, token=token), self.assertRaises(StarterOutputDiagnostic):
                    validate_starter_batch({**batch, "level2": changed}, context, language, check_compilers=False)

    def test_complete_solution_decorative_todo_and_unsafe_loop_are_rejected(self):
        context = self.context()
        complete = '''from typing import List
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        seen = {}
        # TODO: review this answer.
        for index, value in enumerate(nums):
            complement = target - value
            if complement in seen:
                return [seen[complement], index]
            seen[value] = index
        raise NotImplementedError("Unused for valid inputs")'''
        unsafe = TWO_SUM["level2"].replace("for index, value in enumerate(nums):", "while True:").replace(
            'raise NotImplementedError("Complete each search step")', "pass")
        unreachable = TWO_SUM["level1"].replace('raise NotImplementedError("Complete the search")',
                                              'return []\n        raise NotImplementedError("Unreachable")')
        dead_branch = TWO_SUM["level1"].replace('raise NotImplementedError("Complete the search")',
                                              'if False:\n            raise NotImplementedError("Unreachable")\n        return []')
        for code in (complete, unsafe, unreachable, dead_branch):
            with self.subTest(code=code), self.assertRaises(StarterOutputDiagnostic):
                validate_starter_batch({**TWO_SUM, "level2": code}, context, "python")

    def test_captured_live_outputs_preserve_real_rejections_and_fix_false_positives(self):
        # Exact code from the eight real Groq responses; no provider is called.
        cases = json.loads((Path(__file__).parent / "fixtures" / "starter_v2_live_20261018.json")
                           .read_text(encoding="utf-8"))
        expected = {
            ("two-sum", "python"): (("PASS", "SILENT_UNFINISHED_METHOD", "PASS"), "SILENT_UNFINISHED_METHOD"),
            ("3sum", "java"): (("PASS", "MISSING_UNFINISHED_PLACEHOLDER", "UNSAFE_UNFINISHED_LOOP"),
                               "MISSING_UNFINISHED_PLACEHOLDER"),
            ("binary-search", "cpp"): (("PASS", "PASS", "UNREACHABLE_PLACEHOLDER"), "UNREACHABLE_PLACEHOLDER"),
            ("min-stack", "javascript"): (("SILENT_UNFINISHED_METHOD", "PASS", "PASS"), "SILENT_UNFINISHED_METHOD"),
            ("reverse-linked-list", "python"): (("PASS", "COMMENTED_OUT_ALGORITHM", "UNREACHABLE_CODE"),
                                                "COMMENTED_OUT_ALGORITHM"),
            ("maximum-depth-of-binary-tree", "java"): (("PASS", "PASS", "PASS"), "INVALID_LEVEL_PROGRESSION"),
            ("number-of-islands", "cpp"): (("PASS", "PASS", "MISSING_UNFINISHED_PLACEHOLDER"),
                                           "MISSING_UNFINISHED_PLACEHOLDER"),
            ("climbing-stairs", "javascript"): (("PASS", "PASS", "COMMENTED_OUT_ALGORITHM"),
                                                "COMMENTED_OUT_ALGORITHM"),
        }
        self.assertEqual({(case["slug"], case["language"]) for case in cases}, set(expected))

        def verdict(check):
            try:
                check()
                return "PASS"
            except StarterOutputDiagnostic as exc:
                return exc.reason

        for case in cases:
            slug, language = case["slug"], case["language"]
            context = self.context(slug, case["approachId"], language)
            levels = case["levels"]
            with self.subTest(slug=slug, language=language):
                decisions = tuple(verdict(lambda n=n, key=key: validate_level(levels[key], context, language, n))
                                  for n, key in enumerate(("level1", "level2", "level3"), 1))
                batch = verdict(lambda: validate_starter_batch(levels, context, language, check_compilers=False))
                self.assertEqual((decisions, batch), expected[(slug, language)])

    def test_cpp_fail_loud_runtime_error_and_short_explanatory_comments_are_allowed(self):
        cases = json.loads((Path(__file__).parent / "fixtures" / "starter_v2_live_20261018.json")
                           .read_text(encoding="utf-8"))
        islands = next(case for case in cases if case["slug"] == "number-of-islands")
        context = self.context("number-of-islands", "depth-first-flood-fill", "cpp")
        for level in (1, 2):
            code = islands["levels"][f"level{level}"]
            self.assertIn("throw runtime_error(", code)
            validate_level(code, context, "cpp", level)
            validate_level(code.replace("throw runtime_error(", "throw std::runtime_error("), context, "cpp", level)

        explained = TWO_SUM["level2"].replace(
            "        for index, value in enumerate(nums):",
            "        # Keep useful earlier information in the map.\n"
            "        # Example: seen[value] = index\n"
            "        for index, value in enumerate(nums):",
        )
        validate_level(explained, self.context(), "python", 2)

    def test_recursive_helpers_and_normal_collection_operations_are_allowed(self):
        context = self.context("maximum-depth-of-binary-tree", "depth-first-search", "python")
        signature = "    def maxDepth(self, root: Optional[TreeNode]) -> int:"
        def scaffold(body, helper=""):
            return "from typing import Optional\nclass Solution:\n" + signature + "\n" + body + helper
        batch = {
            "level1": scaffold('        depth = 0\n        # TODO: determine how to measure depth.\n        raise NotImplementedError("Complete depth")'),
            "level2": scaffold('        return self._depth(root)\n',
                '    def _depth(self, node):\n        if node is None:\n            return 0\n'
                '        # TODO: explore the nonempty tree.\n        raise NotImplementedError("Complete exploration")'),
            "level3": scaffold('        return self._depth(root)\n',
                '    def _depth(self, node):\n        if node is None:\n            return 0\n'
                '        left = self._depth(node.left)\n        right = self._depth(node.right)\n'
                '        # TODO: combine the child depths.\n        raise NotImplementedError("Complete the depth result")'),
        }
        self.assertEqual(validate_starter_batch(batch, context, "python"), batch)
        java = self.context("valid-anagram", "frequency-count", "java")
        code = java["problem"]["submissionTemplate"]["code"].replace("{\n\n", '{\n        int[] counts = new int[26];\n'
            '        int limit = Math.min(s.length(), t.length());\n'
            '        for (int i = 0; i < limit; i++) {\n'
            '            // TODO: update the character counts.\n'
            '            throw new UnsupportedOperationException("Complete counting");\n        }\n'
            '        throw new UnsupportedOperationException("Complete the comparison");\n', 1)
        validate_level(code, java, "java", 2)
        self.assertEqual(check_syntax(code, "java")["status"], "PASS")

    def test_midpoint_without_bound_updates_and_unreachable_helper_do_not_make_safe_scaffolds(self):
        context = self.context("binary-search", "binary-search", "python")
        code = '''from typing import List
class Solution:
    def search(self, nums: List[int], target: int) -> int:
        left, right = 0, len(nums) - 1
        while left <= right:
            middle = (left + right) // 2
            # TODO: narrow the search range.
        raise NotImplementedError("Cannot be reached on nonempty input")'''
        with self.assertRaises(StarterOutputDiagnostic) as error:
            validate_level(code, context, "python", 2)
        self.assertEqual(error.exception.reason, "UNSAFE_UNFINISHED_LOOP")
        unused = TWO_SUM["level1"].replace('raise NotImplementedError("Complete the search")', "return []")
        unused += '\n    def _unused(self):\n        # TODO: compute a result.\n        raise NotImplementedError("Unused")'
        with self.assertRaises(StarterOutputDiagnostic):
            validate_level(unused, self.context(), "python", 2)

    def test_java_private_helper_is_valid_but_public_overload_is_rejected(self):
        context = self.context("maximum-depth-of-binary-tree", "depth-first-search", "java")
        code = '''class Solution {
    public int maxDepth(TreeNode root) {
        return _depth(root);
    }
    private int _depth(TreeNode node) {
        if (node == null) { return 0; }
        int left = _depth(node.left);
        // TODO: determine how to finish the depth result.
        throw new UnsupportedOperationException("Complete the recursive step");
    }
}'''
        validate_level(code, context, "java", 3)
        self.assertEqual(check_syntax(code, "java")["status"], "PASS")
        extra = code.replace("private int _depth", "public int _depth")
        with self.assertRaises(StarterOutputDiagnostic): validate_level(extra, context, "java", 3)
        extra = code.replace("\n}", " public int maxDepth(int value) { return value; }\n}")
        with self.assertRaises(StarterOutputDiagnostic): validate_level(extra, context, "java", 3)

    def test_progression_and_obvious_approach_contradiction(self):
        for batch in ({**TWO_SUM, "level1": TWO_SUM["level3"], "level3": TWO_SUM["level1"]},
                      {**TWO_SUM, "level3": TWO_SUM["level2"] + "\n# More comments"}):
            with self.assertRaises(StarterOutputDiagnostic) as error:
                validate_starter_batch(batch, self.context(), "python")
            self.assertEqual(error.exception.reason, "INVALID_LEVEL_PROGRESSION")
        with self.assertRaises(StarterOutputDiagnostic) as error:
            validate_starter_batch(TWO_SUM, self.context(approach="brute-force"), "python")
        self.assertEqual(error.exception.reason, "APPROACH_CONTRADICTION")

    def test_invalid_source_is_rejected_in_each_language(self):
        for language in ("python", "java", "javascript", "cpp"):
            context = self.context(language=language)
            batch = deepcopy(TWO_SUM) if language == "python" else MockLLMProvider().generate_starter_batch(context, language)
            if language == "python": batch["level2"] = batch["level2"].replace("seen = {}", "seen = [")
            else: batch["level2"] = batch["level2"].replace("\n", "\n        int broken = ;\n", 1)
            with self.subTest(language=language), self.assertRaises(StarterOutputDiagnostic):
                validate_starter_batch(batch, context, language)

    def test_cpp_visibility_and_preprocessor_and_javascript_prototype_keep_interfaces_immutable(self):
        context = self.context(language="cpp")
        code = MockLLMProvider().generate_starter_batch(context, "cpp")["level2"]
        with self.assertRaises(StarterOutputDiagnostic):
            validate_level(code.replace("public:", "private:"), context, "cpp", 2)
        self.assertEqual(check_syntax("#define public private\n" + code, "cpp")["status"], "FAIL")
        context = self.context("min-stack", "paired-minimums", "javascript")
        code = MockLLMProvider().generate_starter_batch(context, "javascript")["level2"]
        with self.assertRaises(StarterOutputDiagnostic):
            validate_level(code + "\nMinStack.prototype = {};", context, "javascript", 2)

    def test_all_offline_catalog_batches_remain_available(self):
        count = 0
        for slug, problem in CURATED_PROBLEMS.items():
            for approach in problem["approaches"]:
                for language in ("python", "java", "javascript", "cpp"):
                    context = self.context(slug, approach["id"], language)
                    batch = MockLLMProvider().generate_starter_batch(context, language)
                    with self.subTest(slug=slug, approach=approach["id"], language=language):
                        self.assertEqual(validate_starter_batch(batch, context, language, check_compilers=False), batch)
                    count += 1
        self.assertEqual(count, 164)

    def test_representative_fake_groq_batches_and_available_compilers(self):
        for slug, approach, language in REPRESENTATIVE:
            context = self.context(slug, approach, language)
            batch = TWO_SUM if slug == "two-sum" else MockLLMProvider().generate_starter_batch(context, language)
            provider, calls = self.fake_provider(json.dumps(batch))
            with self.subTest(slug=slug, language=language), patch("app.main.get_llm_provider", return_value=provider):
                response = self.request(slug, approach, language)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(len(calls), 1)
                for code in batch.values():
                    self.assertNotEqual(check_syntax(code, language)["status"], "FAIL")

    def test_cpp_compiles_offline_in_existing_sandbox_when_native_compiler_is_unavailable(self):
        available, reason = probe_sandbox()
        if not available: self.skipTest(reason)
        for slug, approach in (("binary-search", "binary-search"), ("number-of-islands", "depth-first-flood-fill")):
            context = self.context(slug, approach, "cpp")
            batch = MockLLMProvider().generate_starter_batch(context, "cpp")
            for level, code in batch.items():
                with self.subTest(slug=slug, level=level):
                    result = offline_syntax(code, "cpp")
                    self.assertEqual(result["status"], "PASS", result)

    def test_old_route_requires_explicit_rollback_flag_and_stays_policy_six(self):
        with patch.dict(os.environ, {"LEETCOACH_ENABLE_LEGACY_STARTER": "false"}):
            response = self.client.post("/api/problems/two-sum/approaches/hash-map/starter-code",
                                        json={"language": "python", "level": 1})
            self.assertEqual(response.status_code, 409)
        response = self.client.post("/api/problems/two-sum/approaches/hash-map/starter-code",
                                    json={"language": "python", "level": 1})
        self.assertEqual(response.json()["policyVersion"], 6)

    def test_bounded_harness_is_dry_by_default_and_counts_one_fake_call_as_three_levels(self):
        self.assertEqual(len(MATRIX), 8)
        self.assertEqual({row[2] for row in MATRIX}, {"python", "java", "javascript", "cpp"})
        with self.assertRaises(SystemExit): parse_args(["--live", "--max-calls", "9"])
        with self.assertRaises(SystemExit): parse_args(["--capture-raw"])
        with tempfile.TemporaryDirectory() as directory, \
             patch("evaluation.starter_v2.SessionLocal", sessionmaker(bind=self.engine)):
            with patch("evaluation.starter_v2.TestClient") as client:
                self.assertEqual(run(["--output-dir", directory]), 0)
                client.assert_not_called()
            data = json.loads((Path(directory) / "starter_v2.json").read_text())
            self.assertEqual(data["metrics"]["realGroqCalls"], 0)
            self.assertEqual(len(data["records"]), 8)
            provider, calls = self.fake_provider(json.dumps(TWO_SUM))
            with patch("app.main.get_llm_provider", return_value=provider), patch.dict(os.environ, {
                    "GROQ_API_KEY": "offline-test", "LEETCOACH_LLM_MODEL": "fake-model"}):
                self.assertEqual(run(["--live", "--max-calls", "1", "--pace-seconds", "0",
                                      "--output-dir", directory]), 0)
            self.assertEqual(len(calls), 1)
            data = json.loads((Path(directory) / "starter_v2.json").read_text())
            self.assertEqual(data["metrics"]["realGroqCalls"], 1)  # Fake SDK, no network.
            self.assertEqual(data["metrics"]["validBatches"], 1)
            self.assertEqual(data["metrics"]["structurallyValidLevels"], 3)
            self.assertIsNotNone(data["records"][0]["providerLatencyMs"])
