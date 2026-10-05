"""Offline provider and DB-grounded hint route regression tests."""
import json
import os
import socket
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app.llm.base import (
    LEVEL_CHARACTER_LIMITS, LEVEL_WORD_LIMITS, ProviderConfigurationError,
    ProviderOutputError, ProviderUnavailableError, SHORT_FALLBACK_HINTS,
    validate_hints,
)
from app.llm.groq_provider import GroqLLMProvider, SYSTEM_PROMPT
from app.llm.mock_provider import MockLLMProvider
from app.llm.provider_factory import get_llm_provider
from app.main import APPROACH_UNAVAILABLE_DETAIL, UNAVAILABLE_DETAIL
from app.models import Approach, Problem
from app.services.problem_repository import find_hint_problem_context
from app.stable_data import CURATED_PROBLEMS


class RecordingProvider:
    def __init__(self, hints=None):
        self.contexts = []
        self.hints = hints if hints is not None else ["First", "Second", "Third"]

    def generate_hints(self, context):
        self.contexts.append(context)
        return self.hints


class HintRouteTests(DatabaseTestCase):
    def test_primary_route_uses_database_primary_and_selected_context(self):
        provider = RecordingProvider()
        with patch("app.main.get_llm_provider", return_value=provider):
            response = self.client.get("/api/problems/two-sum/hints")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "slug": "two-sum", "approachId": "hash-map", "hints": provider.hints,
        })
        self.assertEqual(len(provider.contexts), 1)
        context = provider.contexts[0]
        self.assertEqual(context["approach"]["id"], "hash-map")
        self.assertEqual(context["problem"]["title"], "Two Sum")
        self.assertTrue(context["problem"]["constraints"])
        self.assertTrue(context["problem"]["examples"])
        self.assertTrue(context["approach"]["thinkingSteps"])
        self.assertTrue(context["approach"]["recognitionSignals"])
        self.assertNotIn("submissionTemplate", context["problem"])
        self.assertNotIn("approaches", context)

    def test_approach_route_uses_exact_requested_canonical_key(self):
        provider = RecordingProvider()
        with patch("app.main.get_llm_provider", return_value=provider):
            response = self.client.get("/api/problems/two-sum/approaches/brute-force/hints")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["approachId"], "brute-force")
        self.assertEqual(provider.contexts[0]["approach"]["id"], "brute-force")
        self.assertEqual(len(provider.contexts), 1)

    def test_db_only_problem_without_submission_template_can_get_hints(self):
        with Session(self.engine) as session, session.begin():
            problem = Problem(
                slug="hints-only", title="Hints Only", difficulty="Easy",
                summary="Find a value."
            )
            problem.approaches.append(Approach(
                approach_key="scan", name="Scan", pattern="Iteration",
                summary="Inspect each item.", is_primary=True, display_order=1,
                thinking_steps=["Inspect one item at a time."],
            ))
            session.add(problem)
        provider = RecordingProvider()
        with patch("app.main.get_llm_provider", return_value=provider):
            response = self.client.get("/api/problems/hints-only/hints")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["approachId"], "scan")
        self.assertEqual(provider.contexts[0]["problem"]["constraints"], [])

    def test_all_twenty_seeded_problems_are_eligible_for_mock_hints(self):
        for slug in CURATED_PROBLEMS:
            with self.subTest(slug=slug):
                response = self.client.get(f"/api/problems/{slug}/hints")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()["slug"], slug)
                self.assertEqual(len(response.json()["hints"]), 3)

    def test_unknown_problem_and_approach_keep_404_without_provider_call(self):
        provider = RecordingProvider()
        with patch("app.main.get_llm_provider", return_value=provider):
            for path, detail in (
                ("/api/problems/missing/hints", UNAVAILABLE_DETAIL),
                ("/api/problems/missing/approaches/hash-map/hints", UNAVAILABLE_DETAIL),
                ("/api/problems/two-sum/approaches/missing/hints", APPROACH_UNAVAILABLE_DETAIL),
            ):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json(), {"detail": detail})
        self.assertEqual(provider.contexts, [])

    def test_invalid_provider_output_and_outage_are_sanitized(self):
        for hints in (["only one"], ["one", " ", "three"], ["one", 2, "three"]):
            with self.subTest(hints=hints):
                with patch("app.main.get_llm_provider", return_value=RecordingProvider(hints)):
                    response = self.client.get("/api/problems/two-sum/hints")
                self.assertEqual(response.status_code, 502)
                self.assertEqual(response.json(), {"detail": "Hint provider returned invalid hints."})

        for failure, status, detail in (
            (ProviderConfigurationError("secret configuration"), 503,
             "Hint provider is not configured."),
            (ProviderUnavailableError("secret provider response"), 503,
             "Hint provider is temporarily unavailable."),
        ):
            with patch("app.main.get_llm_provider", side_effect=failure):
                response = self.client.get("/api/problems/two-sum/hints")
            self.assertEqual(response.status_code, status)
            self.assertEqual(response.json(), {"detail": detail})

        failing_provider = RecordingProvider()
        failing_provider.generate_hints = Mock(
            side_effect=ProviderUnavailableError("secret provider response")
        )
        with patch("app.main.get_llm_provider", return_value=failing_provider):
            response = self.client.get("/api/problems/two-sum/hints")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json(), {
            "detail": "Hint provider is temporarily unavailable."
        })

    def test_repository_context_comes_from_database(self):
        with Session(self.engine) as session, session.begin():
            session.scalar(select(Problem).where(Problem.slug == "two-sum")).summary = "Updated DB fact"
        with Session(self.engine) as session:
            context = find_hint_problem_context(session, "two-sum")
        self.assertEqual(context["problem"]["summary"], "Updated DB fact")


