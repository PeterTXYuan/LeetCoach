"""DB-grounded full-solution contract and offline provider validation."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app.llm.base import ProviderConfigurationError, ProviderOutputError, ProviderUnavailableError
from app.llm.groq_provider import GroqLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.solution_validation import validate_solution
from app.services.problem_repository import find_problem_context
from app.stable_data import CURATED_PROBLEMS


LANGUAGES = ("python", "java", "javascript", "cpp")


class FullSolutionTests(DatabaseTestCase):
    def request(self, slug="two-sum", approach="hash-map", language="python"):
        return self.client.post(
            f"/api/problems/{slug}/approaches/{approach}/solution",
            json={"language": language},
        )

    def context(self, slug="two-sum", approach="hash-map", language="python"):
        with Session(self.engine) as session:
            return find_problem_context(session, slug, approach, language)

    def test_all_curated_problem_approach_language_contexts_resolve_from_db(self):
        self.assertEqual(len(CURATED_PROBLEMS), 20)
        for slug, problem in CURATED_PROBLEMS.items():
            for approach in problem["approaches"]:
                for language in LANGUAGES:
                    with self.subTest(slug=slug, approach=approach["id"], language=language):
                        context = self.context(slug, approach["id"], language)
                        self.assertEqual(context["problem"]["slug"], slug)
                        self.assertEqual(context["approach"]["id"], approach["id"])
                        self.assertEqual(context["problem"]["submissionTemplate"]["language"], language)
                        self.assertTrue(context["problem"]["summary"])
                        self.assertTrue(context["problem"]["constraints"])
                        self.assertTrue(context["problem"]["examples"])
                        self.assertTrue(context["approach"]["thinkingSteps"])

    def test_selected_canonical_approach_and_language_template_reach_groq(self):
        calls = []
        for approach in ("hash-map", "brute-force"):
            for language in LANGUAGES:
                context = self.context(approach=approach, language=language)
                result = MockLLMProvider().generate_solution(context, language)

                def create(**kwargs):
                    calls.append(kwargs)
                    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                        content=json.dumps(result)))])

                client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
                provider = GroqLLMProvider(api_key="test-only", model="test-model", client=client)
                with self.subTest(approach=approach, language=language), patch(
                    "app.main.get_llm_provider", return_value=provider
                ):
                    response = self.request(approach=approach, language=language)
                    self.assertEqual(response.status_code, 200, response.text)
                    self.assertTrue(response.json()["isAiGenerated"])
                    self.assertEqual(response.json()["code"], result["code"])
                    sent = json.loads(calls[-1]["messages"][1]["content"])
                    self.assertEqual(sent["context"]["approach"]["id"], approach)
                    self.assertEqual(sent["context"]["problem"]["submissionTemplate"],
                                     context["problem"]["submissionTemplate"])
                    self.assertEqual(sent["language"], language)
                    self.assertNotIn("approaches", sent["context"])
                    self.assertEqual(calls[-1]["response_format"], {"type": "json_object"})
        self.assertEqual(len(calls), 8)  # One structured request per explicit generation.

    def test_db_only_problem_reaches_provider_and_mock_does_not_fabricate_solution(self):
        context = self.context("contains-duplicate", "hash-set", "python")
        self.assertIsNotNone(context)
        self.assertEqual(self.request("contains-duplicate", "hash-set").status_code, 503)

        class RecordingProvider:
            is_ai_generated = True
            def generate_solution(self, received, language):
                self.received = (received, language)
                return {
                    "code": "from typing import List\n\nclass Solution:\n"
                            "    def containsDuplicate(self, nums: List[int]) -> bool:\n"
                            "        return len(set(nums)) != len(nums)",
                    "explanation": "A set keeps each distinct value once. A shorter set means a duplicate exists.",
                    "timeComplexity": "O(n)", "spaceComplexity": "O(n)",
                }
        provider = RecordingProvider()
        with patch("app.main.get_llm_provider", return_value=provider):
            response = self.request("contains-duplicate", "hash-set", "python")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(provider.received, (context, "python"))
        self.assertTrue(response.json()["isAiGenerated"])

    def test_validator_rejects_missing_signatures_design_methods_placeholders_and_syntax(self):
        context = self.context()
        good = MockLLMProvider().generate_solution(context, "python")
        template = context["problem"]["submissionTemplate"]["code"]
        for replacement in (
            {"code": good["code"].replace("def twoSum", "def solve")},
            {"code": good["code"] + "\n# TODO: finish"},
            {"code": "```python\n" + good["code"] + "\n```"},
            {"code": good["code"] + "\n    if"},
            {"explanation": " "},
            {"timeComplexity": 4},
            {"code": ""},
        ):
            with self.subTest(replacement=replacement), self.assertRaises(ProviderOutputError):
                validate_solution({**good, **replacement}, template, "python")
        min_stack = self.context("min-stack", "paired-minimums", "python")
        if min_stack is None:
            # The stable key is checked separately in curated metadata tests.
            self.fail("Expected Min Stack paired-minimums context")
        design_template = min_stack["problem"]["submissionTemplate"]["code"]
        missing_method = design_template.replace("    def getMin(self) -> int:\n        pass", "")
        with self.assertRaises(ProviderOutputError):
            validate_solution({**good, "code": missing_method}, design_template, "python")
        for language in ("java", "javascript", "cpp"):
            language_context = self.context(language=language)
            language_good = MockLLMProvider().generate_solution(language_context, language)
            with self.subTest(language=language), self.assertRaises(ProviderOutputError):
                validate_solution({**language_good, "code": language_good["code"] + "\n}"},
                                  language_context["problem"]["submissionTemplate"]["code"], language)
            with self.subTest(language=language, defect="empty method"), self.assertRaises(ProviderOutputError):
                language_template = language_context["problem"]["submissionTemplate"]["code"]
                validate_solution({**language_good, "code": language_template}, language_template, language)

    def test_bad_groq_output_and_provider_errors_are_sanitized_without_mock_fallback(self):
        good = MockLLMProvider().generate_solution(self.context(), "python")
        for raw in ("not json", json.dumps({"code": good["code"]}),
                    json.dumps({**good, "code": good["code"] + "\n# TODO"})):
            client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
                create=lambda **_: SimpleNamespace(choices=[SimpleNamespace(
                    message=SimpleNamespace(content=raw))]))))
            provider = GroqLLMProvider(api_key="test-only", model="test-model", client=client)
            with self.subTest(raw=raw), patch("app.main.get_llm_provider", return_value=provider):
                response = self.request()
                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.json(), {"detail": "Full solution provider returned invalid output."})
        with patch("app.main.get_llm_provider", side_effect=ProviderConfigurationError("secret")):
            response = self.request()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("secret", response.text)
        for failure, expected in (
            (ProviderUnavailableError("secret"), 503),
            (ProviderOutputError("secret"), 502),
        ):
            provider = Mock(is_ai_generated=True, generate_solution=Mock(side_effect=failure))
            with patch("app.main.get_llm_provider", return_value=provider):
                response = self.request()
            self.assertEqual(response.status_code, expected)
            self.assertNotIn("secret", response.text)
            self.assertNotIn("curated mock", response.text)

    def test_errors_and_language_contract(self):
        self.assertEqual(self.request("unknown").status_code, 404)
        self.assertEqual(self.request(approach="unknown").status_code, 404)
        self.assertEqual(self.request(language="ruby").status_code, 400)
        self.assertEqual(self.request(language="JAVA").json()["language"], "java")

    def test_served_mock_algorithms_handle_representative_edge_cases_in_isolated_python(self):
        cases = (
            ("two-sum", "hash-map", "twoSum", [([2, 7, 11, 15], 9), ([3, 3], 6), ([-3, 4, 3, 90], 0)],
             [[0, 1], [0, 1], [0, 2]]),
            ("two-sum", "brute-force", "twoSum", [([2, 7, 11, 15], 9), ([3, 3], 6), ([-3, 4, 3, 90], 0)],
             [[0, 1], [0, 1], [0, 2]]),
            ("valid-parentheses", "stack", "isValid", [("",), ("{[()]}",), ("([)]",), ("(]",)],
             [True, True, False, False]),
        )
        for slug, approach, method, arguments, expected in cases:
            with self.subTest(slug=slug, approach=approach):
                response = self.request(slug, approach)
                self.assertEqual(response.status_code, 200)
                script = response.json()["code"] + "\n" + (
                    f"assert [getattr(Solution(), {method!r})(*args) for args in {arguments!r}] == {expected!r}\n"
                )
                completed = subprocess.run([sys.executable, "-I", "-c", script],
                                           capture_output=True, text=True, timeout=5, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_mocked_provider_algorithms_for_three_sum_binary_search_and_min_stack(self):
        # These are known-good fake provider payloads, not assertions about live Groq quality.
        examples = (
            ("3sum", "sort-and-two-pointers", """from typing import List
