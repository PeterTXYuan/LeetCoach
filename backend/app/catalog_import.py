"""Import reviewed per-problem JSON into the existing SQLite catalog.

Run migrations and ``python -m app.seed`` first. This command never fetches
problem content, and it never deletes a Problem row for an absent JSON file.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database import engine
from app.models import Problem
from app.seed import seed_data
from app.stable_data import CURATED_PROBLEMS, CURATED_PROBLEM_SPECS, validate_curated_data


class CatalogImportError(ValueError):
    pass


def _utc_time(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value)
    except (TypeError, ValueError) as exc:
        raise CatalogImportError("Review timestamps must be ISO 8601 dates with a timezone.") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise CatalogImportError("Review timestamps must include a timezone.")
    return result.astimezone(timezone.utc)


def _reviewed_provenance(slug: str, spec: dict, provenance: dict) -> None:
    if not isinstance(provenance, dict) or provenance.get("reviewed") is not True:
        raise CatalogImportError(f"{slug}: provenance must be explicitly reviewed.")
    for field in ("reviewedBy", "sourceUrl", "permissionNote"):
        if not isinstance(provenance.get(field), str) or not provenance[field].strip():
            raise CatalogImportError(f"{slug}: provenance.{field} is required.")
    if provenance.get("collectionMethod") not in {"manual_review", "authorized_export"}:
        raise CatalogImportError(f"{slug}: use a reviewed manual or authorized source.")
    if provenance.get("reuseBasis") not in {"original_editorial", "authorized_reuse"}:
        raise CatalogImportError(f"{slug}: record the content reuse basis.")
    if not provenance["sourceUrl"].startswith("https://"):
        raise CatalogImportError(f"{slug}: provenance requires an HTTPS source URL.")
    if _utc_time(provenance.get("reviewedAt")) != _utc_time(spec.get("descriptionVerifiedAt")):
        raise CatalogImportError(f"{slug}: review and description verification dates differ.")


def load_catalog(directory: Path) -> dict:
    """Load and validate a batch; only JSON files present in this directory are in scope."""
    if not directory.is_dir():
        raise CatalogImportError(f"Input directory does not exist: {directory}")
    files = sorted(directory.glob("*.json"))
    if not files:
        raise CatalogImportError("No problem JSON files found; nothing will be changed.")
    batch = {"problems": {}, "related": {}, "specs": {}}
    legacy_numbers = {spec["leetcodeNumber"] for spec in CURATED_PROBLEM_SPECS.values()}
    numbers = set()
    for path in files:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise CatalogImportError(f"{path.name}: cannot read valid JSON.") from exc
        if not isinstance(record, dict) or set(record) != {"slug", "spec", "approaches", "related", "provenance"}:
            raise CatalogImportError(f"{path.name}: expected slug, spec, approaches, related, provenance.")
        slug, spec = record["slug"], record["spec"]
        if not isinstance(slug, str) or path.stem != slug:
            raise CatalogImportError(f"{path.name}: filename must match the problem slug.")
        if slug in CURATED_PROBLEMS or slug in batch["problems"]:
            raise CatalogImportError(f"{slug}: collides with an existing or repeated catalog slug.")
        if not isinstance(spec, dict) or not isinstance(record["approaches"], list) or not isinstance(record["related"], dict):
            raise CatalogImportError(f"{slug}: spec, approaches, or related has the wrong shape.")
        templates = spec.get("submissionTemplates")
        if not isinstance(templates, dict) or set(templates) != {"python", "java", "javascript", "cpp"}:
            raise CatalogImportError(f"{slug}: all four language templates are required.")
        if set(record["related"]) != {"easier", "similar", "harder"}:
            raise CatalogImportError(f"{slug}: related must contain easier, similar, and harder lists.")
        _reviewed_provenance(slug, spec, record["provenance"])
        number = spec.get("leetcodeNumber")
        if type(number) is not int or number <= 0:
            raise CatalogImportError(f"{slug}: a positive LeetCode number is required.")
        if number in legacy_numbers or number in numbers:
            raise CatalogImportError(f"{slug}: repeated LeetCode number.")
        numbers.add(number)
        batch["problems"][slug] = {"slug": slug, "approaches": record["approaches"]}
        batch["related"][slug] = record["related"]
        batch["specs"][slug] = spec
    try:
        validate_curated_data(batch["problems"], batch["related"], batch["specs"])
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise CatalogImportError(f"Catalog validation failed: {exc}") from exc
    known = {slug: (spec["title"], spec["difficulty"]) for slug, spec in CURATED_PROBLEM_SPECS.items()}
    known.update({slug: (spec["title"], spec["difficulty"]) for slug, spec in batch["specs"].items()})
    for slug, groups in batch["related"].items():
        for cards in groups.values():
            if not isinstance(cards, list):
                raise CatalogImportError(f"{slug}: related categories must be lists.")
            for card in cards:
                if not isinstance(card, dict) or not all(isinstance(card.get(key), str) and card[key].strip()
                                                          for key in ("slug", "title", "difficulty")):
                    raise CatalogImportError(f"{slug}: related cards need a slug, title, and difficulty.")
                if card["difficulty"] not in {"Easy", "Medium", "Hard"}:
                    raise CatalogImportError(f"{slug}: related card has invalid difficulty.")
                if card["slug"] in known and (card["title"], card["difficulty"]) != known[card["slug"]]:
                    raise CatalogImportError(f"{slug}: related card disagrees with the supported catalog.")
    return batch


def _matches(problem: Problem, data: dict, spec: dict, related: dict) -> bool:
    scalar_fields = {
        "title": "title", "difficulty": "difficulty", "summary": "summary",
        "leetcode_number": "leetcodeNumber", "description": "description",
        "description_source_url": "descriptionSourceUrl",
        "description_source_type": "descriptionSourceType", "time_limit_ms": "timeLimitMs",
        "memory_limit_mb": "memoryLimitMb", "time_complexity_instruction": "timeComplexityInstruction",
        "space_complexity_instruction": "spaceComplexityInstruction",
    }
    if any(getattr(problem, field) != spec[key] for field, key in scalar_fields.items()):
        return False
    verified = problem.description_verified_at
    if verified is None or verified.replace(tzinfo=verified.tzinfo or timezone.utc).astimezone(timezone.utc) != _utc_time(spec["descriptionVerifiedAt"]):
        return False
    if [item.text for item in problem.constraints] != spec["constraints"]:
        return False
    examples = [{"input": item.input_text, "output": item.output_text, "explanation": item.explanation}
                for item in problem.examples]
    expected_examples = [{"input": item["input"], "output": item["output"],
                          "explanation": item.get("explanation")} for item in spec["examples"]]
    if examples != expected_examples:
        return False
    if {item.language: item.code for item in problem.submission_templates} != spec["submissionTemplates"]:
        return False
    if len(problem.approaches) != len(data["approaches"]):
        return False
    for actual, expected in zip(problem.approaches, data["approaches"]):
        if (actual.approach_key != expected["id"] or actual.name != expected["name"]
                or actual.pattern != expected["pattern"] or actual.summary != expected["summary"]
                or actual.is_primary != expected["isPrimary"] or actual.display_order != expected["displayOrder"]
                or actual.thinking_steps != expected["thinkingSteps"]):
            return False
        signals = actual.recognition_signals
        source = expected.get("recognitionSignals")
        if (signals is None) != (source is None):
            return False
        if signals is not None and (signals.quote != source.get("quote")
                                    or [item.text for item in signals.bullets] != source["bullets"]):
            return False
    expected_related = {(card["slug"], category, order, card["title"], card["difficulty"], card.get("reason"))
                        for category, cards in related.items() for order, card in enumerate(cards, 1)}
    actual_related = {(card.slug, card.category, card.display_order, card.title, card.difficulty, card.reason)
                      for card in problem.related_problems}
    return actual_related == expected_related


def plan_catalog(session: Session, batch: dict) -> dict:
    """Read-only preview of the slugs that will be inserted or exact-synced."""
    legacy_in_db = set(session.scalars(select(Problem.slug).where(Problem.slug.in_(CURATED_PROBLEMS))))
    if legacy_in_db != set(CURATED_PROBLEMS):
        raise CatalogImportError("Seed the original 40 problems before importing JSON.")
    result = {"create": [], "update": [], "unchanged": [], "deleteChildren": {}}
    for slug, data in batch["problems"].items():
        spec = batch["specs"][slug]
        owner = session.scalar(select(Problem).where(Problem.leetcode_number == spec["leetcodeNumber"]))
        if owner is not None and owner.slug != slug:
            raise CatalogImportError(f"{slug}: LeetCode number already belongs to another database row.")
        current = session.scalar(select(Problem).where(Problem.slug == slug))
        if current is not None and current.leetcode_number != spec["leetcodeNumber"]:
            raise CatalogImportError(f"{slug}: existing database slug has a different LeetCode number.")
        status = ("create" if current is None else "unchanged" if _matches(
            current, data, spec, batch["related"][slug]) else "update")
        result[status].append(slug)
        if current is not None:
            removed_approaches = sorted({item.approach_key for item in current.approaches}
                                        - {item["id"] for item in data["approaches"]})
            removed_related = sorted({item.slug for item in current.related_problems}
                                     - {card["slug"] for cards in batch["related"][slug].values()
                                        for card in cards})
            removed_constraints = sorted(item.display_order for item in current.constraints
                                         if item.display_order > len(spec["constraints"]))
            removed_examples = sorted(item.display_order for item in current.examples
                                      if item.display_order > len(spec["examples"]))
            removed_templates = sorted({item.language for item in current.submission_templates}
                                       - set(spec["submissionTemplates"]))
            source_approaches = {item["id"]: item for item in data["approaches"]}
            removed_bullets = {
                item.approach_key: sorted(bullet.display_order for bullet in item.recognition_signals.bullets
                                          if bullet.display_order > len(source_approaches[item.approach_key]
                                                                         ["recognitionSignals"]["bullets"]))
                for item in current.approaches
                if item.approach_key in source_approaches and item.recognition_signals is not None
            }
            removed_bullets = {key: positions for key, positions in removed_bullets.items() if positions}
            if (removed_approaches or removed_related or removed_constraints or removed_examples
                    or removed_templates or removed_bullets):
                result["deleteChildren"][slug] = {
                    "approaches": removed_approaches, "related": removed_related,
                    "constraints": removed_constraints, "examples": removed_examples,
                    "templates": removed_templates, "recognitionBullets": removed_bullets,
                }
    return result


def apply_catalog(batch: dict, bind=None) -> dict:
    """Preflight and import atomically; the legacy 40 are never passed to seed_data."""
    try:
        with Session(bind if bind is not None else engine) as session, session.begin():
            plan = plan_catalog(session, batch)
            seed_data(session, batch["problems"], batch["related"], batch["specs"])
    except SQLAlchemyError as exc:
        raise CatalogImportError("Database rejected the import; all changes were rolled back.") from exc
    return plan


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate or import reviewed local problem JSON files.")
    parser.add_argument("action", choices=("validate", "plan", "apply"))
    parser.add_argument("--input-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        batch = load_catalog(args.input_dir)
        if args.action == "validate":
            print(f"Validated {len(batch['problems'])} reviewed problem JSON files.")
        elif args.action == "plan":
            with Session(engine) as session:
                print(json.dumps(plan_catalog(session, batch), indent=2))
        else:
            print(json.dumps(apply_catalog(batch), indent=2))
    except SQLAlchemyError:
        parser.exit(1, "Catalog import stopped: database unavailable; run migrations and app.seed first.\n")
    except CatalogImportError as exc:
        parser.exit(1, f"Catalog import stopped: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
