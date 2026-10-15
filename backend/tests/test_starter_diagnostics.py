"""Offline-only checks for Starter Code diagnostics; no Groq network calls."""
import json
from types import SimpleNamespace
from unittest.mock import patch

from sqlalchemy.orm import Session

from db_test_support import DatabaseTestCase
from app.llm.groq_provider import GroqLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.starter_diagnostics import provider_reason, starter_observer, starter_raw_capture
from app.services.problem_repository import find_problem_context
from evaluation.replay_starter import replay


class StarterDiagnosticsTests(DatabaseTestCase):
    def context(self, language="python"):
        with Session(self.engine) as session:
            return find_problem_context(session, "two-sum", "hash-map", language)

    def fake_provider(self, response=None, error=None):
        def create(**_kwargs):
            if error:
                raise error
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=response))])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        return GroqLLMProvider(api_key="secret-test-key", model="offline", client=client)

    def request(self, provider):
        with patch("app.main.get_llm_provider", return_value=provider):
            return self.client.post("/api/problems/two-sum/approaches/hash-map/starter-code",
                                    json={"language": "python", "level": 1})

    def test_provider_timeout_and_rate_limit_are_distinct(self):
        class RateLimited(Exception):
            status_code = 429
        self.assertEqual(provider_reason(TimeoutError("secret")), "PROVIDER_TIMEOUT")
        self.assertEqual(provider_reason(RateLimited("secret")), "PROVIDER_RATE_LIMITED")
        for error, reason in ((TimeoutError("secret"), "PROVIDER_TIMEOUT"),
                              (RateLimited("secret"), "PROVIDER_RATE_LIMITED")):
            events = []
            token = starter_observer.set(events.append)
            try:
                response = self.request(self.fake_provider(error=error))
            finally:
                starter_observer.reset(token)
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["usedFallback"])
            self.assertEqual(events[-1]["reason"], reason)
            self.assertEqual(events[-1]["stage"], "provider")
            self.assertNotIn("secret", response.text)
            self.assertNotIn("secret", str(events))

    def test_parse_reasons_and_replay_are_network_free(self):
        context = self.context()
        template = context["problem"]["submissionTemplate"]["code"]
        valid = MockLLMProvider().generate_starter_code(context, "python", 1)
        # Derive the signature from the actual template to avoid fixture spelling assumptions.
        signature = next(line for line in template.splitlines() if "def twoSum" in line)
        changed = valid.replace(signature, signature.replace("twoSum", "other"))
        invalid_syntax = valid.replace("seen = {}", "seen = (")
        no_placeholder = valid.replace("raise NotImplementedError", "pass # removed")
        bare_l1 = template.replace("pass", "# TODO: decide\n        raise NotImplementedError")
        commented = valid.replace("# TODO", "# seen = {}\n        # seen[target] = 0\n        # TODO")
        cases = [
            ("not json", "INVALID_JSON", "parsing"),
            ("{}", "MISSING_CODE_FIELD", "parsing"),
            (json.dumps({"code": 4}), "INVALID_OUTPUT_TYPE", "parsing"),
            (json.dumps({"code": changed}), "CHANGED_SIGNATURE", "validation"),
            (json.dumps({"code": invalid_syntax}), "INVALID_SYNTAX", "validation"),
            (json.dumps({"code": no_placeholder}), "MISSING_UNFINISHED_PLACEHOLDER", "validation"),
            (json.dumps({"code": bare_l1}), "LEVEL_ONE_NO_USEFUL_SETUP", "validation"),
            (json.dumps({"code": commented}), "COMMENTED_OUT_ALGORITHM", "validation"),
        ]
        for content, reason, stage in cases:
            with self.subTest(reason=reason):
                result = replay(content, context, "python", 1)
                self.assertEqual((result["accepted"], result["reason"], result["stage"]),
                                 (False, reason, stage))
        self.assertTrue(replay(json.dumps({"code": valid}), context, "python", 1)["accepted"])

    def test_success_and_capture_default_off_and_public_contract(self):
        context = self.context()
        valid = MockLLMProvider().generate_starter_code(context, "python", 1)
        provider = self.fake_provider(json.dumps({"code": valid}))
        self.assertIsNone(starter_observer.get())
        response = self.request(provider)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(set(payload), {"slug", "approachId", "language", "level", "levelName",
                                        "policyVersion", "isAiGenerated", "code", "notice"})
        self.assertTrue(payload["isAiGenerated"])
        self.assertNotIn("diagnostic", response.text)
        self.assertNotIn("secret-test-key", response.text)
        accepted_events = []
        token = starter_observer.set(accepted_events.append)
        try:
            self.request(provider)
        finally:
            starter_observer.reset(token)
        self.assertEqual([event["kind"] for event in accepted_events], ["accepted"])
        events = []
        token = starter_observer.set(events.append)
        try:
            self.request(self.fake_provider("not json"))
        finally:
            starter_observer.reset(token)
        self.assertEqual([event["kind"] for event in events], ["failure"])

    def test_fallback_keeps_typed_metadata_out_of_public_response(self):
        events = []
        token = starter_observer.set(events.append)
        raw_token = starter_raw_capture.set(True)
        try:
            with self.assertLogs("app.main", level="WARNING") as captured_logs:
                response = self.request(self.fake_provider("private model text; not json"))
        finally:
            starter_raw_capture.reset(raw_token)
            starter_observer.reset(token)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["usedFallback"])
        self.assertEqual(events[0], {"kind": "raw_response", "content": "private model text; not json"})
        self.assertEqual(events[1]["reason"], "INVALID_JSON")
        self.assertNotIn("INVALID_JSON", response.text)
        self.assertIn("reason=INVALID_JSON", captured_logs.output[0])
        self.assertNotIn("private model text", captured_logs.output[0])
        self.assertNotIn("secret-test-key", captured_logs.output[0])

