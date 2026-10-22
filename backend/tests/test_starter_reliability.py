"""Bounded, offline checks that unfinished trusted scaffolds fail loudly."""
import ast
import tempfile
from pathlib import Path

from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app.llm.mock_provider import MockLLMProvider
from app.services.problem_repository import find_problem_context
from app.stable_data import CURATED_PROBLEMS
from evaluation.correctness import _sandbox_run, check_syntax, probe_sandbox


PRELUDE = """from typing import List, Optional
class ListNode:
    def __init__(self, val=0, next=None):
        self.val, self.next = val, next
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val, self.left, self.right = val, left, right
"""


class StarterReliabilityTests(DatabaseTestCase):
    def scaffold(self, slug, approach, language, level):
        with Session(self.engine) as session:
            context = find_problem_context(session, slug, approach, language)
        return MockLLMProvider().generate_starter_code(context, language, level)

    def test_confirmed_defects_and_base_case_guidance(self):
        binary = self.scaffold("binary-search", "binary-search", "cpp", 2)
        self.assertRegex(binary, r"while \(left <= right\) \{\s*// TODO:[^\n]+\n\s*throw logic_error")
        linked = self.scaffold("reverse-linked-list", "iterative-pointers", "python", 2)
        tree = ast.parse(linked)
        loop = next(node for node in ast.walk(tree) if isinstance(node, ast.While))
        self.assertTrue(any(isinstance(node, ast.Raise) for node in loop.body))
        self.assertFalse(any(isinstance(node, ast.Pass) for node in loop.body))
        depth = self.scaffold("maximum-depth-of-binary-tree", "depth-first-search", "python", 2)
        base_branch = next(node for node in ast.walk(ast.parse(depth)) if isinstance(node, ast.If))
        self.assertTrue(any(isinstance(node, ast.Raise) for node in base_branch.body))
        self.assertIn("base-case result for the empty input", depth)
        self.assertNotIn("Compute both child depths", depth)

    def test_all_768_scaffolds_and_while_placeholders(self):
        count = 0
        for slug, problem in CURATED_PROBLEMS.items():
            for approach in problem["approaches"]:
                for language in ("python", "java", "javascript", "cpp"):
                    for level in (1, 2, 3):
                        code = self.scaffold(slug, approach["id"], language, level)
                        count += 1
                        with self.subTest(slug=slug, approach=approach["id"],
                                          language=language, level=level):
                            self.assertIn("TODO", code)
                            if language == "python":
                                for loop in (node for node in ast.walk(ast.parse(code))
                                             if isinstance(node, ast.While)):
                                    self.assertTrue(any(isinstance(node, (ast.Raise, ast.Break))
                                                        for node in ast.walk(ast.Module(
                                                            body=loop.body, type_ignores=[]))))
                            else:
                                # Static coverage supplements the bounded runtime probes below.
                                lines = code.splitlines()
                                for index, line in enumerate(lines):
                                    if line.lstrip().startswith("while ("):
                                        indent = len(line) - len(line.lstrip())
                                        body = []
                                        for following in lines[index + 1:]:
                                            if following.strip() == "}" and len(following) - len(following.lstrip()) == indent:
                                                break
                                            body.append(following)
                                        self.assertTrue(any("throw " in row for row in body))
        self.assertEqual(count, 768)

    def test_representative_unfinished_paths_in_isolated_runtime(self):
        available, reason = probe_sandbox()
        if not available:
            self.skipTest(reason)
        cases = (
            ("binary-search", "binary-search", 2, "Solution().search([1, 3, 5], 2)"),
            ("binary-search", "binary-search", 2, "Solution().search([], 2)"),
            ("reverse-linked-list", "iterative-pointers", 2, "Solution().reverseList(ListNode(1, ListNode(2)))"),
            ("reverse-linked-list", "iterative-pointers", 2, "Solution().reverseList(None)"),
            ("maximum-depth-of-binary-tree", "depth-first-search", 2, "Solution().maxDepth(None)"),
            ("maximum-depth-of-binary-tree", "depth-first-search", 2, "Solution().maxDepth(TreeNode(1))"),
            ("number-of-islands", "depth-first-flood-fill", 3, "Solution().numIslands([['1']])"),
            ("number-of-islands", "depth-first-flood-fill", 3, "Solution().numIslands([])"),
            ("min-stack", "paired-minimums", 3, "MinStack().push(1)"),
            ("valid-parentheses", "replace-pairs", 2, "Solution().isValid('()')"),
            ("two-sum-ii-input-array-is-sorted", "binary-search-complement", 2,
             "Solution().twoSum([2, 7, 11], 9)"),
            ("climbing-stairs", "memoized-recursion", 2, "Solution().climbStairs(1)"),
        )
        with tempfile.TemporaryDirectory() as directory:
            for slug, approach, level, expression in cases:
                with self.subTest(slug=slug, approach=approach, level=level, expression=expression):
                    code = self.scaffold(slug, approach, "python", level)
                    source = (PRELUDE + "\n" + code + "\ntry:\n    " + expression +
                              "\nexcept NotImplementedError:\n    verdict = 'PASS'\n"
                              "except Exception:\n    verdict = 'FAIL'\n"
                              "else:\n    verdict = 'FAIL'\n"
                              "print('LEETCOACH_RESULT=' + json.dumps([{'status': verdict}]))\n")
                    source = "import json\n" + source
                    result = _sandbox_run(source, "py",
                                          "ulimit -t 3; ulimit -v 393216; "
                                          "timeout 2s /usr/bin/python3 -I /work/case.py",
                                          Path(directory))
                    self.assertEqual(result["status"], "PASS", result)

    def test_cpp_binary_search_missing_target_and_empty_input_are_bounded(self):
        available, reason = probe_sandbox()
        if not available:
            self.skipTest(reason)
        code = self.scaffold("binary-search", "binary-search", "cpp", 2)
        source = ("#include <bits/stdc++.h>\nusing namespace std;\n" + code +
                  "\nint main() {\n    cout << \"LEETCOACH_RESULT=\\n\";\n"
                  "    for (auto nums : {vector<int>{1,3,5}, vector<int>{}}) {\n"
                  "        try { Solution().search(nums, 2); cout << \"FAIL\\n\"; }\n"
                  "        catch (const logic_error&) { cout << \"PASS\\n\"; }\n"
                  "    }\n}\n")
        with tempfile.TemporaryDirectory() as directory:
            result = _sandbox_run(source, "cpp", "ulimit -t 5; ulimit -v 786432; "
                                  "g++ -std=c++17 -O0 -o /work/case /work/case.cpp 2>&1 && "
                                  "printf 'COMPILE_OK\\n' && timeout 2s /work/case",
                                  Path(directory), [{"input": "missing"}, {"input": "empty"}])
        self.assertEqual(result["status"], "PASS", result)

        islands = self.scaffold("number-of-islands", "depth-first-flood-fill", "cpp", 1)
        source = ("#include <bits/stdc++.h>\nusing namespace std;\n" + islands +
                  "\nint main() { vector<vector<char>> grid;\n"
                  "    cout << \"LEETCOACH_RESULT=\\n\";\n"
                  "    try { Solution().numIslands(grid); cout << \"FAIL\\n\"; }\n"
                  "    catch (const logic_error&) { cout << \"PASS\\n\"; }\n}\n")
        with tempfile.TemporaryDirectory() as directory:
            result = _sandbox_run(source, "cpp", "ulimit -t 5; ulimit -v 786432; "
                                  "g++ -std=c++17 -O0 -o /work/case /work/case.cpp 2>&1 && "
                                  "printf 'COMPILE_OK\\n' && timeout 2s /work/case",
                                  Path(directory), [{"input": "empty grid"}])
        self.assertEqual(result["status"], "PASS", result)

    def test_representative_java_and_javascript_syntax(self):
        with tempfile.TemporaryDirectory() as directory:
            for slug, approach in (("binary-search", "binary-search"),
                                   ("reverse-linked-list", "iterative-pointers"),
                                   ("maximum-depth-of-binary-tree", "depth-first-search"),
                                   ("number-of-islands", "depth-first-flood-fill")):
                for language in ("java", "javascript"):
                    for level in (1, 2, 3):
                        with self.subTest(slug=slug, language=language, level=level):
                            code = self.scaffold(slug, approach, language, level)
                            if language == "java" and slug == "reverse-linked-list":
                                code += "\nclass ListNode { int val; ListNode next; }\n"
                            if language == "java" and slug == "maximum-depth-of-binary-tree":
                                code += "\nclass TreeNode { int val; TreeNode left, right; }\n"
                            result = check_syntax(code, language, Path(directory))
                            self.assertIn(result["status"], {"PASS", "NOT_RUN"}, result)
