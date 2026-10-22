import ast
import json
from types import SimpleNamespace
from unittest.mock import patch

from db_test_support import DatabaseTestCase
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.llm.base import (
    ProviderConfigurationError, ProviderOutputError, ProviderUnavailableError,
    validate_starter_code,
)
from app.llm.groq_provider import GroqLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.services.problem_repository import find_problem_context
from app.models import Approach, Problem, ProblemSubmissionTemplate
from app.stable_data import CURATED_PROBLEMS, CURATED_PROBLEM_SPECS


class StarterCodeTests(DatabaseTestCase):
    def request(self, slug="two-sum", approach="hash-map", language="python", level=1):
        return self.client.post(
            f"/api/problems/{slug}/approaches/{approach}/starter-code",
            json={"language": language, "level": level},
        )

    def test_all_curated_approaches_languages_and_levels_are_offline_and_progressive(self):
        # These detailed deterministic fixtures predate the catalog expansion.
        # New problems use generic offline shells and receive linked content in Groq mode.
        for slug, problem in list(CURATED_PROBLEMS.items())[:20]:
            for approach in problem["approaches"]:
                for language in ("python", "java", "javascript", "cpp"):
                    codes = []
                    for level in (1, 2, 3):
                        with self.subTest(slug=slug, approach=approach["id"], language=language, level=level):
                            result = self.request(slug, approach["id"], language, level)
                            self.assertEqual(result.status_code, 200, result.text)
                            data = result.json()
                            self.assertEqual((data["slug"], data["approachId"], data["language"], data["level"]),
                                             (slug, approach["id"], language, level))
                            self.assertFalse(data["isAiGenerated"])
                            self.assertEqual(data["policyVersion"], 6)
                            self.assertEqual(data["levelName"], {1: "Kickstart", 2: "Guided", 3: "Strong Scaffold"}[level])
                            self.assertIn("TODO", data["code"])
                            self.assertNotIn("```", data["code"])
                            signature = CURATED_PROBLEM_SPECS[slug]["submissionTemplates"][language].splitlines()[
                                {"python": 1, "java": 1, "javascript": 0, "cpp": 2}[language]
                            ].strip().rstrip(" {")
                            self.assertIn(signature, data["code"])
                            codes.append(data["code"])
                            if language == "python": ast.parse(data["code"])
                    self.assertEqual(len(set(codes)), 3)
                    self.assertNotRegex(codes[0], r"(?m)^\s*(?:for|while|if)\b")
                    self.assertNotIn("implement the selected approach", codes[0].lower())
                    self.assertNotEqual(codes[0].strip(), CURATED_PROBLEM_SPECS[slug]["submissionTemplates"][language].strip())
                    initial_setup = [line.strip() for line in codes[0].splitlines()
                                     if line.strip() and "=" in line
                                     and not line.lstrip().startswith(("#", "//", "import ", "from ", "using "))
                                     and not any(token in line for token in ("class ", "def ", "function", "throw ", "raise "))]
                    for setup in initial_setup:
                        self.assertIn(setup, codes[1])
                        self.assertIn(setup, codes[2])
                    if slug != "min-stack":
                        self.assertRegex(codes[2], r"\b(?:for|while|if)\s*(?:\(|\w)")

    def test_exact_db_approach_and_submission_template_reach_provider(self):
        with Session(self.engine) as session, session.begin():
            approach_row = session.scalar(select(Approach).join(Problem).where(
                Problem.slug == "two-sum", Approach.approach_key == "brute-force"))
            template_row = session.scalar(select(ProblemSubmissionTemplate).join(Problem).where(
                Problem.slug == "two-sum", ProblemSubmissionTemplate.language == "java"))
            approach_row.summary = "DB-only baseline summary"
            template_row.code = template_row.code.replace("class Solution", "class DatabaseSolution")
        captured = []
        class RecordingProvider(MockLLMProvider):
            def generate_starter_code(self, context, language, level):
                captured.append((context, language, level))
                return super().generate_starter_code(context, language, level)
        with patch("app.main.get_llm_provider", return_value=RecordingProvider()):
            result = self.request("two-sum", "brute-force", "java", 2)
        self.assertEqual(result.status_code, 200, result.text)
        context, language, level = captured[0]
        self.assertEqual((context["problem"]["slug"], context["approach"]["id"], language, level),
                         ("two-sum", "brute-force", "java", 2))
        self.assertTrue(context["problem"]["constraints"])
        self.assertTrue(context["problem"]["examples"])
        self.assertEqual(context["approach"]["summary"], "DB-only baseline summary")
        self.assertIn("class DatabaseSolution", context["problem"]["submissionTemplate"]["code"])
        self.assertIn("class DatabaseSolution", result.json()["code"])

    def test_validation_and_sanitized_errors(self):
        for slug, approach in (("missing", "hash-map"), ("two-sum", "missing")):
            self.assertEqual(self.request(slug, approach).status_code, 404)
        self.assertEqual(self.request(language="ruby").status_code, 400)
        self.assertEqual(self.request(language="JAVA").json()["language"], "java")
        for level in (0, 4, "2", 2.0, True, None):
            self.assertEqual(self.request(level=level).status_code, 422)
        for exception, status in ((ProviderConfigurationError("private"), 503),
                                  (ProviderUnavailableError("private"), 503),
                                  (ProviderOutputError("private"), 502)):
            with patch("app.main.get_llm_provider", side_effect=exception):
                response = self.request()
            self.assertEqual(response.status_code, status)
            self.assertNotIn("private", response.text)

    def test_structured_groq_request_without_network(self):
        with Session(self.engine) as session:
            context = find_problem_context(session, "two-sum", "hash-map", "java")
        plan = {"edits": [{"slot": "todo-1", "lines": ["int remainingSlots = nums.length - index;"]}]}
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps(plan)))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        provider = GroqLLMProvider(api_key="test-only", model="test-model", client=client)
        with patch("app.main.get_llm_provider", return_value=provider):
            response = self.request(level=3, language="java")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["isAiGenerated"])
        self.assertEqual(response.json()["policyVersion"], 6)
        self.assertEqual(len(calls), 1)
        sent = json.loads(calls[0]["messages"][1]["content"])
        self.assertEqual((sent["context"]["approach"]["id"], sent["language"], sent["level"]),
                         ("hash-map", "java", 3))
        self.assertEqual(calls[0]["response_format"], {"type": "json_object"})
        self.assertIn("baselineScaffold", sent)
        self.assertTrue(sent["editableSlots"])
        for bad in ({"code": "```java\ncode\n```"}, {"code": "class Solution {}"}, ["wrong"]):
            client.chat.completions.create = lambda **_: SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(bad)))])
            with patch("app.main.get_llm_provider", return_value=provider):
                fallback = self.request(level=3, language="java")
            self.assertEqual(fallback.status_code, 200)
            self.assertFalse(fallback.json()["isAiGenerated"])
            self.assertTrue(fallback.json()["usedFallback"])
            self.assertIn("TODO", fallback.json()["code"])
        self.assertIn("int remainingSlots = nums.length - index;", response.json()["code"])
        self.assertNotIn("usedFallback", response.json())
        client.chat.completions.create = lambda **_: (_ for _ in ()).throw(TimeoutError("secret"))
        with patch("app.main.get_llm_provider", return_value=provider):
            response = self.request(level=3, language="java")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["usedFallback"])
        self.assertNotIn("secret", response.text)

    def test_output_validator_rejects_changed_or_fenced_code(self):
        template = CURATED_PROBLEM_SPECS["two-sum"]["submissionTemplates"]["python"]
        for bad in ("", "```python\n" + template + "\n```",
                    "class Solution:\n    def other():\n        # TODO\n        pass",
                    template.replace("pass", "# TODO: review\n        return [0, 1]")):
            with self.assertRaises(ProviderOutputError):
                validate_starter_code(bad, template, "python", 2)

    def test_validator_blocks_obvious_solution_leaks_and_broken_design_shells(self):
        java = CURATED_PROBLEM_SPECS["two-sum"]["submissionTemplates"]["java"]
        commented_answer = """class Solution {
    public int[] twoSum(int[] nums, int target) {
        java.util.Map<Integer, Integer> seen = new java.util.HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            int complement = target - nums[i];
            // TODO: think about this
            // if (seen.containsKey(complement)) {
            // return new int[]{seen.get(complement), i};
            // seen.put(nums[i], i);
        }
        throw new UnsupportedOperationException("Complete the TODOs");
    }
}"""
        completed_then_throw = """class Solution {
    public int[] twoSum(int[] nums, int target) {
        // TODO: review this solution
        java.util.Map<Integer, Integer> seen = new java.util.HashMap<>();
        for (int i = 0; i < nums.length; i++) {
            int complement = target - nums[i];
            if (seen.containsKey(complement)) return new int[]{seen.get(complement), i};
            seen.put(nums[i], i);
        }
        return new int[] {};
        throw new UnsupportedOperationException("Complete the TODOs");
    }
}"""
        decorative = java.replace("\n\n", "\n        // TODO: review this complete code.\n"
                                  "        return new int[] {};\n"
                                  "        throw new UnsupportedOperationException(\"Complete the TODOs\");\n", 1)
        for bad in (commented_answer, completed_then_throw, decorative):
            with self.subTest(bad=bad[:35]), self.assertRaises(ProviderOutputError):
                validate_starter_code(bad, java, "java", 3)

        with Session(self.engine) as session:
            two_sum_context = find_problem_context(session, "two-sum", "hash-map", "java")
        mock = MockLLMProvider()
        minimal = mock.generate_starter_code(two_sum_context, "java", 1)
        guided = mock.generate_starter_code(two_sum_context, "java", 2)
        early_loop = minimal.replace(
            'throw new UnsupportedOperationException("Complete the TODOs");',
            'for (int i = 0; i < nums.length; i++) { /* TODO: decide */ }\n'
            '        throw new UnsupportedOperationException("Complete the TODOs");', 1)
        with self.assertRaises(ProviderOutputError):
            validate_starter_code(early_loop, java, "java", 1)
        self.assertIn("for (", guided)
        invalid_condition = guided.replace("for (int index = 0; index < nums.length; index++) {",
                                           "if (/* TODO */) {", 1)
        with self.assertRaises(ProviderOutputError):
            validate_starter_code(invalid_condition, java, "java", 2)
        bare_kickstart = java.replace("{\n\n", "{\n        // TODO: decide what to do.\n"
                                      '        throw new UnsupportedOperationException("Complete the TODOs");\n', 1)
        with self.assertRaises(ProviderOutputError):
            validate_starter_code(bare_kickstart, java, "java", 1)
        with self.assertRaises(ProviderOutputError):
            validate_starter_code(bare_kickstart.replace("// TODO: decide what to do.",
                                                         "/* TODO: decide what to do. */"), java, "java", 1)

        min_stack = CURATED_PROBLEM_SPECS["min-stack"]["submissionTemplates"]["python"]
        with Session(self.engine) as session:
            context = find_problem_context(session, "min-stack", "paired-minimums", "python")
        valid_design = MockLLMProvider().generate_starter_code(context, "python", 3)
        broken_design = valid_design.replace("    def getMin(self) -> int:", "    def minimum(self) -> int:")
        with self.assertRaises(ProviderOutputError):
            validate_starter_code(broken_design, min_stack, "python", 3)

    def test_accepts_teaching_depth_examples_in_each_language(self):
        mock = MockLLMProvider()
        for slug, approach, language in (
            ("two-sum", "hash-map", "java"),
            ("3sum", "sort-and-two-pointers", "python"),
            ("min-stack", "paired-minimums", "javascript"),
            ("maximum-depth-of-binary-tree", "breadth-first-search", "cpp"),
        ):
            with Session(self.engine) as session:
                context = find_problem_context(session, slug, approach, language)
            codes = [mock.generate_starter_code(context, language, level) for level in (1, 2, 3)]
            template = context["problem"]["submissionTemplate"]["code"]
            for level, code in enumerate(codes, start=1):
                with self.subTest(slug=slug, approach=approach, language=language, level=level):
                    self.assertEqual(validate_starter_code(code, template, language, level), code)
                    self.assertIn("TODO", code)
            self.assertEqual(len(set(codes)), 3)
            if slug == "two-sum":
                self.assertIn("Map<Integer, Integer>", codes[0])
                self.assertNotIn("for (", codes[0])
                self.assertIn("for (", codes[1])
                self.assertIn("int current =", codes[1])
                self.assertNotIn("complement =", codes[1])
                self.assertIn("Map<Integer, Integer>", codes[2])
                self.assertIn("complement", codes[2])
                self.assertNotIn("seen.put(", codes[2])
            if slug == "3sum":
                self.assertIn("nums.sort()", codes[0])
                self.assertIn("results = []", codes[0])
                self.assertNotIn("for first", codes[0])
                self.assertIn("for first", codes[1])
                self.assertIn("left, right =", codes[1])
                self.assertNotIn("while left < right", codes[1])
                self.assertIn("while left < right", codes[2])
                self.assertIn("total =", codes[2])
                self.assertIn("elif total < 0", codes[2])
                self.assertNotIn("left +=", codes[2])
                self.assertNotIn("results.append", codes[2])
            if slug == "min-stack":
                self.assertIn("MinStack.prototype.getMin", codes[2])
                self.assertTrue(all("this.pairs = []" in code for code in codes))
                self.assertTrue(all("this.minimums" not in code for code in codes))
                self.assertIn("previousPair", codes[1])
                self.assertIn("if (previousPair)", codes[2])

    def test_min_stack_java_retains_all_methods_and_shared_state(self):
        with Session(self.engine) as session:
            context = find_problem_context(session, "min-stack", "paired-minimums", "java")
        codes = [MockLLMProvider().generate_starter_code(context, "java", level)
                 for level in (1, 2, 3)]
        for code in codes:
            for signature in ("public MinStack()", "public void push(int val)",
                              "public void pop()", "public int top()", "public int getMin()"):
                self.assertIn(signature, code)
            self.assertIn("Deque<int[]> pairs", code)
            self.assertNotIn("Deque<Integer> minimums", code)
        self.assertNotIn("previousPair", codes[0])
        self.assertIn("previousPair", codes[1])
        self.assertIn("if (previousPair != null)", codes[2])
        self.assertNotIn("pairs.push(", codes[2])