class Solution:
    def threeSum(self, nums: List[int]) -> List[List[int]]:
        nums.sort()
        result = []
        for i in range(len(nums) - 2):
            if i and nums[i] == nums[i - 1]:
                continue
            left, right = i + 1, len(nums) - 1
            while left < right:
                total = nums[i] + nums[left] + nums[right]
                if total < 0:
                    left += 1
                elif total > 0:
                    right -= 1
                else:
                    result.append([nums[i], nums[left], nums[right]])
                    left += 1
                    right -= 1
                    while left < right and nums[left] == nums[left - 1]:
                        left += 1
                    while left < right and nums[right] == nums[right + 1]:
                        right -= 1
        return result""", """
solver = Solution()
assert sorted(solver.threeSum([-1, 0, 1, 2, -1, -4])) == [[-1, -1, 2], [-1, 0, 1]]
assert solver.threeSum([]) == []
assert solver.threeSum([0, 0, 0, 0]) == [[0, 0, 0]]
assert solver.threeSum([1, 2, -2, -1]) == []""", "O(n^2)", "O(n) excluding output"),
            ("binary-search", "binary-search", """from typing import List
class Solution:
    def search(self, nums: List[int], target: int) -> int:
        low, high = 0, len(nums) - 1
        while low <= high:
            mid = low + (high - low) // 2
            if nums[mid] == target:
                return mid
            if nums[mid] < target:
                low = mid + 1
            else:
                high = mid - 1
        return -1""", """
