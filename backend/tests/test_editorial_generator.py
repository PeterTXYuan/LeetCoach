"""Offline editorial generator checks; no model or database calls."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from app.catalog_import import CatalogImportError, load_catalog
from app.editorial_generator import (
    EFFORT, MODEL, EditorialGeneratorError, _load_fact_file, _prompt,
    assemble_draft, check_codex_cli, generate_batch, run_codex,
)


PILOT = Path(__file__).resolve().parents[1] / "catalog" / "problems"


def editorial(title="A problem"):
    return {
        "summary": f"Solve {title} under the stated rules.",
        "description": f"For {title}, use the supplied input to produce the required result while obeying every stated constraint.",
        "approaches": [{
            "id": "example-method", "name": "Example Method", "pattern": "Review Pattern",
            "summary": "Work through the input while maintaining the required result.",
            "timeComplexityExplanation": "O(n) because each item is visited once.",
            "spaceComplexityExplanation": "O(1) because only fixed working state is kept.",
            "thinkingSteps": ["Identify the required output.", "Track the useful state as input is processed."],
            "recognitionSignals": {"bullets": [
                "The output depends on the input.", "The constraints shape the method."
            ]},
        }],
    }


class EditorialGeneratorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.input_dir = self.root / "facts"
        self.output_dir = self.root / "drafts"
        self.input_dir.mkdir()
        for source in PILOT.glob("*.json"):
            (self.input_dir / source.name).write_bytes(source.read_bytes())

    def test_ten_pilot_inputs_generate_separate_unreviewed_drafts_and_resume(self):
        original = {path.name: path.read_bytes() for path in self.input_dir.glob("*.json")}
        calls = []

        def fake_generate(source, task_facts):
            calls.append(source["slug"])
            self.assertIn(source["spec"]["description"], task_facts)
            return editorial(source["spec"]["title"]), {
                "input_tokens": 50, "output_tokens": 30,
            }

        results = generate_batch(self.input_dir, self.output_dir,
                                 cli_check=lambda: None, generate=fake_generate)
        self.assertEqual(len(calls), 10)
        self.assertEqual([item["status"] for item in results], ["generated"] * 10)
        self.assertEqual(original, {path.name: path.read_bytes() for path in self.input_dir.glob("*.json")})
        self.assertEqual(len(list(self.output_dir.glob("*.json"))), 10)
        self.assertIn("input 500, output 300", (self.output_dir / "report.md").read_text())
        for source_path in self.input_dir.glob("*.json"):
            source = json.loads(source_path.read_text(encoding="utf-8"))
            draft = json.loads((self.output_dir / source_path.name).read_text(encoding="utf-8"))
            self.assertFalse(draft["provenance"]["reviewed"])
            self.assertEqual(draft["provenance"]["sourceUrl"], source["provenance"]["sourceUrl"])
            self.assertIn(source["provenance"]["permissionNote"], draft["provenance"]["permissionNote"])
            self.assertEqual(draft["related"], source["related"])
            for field in ("title", "difficulty", "leetcodeNumber", "constraints", "examples",
                          "submissionTemplates", "descriptionSourceUrl", "descriptionVerifiedAt",
                          "timeComplexityInstruction", "spaceComplexityInstruction"):
                self.assertEqual(draft["spec"][field], source["spec"][field])
            self.assertIn("Time: O(n)", draft["approaches"][0]["summary"])
        with self.assertRaisesRegex(CatalogImportError, "explicitly reviewed"):
            load_catalog(self.output_dir)
        second = generate_batch(self.input_dir, self.output_dir,
                                cli_check=lambda: self.fail("CLI should not run"),
                                generate=lambda *_: self.fail("completed drafts should be skipped"))
        self.assertEqual([item["status"] for item in second], ["skipped"] * 10)

    def test_facts_only_input_and_small_prompt(self):
        path = self.input_dir / "move-zeroes.json"
        source = json.loads(path.read_text(encoding="utf-8"))
        source.pop("approaches")
        source["spec"].pop("summary")
        source["spec"]["taskFacts"] = ["Move zeros in place.", "Preserve nonzero order."]
        source["spec"].pop("description")
        path.write_text(json.dumps(source), encoding="utf-8")
        loaded, facts = _load_fact_file(path)
        prompt = _prompt(loaded, facts)
        self.assertIn("Move zeros in place", prompt)
        self.assertNotIn("submissionTemplates", prompt)
        self.assertNotIn("permissionNote", prompt)
        draft = assemble_draft(loaded, editorial("Move Zeroes"))
        self.assertNotIn("taskFacts", draft["spec"])
        self.assertEqual(set(draft), {"slug", "spec", "approaches", "related", "provenance"})

    def test_resume_flags_changed_facts_and_preserves_old_draft(self):
        path = self.input_dir / "move-zeroes.json"
        target = self.output_dir / path.name

        def generated(source, facts):
            return editorial(source["spec"]["title"]), {"input_tokens": 10, "output_tokens": 5}

        first = generate_batch(self.input_dir, self.output_dir, slugs=["move-zeroes"],
                               cli_check=lambda: None, generate=generated)
        self.assertEqual(first[0]["status"], "generated")
        draft_before = target.read_bytes()
        checkpoint = self.output_dir / ".checkpoints" / "move-zeroes.json"
        checkpoint_before = checkpoint.read_bytes()
        source = json.loads(path.read_text(encoding="utf-8"))
        path.write_text(json.dumps(source, sort_keys=True, indent=4), encoding="utf-8")
        same = generate_batch(self.input_dir, self.output_dir, slugs=["move-zeroes"],
                              cli_check=lambda: self.fail("no CLI preflight on resume"),
                              generate=lambda *_: self.fail("format-only edit should skip"))
        self.assertEqual(same[0]["status"], "skipped")

        source["spec"]["constraints"].append("Additional manually reviewed constraint.")
        path.write_text(json.dumps(source), encoding="utf-8")
        stale = generate_batch(self.input_dir, self.output_dir, slugs=["move-zeroes"],
                               cli_check=lambda: self.fail("no CLI preflight for stale draft"),
                               generate=lambda *_: self.fail("stale draft must not be overwritten"))
        self.assertEqual(stale[0]["status"], "stale")
        self.assertIn("reviewed input changed", stale[0]["note"])
        self.assertEqual(target.read_bytes(), draft_before)
        self.assertEqual(checkpoint.read_bytes(), checkpoint_before)
        self.assertIn("input 10, output 5", (self.output_dir / "report.md").read_text())

        target.rename(self.root / "preserved-old-draft.json")
        regenerated = generate_batch(self.input_dir, self.output_dir, slugs=["move-zeroes"],
                                     cli_check=lambda: None, generate=generated)
        self.assertEqual(regenerated[0]["status"], "generated")
        self.assertEqual(len(json.loads(checkpoint.read_text())["attempts"]), 2)
        self.assertIn("input 20, output 10", (self.output_dir / "report.md").read_text())
        self.assertEqual((self.root / "preserved-old-draft.json").read_bytes(), draft_before)

    def test_failed_editorial_usage_survives_retry_and_skip(self):
        attempts = []

        def generator(source, facts):
            attempts.append(source["slug"])
            if len(attempts) == 1:
                bad = editorial()
                bad["summary"] = source["spec"]["title"]
                return bad, {"input_tokens": 7, "output_tokens": 3}
            return editorial(), {"input_tokens": 11, "output_tokens": 4}

        first = generate_batch(self.input_dir, self.output_dir, slugs=["move-zeroes"],
                               cli_check=lambda: None, generate=generator)
        self.assertEqual(first[0]["status"], "failed")
        self.assertFalse((self.output_dir / "move-zeroes.json").exists())
        self.assertIn("input 7, output 3", (self.output_dir / "report.md").read_text())
        second = generate_batch(self.input_dir, self.output_dir, slugs=["move-zeroes"],
                                cli_check=lambda: None, generate=generator)
        self.assertEqual(second[0]["status"], "generated")
        self.assertIn("input 18, output 7", (self.output_dir / "report.md").read_text())
        resumed = generate_batch(self.input_dir, self.output_dir, slugs=["move-zeroes"],
                                 cli_check=lambda: self.fail("no CLI preflight on resume"),
                                 generate=lambda *_: self.fail("successful draft must be skipped"))
        self.assertEqual(resumed[0]["status"], "skipped")
        self.assertIn("input 18, output 7", (self.output_dir / "report.md").read_text())
        checkpoint = json.loads((self.output_dir / ".checkpoints" / "move-zeroes.json").read_text())
        self.assertEqual([item["status"] for item in checkpoint["attempts"]], ["failed", "generated"])

    def test_old_draft_without_fingerprint_is_preserved_and_usage_migrates(self):
        source = json.loads((self.input_dir / "move-zeroes.json").read_text(encoding="utf-8"))
        draft = assemble_draft(source, editorial())
        self.output_dir.mkdir()
        target = self.output_dir / "move-zeroes.json"
        target.write_text(json.dumps(draft), encoding="utf-8")
        original = target.read_bytes()
        (self.output_dir / "report.md").write_text(
            "| Problem | Status | Input tokens | Output tokens | Note |\n"
            "| --- | --- | ---: | ---: | --- |\n"
            "| move-zeroes | generated | 15133 | 534 | |\n", encoding="utf-8")
        result = generate_batch(self.input_dir, self.output_dir, slugs=["move-zeroes"],
                                cli_check=lambda: self.fail("legacy draft must not generate"),
                                generate=lambda *_: self.fail("legacy draft must not be overwritten"))
        self.assertEqual(result[0]["status"], "stale")
        self.assertIn("no input fingerprint", result[0]["note"])
        self.assertEqual(target.read_bytes(), original)
        self.assertTrue((self.output_dir / "report.legacy.md").exists())
        self.assertIn("input 15133, output 534", (self.output_dir / "report.md").read_text())

    def test_invalid_output_fails_without_overwriting_or_importing(self):
        def broken(source, facts):
            output = editorial()
            output["approaches"][0]["id"] = "Not Kebab Case"
            return output, None

        results = generate_batch(self.input_dir, self.output_dir, slugs=["move-zeroes"],
                                 cli_check=lambda: None, generate=broken)
        self.assertEqual(results[0]["status"], "failed")
        self.assertFalse((self.output_dir / "move-zeroes.json").exists())
        self.assertTrue((self.output_dir / "report.md").exists())
        source = json.loads((self.input_dir / "move-zeroes.json").read_text(encoding="utf-8"))
        title_only = editorial()
        title_only["summary"] = source["spec"]["title"]
        with self.assertRaisesRegex(EditorialGeneratorError, "repeats the title"):
            assemble_draft(source, title_only)
        with self.assertRaisesRegex(EditorialGeneratorError, "outside"):
            generate_batch(self.input_dir, self.input_dir / "drafts", cli_check=lambda: None)
        bad = json.loads((self.input_dir / "move-zeroes.json").read_text(encoding="utf-8"))
        bad["provenance"]["reviewed"] = False
        (self.input_dir / "move-zeroes.json").write_text(json.dumps(bad), encoding="utf-8")
        self.assertEqual(generate_batch(self.input_dir, self.output_dir, slugs=["move-zeroes"],
                                        cli_check=lambda: None, generate=lambda *_: (editorial(), None))[0]["status"],
                         "failed")

    def test_cli_account_model_and_exact_exec_options(self):
        catalog = {"models": [{"slug": MODEL, "supported_reasoning_levels": [{"effort": EFFORT}]}]}

        def metadata_run(command, **kwargs):
            if command[1:3] == ["login", "status"]:
                return SimpleNamespace(returncode=0, stdout="", stderr="Logged in using ChatGPT")
            return SimpleNamespace(returncode=0, stdout=json.dumps(catalog), stderr="")

        check_codex_cli(run=metadata_run)
        def api_key_login(command, **kwargs):
            return SimpleNamespace(returncode=0, stdout="", stderr="Logged in using API key")
        with self.assertRaisesRegex(EditorialGeneratorError, "ChatGPT"):
            check_codex_cli(run=api_key_login)
        with self.assertRaisesRegex(EditorialGeneratorError, MODEL):
            check_codex_cli(run=lambda command, **kwargs: SimpleNamespace(
                returncode=0, stdout="" if command[1] == "login" else json.dumps({"models": []}),
                stderr="Logged in using ChatGPT" if command[1] == "login" else ""))

        source = json.loads((self.input_dir / "move-zeroes.json").read_text(encoding="utf-8"))

        def fake_exec(command, **kwargs):
            self.assertEqual(command[:2], ["codex", "exec"])
            self.assertIn("--output-schema", command)
            self.assertIn("--ephemeral", command)
            self.assertIn("--ignore-user-config", command)
            self.assertIn("read-only", command)
            self.assertIn(MODEL, command)
            self.assertIn('model_reasoning_effort="medium"', command)
            self.assertNotIn("OPENAI_API_KEY", kwargs["env"])
            self.assertNotIn("CODEX_API_KEY", kwargs["env"])
            self.assertNotIn("CODEX_ACCESS_TOKEN", kwargs["env"])
            Path(command[command.index("--output-last-message") + 1]).write_text(
                json.dumps(editorial()), encoding="utf-8")
            return SimpleNamespace(returncode=0, stdout=json.dumps({
                "type": "turn.completed", "usage": {"input_tokens": 17, "output_tokens": 9}}))

        result, usage = run_codex(source, source["spec"]["description"], run=fake_exec)
        self.assertEqual(result["approaches"][0]["id"], "example-method")
        self.assertEqual(usage, {"input_tokens": 17, "output_tokens": 9})


if __name__ == "__main__":
    unittest.main()
