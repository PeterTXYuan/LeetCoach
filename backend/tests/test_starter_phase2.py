"""Phase 2 Starter Code quality regressions; all provider responses are offline fakes."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app.llm.base import StarterOutputDiagnostic, validate_starter_code
from app.llm.groq_provider import GroqLLMProvider, STARTER_SYSTEM_PROMPT, _starter_design
from app.llm.mock_provider import MockLLMProvider
from app.services.problem_repository import find_problem_context


class StarterPhase2Tests(DatabaseTestCase):
    def context(self, slug, approach, language):
        with Session(self.engine) as session:
            return find_problem_context(session, slug, approach, language)

    def mock(self, context, language, level):
        return MockLLMProvider().generate_starter_code(context, language, level)

    def assert_rejected(self, code, context, language, level, reason):
        with self.assertRaises(StarterOutputDiagnostic) as caught:
            validate_starter_code(code, context["problem"]["submissionTemplate"]["code"], language, level)
        self.assertEqual(caught.exception.reason, reason)

    def test_missing_placeholders_and_decorative_throw(self):
        python = self.context("two-sum", "hash-map", "python")
        code = self.mock(python, "python", 1).replace(
            'raise NotImplementedError("Complete the TODOs")', 'raise ValueError("No answer")')
        self.assert_rejected(code, python, "python", 1, "MISSING_UNFINISHED_PLACEHOLDER")

        java = self.context("3sum", "sort-and-two-pointers", "java")
        code = self.mock(java, "java", 1).replace(
            'throw new UnsupportedOperationException("Complete the TODOs");', 'return results;')
        self.assert_rejected(code, java, "java", 1, "MISSING_UNFINISHED_PLACEHOLDER")

        javascript = self.context("min-stack", "paired-minimums", "javascript")
        code = self.mock(javascript, "javascript", 1).replace(
            'throw new Error("Complete the TODOs");', '')
        self.assert_rejected(code, javascript, "javascript", 1, "MISSING_UNFINISHED_PLACEHOLDER")
        partly_silent = self.mock(javascript, "javascript", 1).replace(
            'throw new Error("Complete the TODOs");', '', 1)
        self.assert_rejected(partly_silent, javascript, "javascript", 1, "SILENT_UNFINISHED_METHOD")

        two_sum_java = self.context("two-sum", "hash-map", "java")
        complete_return = self.mock(two_sum_java, "java", 3).replace(
            'throw new UnsupportedOperationException("Complete the TODOs");',
            'return new int[] {};\n        throw new UnsupportedOperationException("Complete the TODOs");')
        self.assert_rejected(complete_return, two_sum_java, "java", 3, "APPARENT_COMPLETE_SOLUTION")

        for language in ("python", "java", "javascript", "cpp"):
            context = self.context("min-stack", "paired-minimums", language)
            for level in (1, 2, 3):
                code = self.mock(context, language, level)
                self.assertEqual(validate_starter_code(
                    code, context["problem"]["submissionTemplate"]["code"], language, level), code)

    def test_commented_declarations_and_direct_recipe(self):
        js = self.context("min-stack", "paired-minimums", "javascript")
        code = self.mock(js, "javascript", 2).replace(
            '    throw new Error("Complete the TODOs");',
            '    // const previousMinimum = this.pairs.length ? this.pairs.at(-1)[1] : val;\n'
            '    // const newMinimum = Math.min(val, previousMinimum);\n'
            '    throw new Error("Complete the TODOs");', 1)
        self.assert_rejected(code, js, "javascript", 2, "COMMENTED_OUT_ALGORITHM")

        for language, comments in (
            ("java", "// int complement = target - current;\n        // int earlier = seen.get(complement);"),
            ("cpp", "// auto found = seen.find(complement);\n        // int earlier = found->second;"),
        ):
            context = self.context("two-sum", "hash-map", language)
            code = self.mock(context, language, 3)
            placeholder = ('throw new UnsupportedOperationException' if language == "java"
                           else 'throw logic_error')
            code = code.replace('        ' + placeholder, '        ' + comments + '\n        ' + placeholder, 1)
            self.assert_rejected(code, context, language, 3, "COMMENTED_OUT_ALGORITHM")

        python = self.context("two-sum", "hash-map", "python")
        code = self.mock(python, "python", 3)
        code = code.replace(
            '# TODO: decide whether the complement was seen earlier.',
            '# TODO: if complement in seen, return [seen[complement], index]')
        code = code.replace(
            '# TODO: construct indices or remember this value and position.',
            '# TODO: otherwise store the current number and index in seen')
        self.assert_rejected(code, python, "python", 3, "ALGORITHM_RECIPE_IN_COMMENTS")

        good = self.mock(python, "python", 3).replace(
            '# TODO: decide whether the complement was seen earlier.',
            '# TODO: Decide whether an earlier value can complete the pair.')
        good = good.replace(
            '# TODO: construct indices or remember this value and position.',
            '# TODO: Update information available to later iterations.')
        self.assertEqual(validate_starter_code(
            good, python["problem"]["submissionTemplate"]["code"], "python", 3), good)

    def test_paired_minimums_storage_and_independent_mixed_levels(self):
        scan = self.context("min-stack", "scan-for-minimum", "javascript")
        self.assertIn("ordinary value stack", _starter_design(scan))
        self.assertTrue(all("this.values = []" in self.mock(scan, "javascript", level)
                            for level in (1, 2, 3)))
        for language, marker in (("python", "self.pairs = []"),
                                 ("java", "Deque<int[]> pairs"),
                                 ("javascript", "this.pairs = []"),
                                 ("cpp", "vector<pair<int, int>> pairs")):
            context = self.context("min-stack", "paired-minimums", language)
            codes = [self.mock(context, language, level) for level in (1, 2, 3)]
            self.assertEqual(len(set(codes)), 3)
            self.assertTrue(all(marker in code for code in codes))
            self.assertTrue(all("minimums" not in code and "self.values" not in code and
                                "this.values" not in code for code in codes))
            template = context["problem"]["submissionTemplate"]["code"]
            for code in codes:
                for line in template.splitlines():
                    if "(" in line:
                        self.assertIn(line.strip().rstrip(" {"), code)
            if language == "cpp":
                self.assertTrue(all("#include <stdexcept>" in code and
                                    "#include <utility>" in code for code in codes))

        context = self.context("min-stack", "paired-minimums", "javascript")
        generated = [self.mock(context, "javascript", level) for level in (1, 2, 3)]
        for sources in ((True, True, True), (False, True, False),
                        (True, False, True), (False, False, False)):
            calls = []
            def create(**kwargs):
                sent = json.loads(kwargs["messages"][1]["content"])
                level = sent["level"]
                calls.append(level)
                self.assertIn("one stack of (value, minimum-so-far) pairs", sent["starterDesign"])
                content = json.dumps({"edits": [{"slot": "todo-2", "lines": [
                    "const pairCount = this.pairs.length;"
                ]}]} if sources[level - 1] else {"code": "bad"})
                return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
            client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
            provider = GroqLLMProvider(api_key="offline", model="fake", client=client)
            responses = []
            with patch("app.main.get_llm_provider", return_value=provider):
                for level in (1, 2, 3):
                    result = self.client.post(
                        "/api/problems/min-stack/approaches/paired-minimums/starter-code",
                        json={"language": "javascript", "level": level})
                    self.assertEqual(result.status_code, 200, result.text)
                    responses.append(result.json())
            self.assertEqual(calls, [1, 2, 3])
            self.assertEqual([item["isAiGenerated"] for item in responses], list(sources))
            self.assertTrue(all("this.pairs = []" in item["code"] for item in responses))
            self.assertTrue(all("this.values" not in item["code"] and "this.minimums" not in item["code"]
                                for item in responses))
            self.assertTrue(all(item["policyVersion"] == 5 for item in responses))
        self.assertIn("backend already owns the authoritative submission signature", STARTER_SYSTEM_PROMPT)
        self.assertIn("lines array must contain exactly ONE", STARTER_SYSTEM_PROMPT)
        self.assertIn("not state an if/lookup/return/store recipe", STARTER_SYSTEM_PROMPT)

