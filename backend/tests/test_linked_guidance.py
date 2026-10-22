"""Policy 9 regressions use fake providers; never contact Groq."""
from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from test_starter_v2 import TWO_SUM
from app.llm.base import StarterOutputDiagnostic
from app.llm.groq_provider import GroqLLMProvider
from app.llm.starter_diagnostics import starter_observer
from app.llm.linked_guidance import validate_linked_bundle, check_linked_correctness
from app.services.problem_repository import find_problem_context


ANSWER = {
    "code": '''from typing import List
class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        seen = {}
        for index, value in enumerate(nums):
            complement = target - value
            if complement in seen:
                return [seen[complement], index]
            seen[value] = index
        raise ValueError("No valid pair")''',
    "explanation": "Store earlier indices and find the needed partner.",
    "timeComplexity": "O(n)", "spaceComplexity": "O(n)",
}


class LinkedGuidanceTests(DatabaseTestCase):
    def context(self):
        with Session(self.engine) as session:
            return find_problem_context(session, "two-sum", "hash-map", "python")

    def payload(self):
        return {**deepcopy(TWO_SUM), "solution": deepcopy(ANSWER)}

    def test_one_provider_call_four_validated_outputs_and_policy9(self):
        output = self.payload()
        calls = []
        class Provider:
            is_ai_generated = True
            def generate_guidance_bundle(self, context, language):
                calls.append((context["approach"]["id"], language))
                return {"output": output, "usage": {"promptTokens": 100,
                    "completionTokens": 200, "totalTokens": 300, "latencyMs": 8,
                    "outputChars": 400, "finishReason": "stop"}}
        with patch("app.main.get_llm_provider", return_value=Provider()), patch(
            "app.main.check_linked_correctness", return_value={"status": "PASS", "summary": "4/4 fixtures passed"}
        ):
            response = self.client.post("/api/problems/two-sum/approaches/hash-map/guidance",
                                        json={"language": "python"})
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual(calls, [("hash-map", "python")])
        self.assertEqual(data["policyVersion"], 9)
        self.assertEqual(data["kind"], "linked")
        self.assertTrue(data["generationId"])
        self.assertEqual(data["solution"]["code"], ANSWER["code"])
        self.assertEqual(data["verification"]["status"], "PASS")
        self.assertEqual(data["usage"]["totalTokens"], 300)

    def test_broken_submission_signature_still_keeps_all_four_out_of_response(self):
        output = self.payload()
        output["solution"]["code"] = output["solution"]["code"].replace("def twoSum(", "def wrongName(")
        class Provider:
            is_ai_generated = True
            def generate_guidance_bundle(self, context, language):
                return {"output": output, "usage": {}}
        with patch("app.main.get_llm_provider", return_value=Provider()):
            response = self.client.post("/api/problems/two-sum/approaches/hash-map/guidance",
                                        json={"language": "python"})
        self.assertEqual(response.status_code, 502)
        self.assertNotIn("level1", response.json())

    def test_failing_isolated_fixtures_warn_and_not_run_is_explicit(self):
        class Provider:
            is_ai_generated = True
            def generate_guidance_bundle(self, context, language):
                return {"output": self_output, "usage": {}}
        self_output = self.payload()
        with patch("app.main.get_llm_provider", return_value=Provider()), patch(
            "app.main.check_linked_correctness", return_value={"status": "FAIL", "summary": "2/4 fixtures passed"}
        ):
            failed = self.client.post("/api/problems/two-sum/approaches/hash-map/guidance",
                                      json={"language": "python"})
            self.assertEqual(failed.status_code, 200, failed.text)
            self.assertEqual(failed.json()["verification"]["status"], "FAIL")
            self.assertIn("CORRECTNESS_FIXTURE_FAILED",
                          [warning["code"] for warning in failed.json()["warnings"]])
        with patch("app.main.get_llm_provider", return_value=Provider()), patch(
            "app.main.check_linked_correctness", return_value={"status": "NOT_RUN", "summary": "No sandbox"}
        ):
            response = self.client.post("/api/problems/two-sum/approaches/hash-map/guidance",
                                        json={"language": "python"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["verification"]["status"], "NOT_RUN")

    def test_design_and_incomplete_answers_are_soft_warnings(self):
        context = self.context()
        output = self.payload()
        output["level2"] = output["level2"].replace("seen = {}", "other = {}")
        self.assertIn("INCOMPATIBLE_LEVEL_DESIGN",
                      [warning["code"] for warning in validate_linked_bundle(output, context, "python")["warnings"]])
        output = self.payload()
        output["solution"]["code"] = output["solution"]["code"].replace(
            "return [seen[complement], index]", 'raise NotImplementedError("later")')
        self.assertIn("INCOMPLETE_FULL_SOLUTION",
                      [warning["code"] for warning in validate_linked_bundle(output, context, "python")["warnings"]])
        output = self.payload()
        output["solution"]["code"] = output["solution"]["code"].replace(
            'raise ValueError("No valid pair")', "return []")
        self.assertIn("POSSIBLE_EMPTY_ANSWER",
                      [warning["code"] for warning in validate_linked_bundle(output, context, "python")["warnings"]])
        output = self.payload()
        output["level2"] = output["level1"].replace("decide what information", "explain what information")
        self.assertIn("INVALID_LEVEL_PROGRESSION",
                      [warning["code"] for warning in validate_linked_bundle(output, context, "python")["warnings"]])

    def test_minimal_level_and_long_correct_complexity_text_are_accepted(self):
        output = self.payload()
        output["level1"] = ("from typing import List\nclass Solution:\n"
            "    def twoSum(self, nums: list[int], target: int) -> list[int]:\n"
            "        # TODO: implement the hash-map approach\n"
            "        raise NotImplementedError('not implemented')")
        output["solution"]["timeComplexity"] = (
            "O(n) time: each input value is visited once, with expected constant-time "
            "hash-map reads and writes for every value in the input array."
        )
        result = validate_linked_bundle(output, self.context(), "python")
        self.assertEqual(result["solution"]["timeComplexity"], output["solution"]["timeComplexity"])
        self.assertIn("NO_USEFUL_SETUP", [warning["code"] for warning in result["warnings"]])

    def test_malformed_source_and_invalid_syntax_remain_hard_failures(self):
        context = self.context()
        output = self.payload()
        output["level2"] = output["level2"].replace("def twoSum(", "def renamed(")
        with self.assertRaises(StarterOutputDiagnostic) as error:
            validate_linked_bundle(output, context, "python")
        self.assertEqual(error.exception.reason, "CHANGED_SIGNATURE")
        output = self.payload()
        output["level2"] += "\nif ("
        with self.assertRaises(StarterOutputDiagnostic) as error:
            validate_linked_bundle(output, context, "python")
        self.assertEqual(error.exception.reason, "INVALID_SYNTAX")

    def test_unavailable_syntax_checker_adds_warning_instead_of_rejecting(self):
        with patch("app.llm.linked_guidance.check_syntax", return_value={
            "status": "FAIL", "summary": "Bounded syntax check could not complete"
        }):
            result = validate_linked_bundle(self.payload(), self.context(), "python")
        self.assertIn("SYNTAX_NOT_CHECKED", [warning["code"] for warning in result["warnings"]])

    def test_provider_records_usage_and_rejects_token_truncation(self):
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(self.payload())), finish_reason="length")],
                usage=SimpleNamespace(prompt_tokens=60, completion_tokens=10000, total_tokens=10060))
        provider = GroqLLMProvider("unused", "openai/gpt-oss-120b", client=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
        with self.assertRaises(StarterOutputDiagnostic) as error:
            provider.generate_guidance_bundle(self.context(), "python")
        self.assertEqual(error.exception.reason, "TOKEN_LIMIT_TRUNCATION")
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["max_completion_tokens"], 10000)
        self.assertEqual(calls[0]["timeout"], 30.0)
        self.assertIn("In L2/L3, add short comments", calls[0]["messages"][0]["content"])

    def test_completed_provider_records_metrics_without_raw_code(self):
        observed = []
        content = json.dumps(self.payload())
        def create(**kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=content), finish_reason="stop")],
                usage=SimpleNamespace(prompt_tokens=61, completion_tokens=723, total_tokens=784))
        provider = GroqLLMProvider("unused", "openai/gpt-oss-120b", client=SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))))
        token = starter_observer.set(observed.append)
        try:
            response = provider.generate_guidance_bundle(self.context(), "python")
        finally:
            starter_observer.reset(token)
        self.assertEqual(response["output"], self.payload())
        self.assertEqual(response["usage"]["totalTokens"], 784)
        self.assertEqual(response["usage"]["outputChars"], len(content))
        self.assertEqual(response["usage"]["finishReason"], "stop")
        self.assertTrue(any(event["kind"] == "linked_usage" for event in observed))
        self.assertFalse(any(event["kind"] == "raw_response" for event in observed))

    def test_mock_is_starter_only_with_optional_independent_answer(self):
        response = self.client.post("/api/problems/two-sum/approaches/hash-map/guidance",
                                    json={"language": "python"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["kind"], "starterOnlyMock")
        self.assertEqual(response.json()["policyVersion"], 9)
        self.assertEqual(response.json()["verification"]["status"], "NOT_RUN")

    def test_real_isolated_fixture_when_sandbox_available(self):
        good = check_linked_correctness("two-sum", "python", ANSWER["code"])
        self.assertIn(good["status"], {"PASS", "NOT_RUN"})
        if good["status"] == "PASS":
            wrong = ANSWER["code"].replace("return [seen[complement], index]", "return [0, 0]")
            self.assertEqual(check_linked_correctness("two-sum", "python", wrong)["status"], "FAIL")

    def test_binary_search_stages_retain_bounds_and_complete_the_search(self):
        with Session(self.engine) as session:
            context = find_problem_context(session, "binary-search", "binary-search", "python")
        head = "class Solution:\n    def search(self, nums: list[int], target: int) -> int:\n"
        setup = "        left, right = 0, len(nums) - 1\n"
        levels = {
            "level1": head + setup + "        # TODO: search within the current bounds.\n        raise NotImplementedError('search')",
            "level2": head + setup + "        while left <= right:\n            mid = (left + right) // 2\n            # TODO: compare the middle value.\n            raise NotImplementedError('comparison')\n        raise NotImplementedError('result')",
            "level3": head + setup + "        while left <= right:\n            mid = (left + right) // 2\n            if nums[mid] == target:\n                return mid\n            # TODO: move the correct boundary.\n            raise NotImplementedError('boundary')\n        return -1",
            "solution": {**ANSWER, "code": head + setup +
                "        while left <= right:\n            mid = (left + right) // 2\n"
                "            if nums[mid] == target:\n                return mid\n"
                "            if nums[mid] < target:\n                left = mid + 1\n"
                "            else:\n                right = mid - 1\n        return -1"},
        }
        self.assertEqual(validate_linked_bundle(levels, context, "python")["solution"]["code"],
                         levels["solution"]["code"])
        unsafe = deepcopy(levels)
        unsafe["level2"] = unsafe["level2"].replace(
            "raise NotImplementedError('comparison')", "pass")
        self.assertIn("UNSAFE_UNFINISHED_LOOP", [warning["code"] for warning in
            validate_linked_bundle(unsafe, context, "python")["warnings"]])

    def test_reverse_linked_list_stages_retain_pointer_state(self):
        with Session(self.engine) as session:
            context = find_problem_context(session, "reverse-linked-list", "iterative-pointers", "python")
        head = "class Solution:\n    def reverseList(self, head: ListNode | None) -> ListNode | None:\n"
        setup = "        previous = None\n        current = head\n"
        levels = {
            "level1": head + setup + "        # TODO: reverse each link.\n        raise NotImplementedError('links')",
            "level2": head + setup + "        while current is not None:\n            following = current.next\n            # TODO: redirect the current link.\n            raise NotImplementedError('redirect')\n        raise NotImplementedError('result')",
            "level3": head + setup + "        while current is not None:\n            following = current.next\n            current.next = previous\n            # TODO: advance both pointers.\n            raise NotImplementedError('advance')\n        return previous",
            "solution": {**ANSWER, "code": head + setup +
                "        while current is not None:\n            following = current.next\n"
                "            current.next = previous\n            previous = current\n"
                "            current = following\n        return previous"},
        }
        self.assertEqual(validate_linked_bundle(levels, context, "python")["solution"]["code"],
                         levels["solution"]["code"])

    def test_three_sum_java_stages_complete_the_same_two_pointer_flow(self):
        with Session(self.engine) as session:
            context = find_problem_context(session, "3sum", "sort-and-two-pointers", "java")
        head = "import java.util.*;\nclass Solution {\n    public List<List<Integer>> threeSum(int[] nums) {\n"
        setup = "        Arrays.sort(nums);\n        List<List<Integer>> result = new ArrayList<>();\n"
        loop = ("        int n = nums.length;\n        for (int i = 0; i < n - 2; i++) {\n"
                "            if (i > 0 && nums[i] == nums[i - 1]) continue;\n"
                "            int left = i + 1;\n            int right = n - 1;\n"
                "            while (left < right) {\n                int sum = nums[i] + nums[left] + nums[right];\n")
        levels = {
            "level1": head + setup + "        // TODO: inspect groups of three.\n        throw new UnsupportedOperationException(\"triplets\");\n    }\n}",
            "level2": head + setup + loop +
                "                // TODO: use the sum to decide how to move.\n"
                "                throw new UnsupportedOperationException(\"pointer logic\");\n"
                "            }\n        }\n        return result;\n    }\n}",
            "level3": head + setup + loop +
                "                if (sum == 0) {\n"
                "                    // TODO: collect a unique triplet and move both pointers.\n"
                "                    throw new UnsupportedOperationException(\"triplet handling\");\n"
                "                } else if (sum < 0) {\n                    left++;\n"
                "                } else {\n                    right--;\n                }\n"
                "            }\n        }\n        return result;\n    }\n}",
            "solution": {**ANSWER, "code": head + setup + loop +
                "                if (sum == 0) {\n"
                "                    result.add(Arrays.asList(nums[i], nums[left], nums[right]));\n"
                "                    left++; right--;\n"
                "                    while (left < right && nums[left] == nums[left - 1]) left++;\n"
                "                    while (left < right && nums[right] == nums[right + 1]) right--;\n"
                "                } else if (sum < 0) {\n                    left++;\n"
                "                } else {\n                    right--;\n                }\n"
                "            }\n        }\n        return result;\n    }\n}"},
        }
        self.assertEqual(validate_linked_bundle(levels, context, "java")["solution"]["code"],
                         levels["solution"]["code"])
        unsafe = deepcopy(levels)
        unsafe["level2"] = unsafe["level2"].replace(
            'throw new UnsupportedOperationException("pointer logic");', "left++;")
        self.assertIn("UNSAFE_UNFINISHED_LOOP", [warning["code"] for warning in
            validate_linked_bundle(unsafe, context, "java")["warnings"]])

    def test_min_stack_javascript_stages_keep_one_pair_stack(self):
        with Session(self.engine) as session:
            context = find_problem_context(session, "min-stack", "paired-minimums", "javascript")
        constructor = "var MinStack = function() {\n    this.stack = [];\n};\n"
        def method(name, arg, body):
            return f"MinStack.prototype.{name} = function({arg}) {{\n{body}\n}};\n"
        todo = lambda action: f"    // TODO: {action}.\n    throw new Error('complete {action}');"
        previous = "    const previous = this.stack.length ? this.stack[this.stack.length - 1][1] : Infinity;\n"
        def version(level):
            push = (todo("store value with minimum") if level == 1 else
                    previous + (todo("finish pair insertion") if level == 2 else
                    "    this.stack.push([value, Math.min(previous, value)]);"))
            pop = todo("remove the last pair") if level < 4 else "    this.stack.pop();"
            top = todo("read the last value") if level < 3 else "    return this.stack[this.stack.length - 1][0];"
            minimum = todo("read the last minimum") if level < 4 else "    return this.stack[this.stack.length - 1][1];"
            return (constructor + method("push", "value", push) + method("pop", "", pop) +
                    method("top", "", top) + method("getMin", "", minimum))
        levels = {"level1": version(1), "level2": version(2), "level3": version(3),
                  "solution": {**ANSWER, "code": version(4)}}
        self.assertEqual(validate_linked_bundle(levels, context, "javascript")["solution"]["code"],
                         levels["solution"]["code"].strip())
        minimal = deepcopy(levels)
        minimal["level1"] = minimal["level1"].replace(
            "    this.stack = [];", "    // TODO: set up stack storage.\n    throw new Error('NotImplemented');")
        self.assertIn("INCOMPATIBLE_LEVEL_DESIGN", [warning["code"] for warning in
            validate_linked_bundle(minimal, context, "javascript")["warnings"]])
