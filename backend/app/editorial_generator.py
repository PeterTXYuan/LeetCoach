"""Draft importer-compatible editorial JSON through a local ChatGPT-authenticated Codex CLI.

This command never imports data. Generated drafts remain unreviewed until a
person checks the prose, approach claims, source permissions, and examples.
"""
import argparse
import copy
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from app.catalog_import import CatalogImportError, _reviewed_provenance, load_catalog


MODEL = "gpt-5.6-sol"
EFFORT = "medium"
LANGUAGES = {"python", "java", "javascript", "cpp"}
FACT_FIELDS = (
    "title", "difficulty", "leetcodeNumber", "descriptionSourceUrl",
    "descriptionSourceType", "descriptionVerifiedAt", "timeLimitMs", "memoryLimitMb",
    "timeComplexityInstruction", "spaceComplexityInstruction", "constraints", "examples",
    "submissionTemplates",
)


def _object(properties):
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


OUTPUT_SCHEMA = _object({
    "summary": {"type": "string"},
    "description": {"type": "string"},
    "approaches": {"type": "array", "items": _object({
        "id": {"type": "string"}, "name": {"type": "string"},
        "pattern": {"type": "string"}, "summary": {"type": "string"},
        "timeComplexityExplanation": {"type": "string"},
        "spaceComplexityExplanation": {"type": "string"},
        "thinkingSteps": {"type": "array", "items": {"type": "string"}},
        "recognitionSignals": _object({
            "bullets": {"type": "array", "items": {"type": "string"}}
        }),
    })},
})


class EditorialGeneratorError(ValueError):
    def __init__(self, message, *, usage=None):
        super().__init__(message)
        self.usage = usage


def _cli_env():
    env = os.environ.copy()
    # Never let an API key or alternate endpoint silently replace ChatGPT login.
    for name in ("OPENAI_API_KEY", "CODEX_API_KEY", "CODEX_ACCESS_TOKEN",
                 "OPENAI_BASE_URL", "OPENAI_API_BASE"):
        env.pop(name, None)
    return env


def check_codex_cli(run=subprocess.run):
    """Fail closed if the requested account, model, or effort is unavailable."""
    try:
        login = run(["codex", "login", "status"], capture_output=True,
                    text=True, encoding="utf-8", errors="replace", timeout=20,
                    env=_cli_env())
        if login.returncode or "Logged in using ChatGPT" not in (login.stdout + login.stderr):
            raise EditorialGeneratorError("Codex CLI is not signed in with ChatGPT. Run `codex login` locally.")
        catalog = run(["codex", "debug", "models"], capture_output=True,
                      text=True, encoding="utf-8", errors="replace", timeout=30,
                      env=_cli_env())
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EditorialGeneratorError("Codex CLI login or model catalog is unavailable.") from exc
    if catalog.returncode:
        raise EditorialGeneratorError("Codex CLI model catalog is unavailable; no provider fallback was used.")
    try:
        models = json.loads(catalog.stdout)["models"]
    except (ValueError, KeyError, TypeError) as exc:
        raise EditorialGeneratorError("Codex CLI returned an unreadable model catalog.") from exc
    selected = next((model for model in models if model.get("slug") == MODEL), None)
    if selected is None or EFFORT not in {
        level.get("effort") for level in selected.get("supported_reasoning_levels", [])
    }:
        raise EditorialGeneratorError(f"Codex CLI does not offer {MODEL} at {EFFORT} reasoning.")