class ProviderTests(unittest.TestCase):
    def test_mock_is_deterministic_offline_and_returns_three_hints(self):
        context = {"approach": {
            "summary": "Try each item.", "pattern": "Scanning",
            "thinkingSteps": ["Inspect the next item."],
            "recognitionSignals": {"bullets": ["You need one value.", "The input is a list."]},
        }}
        with patch.object(socket, "create_connection", side_effect=AssertionError("network")):
            first = MockLLMProvider().generate_hints(context)
            second = MockLLMProvider().generate_hints(context)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)
        self.assertTrue(all(isinstance(hint, str) and hint.strip() for hint in first))
        self.assertTrue(all(
            len(hint.split()) <= LEVEL_WORD_LIMITS[index]
            for index, hint in enumerate(first)
        ))
        self.assertNotIn("Scanning", " ".join(first[:2]))

    def test_hint_length_guard_preserves_short_clues_and_replaces_long_explanations(self):
        long_explanation = "You should implement the entire algorithm by carefully following " * 5
        self.assertEqual(validate_hints([
            "Which part matters? More explanation that should be removed. " * 4,
            long_explanation,
            "What could you remember?",
        ]), ["Which part matters?", SHORT_FALLBACK_HINTS[1], "What could you remember?"])
        self.assertEqual(validate_hints([
            "Hint 1: Which part matters?", "2. What could help?", "- What could you check?"
        ]), ["Which part matters?", "What could help?", "What could you check?"])

    def test_mock_hints_stay_concise_for_every_curated_approach(self):
        from app.stable_data import CURATED_PROBLEM_SPECS

        for slug, problem in CURATED_PROBLEMS.items():
            for approach in problem["approaches"]:
                with self.subTest(slug=slug, approach=approach["id"]):
                    context = {"problem": CURATED_PROBLEM_SPECS[slug], "approach": approach}
                    hints = MockLLMProvider().generate_hints(context)
                    self.assertEqual(len(hints), 3)
                    self.assertTrue(all(
                        len(hint.split()) <= LEVEL_WORD_LIMITS[index]
                        and len(hint) <= LEVEL_CHARACTER_LIMITS[index]
                        for index, hint in enumerate(hints)
                    ))

    def test_factory_selects_mock_and_requires_groq_configuration(self):
        with patch("app.llm.provider_factory.load_dotenv", return_value=False):
            with patch.dict(os.environ, {"LEETCOACH_LLM_PROVIDER": "mock", "GROQ_API_KEY": ""}):
                self.assertIsInstance(get_llm_provider(), MockLLMProvider)
            with patch.dict(os.environ, {
                "LEETCOACH_LLM_PROVIDER": "groq", "GROQ_API_KEY": "",
                "LEETCOACH_LLM_MODEL": "test-model",
            }):
                with self.assertRaises(ProviderConfigurationError):
                    get_llm_provider()
            with patch.dict(os.environ, {
                "LEETCOACH_LLM_PROVIDER": "groq", "GROQ_API_KEY": "test-only-key",
                "LEETCOACH_LLM_MODEL": "",
            }):
                with self.assertRaises(ProviderConfigurationError):
                    get_llm_provider()
            with patch.dict(os.environ, {
                "LEETCOACH_LLM_PROVIDER": "groq", "GROQ_API_KEY": "test-only-key",
                "LEETCOACH_LLM_MODEL": "test-model",
            }):
                with patch("app.llm.provider_factory.GroqLLMProvider") as provider_class:
                    self.assertIs(get_llm_provider(), provider_class.return_value)
                    provider_class.assert_called_once_with(
                        api_key="test-only-key", model="test-model"
                    )

    def test_groq_provider_makes_one_structured_call_and_validates_output(self):
        calls = []

        def create(**kwargs):
            calls.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
                content=json.dumps({"hints": [
                    "What matters?", "What could help?", "What could you check?"
                ]})
            ))])

        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        provider = GroqLLMProvider("test-only-key", "configured-model", client=client)
        context = {"problem": {"slug": "two-sum"}, "approach": {"id": "hash-map"}}
        self.assertEqual(provider.generate_hints(context), [
            "What matters?", "What could help?", "What could you check?"
        ])
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]["model"], "configured-model")
        self.assertEqual(calls[0]["response_format"], {"type": "json_object"})
        self.assertEqual(json.loads(calls[0]["messages"][1]["content"]), context)
        self.assertNotIn("test-only-key", str(calls[0]))
        self.assertIn("at most 18 words and 120 characters", SYSTEM_PROMPT)
        self.assertIn("Hint 1: at most 10 words", SYSTEM_PROMPT)
        self.assertIn("Never state the full algorithm", SYSTEM_PROMPT)

    def test_groq_hides_direct_recipe_or_approach_name_if_model_ignores_prompt(self):
        content = json.dumps({"hints": [
            "Use a Hash Map.",
            "Could you use `seen` to track values?",
            "Check every value, store its index, and return the matching pair.",
        ]})
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(
                message=SimpleNamespace(content=content)
            )])
        )))
        provider = GroqLLMProvider("test-only-key", "model", client=client)
        self.assertEqual(provider.generate_hints({"approach": {
            "id": "hash-map", "name": "One-pass Hash Map", "pattern": "Hash Map"
        }}), list(SHORT_FALLBACK_HINTS))

    def test_groq_provider_rejects_invalid_json_and_hint_count(self):
        for content in ("not json", '{"hints": ["one"]}', '{"hints": ["one", "", "three"]}'):
            with self.subTest(content=content):
                client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
                    create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(
                        message=SimpleNamespace(content=content)
                    )])
                )))
                with self.assertRaises(ProviderOutputError):
                    GroqLLMProvider("test-only-key", "model", client=client).generate_hints({})

    def test_groq_timeout_is_a_sanitized_provider_failure(self):
        def timeout(**kwargs):
            raise TimeoutError("internal transport details")

        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(
            create=timeout
        )))
        provider = GroqLLMProvider("test-only-key", "model", client=client)
        with self.assertRaises(ProviderUnavailableError) as captured:
            provider.generate_hints({})
        self.assertEqual(str(captured.exception), "Hint provider unavailable")


if __name__ == "__main__":
    unittest.main()
