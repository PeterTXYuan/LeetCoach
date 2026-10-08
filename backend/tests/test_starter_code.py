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
        for slug, problem in CURATED_PROBLEMS.items():
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
                            self.assertIn("TODO", data["code"])
                            self.assertNotIn("```", data["code"])
                            signature = CURATED_PROBLEM_SPECS[slug]["submissionTemplates"][language].splitlines()[
                                {"python": 1, "java": 1, "javascript": 0, "cpp": 2}[language]
                            ].strip().rstrip(" {")
                            self.assertIn(signature, data["code"])
                            codes.append(data["code"])
                            if language == "python": ast.parse(data["code"])
                    self.assertEqual(len(set(codes)), 3)
                    self.assertLess(len(codes[0]), len(codes[1]))
                    self.assertLess(len(codes[1]), len(codes[2]))

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
        code = MockLLMProvider().generate_starter_code(context, "java", 3)
        calls = []
        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps({"code": code})))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        provider = GroqLLMProvider(api_key="test-only", model="test-model", client=client)
        with patch("app.main.get_llm_provider", return_value=provider):
            response = self.request(level=3, language="java")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertTrue(response.json()["isAiGenerated"])
        self.assertEqual(len(calls), 1)
        sent = json.loads(calls[0]["messages"][1]["content"])
        self.assertEqual((sent["context"]["approach"]["id"], sent["language"], sent["level"]),
                         ("hash-map", "java", 3))
        self.assertEqual(calls[0]["response_format"], {"type": "json_object"})
        for bad in ({"code": "```java\ncode\n```"}, {"code": "class Solution {}"}, ["wrong"]):
            client.chat.completions.create = lambda **_: SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(bad)))])
            with patch("app.main.get_llm_provider", return_value=provider):
                fallback = self.request(level=3, language="java")
            self.assertEqual(fallback.status_code, 200)
            self.assertFalse(fallback.json()["isAiGenerated"])
            self.assertTrue(fallback.json()["usedFallback"])
            self.assertIn("TODO", fallback.json()["code"])
        for usable in ({"code": code, "extra": "harmless"}, {"code": f"```java\n{code}\n```"}):
            client.chat.completions.create = lambda **_: SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=json.dumps(usable)))])
            with patch("app.main.get_llm_provider", return_value=provider):
                accepted = self.request(level=3, language="java")
            self.assertEqual(accepted.status_code, 200)
            self.assertTrue(accepted.json()["isAiGenerated"])
            self.assertNotIn("usedFallback", accepted.json())
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