def _load_fact_file(path: Path):
    try:
        source = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise EditorialGeneratorError(f"{path.name}: cannot read JSON facts.") from exc
    accepted_keys = ({"slug", "spec", "approaches", "related", "provenance"},
                     {"slug", "spec", "related", "provenance"})
    if not isinstance(source, dict) or set(source) not in accepted_keys:
        raise EditorialGeneratorError(f"{path.name}: expected importer-style facts and provenance.")
    slug = source["slug"]
    spec = source["spec"]
    if not isinstance(slug, str) or path.stem != slug or not isinstance(spec, dict):
        raise EditorialGeneratorError(f"{path.name}: slug, filename, or spec is invalid.")
    if not isinstance(source["related"], dict) or set(source["related"]) != {
        "easier", "similar", "harder"
    } or not all(isinstance(group, list) for group in source["related"].values()):
        raise EditorialGeneratorError(f"{slug}: related cards need all three groups.")
    if not all(field in spec for field in FACT_FIELDS):
        raise EditorialGeneratorError(f"{slug}: missing verified problem facts.")
    if not _nonempty(spec["title"]):
        raise EditorialGeneratorError(f"{slug}: reviewed title is required.")
    task_facts = spec.get("taskFacts") or spec.get("description")
    if isinstance(task_facts, list):
        if not task_facts or not all(isinstance(item, str) and item.strip() for item in task_facts):
            raise EditorialGeneratorError(f"{slug}: taskFacts must contain reviewed statements.")
        task_facts = "\n".join(task_facts)
    if not isinstance(task_facts, str) or not task_facts.strip():
        raise EditorialGeneratorError(f"{slug}: reviewed taskFacts or description is required.")
    if spec["descriptionSourceUrl"] != f"https://leetcode.com/problems/{slug}/":
        raise EditorialGeneratorError(f"{slug}: official problem URL does not match slug.")
    if spec["descriptionSourceType"] != "curated_restatement":
        raise EditorialGeneratorError(f"{slug}: description source type must be curated_restatement.")
    if spec["difficulty"] not in {"Easy", "Medium", "Hard"} or type(spec["leetcodeNumber"]) is not int or spec["leetcodeNumber"] <= 0:
        raise EditorialGeneratorError(f"{slug}: number or difficulty is invalid.")
    if not isinstance(spec["submissionTemplates"], dict) or set(spec["submissionTemplates"]) != LANGUAGES or not all(
        isinstance(code, str) and code.strip() for code in spec["submissionTemplates"].values()
    ):
        raise EditorialGeneratorError(f"{slug}: all four verified submission contracts are required.")
    if (not isinstance(spec["constraints"], list) or not spec["constraints"]
            or not all(_nonempty(item) for item in spec["constraints"])
            or not isinstance(spec["examples"], list) or not spec["examples"]
            or not all(isinstance(item, dict) and _nonempty(item.get("input"))
                       and _nonempty(item.get("output")) for item in spec["examples"])):
        raise EditorialGeneratorError(f"{slug}: reviewed constraints and examples are required.")
    try:
        _reviewed_provenance(slug, spec, source["provenance"])
    except (CatalogImportError, KeyError, TypeError) as exc:
        raise EditorialGeneratorError(f"{slug}: facts require reviewed provenance: {exc}") from exc
    return source, task_facts


def _prompt(source, task_facts):
    spec = source["spec"]
    facts = {
        "title": spec["title"], "difficulty": spec["difficulty"],
        "taskFacts": task_facts, "constraints": spec["constraints"],
        "examples": spec["examples"],
        "timeComplexityInstruction": spec["timeComplexityInstruction"],
        "spaceComplexityInstruction": spec["spaceComplexityInstruction"],
    }
    return (
        "Write original, concise LeetCoach editorial JSON for these manually reviewed facts. "
        "Use only the supplied facts; never browse, access files, invent requirements, or claim permissions. "
        "Keep the description approach-neutral and include every task rule. "
        "Make the summary one short sentence about the task, not just the title. "
        "Produce 1 or 2 distinct valid canonical approaches, ordered best-first, with stable kebab-case ids. "
        "Each approach summary explains the method; give one short sentence each for time and space complexity "
        "with the cause, including recursion stack where relevant. Respect mandatory complexity instructions. "
        "Give 2-4 beginner-friendly thinking steps and 2-3 short recognition bullets about clues in the task, "
        "not implementation instructions. Do not copy example wording into editorial prose. "
        "Return only the schema fields.\nFacts: " + json.dumps(facts, ensure_ascii=False, separators=(",", ":"))
    )


