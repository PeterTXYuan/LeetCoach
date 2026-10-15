"""Contract-first Starter Code regressions. All Groq responses are fake/offline."""
import ast
import json
import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app.llm.base import StarterOutputDiagnostic, validate_starter_code
from app.llm.groq_provider import GroqLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.starter_contract import assemble_starter_plan, starter_slots, trusted_starter
from app.llm.starter_diagnostics import starter_observer
from app.services.problem_repository import find_problem_context
from evaluation.correctness import _sandbox_run, check_syntax, probe_sandbox


class StarterContractTests(DatabaseTestCase):
    def context(self, slug, approach, language):
        with Session(self.engine) as session:
            return find_problem_context(session, slug, approach, language)

    def assembled(self, context, language, level, line, slot="todo-1", guidance=None):
        baseline = trusted_starter(context, language, level)
        edit = {"slot": slot, "lines": [line]}
        if guidance is not None:
            edit["guidance"] = guidance
        return assemble_starter_plan({"edits": [edit]}, baseline,
                                     context["problem"]["submissionTemplate"]["code"], language, level)

    def fake_provider(self, payload):
        def create(**_kwargs):
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps(payload)))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        return GroqLLMProvider(api_key="offline", model="fake", client=client)

    def test_linked_list_level_three_adds_structure_beyond_guided(self):
        for slug, approach, new_structure in (
            ("reverse-linked-list", "iterative-pointers", "next_node = current.next"),
            ("merge-two-sorted-lists", "iterative-merge", "if first.val <= second.val:"),
        ):
            context = self.context(slug, approach, "python")
            provider = MockLLMProvider()
            guided = provider.generate_starter_code(context, "python", 2)
            strong = provider.generate_starter_code(context, "python", 3)
            self.assertNotIn(new_structure, guided)
            self.assertIn(new_structure, strong)
            self.assertIn("while ", guided)
            self.assertIn("while ", strong)
            self.assertIn("NotImplementedError", strong)
            ast.parse(strong)

    def test_java_3sum_each_level_keeps_exact_signature_and_compiles(self):
        context = self.context("3sum", "sort-and-two-pointers", "java")
        signature = "public List<List<Integer>> threeSum(int[] nums)"
        additions = {
            1: ("todo-1", "int inputLength = nums.length;"),
            2: ("todo-1", "int remaining = right - left;"),
            3: ("todo-1", "int currentFirst = nums[first];"),
        }
        with tempfile.TemporaryDirectory() as directory:
            for level, (slot, line) in additions.items():
                with self.subTest(level=level):
                    code = self.assembled(context, "java", level, line, slot)
                    self.assertEqual(code.count(signature), 1)
                    self.assertEqual(code.count("class Solution"), 1)
                    self.assertIn(line, code)
                    self.assertIn("UnsupportedOperationException", code)
                    self.assertEqual(check_syntax(code, "java", Path(directory))["status"],
                                     "PASS" if shutil.which("javac") else "NOT_RUN")

    def test_historical_full_file_and_malformed_java_are_rejected_without_template_mutation(self):
        context = self.context("3sum", "sort-and-two-pointers", "java")
        template = context["problem"]["submissionTemplate"]["code"]
        baseline = trusted_starter(context, "java", 1)
        historical = (
            "import java.util.*;\\nclass Solution {\\n"
            "public List<List<Integer>> threeSum(int[] nums) {\\n"
            "throw new UnsupportedOperationException(\\\"Complete the TODOs\\\");\\n}\\n}"
        )
        fully_qualified = baseline.replace("public List<List<Integer>>",
                                           "public java.util.List<java.util.List<Integer>>")
        for payload in ({"code": historical}, {"code": fully_qualified},
                        {"edits": [{"slot": "todo-1", "lines": ["int x = nums.length;\\nreturn results;"]}]},
                        {"edits": [{"slot": "todo-1", "lines": ["int x = nums.length;\nreturn results;"]}]}):
            with self.subTest(payload=payload):
                with self.assertRaises(StarterOutputDiagnostic):
                    GroqLLMProvider.parse_starter_content(json.dumps(payload), context, "java", 1)
                self.assertEqual(context["problem"]["submissionTemplate"]["code"], template)
                self.assertEqual(trusted_starter(context, "java", 1), baseline)

    def test_valid_edits_in_all_four_languages_preserve_template_and_are_executable(self):
        lines = {"python": "count = len(nums)", "java": "int count = nums.length;",
                 "javascript": "const count = nums.length;", "cpp": "int count = nums.size();"}
        for language, line in lines.items():
            with self.subTest(language=language):
                context = self.context("two-sum", "hash-map", language)
                baseline = trusted_starter(context, language, 1)
                code = self.assembled(context, language, 1, line)
                self.assertIn(line, code)
                self.assertEqual(len(code.splitlines()), len(baseline.splitlines()) + 1)
                for template_line in context["problem"]["submissionTemplate"]["code"].splitlines():
                    if "(" in template_line or template_line.strip().startswith("class "):
                        self.assertIn(template_line.strip().rstrip(" {"), code)
                if language == "python":
                    ast.parse(code)
                elif language in {"java", "javascript"}:
                    with tempfile.TemporaryDirectory() as directory:
                        result = check_syntax(code, language, Path(directory))
                    if shutil.which("javac" if language == "java" else "node"):
                        self.assertEqual(result["status"], "PASS", result)
                elif language == "cpp" and probe_sandbox()[0]:
                    with tempfile.TemporaryDirectory() as directory:
                        result = _sandbox_run(
                            "#include <bits/stdc++.h>\nusing namespace std;\n" + code,
                            "cpp",
                            "g++ -std=c++17 -fsyntax-only /work/case.cpp 2>&1 && "
                            "printf 'COMPILE_OK\\nLEETCOACH_RESULT=\\nPASS\\n'",
                            Path(directory), [{"language": "cpp"}],
                        )
                    self.assertEqual(result["status"], "PASS", result)

    def test_unknown_target_empty_generic_and_structural_edit_use_typed_reasons(self):
        context = self.context("two-sum", "hash-map", "python")
        baseline = trusted_starter(context, "python", 1)
        template = context["problem"]["submissionTemplate"]["code"]
        cases = [
            ({"edits": []}, "EMPTY_AI_CONTRIBUTION"),
            ({"edits": [{"slot": "missing", "lines": ["count = len(nums)"]}]}, "UNKNOWN_EDIT_TARGET"),
            ({"edits": [{"slot": "todo-1", "lines": ["# TODO: think"]}]}, "UNSAFE_STRUCTURE_MODIFICATION"),
            ({"edits": [{"slot": "todo-1", "lines": ["count = 0"]}]}, "EMPTY_AI_CONTRIBUTION"),
            ({"edits": [{"slot": "todo-1", "lines": ["seen = {}"]}]}, "UNSAFE_STRUCTURE_MODIFICATION"),
            ({"edits": [{"slot": "todo-1", "lines": ["def other(nums):"]}]}, "UNSAFE_STRUCTURE_MODIFICATION"),
            ({"edits": [{"slot": "todo-1", "lines": ["count = len(nums)"],
                         "guidance": "For each value, determine the complement needed to reach the target."}]},
             "EMPTY_AI_CONTRIBUTION"),
        ]
        for plan, reason in cases:
            with self.subTest(plan=plan):
                with self.assertRaises(StarterOutputDiagnostic) as caught:
                    assemble_starter_plan(plan, baseline, template, "python", 1)
                self.assertEqual(caught.exception.reason, reason)

    def test_two_sum_recipe_unreachable_todo_and_conceptual_guidance(self):
        context = self.context("two-sum", "hash-map", "python")
        baseline = trusted_starter(context, "python", 2)
        template = context["problem"]["submissionTemplate"]["code"]
        leaked = baseline.replace(
            "# TODO: Determine which earlier value could complete the target pair.",
            "# TODO: If complement is already in seen, return the pair of indices.\n"
            "            # TODO: Store the current number and index in seen.")
        with self.assertRaises(StarterOutputDiagnostic) as caught:
            validate_starter_code(leaked, template, "python", 2)
        self.assertEqual(caught.exception.reason, "ALGORITHM_RECIPE_IN_COMMENTS")
        unreachable = baseline.replace(
            "# TODO: Determine which earlier value could complete the target pair.",
            "# TODO: Think about an earlier value.\n"
            "            raise NotImplementedError('Complete the TODOs')\n"
            "            # TODO: Consider later iterations.")
        with self.assertRaises(StarterOutputDiagnostic) as caught:
            validate_starter_code(unreachable, template, "python", 2)
        self.assertEqual(caught.exception.reason, "UNREACHABLE_TODO")
        good = self.assembled(context, "python", 2, "gap = target - current",
                              guidance="What information might help a later pass?")
        self.assertIn("gap = target - current", good)
        self.assertIn("# TODO: What information might help a later pass?", good)

    def test_min_stack_pair_plan_progression_and_mixed_fallback(self):
        context = self.context("min-stack", "paired-minimums", "javascript")
        plan = {"edits": [{"slot": "todo-2", "lines": ["const pairCount = this.pairs.length;"]}]}
        codes = []
        for level in (1, 2, 3):
            baseline = trusted_starter(context, "javascript", level)
            ai = self.assembled(context, "javascript", level,
                                "const pairCount = this.pairs.length;", slot="todo-2")
            codes.append(ai)
            self.assertIn("this.pairs = []", ai)
            self.assertIn("throw new Error", ai)
            self.assertEqual(ai.count("MinStack.prototype."), 4)
            for row in baseline.splitlines():
                self.assertIn(row.strip(), [candidate.strip() for candidate in ai.splitlines()])
        self.assertIn("const previousPair", codes[1])
        self.assertIn("const previousPair", codes[2])
        self.assertIn("if (previousPair)", codes[2])
        provider = self.fake_provider(plan)
        with patch("app.main.get_llm_provider", return_value=provider):
            result = self.client.post("/api/problems/min-stack/approaches/paired-minimums/starter-code",
                                      json={"language": "javascript", "level": 3})
        self.assertTrue(result.json()["isAiGenerated"])
        self.assertIn("this.pairs = []", result.json()["code"])
        # An invalid plan on any independently requested level reuses the same
        # pair-stack baseline and never changes its API identity.
        with patch("app.main.get_llm_provider", return_value=self.fake_provider({"edits": []})):
            fallback = self.client.post("/api/problems/min-stack/approaches/paired-minimums/starter-code",
                                        json={"language": "javascript", "level": 2})
        self.assertTrue(fallback.json()["usedFallback"])
        self.assertIn("this.pairs = []", fallback.json()["code"])

    def test_maximum_depth_guided_recurrence_is_not_accepted(self):
        context = self.context("maximum-depth-of-binary-tree", "depth-first-search", "python")
        baseline = trusted_starter(context, "python", 2)
        template = context["problem"]["submissionTemplate"]["code"]
        historical = (
            "class Solution:\n"
            "    def maxDepth(self, root: Optional[TreeNode]) -> int:\n"
            "        if not root:\n            return 0\n"
            "        left_depth = self.maxDepth(root.left)\n"
            "        # TODO: compute depth of right subtree\n"
            "        right_depth = self.maxDepth(root.right)\n"
            "        # TODO: return 1 plus the larger of left_depth and right_depth\n"
            "        raise NotImplementedError('Complete the TODOs')"
        )
        with self.assertRaises(StarterOutputDiagnostic) as caught:
            validate_starter_code(historical, template, "python", 2)
        self.assertEqual(caught.exception.reason, "ALGORITHM_RECIPE_IN_COMMENTS")
        with self.assertRaises(StarterOutputDiagnostic) as caught:
            assemble_starter_plan({"edits": [{"slot": "todo-1", "lines": [
                "right_depth = self.maxDepth(root.right)"
            ]}]}, baseline, template, "python", 2)
        self.assertEqual(caught.exception.reason, "UNSAFE_STRUCTURE_MODIFICATION")
        self.assertEqual(ast.parse(baseline).__class__.__name__, "Module")

    def test_route_rejects_full_file_response_with_safe_fallback_and_diagnostic(self):
        context = self.context("3sum", "sort-and-two-pointers", "java")
        baseline = trusted_starter(context, "java", 1)
        provider = self.fake_provider({"code": baseline.replace("public List<List<Integer>>",
                                                                "public java.util.List<java.util.List<Integer>>")})
        events = []
        token = starter_observer.set(events.append)
        try:
            with patch("app.main.get_llm_provider", return_value=provider):
                response = self.client.post("/api/problems/3sum/approaches/sort-and-two-pointers/starter-code",
                                            json={"language": "java", "level": 1})
        finally:
            starter_observer.reset(token)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["code"], baseline)
        self.assertFalse(response.json()["isAiGenerated"])
        self.assertTrue(response.json()["usedFallback"])
        self.assertEqual(events[-1]["reason"], "INVALID_GENERATION_PLAN")