solver = Solution()
assert solver.search([-1, 0, 3, 5, 9, 12], 9) == 4
assert solver.search([-1, 0, 3, 5, 9, 12], 2) == -1
assert solver.search([], 2) == -1
assert solver.search([5], 5) == 0
assert solver.search([5], 4) == -1""", "O(log n)", "O(1)"),
            ("min-stack", "paired-minimums", """class MinStack:
    def __init__(self):
        self.values = []

    def push(self, val: int) -> None:
        minimum = min(val, self.values[-1][1]) if self.values else val
        self.values.append((val, minimum))

    def pop(self) -> None:
        self.values.pop()

    def top(self) -> int:
        return self.values[-1][0]

    def getMin(self) -> int:
        return self.values[-1][1]""", """
stack = MinStack()
stack.push(-2); stack.push(0); stack.push(-3)
assert stack.getMin() == -3
stack.pop()
assert stack.top() == 0 and stack.getMin() == -2
stack.push(-2)
assert stack.getMin() == -2
stack.pop(); stack.pop()
assert stack.top() == -2 and stack.getMin() == -2""", "O(1) per operation", "O(n) storage"),
        )
        for slug, approach, code, assertions, time_complexity, space_complexity in examples:
            with self.subTest(slug=slug, approach=approach):
                provider = Mock(is_ai_generated=True, generate_solution=Mock(return_value={
                    "code": code, "explanation": "Maintain the selected approach's state and update it.",
                    "timeComplexity": time_complexity, "spaceComplexity": space_complexity,
                }))
                with patch("app.main.get_llm_provider", return_value=provider):
                    response = self.request(slug, approach)
                self.assertEqual(response.status_code, 200, response.text)
                self.assertEqual(response.json()["code"], code)
                completed = subprocess.run([sys.executable, "-I", "-c", code + assertions],
                                           capture_output=True, text=True, timeout=5, check=False)
                self.assertEqual(completed.returncode, 0, completed.stderr)

    def test_offline_javascript_and_java_solutions_parse_when_tools_exist(self):
        for language, executable, filename, argument in (
            ("javascript", "node", "solution.js", "--check"),
            ("java", "javac", "Solution.java", None),
        ):
            if shutil.which(executable) is None:
                continue
            for slug, problem in CURATED_PROBLEMS.items():
                for approach in problem["approaches"]:
                    context = self.context(slug, approach["id"], language)
                    try:
                        code = MockLLMProvider().generate_solution(context, language)["code"]
                    except ProviderUnavailableError:
                        continue
                    with self.subTest(slug=slug, approach=approach["id"], language=language):
                        with tempfile.TemporaryDirectory() as temp_dir:
                            source = Path(temp_dir) / filename
                            source.write_text(code, encoding="utf-8")
                            command = [executable, argument, str(source)] if argument else [
                                executable, "-d", temp_dir, str(source)]
                            completed = subprocess.run(command, capture_output=True, text=True,
                                                       timeout=10, check=False)
                            self.assertEqual(completed.returncode, 0, completed.stderr)