def _usage(stdout):
    usage = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if event.get("type") == "turn.completed":
            usage = event.get("usage")
    return usage


def _fingerprint(source):
    """Hash JSON values, not source formatting or key order."""
    canonical = json.dumps(source, sort_keys=True, ensure_ascii=False,
                           separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _checkpoint_path(output_dir, slug):
    return output_dir / ".checkpoints" / f"{slug}.json"


def _read_checkpoint(path):
    if not path.exists():
        return {"draftInputFingerprint": None, "attempts": []}
    try:
        checkpoint = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError) as exc:
        raise EditorialGeneratorError(f"Unreadable checkpoint: {path.name}; existing draft and usage were preserved.") from exc
    if (not isinstance(checkpoint, dict) or set(checkpoint) != {"draftInputFingerprint", "attempts"}
            or not isinstance(checkpoint["attempts"], list)):
        raise EditorialGeneratorError(f"Invalid checkpoint: {path.name}; existing draft and usage were preserved.")
    for item in checkpoint["attempts"]:
        if not isinstance(item, dict) or not isinstance(item.get("usage"), (dict, type(None))):
            raise EditorialGeneratorError(f"Invalid usage checkpoint: {path.name}; existing data were preserved.")
        if isinstance(item["usage"], dict) and any(
            type(value) is not int or value < 0 for key, value in item["usage"].items()
            if key in {"input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens"}
        ):
            raise EditorialGeneratorError(f"Invalid token count in {path.name}; existing data were preserved.")
    return checkpoint


def _record_attempt(path, checkpoint, fingerprint, status, usage):
    updated = copy.deepcopy(checkpoint)
    updated["attempts"].append({"inputFingerprint": fingerprint, "status": status,
                                "usage": copy.deepcopy(usage)})
    if status == "generated":
        updated["draftInputFingerprint"] = fingerprint
    path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(path, updated)
    return updated


def _token_totals(attempts):
    available = [item["usage"] for item in attempts if isinstance(item, dict)
                 and isinstance(item.get("usage"), dict)]
    if not available:
        return None
    return {key: sum(value.get(key, 0) for value in available)
            for key in ("input_tokens", "output_tokens", "cached_input_tokens",
                        "reasoning_output_tokens") if any(key in value for value in available)}


def _all_token_totals(output_dir):
    attempts = []
    for path in sorted((output_dir / ".checkpoints").glob("*.json")):
        attempts.extend(_read_checkpoint(path)["attempts"])
    return _token_totals(attempts)


def _migrate_legacy_report(output_dir):
    """Retain usage from the old per-run Markdown report without trusting its draft freshness."""
    report = output_dir / "report.md"
    if not report.exists():
        return
    old = report.read_text(encoding="utf-8")
    if "| Problem | Status | Input tokens | Output tokens | Note |" not in old:
        return
    backup = output_dir / "report.legacy.md"
    if not backup.exists():
        backup.write_text(old, encoding="utf-8")
    for line in old.splitlines():
        fields = [field.strip() for field in line.split("|")]
        if len(fields) < 7 or fields[2] not in {"generated", "failed"}:
            continue
        slug, input_count, output_count = fields[1], fields[3], fields[4]
        if (re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug) is None
                or not input_count.isdecimal() or not output_count.isdecimal()):
            continue
        checkpoint_path = _checkpoint_path(output_dir, slug)
        if checkpoint_path.exists():
            continue
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        _write_json(checkpoint_path, {"draftInputFingerprint": None, "attempts": [{
            "inputFingerprint": None, "status": "legacy",
            "usage": {"input_tokens": int(input_count), "output_tokens": int(output_count)},
        }]})


def run_codex(source, task_facts, *, run=subprocess.run):
    with tempfile.TemporaryDirectory(prefix="leetcoach-editorial-") as directory:
        root = Path(directory)
        schema_path = root / "schema.json"
        output_path = root / "editorial.json"
        schema_path.write_text(json.dumps(OUTPUT_SCHEMA), encoding="utf-8")
        command = ["codex", "exec", "--json", "--ephemeral", "--ignore-user-config",
                   "--skip-git-repo-check", "--sandbox", "read-only", "-C", str(root),
                   "--model", MODEL, "-c", f'model_reasoning_effort="{EFFORT}"',
                   "--output-schema", str(schema_path), "--output-last-message", str(output_path), "-"]
        try:
            result = run(command, input=_prompt(source, task_facts), capture_output=True,
                         text=True, encoding="utf-8", errors="replace", timeout=180,
                         env=_cli_env())
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise EditorialGeneratorError("Codex CLI execution was unavailable or timed out.") from exc
        usage = _usage(result.stdout)
        if result.returncode:
            # stderr may include the prompt or account details; do not persist it.
            raise EditorialGeneratorError(f"Codex CLI exited with status {result.returncode}.", usage=usage)
        try:
            editorial = json.loads(output_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, ValueError) as exc:
            raise EditorialGeneratorError("Codex CLI did not return structured editorial JSON.",
                                          usage=usage) from exc
        return editorial, usage


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def assemble_draft(source, editorial):
    if not isinstance(editorial, dict) or set(editorial) != {"summary", "description", "approaches"}:
        raise EditorialGeneratorError("Generated editorial has missing or extra fields.")
    if not _nonempty(editorial["summary"]) or not _nonempty(editorial["description"]):
        raise EditorialGeneratorError("Generated summary or description is empty.")
    if editorial["summary"].strip().casefold().rstrip(".") == source["spec"]["title"].strip().casefold():
        raise EditorialGeneratorError("Generated summary repeats the title without describing the task.")
    proposed = editorial["approaches"]
    if not isinstance(proposed, list) or not 1 <= len(proposed) <= 2:
        raise EditorialGeneratorError("Generated editorial needs one or two approaches.")
    approaches = []
    seen = set()
    keys = {"id", "name", "pattern", "summary", "timeComplexityExplanation",
            "spaceComplexityExplanation", "thinkingSteps", "recognitionSignals"}
    for order, item in enumerate(proposed, 1):
        if not isinstance(item, dict) or set(item) != keys:
            raise EditorialGeneratorError("Generated approach fields are incomplete.")
        if not all(_nonempty(item[field]) for field in keys - {"thinkingSteps", "recognitionSignals"}):
            raise EditorialGeneratorError("Generated approach text is empty.")
        key = item["id"]
        if re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", key) is None or key in seen:
            raise EditorialGeneratorError("Generated approach IDs must be unique kebab-case keys.")
        seen.add(key)
        steps = item["thinkingSteps"]
        signals = item["recognitionSignals"]
        if not isinstance(steps, list) or not 2 <= len(steps) <= 4 or not all(map(_nonempty, steps)):
            raise EditorialGeneratorError("Generated thinking steps are incomplete.")
        if not isinstance(signals, dict) or set(signals) != {"bullets"} or not isinstance(signals["bullets"], list) or not 2 <= len(signals["bullets"]) <= 3 or not all(map(_nonempty, signals["bullets"])):
            raise EditorialGeneratorError("Generated recognition signals are incomplete.")
        approaches.append({
            "id": key, "name": item["name"].strip(), "pattern": item["pattern"].strip(),
            "summary": (f"{item['summary'].strip()} Time: {item['timeComplexityExplanation'].strip()} "
                        f"Space: {item['spaceComplexityExplanation'].strip()}"),
            "isPrimary": order == 1, "displayOrder": order,
            "thinkingSteps": [step.strip() for step in steps],
            "recognitionSignals": {"quote": None,
                                   "bullets": [bullet.strip() for bullet in signals["bullets"]]},
        })
    spec = {field: copy.deepcopy(source["spec"][field]) for field in FACT_FIELDS}
    spec["summary"] = editorial["summary"].strip()
    spec["description"] = editorial["description"].strip()
    provenance = copy.deepcopy(source["provenance"])
    provenance["reviewed"] = False  # Importer rejects drafts until editorial review.
    provenance["permissionNote"] += " Generated editorial is unreviewed; source permission and originality must be checked before import."
    return {"slug": source["slug"], "spec": spec, "approaches": approaches,
            "related": copy.deepcopy(source["related"]), "provenance": provenance}


def validate_draft(draft):
    """Exercise the existing importer validation in memory without approving the draft."""
    checked = copy.deepcopy(draft)
    checked["provenance"]["reviewed"] = True
    with tempfile.TemporaryDirectory(prefix="leetcoach-draft-check-") as directory:
        (Path(directory) / f"{draft['slug']}.json").write_text(json.dumps(checked), encoding="utf-8")
        try:
            load_catalog(Path(directory))
        except CatalogImportError as exc:
            raise EditorialGeneratorError(f"Importer rejected generated draft: {exc}") from exc


def _write_json(path, value):
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def _write_report(path, outcomes):
    counts = {status: sum(item["status"] == status for item in outcomes)
              for status in ("generated", "skipped", "stale", "failed")}
    totals = _all_token_totals(path.parent) or {}
    lines = ["# Editorial draft run", "", f"Model: `{MODEL}`; reasoning: `{EFFORT}`; authentication: local ChatGPT Codex CLI.",
             f"This run: generated {counts['generated']}; skipped {counts['skipped']}; stale {counts['stale']}; failed {counts['failed']}.",
             f"Cumulative recorded Codex tokens: input {totals.get('input_tokens', '—')}, "
             f"output {totals.get('output_tokens', '—')}; cached input {totals.get('cached_input_tokens', '—')}, "
             f"reasoning output {totals.get('reasoning_output_tokens', '—')} "
             "(all checkpointed attempts with available usage).", "",
             "| Problem | Status | Cumulative input tokens | Cumulative output tokens | Note |",
             "| --- | --- | ---: | ---: | --- |"]
    for item in outcomes:
        usage = item.get("usage") or {}
        lines.append(f"| {item['slug']} | {item['status']} | {usage.get('input_tokens', '—')} | "
                     f"{usage.get('output_tokens', '—')} | {item.get('note', '')} |")
    lines.extend(["", "Drafts have `provenance.reviewed: false`; a human must review and explicitly approve them before importer validation and apply.", ""])
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text("\n".join(lines), encoding="utf-8")
    temporary.replace(path)


def generate_batch(input_dir: Path, output_dir: Path, *, slugs=None, limit=None,
                   cli_check=check_codex_cli, generate=run_codex):
    input_dir = input_dir.resolve()
    output_dir = output_dir.resolve()
    if not input_dir.is_dir():
        raise EditorialGeneratorError("Input fact directory does not exist.")
    if output_dir == input_dir or input_dir in output_dir.parents:
        raise EditorialGeneratorError("Draft output must be outside the reviewed input directory.")
    files = sorted(input_dir.glob("*.json"))
    if slugs:
        wanted = set(slugs)
        files = [path for path in files if path.stem in wanted]
        missing = wanted - {path.stem for path in files}
        if missing:
            raise EditorialGeneratorError(f"Requested problem facts are missing: {', '.join(sorted(missing))}")
    if limit is not None:
        files = files[:limit]
    if not files:
        raise EditorialGeneratorError("No reviewed JSON facts selected.")
    output_dir.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_report(output_dir)
    outcomes = []
    pending = [path for path in files if not (output_dir / path.name).exists()]
    if pending:
        cli_check()  # No model call is made if ChatGPT auth or exact model is unavailable.
    for path in files:
        target = output_dir / path.name
        checkpoint_path = _checkpoint_path(output_dir, path.stem)
        try:
            source, task_facts = _load_fact_file(path)
            fingerprint = _fingerprint(source)
            checkpoint = _read_checkpoint(checkpoint_path)
        except EditorialGeneratorError as exc:
            outcomes.append({"slug": path.stem, "status": "failed", "note": str(exc).replace("|", "/")})
            _write_report(output_dir / "report.md", outcomes)
            continue
        if target.exists():
            recorded = checkpoint["draftInputFingerprint"]
            if recorded != fingerprint:
                note = ("draft has no input fingerprint; preserve and review it manually"
                        if recorded is None else
                        "reviewed input changed; old draft preserved; move it before regenerating")
                outcomes.append({"slug": path.stem, "status": "stale", "usage": _token_totals(checkpoint["attempts"]),
                                 "note": note})
            else:
                try:
                    existing = json.loads(target.read_text(encoding="utf-8"))
                    if existing.get("slug") != path.stem or existing.get("provenance", {}).get("reviewed") is not False:
                        raise ValueError("not an unreviewed draft")
                    if existing["spec"]["summary"].strip().casefold().rstrip(".") == existing["spec"]["title"].strip().casefold():
                        raise ValueError("title-only summary")
                    validate_draft(existing)
                    outcomes.append({"slug": path.stem, "status": "skipped",
                                     "usage": _token_totals(checkpoint["attempts"]),
                                     "note": "matching input fingerprint"})
                except (OSError, UnicodeError, ValueError, AttributeError, KeyError, EditorialGeneratorError):
                    outcomes.append({"slug": path.stem, "status": "failed", "usage": _token_totals(checkpoint["attempts"]),
                                     "note": "existing draft is invalid; review it manually"})
        else:
            usage = None
            try:
                editorial, usage = generate(source, task_facts)
                draft = assemble_draft(source, editorial)
                validate_draft(draft)
                _write_json(target, draft)
                checkpoint = _record_attempt(checkpoint_path, checkpoint, fingerprint, "generated", usage)
                outcomes.append({"slug": path.stem, "status": "generated",
                                 "usage": _token_totals(checkpoint["attempts"])})
            except EditorialGeneratorError as exc:
                checkpoint = _record_attempt(checkpoint_path, checkpoint, fingerprint,
                                             "failed", usage if usage is not None else exc.usage)
                outcomes.append({"slug": path.stem, "status": "failed",
                                 "usage": _token_totals(checkpoint["attempts"]),
                                 "note": str(exc).replace("|", "/")})
        _write_report(output_dir / "report.md", outcomes)  # Per-problem checkpoint.
    return outcomes


def main(argv=None):
    parser = argparse.ArgumentParser(description="Draft editorial JSON using locally signed-in Codex CLI.")
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--slug", action="append", dest="slugs", help="Select one slug (repeatable).")
    parser.add_argument("--limit", type=int, help="Process at most this many sorted inputs.")
    args = parser.parse_args(argv)
    if args.limit is not None and args.limit < 1:
        parser.error("--limit must be positive")
    try:
        outcomes = generate_batch(args.input_dir, args.output_dir, slugs=args.slugs, limit=args.limit)
    except EditorialGeneratorError as exc:
        parser.exit(1, f"Editorial generation stopped: {exc}\n")
    print(f"Generated {sum(item['status'] == 'generated' for item in outcomes)}; "
          f"skipped {sum(item['status'] == 'skipped' for item in outcomes)}; "
          f"stale {sum(item['status'] == 'stale' for item in outcomes)}; "
          f"failed {sum(item['status'] == 'failed' for item in outcomes)}. Report: {args.output_dir / 'report.md'}")
    return int(any(item["status"] in {"stale", "failed"} for item in outcomes))


if __name__ == "__main__":
    raise SystemExit(main())
